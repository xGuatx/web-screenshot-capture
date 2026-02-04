"""Cache Redis optionnel pour les captures."""

import hashlib
import json
from typing import Optional, Dict
from api.config import settings, logger

# Import conditionnel de Redis
redis_client = None
if settings.REDIS_ENABLED:
    try:
        import redis
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=False,  # On stocke du binaire (screenshots)
            socket_connect_timeout=2,
            socket_timeout=2
        )
        # Test connection
        redis_client.ping()
        logger.info(f"[+] Redis cache active: {settings.REDIS_HOST}:{settings.REDIS_PORT} (TTL: {settings.REDIS_CACHE_TTL}s)")
    except Exception as e:
        logger.warning(f"[!] Redis active mais connexion echouee: {e}")
        logger.warning("[!] Fonctionnement sans cache")
        redis_client = None
else:
    logger.info("[+] Redis cache desactive (REDIS_ENABLED=false)")


def _generate_cache_key(url: str, options: Dict) -> str:
    """
    Genere une cle de cache unique basee sur l'URL et les options.

    Args:
        url: URL capturee
        options: Options de capture (device, full_page, delay, etc.)

    Returns:
        Cle de cache (hash SHA256)
    """
    # Construire une chaine unique avec URL + options pertinentes
    key_data = {
        "url": url,
        "device": options.get("device", "desktop"),
        "full_page": options.get("full_page", False),
        "delay": options.get("delay", 0),
        "grab_html": options.get("grab_html", False),
    }

    key_string = json.dumps(key_data, sort_keys=True)
    cache_key = f"shoturl:capture:{hashlib.sha256(key_string.encode()).hexdigest()}"

    return cache_key


async def get_cached_capture(url: str, options: Dict) -> Optional[Dict]:
    """
    Recupere une capture depuis le cache Redis.

    Args:
        url: URL a chercher
        options: Options de capture

    Returns:
        Dict avec capture ou None si pas en cache
    """
    if not redis_client:
        return None

    try:
        cache_key = _generate_cache_key(url, options)
        cached_data = redis_client.get(cache_key)

        if cached_data:
            logger.info(f"[CACHE HIT] {url}")
            # Deserialize
            result = json.loads(cached_data)
            return result
        else:
            logger.debug(f"[CACHE MISS] {url}")
            return None

    except Exception as e:
        logger.warning(f"[!] Erreur lecture cache: {e}")
        return None


async def set_cached_capture(url: str, options: Dict, capture_data: Dict) -> bool:
    """
    Stocke une capture dans le cache Redis.

    IMPORTANT: Ne cache que si conditions sont remplies pour eviter
    de servir des captures incompletes ou obsoletes.

    Args:
        url: URL capturee
        options: Options de capture
        capture_data: Donnees a cacher

    Returns:
        True si stocke avec succes, False sinon
    """
    if not redis_client:
        return False

    try:
        # REGLES DE CACHE INTELLIGENT (si activees)
        if settings.REDIS_SMART_CACHE:
            # Regle 1 : Ne pas cacher si delay=0 (page possiblement incomplete)
            if options.get("delay", 0) == 0:
                logger.debug(f"[CACHE SKIP] {url} - delay=0 (page possiblement incomplete)")
                return False

            # Regle 2 : Ne pas cacher les domaines dynamiques (Twitch, YouTube, etc.)
            dynamic_domains = ["twitch.tv", "youtube.com", "instagram.com", "twitter.com", "facebook.com"]
            if any(domain in url.lower() for domain in dynamic_domains):
                logger.debug(f"[CACHE SKIP] {url} - domaine dynamique")
                return False

            # Regle 3 : Verifier que la capture a suffisamment de contenu
            network_logs = capture_data.get("network_logs", [])
            if len(network_logs) < 5:  # Trop peu de requetes = page incomplete
                logger.debug(f"[CACHE SKIP] {url} - trop peu de requetes reseau ({len(network_logs)})")
                return False

        # Si toutes les conditions OK  cache
        cache_key = _generate_cache_key(url, options)

        # Serialize en JSON
        serialized = json.dumps(capture_data)

        # Stocker avec TTL
        redis_client.setex(
            cache_key,
            settings.REDIS_CACHE_TTL,
            serialized
        )

        logger.info(f"[CACHE SET] {url} (TTL: {settings.REDIS_CACHE_TTL}s)")
        return True

    except Exception as e:
        logger.warning(f"[!] Erreur ecriture cache: {e}")
        return False


async def invalidate_cache(url: str, options: Dict) -> bool:
    """
    Invalide une entree du cache.

    Args:
        url: URL a invalider
        options: Options de capture

    Returns:
        True si invalide, False sinon
    """
    if not redis_client:
        return False

    try:
        cache_key = _generate_cache_key(url, options)
        redis_client.delete(cache_key)
        logger.debug(f"[CACHE INVALIDATE] {url}")
        return True
    except Exception as e:
        logger.warning(f"[!] Erreur invalidation cache: {e}")
        return False


def get_cache_stats() -> Dict:
    """
    Recupere les statistiques du cache.

    Returns:
        Dict avec stats ou empty dict si Redis desactive
    """
    if not redis_client:
        return {
            "enabled": False,
            "status": "disabled"
        }

    try:
        info = redis_client.info("stats")
        keyspace = redis_client.info("keyspace")

        # Compter les cles shoturl
        shoturl_keys = 0
        try:
            cursor = 0
            while True:
                cursor, keys = redis_client.scan(cursor, match="shoturl:capture:*", count=100)
                shoturl_keys += len(keys)
                if cursor == 0:
                    break
        except:
            shoturl_keys = -1

        return {
            "enabled": True,
            "status": "connected",
            "host": f"{settings.REDIS_HOST}:{settings.REDIS_PORT}",
            "ttl_seconds": settings.REDIS_CACHE_TTL,
            "cached_captures": shoturl_keys,
            "total_connections": info.get("total_connections_received", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
        }
    except Exception as e:
        return {
            "enabled": True,
            "status": "error",
            "error": str(e)
        }
