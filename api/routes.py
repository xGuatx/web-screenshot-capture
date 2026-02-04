"""Routes API FastAPI pour ShotURL v3.0."""

from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.models import CaptureRequest, CaptureResponse, HealthResponse, ErrorResponse
from api.security import (
    is_valid_url,
    is_reachable,
    extract_safelink_url,
    probe_url_scheme,
    sanitize_selector,
    parse_device_dimensions
)
from api.capture import capturer
from api.session import session_manager
from api.browser import browser_pool
from api.config import settings, logger
from api.cache import get_cached_capture, set_cached_capture, get_cache_stats

# Creer le router
router = APIRouter()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@router.post("/capture", response_model=CaptureResponse, tags=["Capture"])
@limiter.limit("10/minute")
async def capture_screenshot(request: Request, capture_req: CaptureRequest):
    """
    Capture complete d'un site web: screenshot + reseau + DOM.

    - **url**: URL du site a analyser
    - **full_page**: Capture complete de la page (defaut: False)
    - **device**: Type d'appareil (desktop, tablet, phone)
    - **width/height**: Dimensions personnalisees (optionnel)
    - **delay**: Delai avant capture en secondes (0-30)
    - **click**: Selecteur CSS d'element a cliquer avant capture
    - **hide**: Selecteurs CSS d'elements a masquer (separes par virgule)
    - **grab_html**: Capturer le HTML source (defaut: False)

    Returns:
        Objet avec screenshot (base64), logs reseau, elements DOM
    """
    session_id = None

    try:
        # Verifier la limite de sessions concurrentes
        active_sessions = len(session_manager.sessions)
        if active_sessions >= settings.MAX_CONCURRENT_SESSIONS:
            logger.warning(
                f"Too many concurrent sessions: {active_sessions}/{settings.MAX_CONCURRENT_SESSIONS}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many concurrent requests ({active_sessions}). Please wait and try again."
            )

        # Creer une session
        session_id = session_manager.create_session()

        # Extraire URL originale si SafeLink
        url = extract_safelink_url(capture_req.url)

        # Detecter le meilleur protocole (HTTP vs HTTPS)
        url = probe_url_scheme(url)
        logger.debug(f"URL apres detection protocole: {url}")

        # Validation securite
        if not is_valid_url(url):
            logger.warning(f"URL invalide ou dangereuse: {url}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL invalide, dangereuse ou non autorisee (IP privee, domaine local, etc.)"
            )

        if not is_reachable(url):
            logger.warning(f"URL non accessible: {url}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="URL non accessible (DNS echoue ou timeout)"
            )

        # Valider dimensions
        width, height = parse_device_dimensions(
            device=capture_req.device,
            width=capture_req.width,
            height=capture_req.height
        )

        # Valider selecteurs
        click_selector = sanitize_selector(capture_req.click) if capture_req.click else None
        hide_selectors = capture_req.hide if capture_req.hide else None

        if capture_req.hide:
            # Valider chaque selecteur individuellement
            for sel in capture_req.hide.split(','):
                if not sanitize_selector(sel.strip()):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Selecteur CSS invalide: {sel}"
                    )

        # Log de la requete
        logger.info(f"[TARGET] Capture demandee: {url} (session: {session_id[:8]}...)")

        # Verifier le cache Redis (si active)
        cache_options = {
            "device": capture_req.device,
            "full_page": capture_req.full_page,
            "delay": capture_req.delay,
            "grab_html": capture_req.grab_html,
        }

        cached_result = await get_cached_capture(url, cache_options)
        if cached_result:
            logger.info(f"[CACHE HIT] Serving cached capture for {url}")
            await session_manager.cleanup_session(session_id)
            return cached_result

        # Capture
        result = await capturer.capture_all(
            url=url,
            full_page=capture_req.full_page,
            width=width,
            height=height,
            delay=capture_req.delay,
            click_selector=click_selector,
            hide_selectors=hide_selectors,
            grab_html=capture_req.grab_html
        )

        # Ajouter le session_id
        result["session_id"] = session_id

        # Mettre en cache si active
        await set_cached_capture(url, cache_options, result)

        logger.info(f"[OK] Capture reussie: {url} (session: {session_id[:8]}...)")

        return result

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"[ERROR] Erreur capture: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la capture: {str(e)}"
        )

    finally:
        # Cleanup session apres capture
        if session_id:
            await session_manager.cleanup_session(session_id)


@router.get("/health", response_model=HealthResponse, tags=["Admin"])
@limiter.limit("30/minute")
async def health_check(request: Request):
    """
    Health check de l'application.

    Retourne:
    - Statut general
    - Nombre de sessions actives
    - Utilisation memoire
    - Statistiques du pool de navigateurs
    """
    try:
        stats = session_manager.get_stats()
        browser_stats = await browser_pool.get_stats()
        cache_stats = get_cache_stats()

        response = {
            "status": "healthy",
            "version": settings.VERSION,
            "active_sessions": stats["active_sessions"],
            "active_contexts": browser_stats["active_contexts"],
            "memory_percent": stats["memory_percent"],
            "memory_used_mb": stats["memory_used_mb"],
            "memory_available_mb": stats["memory_available_mb"],
            "browser_pool": browser_stats,
            "cache": cache_stats
        }

        return response

    except Exception as e:
        logger.error(f"Erreur health check: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "error": str(e)}
        )


@router.get("/sessions", tags=["Admin"])
@limiter.limit("20/minute")
async def list_sessions(request: Request):
    """
    Liste toutes les sessions actives.

    Returns:
        Dict des sessions avec leurs informations
    """
    try:
        sessions = session_manager.get_all_sessions()
        return {
            "count": len(sessions),
            "sessions": sessions
        }

    except Exception as e:
        logger.error(f"Erreur list sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/sessions/{session_id}/stop", tags=["Admin"])
@limiter.limit("20/minute")
async def stop_session(request: Request, session_id: str):
    """
    Arrete et nettoie une session specifique.

    Args:
        session_id: ID de la session a arreter

    Returns:
        Message de confirmation
    """
    try:
        session = await session_manager.get_session(session_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} non trouvee"
            )

        await session_manager.cleanup_session(session_id)

        logger.info(f"Session arretee manuellement: {session_id}")

        return {
            "message": f"Session {session_id} arretee avec succes"
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Erreur stop session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/stats", tags=["Admin"])
@limiter.limit("20/minute")
async def get_stats(request: Request):
    """
    Recupere les statistiques detaillees de l'application.

    Returns:
        Stats completes (sessions, memoire, navigateurs)
    """
    try:
        session_stats = session_manager.get_stats()
        browser_stats = await browser_pool.get_stats()

        return {
            "sessions": session_stats,
            "browser_pool": browser_stats,
            "config": {
                "max_concurrent_browsers": settings.MAX_CONCURRENT_BROWSERS,
                "max_concurrent_sessions": settings.MAX_CONCURRENT_SESSIONS,
                "max_memory_mb": settings.MAX_MEMORY_MB,
                "browser_timeout": settings.BROWSER_TIMEOUT,
                "cleanup_interval": settings.CLEANUP_INTERVAL
            }
        }

    except Exception as e:
        logger.error(f"Erreur get stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
