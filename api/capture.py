"""Capture de screenshots, reseau et DOM avec Playwright."""

import base64
import re
import asyncio
from typing import Dict, List, Optional
from playwright.async_api import Page, BrowserContext, Response

from api.config import settings, logger
from api.browser import browser_pool


class NetworkCapture:
    """Gere la capture des requetes reseau."""

    def __init__(self):
        self.logs: List[Dict] = []
        self.exclude_pattern = self._compile_exclude_pattern()

    def _compile_exclude_pattern(self) -> re.Pattern:
        """Compile le pattern d'exclusion reseau."""
        pattern = '|'.join(settings.NETWORK_EXCLUDE_PATTERNS)
        return re.compile(pattern, re.IGNORECASE)

    def should_exclude(self, url: str) -> bool:
        """Verifie si une URL doit etre exclue."""
        return bool(self.exclude_pattern.search(url))

    def log_request(self, request):
        """Log une requete HTTP."""
        url = request.url
        if not self.should_exclude(url):
            self.logs.append({
                "url": url,
                "method": request.method,
                "type": request.resource_type,
                "timestamp": asyncio.get_event_loop().time()
            })

    def log_response(self, response: Response):
        """Complete les infos d'une reponse."""
        url = response.url
        for log in self.logs:
            if log["url"] == url and "status" not in log:
                log["status"] = response.status
                log["status_text"] = response.status_text
                break

    def get_logs(self) -> List[Dict]:
        """Retourne tous les logs captures."""
        return self.logs


