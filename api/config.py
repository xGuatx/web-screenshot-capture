"""Configuration centralisee pour ShotURL v3.0 avec optimisation RAM 4GB."""

import os
import logging
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration de l'application avec variables d'environnement."""

    # App info
    APP_NAME: str = "ShotURL"
    VERSION: str = "3.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"

    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Securite
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-this-in-production")
    ALLOW_LOCAL_URLS: bool = os.getenv("ALLOW_LOCAL_URLS", "False").lower() == "true"
    MAX_SELECTOR_LENGTH: int = 200

    # API Documentation Security
    DOCS_USERNAME: str = os.getenv("DOCS_USERNAME", "admin")
    DOCS_PASSWORD: str = os.getenv("DOCS_PASSWORD", "shoturl2026")

    # Limites strictes pour 4GB RAM
    MAX_CONCURRENT_BROWSERS: int = int(os.getenv("MAX_CONCURRENT_BROWSERS", "4"))  # ~1GB pour navigateurs
    MAX_CONCURRENT_SESSIONS: int = int(os.getenv("MAX_CONCURRENT_SESSIONS", "10"))
    MAX_MEMORY_MB: int = int(os.getenv("MAX_MEMORY_MB", "3500"))  # Alerte a 3.5GB

    # Timeouts (en secondes)
    BROWSER_TIMEOUT: int = int(os.getenv("BROWSER_TIMEOUT", "20"))
    PAGE_LOAD_TIMEOUT: int = int(os.getenv("PAGE_LOAD_TIMEOUT", "10"))
    SESSION_TIMEOUT: int = int(os.getenv("SESSION_TIMEOUT", "300"))  # 5min

    # Cleanup
    CLEANUP_INTERVAL: int = int(os.getenv("CLEANUP_INTERVAL", "30"))  # 30s

    # Redis Cache (Optional)
    REDIS_ENABLED: bool = os.getenv("REDIS_ENABLED", "False").lower() == "true"
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_CACHE_TTL: int = int(os.getenv("REDIS_CACHE_TTL", "180"))  # 3min par defaut

    # Cache intelligent (regles strictes pour eviter captures incompletes)
    REDIS_SMART_CACHE: bool = os.getenv("REDIS_SMART_CACHE", "True").lower() == "true"
    # Si false: cache toutes les captures (risque de servir du contenu incomplet)
    # Si true: skip delay=0, domaines dynamiques, pages avec peu de requetes

    # Pre-warm contexts (Performance)
    PREWARM_ENABLED: bool = os.getenv("PREWARM_ENABLED", "False").lower() == "true"
    PREWARM_COUNT: int = int(os.getenv("PREWARM_COUNT", "2"))  # Nombre de contexts chauds

    # Dimensions
    MIN_WIDTH: int = 200
    MIN_HEIGHT: int = 200
    MAX_WIDTH: int = 3840
    MAX_HEIGHT: int = 2160

    # Default dimensions par device
    DEVICE_DIMENSIONS: dict = {
        "desktop": (1920, 1080),  # Full HD pour un affichage moderne
        "tablet": (768, 1024),
        "phone": (375, 667),
    }

    # URLs/Domaines bloques
    BLOCKED_DOMAINS: List[str] = ['.local', '.lan', '.internal']
    BLOCKED_KEYWORDS: List[str] = ['localhost', '127.0.0.1', '0.0.0.0']

    # Patterns d'exclusion reseau
    NETWORK_EXCLUDE_PATTERNS: List[str] = [
        r'fonts\.gstatic\.com',
        r'data:image',
        r'fonts\.googleapis\.com',
        r'accounts\.google\.com',
        r'/css/',
        r'/themes?/',
        r'\.(svg|png|jpeg|jpg|gif|woff2|css|webp|ico)$',
        # Blocage agressif pub/analytics pour Twitch
        r'doubleclick\.net',
        r'google-analytics\.com',
        r'googletagmanager\.com',
        r'googlesyndication\.com',
        r'facebook\.net',
        r'scorecardresearch\.com',
        r'moatads\.com',
        r'adsystem\.com',
        r'amazon-adsystem\.com',
        r'advertising\.com',
        r'analytics',
        r'telemetry',
        r'tracking',
        r'/ads/',
        r'/advert'
    ]

    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    LOG_DIR: Path = BASE_DIR / "logs"
    STATIC_DIR: Path = BASE_DIR / "web" / "dist"

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    class Config:
        env_file = ".env"
        case_sensitive = True


# Instance globale
settings = Settings()

# Ensure directories exist
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)


# Setup logging
def setup_logging():
    """Configure le logging de l'application."""
    import os
    handlers = [logging.StreamHandler()]

    # Only use file logging if not in Docker or if LOG_DIR is writable
    if not os.environ.get("DOCKER_CONTAINER") and settings.LOG_DIR.exists():
        try:
            handlers.append(logging.FileHandler(settings.LOG_DIR / "app.log", encoding="utf-8"))
        except PermissionError:
            # Fallback to stdout only in Docker or when no write permission
            pass

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper()),
        format=settings.LOG_FORMAT,
        handlers=handlers
    )
    return logging.getLogger("shoturl")


logger = setup_logging()
