"""Pool de navigateurs Playwright optimise pour 4GB RAM."""

import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Playwright

from api.config import settings, logger


class BrowserPool:
    """
    Pool de navigateurs Playwright avec limite stricte pour optimiser la RAM.
    Reutilise un seul navigateur et cree des contextes isoles.
    """

    def __init__(self):
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.contexts: list[BrowserContext] = []
        self.prewarm_contexts: list[BrowserContext] = []  # Contexts pre-chauds
        self.semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_BROWSERS)
        self._lock = asyncio.Lock()
        self._prewarm_lock = asyncio.Lock()

    async def initialize(self):
        """Initialise Playwright et lance le navigateur partage."""
        try:
            logger.info("Initialisation du pool de navigateurs Playwright...")

            self.playwright = await async_playwright().start()

            # Lancer UN SEUL navigateur reutilise (economie RAM)
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-dev-shm-usage',      # Evite /dev/shm (important!)
                    '--disable-gpu',
                    '--disable-software-rasterizer',  # Pas de rendu logiciel
                    '--no-sandbox',                 # Pour Docker
                    '--disable-setuid-sandbox',
                    '--disable-web-security',       # Pour sites malveillants
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-extensions',
                    '--disable-background-networking',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-breakpad',
                    '--disable-component-extensions-with-background-pages',
                    '--disable-features=TranslateUI',
                    '--disable-ipc-flooding-protection',
                    '--disable-renderer-backgrounding',
                    '--enable-features=NetworkService,NetworkServiceInProcess',
                    '--force-color-profile=srgb',
                    '--hide-scrollbars',
                    '--metrics-recording-only',
                    '--mute-audio',
                    '--no-first-run',
                    '--disable-crash-reporter',
                    '--disable-gl-drawing-for-tests',  # Desactive OpenGL
                    # Limite memoire JS
                    '--js-flags=--max-old-space-size=512',  # 512MB heap JS
                ]
            )

            logger.info(f"[+] Pool de navigateurs initialise (max {settings.MAX_CONCURRENT_BROWSERS} contextes)")

            # Pre-warm contexts si active
            if settings.PREWARM_ENABLED:
                await self._prewarm_contexts()

        except Exception as e:
            logger.error(f"[-] Echec initialisation pool: {e}")
            raise

    async def _prewarm_contexts(self):
        """Pre-cree des contexts chauds pour reduire la latence."""
        try:
            logger.info(f"[PREWARM] Creation de {settings.PREWARM_COUNT} contexts pre-chauds...")

            for i in range(settings.PREWARM_COUNT):
                context = await self._create_context()
                async with self._prewarm_lock:
                    self.prewarm_contexts.append(context)

            logger.info(f"[+] {len(self.prewarm_contexts)} contexts pre-chauds prets")

        except Exception as e:
            logger.warning(f"[!] Erreur pre-warm contexts: {e}")

    async def _create_context(
        self,
        width: int = 1024,
        height: int = 768,
        user_agent: Optional[str] = None
    ) -> BrowserContext:
        """Cree un nouveau contexte (interne)."""
        if not self.browser:
            raise RuntimeError("Browser pool non initialise")

        context = await self.browser.new_context(
            viewport={'width': width, 'height': height},
            user_agent=user_agent or (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            ignore_https_errors=True,
            bypass_csp=True,
            java_script_enabled=True,
            accept_downloads=False,
        )

        context.set_default_timeout(60000)

        # Bloquer fonts et media
        await context.route("**/*", lambda route: (
            route.abort() if route.request.resource_type in ["font", "media"]
            else route.continue_()
        ))

        return context

    async def get_context(
        self,
        width: int = 1024,
        height: int = 768,
        user_agent: Optional[str] = None
    ) -> BrowserContext:
        """
        Obtient un contexte de navigation isole.
        Si pre-warm active, utilise un context pre-chaud et en recree un.
        Sinon, cree un nouveau context a la demande.

        Args:
            width: Largeur viewport
            height: Hauteur viewport
            user_agent: User-Agent custom (optionnel)

        Returns:
            BrowserContext Playwright
        """
        try:
            if not self.browser:
                raise RuntimeError("Browser pool non initialise. Appelez initialize() d'abord.")

            context = None

            # Essayer d'utiliser un context pre-chaud
            if settings.PREWARM_ENABLED and self.prewarm_contexts:
                async with self._prewarm_lock:
                    if self.prewarm_contexts:
                        context = self.prewarm_contexts.pop(0)
                        logger.debug(f"[PREWARM] Utilisation context pre-chaud ({len(self.prewarm_contexts)} restants)")

                # Recreer un context pre-chaud en arriere-plan (non-bloquant)
                asyncio.create_task(self._refill_prewarm())

            # Sinon creer un nouveau context
            if not context:
                context = await self._create_context(width, height, user_agent)
                logger.debug(f"Contexte cree a la demande")

            async with self._lock:
                self.contexts.append(context)

            logger.debug(f"Contextes actifs: {len(self.contexts)}/{settings.MAX_CONCURRENT_BROWSERS}")
            return context

        except Exception as e:
            logger.error(f"Erreur creation contexte: {e}")
            raise

    async def _refill_prewarm(self):
        """Recree un context pre-chaud (tache en arriere-plan)."""
        try:
            if len(self.prewarm_contexts) < settings.PREWARM_COUNT:
                new_context = await self._create_context()
                async with self._prewarm_lock:
                    self.prewarm_contexts.append(new_context)
                logger.debug(f"[PREWARM] Context recharge ({len(self.prewarm_contexts)}/{settings.PREWARM_COUNT})")
        except Exception as e:
            logger.warning(f"[!] Erreur refill prewarm: {e}")

    async def release_context(self, context: BrowserContext):
        """
        Libere un contexte de navigation.

        Args:
            context: Contexte a liberer
        """
        try:
            await context.close()
        except Exception as e:
            logger.warning(f"Erreur fermeture contexte: {e}")

        # TOUJOURS retirer le contexte de la liste, meme si close() a echoue
        try:
            async with self._lock:
                if context in self.contexts:
                    self.contexts.remove(context)
            logger.debug(f"Contexte libere ({len(self.contexts)} actifs)")
        except Exception as e:
            logger.error(f"Erreur critique lors du retrait du contexte: {e}")

    async def cleanup(self):
        """Nettoie toutes les ressources du pool."""
        try:
            logger.info("Nettoyage du pool de navigateurs...")

            # Fermer tous les contextes actifs
            for context in self.contexts.copy():
                try:
                    await context.close()
                except Exception as e:
                    logger.warning(f"Erreur fermeture contexte: {e}")

            self.contexts.clear()

            # Fermer tous les contextes pre-chauds
            for context in self.prewarm_contexts.copy():
                try:
                    await context.close()
                except Exception as e:
                    logger.warning(f"Erreur fermeture prewarm context: {e}")

            self.prewarm_contexts.clear()

            # Fermer le navigateur
            if self.browser:
                await self.browser.close()
                self.browser = None

            # Arreter Playwright
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None

            logger.info("[+] Pool de navigateurs nettoye")

        except Exception as e:
            logger.error(f"Erreur cleanup pool: {e}")

    async def get_stats(self) -> dict:
        """Retourne les statistiques du pool."""
        return {
            "active_contexts": len(self.contexts),
            "prewarm_contexts": len(self.prewarm_contexts) if settings.PREWARM_ENABLED else 0,
            "prewarm_enabled": settings.PREWARM_ENABLED,
            "max_contexts": settings.MAX_CONCURRENT_BROWSERS,
            "browser_running": self.browser is not None,
        }


# Instance globale du pool
browser_pool = BrowserPool()
