"""
Point d'entree FastAPI pour ShotURL v3.0.
API optimisee pour 4GB RAM avec Playwright.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
import uvicorn
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from api.config import settings, logger
from api.routes import router
from api.browser import browser_pool
from api.session import session_manager

# Rate limiter initialization
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/hour", "30/minute"],
    headers_enabled=True
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gere le cycle de vie de l'application.
    Startup: Initialise le pool de navigateurs et demarre le cleanup.
    Shutdown: Nettoie toutes les ressources.
    """
    # ========== STARTUP ==========
    logger.info(f"[START] Demarrage de ShotURL v{settings.VERSION}")
    logger.info(f"Configuration: {settings.MAX_CONCURRENT_BROWSERS} navigateurs max, "
                f"{settings.MAX_MEMORY_MB}MB RAM max")

    try:
        # Initialiser le pool de navigateurs
        await browser_pool.initialize()

        # Demarrer le cleanup automatique des sessions
        session_manager.start_cleanup()

        logger.info("[OK] Application demarree avec succes!")

    except Exception as e:
        logger.error(f"[ERROR] Erreur lors du demarrage: {e}")
        raise

    yield  # L'application tourne ici

    # ========== SHUTDOWN ==========
    logger.info("[STOP] Arret de l'application...")

    try:
        # Arreter le cleanup
        await session_manager.stop_cleanup()

        # Nettoyer le pool de navigateurs
        await browser_pool.cleanup()

        logger.info("[OK] Application arretee proprement")

    except Exception as e:
        logger.error(f"[WARNING]  Erreur lors de l'arret: {e}")


# Creer l'application FastAPI (desactiver docs par defaut pour customisation)
app = FastAPI(
    title="ShotURL API",
    description=(
        "API securisee de capture et analyse de sites web potentiellement malveillants. "
        "Optimisee pour 4GB RAM avec Playwright."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url=None,  # Desactive pour customisation
    redoc_url=None,  # Desactive pour customisation
    openapi_url="/api/openapi.json"
)

# Custom rate limit error handler avec message personnalise
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handler personnalise pour les erreurs de rate limiting."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": "Limite maximale de requetes atteinte. Veuillez reessayer plus tard.",
            "detail": "Too many requests. Please try again later.",
            "retry_after": "60 seconds"
        },
        headers={"Retry-After": "60"}
    )

# Ajouter le rate limiter a l'app
app.state.limiter = limiter

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # A restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclure les routes API
app.include_router(router, prefix="/api", tags=["API"])


# Routes de documentation avec rate limiting et sans "Try it out"
@app.get("/api/docs", include_in_schema=False)
@limiter.limit("30/minute")
async def get_docs(request: Request):
    """Swagger UI - avec Try it out desactive."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>ShotURL API - Documentation</title>
        <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
        <style>
            /* Cacher les boutons Try it out et Execute */
            .try-out, .execute-wrapper, .btn.try-out__btn, .opblock-control__btn {
                display: none !important;
            }
            /* Cacher aussi la section Parameters pour empecher l'edition */
            .opblock-body .parameters {
                pointer-events: none;
                opacity: 0.6;
            }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
        <script>
            window.onload = function() {
                window.ui = SwaggerUIBundle({
                    url: '/api/openapi.json',
                    dom_id: '#swagger-ui',
                    deepLinking: true,
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.SwaggerUIStandalonePreset
                    ],
                    plugins: [
                        SwaggerUIBundle.plugins.DownloadUrl
                    ],
                    supportedSubmitMethods: [], // Desactiver tous les boutons submit
                    docExpansion: 'list',
                    defaultModelsExpandDepth: 1,
                    defaultModelExpandDepth: 1
                });
            }
        </script>
    </body>
    </html>
    """)


@app.get("/api/redoc", include_in_schema=False)
@limiter.limit("30/minute")
async def get_redoc(request: Request):
    """ReDoc UI - documentation en lecture seule."""
    return get_redoc_html(
        openapi_url="/api/openapi.json",
        title=f"{app.title} - Documentation"
    )


# Servir les fichiers statiques du frontend (si build existe)
# IMPORTANT: Mount assets BEFORE mounting root to avoid conflicts
if settings.STATIC_DIR.exists():
    try:
        # Mount assets directory first (JS/CSS bundles)
        assets_dir = settings.STATIC_DIR / "assets"
        if assets_dir.exists():
            app.mount(
                "/assets",
                StaticFiles(directory=str(assets_dir)),
                name="assets"
            )
            logger.info(f"[+] Assets montes depuis {assets_dir}")

        # Mount root directory with html=True for SPA routing
        # This will serve index.html for any unmatched routes
        app.mount(
            "/",
            StaticFiles(directory=str(settings.STATIC_DIR), html=True),
            name="static"
        )
        logger.info(f"[+] Fichiers statiques montes depuis {settings.STATIC_DIR}")
    except Exception as e:
        logger.warning(f"[WARNING]  Impossible de monter les fichiers statiques: {e}")
else:
    # If frontend not built, provide API info at root
    @app.get("/", include_in_schema=False)
    async def root():
        """Fallback when frontend is not built."""
        return {
            "app": "ShotURL",
            "version": settings.VERSION,
            "status": "running",
            "api_docs": "/api/docs",
            "health": "/api/health",
            "message": "Frontend not built yet. Visit /api/docs for API documentation."
        }


# Point d'entree pour lancement direct
if __name__ == "__main__":
    logger.info(f"Lancement du serveur sur {settings.HOST}:{settings.PORT}")

    uvicorn.run(
        "api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