class DOMExtractor:
    """Extrait les elements interactifs du DOM."""

    @staticmethod
    async def extract_elements(page: Page) -> Dict:
        """
        Extrait les elements interactifs (boutons, forms, scripts, etc.).

        Args:
            page: Page Playwright

        Returns:
            Dict avec clickable_elements, forms, scripts, popups
        """
        try:
            elements = await page.evaluate("""
                () => {
                    // Fonction pour verifier si un element est visible
                    const isVisible = (el) => {
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        return style.display !== 'none' &&
                               style.visibility !== 'hidden' &&
                               style.opacity !== '0' &&
                               el.offsetWidth > 0 &&
                               el.offsetHeight > 0;
                    };

                    // Elements cliquables - inclure TOUS les boutons, liens, inputs, divs cliquables
                    const clickable = [
                        ...document.querySelectorAll('button, input[type="submit"], input[type="button"], a[href], [role="button"], [onclick], div[class*="button"], div[class*="btn"], span[role="button"], [class*="accept"], [class*="reject"], [class*="refuse"], [class*="decline"], [id*="accept"], [id*="reject"], [id*="refuse"], [id*="decline"], div[onclick]')
                    ]
                        .filter(el => isVisible(el))
                        .slice(0, 300)  // Augmente pour capturer plus d'elements
                        .map(el => {
                            // Obtenir le texte visible directement de l'element (sans enfants profonds)
                            let directText = '';
                            for (let node of el.childNodes) {
                                if (node.nodeType === Node.TEXT_NODE) {
                                    directText += node.textContent;
                                }
                            }
                            directText = directText.trim();

                            // Generer un selecteur CSS unique
                            let selector = el.tagName.toLowerCase();
                            if (el.id) {
                                selector = `#${el.id}`;
                            } else if (el.className) {
                                const classes = el.className.trim().split(/\s+/).slice(0, 2).join('.');
                                if (classes) selector = `${selector}.${classes}`;
                            }

                            return {
                                tag: el.tagName.toLowerCase(),
                                text: (directText || el.textContent?.trim() || '').substring(0, 200),
                                id: el.id || '',
                                classes: el.className || '',
                                href: el.href || '',
                                type: el.type || '',
                                role: el.getAttribute('role') || '',
                                visible: isVisible(el),
                                aria_label: el.getAttribute('aria-label') || '',
                                onclick: el.hasAttribute('onclick'),
                                selector: selector
                            };
                        });

                    // Separer les elements visibles et caches
                    const visibleElements = clickable.filter(el => el.visible);
                    const hiddenElements = clickable.filter(el => !el.visible);

                    // Formulaires
                    const forms = [...document.querySelectorAll('form')]
                        .slice(0, 20)
                        .map(form => ({
                            action: form.action || '',
                            method: form.method.toUpperCase() || 'GET',
                            id: form.id || '',
                            inputs: [...form.querySelectorAll('input, textarea, select')]
                                .slice(0, 50)
                                .map(inp => ({
                                    name: inp.name || '',
                                    type: inp.type || inp.tagName.toLowerCase(),
                                    required: inp.required || false
                                }))
                        }));

                    // Scripts
                    const scripts = [...document.querySelectorAll('script')]
                        .slice(0, 50)
                        .map(script => ({
                            src: script.src || '',
                            inline: !script.src,
                            type: script.type || 'text/javascript',
                            content: !script.src ? script.textContent : ''
                        }));

                    // Popups potentiels - inclure cookies, modals, overlays
                    const popups = [
                        ...document.querySelectorAll('[class*="modal"], [class*="popup"], [class*="overlay"], [class*="cookie"], [class*="consent"], [class*="gdpr"], [id*="cookie"], [id*="consent"]')
                    ]
                        .filter(el => isVisible(el))
                        .slice(0, 30)
                        .map(popup => {
                            // Chercher les boutons dans le popup
                            const buttons = [...popup.querySelectorAll('button, [role="button"], div[onclick]')]
                                .filter(btn => isVisible(btn))
                                .map(btn => btn.textContent?.trim() || '')
                                .filter(text => text.length > 0);

                            return {
                                id: popup.id || '',
                                classes: popup.className || '',
                                visible: isVisible(popup),
                                text: popup.textContent?.trim().substring(0, 300) || '',
                                buttons: buttons
                            };
                        });

                    // Redirections meta
                    const metaRefresh = document.querySelector('meta[http-equiv="refresh"]');
                    const redirect = metaRefresh ? metaRefresh.getAttribute('content') : null;

                    return {
                        clickable_elements: visibleElements,
                        hidden_elements: hiddenElements,
                        forms: forms,
                        scripts: scripts,
                        popups: popups,
                        redirect: redirect,
                        title: document.title,
                        url: window.location.href
                    };
                }
            """)

            logger.debug(f"[+] DOM extrait: {len(elements['clickable_elements'])} elements cliquables, "
                        f"{len(elements['forms'])} forms, {len(elements['scripts'])} scripts")

            return elements

        except Exception as e:
            logger.error(f"Erreur extraction DOM: {e}")
            return {
                "clickable_elements": [],
                "forms": [],
                "scripts": [],
                "popups": [],
                "error": str(e)
            }


class Capturer:
    """Gere toutes les captures (screenshot, reseau, DOM)."""

    async def capture_all(
        self,
        url: str,
        full_page: bool = False,
        width: int = 1024,
        height: int = 768,
        delay: int = 0,
        click_selector: Optional[str] = None,
        hide_selectors: Optional[str] = None,
        grab_html: bool = False
    ) -> Dict:
        """
        Capture complete: screenshot + reseau + DOM.

        Args:
            url: URL a capturer
            full_page: Capture full-page ou viewport
            width: Largeur viewport
            height: Hauteur viewport
            delay: Delai avant capture (secondes)
            click_selector: Selecteur CSS d'element a cliquer
            hide_selectors: Selecteurs CSS d'elements a masquer (separes par virgule)
            grab_html: Capturer le HTML source

        Returns:
            Dict avec screenshot, network_logs, dom_elements, html (optionnel)
        """
        context: Optional[BrowserContext] = None
        page: Optional[Page] = None

        # Acquerir le semaphore pour toute la duree de la capture
        # Ceci limite vraiment le nombre de captures concurrentes
        async with browser_pool.semaphore:
            try:
                logger.debug(f"Semaphore acquis pour {url}")

                # Obtenir un contexte du pool
                context = await browser_pool.get_context(width=width, height=height)
                logger.debug(f"Contexte obtenu pour {url}")

                # Creer page avec capture reseau
                logger.debug(f"Creation page pour {url}")
                try:
                    # Timeout explicite pour new_page() car il peut bloquer indefiniment
                    page = await asyncio.wait_for(context.new_page(), timeout=30.0)
                    logger.debug(f"Page creee pour {url}")
                except asyncio.TimeoutError:
                    logger.error(f"Timeout lors de la creation de page pour {url}")
                    raise RuntimeError(f"Timeout lors de la creation de la page apres 30s")
                network = NetworkCapture()

                # Attacher listeners reseau
                page.on("request", network.log_request)
                page.on("response", network.log_response)

                logger.info(f"Chargement de {url}...")

                # Naviguer vers l'URL
                navigation_error = None
                try:
                    await page.goto(
                        url,
                        timeout=settings.PAGE_LOAD_TIMEOUT * 1000,
                        wait_until="domcontentloaded"  # Plus rapide que "networkidle"
                    )
                except Exception as e:
                    error_msg = str(e)
                    # Erreurs critiques qui empechent toute navigation
                    if "net::ERR_NAME_NOT_RESOLVED" in error_msg or "net::ERR_CONNECTION_REFUSED" in error_msg:
                        logger.error(f"Erreur critique de navigation: {e}")
                        raise RuntimeError(f"URL inaccessible: {url}. Le domaine n'existe pas ou refuse la connexion.")

                    logger.warning(f"Timeout ou erreur navigation: {e}")
                    navigation_error = error_msg
                    # Continuer pour les timeouts/erreurs mineures si la page a partiellement charge

                # Delai optionnel
                if delay > 0:
                    logger.debug(f"Attente de {delay}s...")
                    await page.wait_for_timeout(delay * 1000)

                # Clic sur element
                if click_selector:
                    try:
                        await page.click(click_selector, timeout=2000)
                        await page.wait_for_timeout(500)  # Laisser le DOM se mettre a jour
                        logger.debug(f"[+] Clique sur: {click_selector}")
                    except Exception as e:
                        logger.warning(f"Impossible de cliquer sur '{click_selector}': {e}")

                # Masquer elements
                if hide_selectors:
                    for selector in hide_selectors.split(','):
                        selector = selector.strip()
                        try:
                            await page.evaluate(f"""
                                document.querySelectorAll('{selector}').forEach(
                                    el => el.style.display = 'none'
                                )
                            """)
                            logger.debug(f"[+] Masque: {selector}")
                        except Exception as e:
                            logger.warning(f"Impossible de masquer '{selector}': {e}")

                # Attendre un peu pour que les changements s'appliquent
                await page.wait_for_timeout(300)

                # PARALLELISATION: Capture screenshot + Extraction DOM + HTML en parallele
                logger.debug("Capture parallele (screenshot + DOM + HTML)...")

                tasks = [
                    page.screenshot(full_page=full_page, type="png"),  # Screenshot
                    DOMExtractor.extract_elements(page),  # DOM extraction
                ]

                # HTML source (optionnel)
                if grab_html:
                    tasks.append(page.content())

                # Executer en parallele
                results = await asyncio.gather(*tasks)

                # Extraire resultats
                screenshot = results[0]
                screenshot_b64 = base64.b64encode(screenshot).decode()
                dom_elements = results[1]
                html_source = results[2] if grab_html else None

                # Construire resultat
                result = {
                    "screenshot": screenshot_b64,
                    "screenshot_format": "png",
                    "network_logs": network.get_logs(),
                    "dom_elements": dom_elements,
                    "final_url": page.url,  # URL finale (apres redirections)
                    "capture_config": {
                        "full_page": full_page,
                        "width": width,
                        "height": height,
                        "delay": delay
                    }
                }

                if html_source:
                    result["html_source"] = html_source

                logger.info(f"[+] Capture reussie de {url} ({len(network.get_logs())} requetes reseau)")

                return result

            except Exception as e:
                logger.error(f"[-] Erreur capture de {url}: {e}")
                raise

            finally:
                # Cleanup
                if page:
                    await page.close()
                if context:
                    await browser_pool.release_context(context)


# Instance globale
capturer = Capturer()
