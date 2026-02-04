"""Validation d'URLs et securite anti-SSRF pour ShotURL v3.0."""

import re
import socket
import ipaddress
from typing import Optional
from urllib.parse import urlparse

from api.config import settings, logger


def is_valid_url(url: str) -> bool:
    """
    Valide qu'une URL est sure et accessible.
    Protege contre SSRF, IPs privees, domaines locaux.

    Args:
        url: URL a valider

    Returns:
        True si l'URL est sure, False sinon
    """
    try:
        # Ajouter le protocole si manquant (HTTP pour suivre les redirections naturelles)
        if not re.match(r'^[a-zA-Z]+://', url):
            url = 'http://' + url

        parsed = urlparse(url)
        host = parsed.hostname or parsed.path

        if not host:
            logger.warning(f"URL sans hostname: {url}")
            return False

        # Bloquer les hostnames purement numeriques
        if host.isdigit():
            logger.warning(f"Hostname numerique bloque: {host}")
            return False

        # Bloquer les IPs hexadecimales (0x7f000001)
        if host.lower().startswith("0x"):
            logger.warning(f"IP hexadecimale bloquee: {host}")
            return False

        # Bloquer les IPv4 avec leading zeros (127.00.0.1)
        if re.fullmatch(r'(?:\d{1,3}\.){1,3}\d{1,3}', host):
            parts = host.split('.')
            for part in parts:
                if len(part) > 1 and part.startswith('0'):
                    logger.warning(f"IPv4 obfusquee bloquee: {host}")
                    return False

        # Verifier si c'est une IP
        try:
            ip = ipaddress.ip_address(host)
            # Bloquer les IPs privees/locales/reservees
            if (ip.is_private or ip.is_loopback or ip.is_reserved or
                ip.is_multicast or ip.is_link_local):
                logger.warning(f"IP non-publique bloquee: {ip}")
                return False
            return True
        except ValueError:
            pass  # Ce n'est pas une IP, continuer avec les domaines

        # Verifier les domaines bloques
        host_lower = host.lower()
        if any(host_lower.endswith(suffix) for suffix in settings.BLOCKED_DOMAINS):
            logger.warning(f"Domaine bloque: {host}")
            return False

        if any(keyword in host_lower for keyword in settings.BLOCKED_KEYWORDS):
            logger.warning(f"Mot-cle bloque dans le domaine: {host}")
            return False

        return True

    except Exception as e:
        logger.error(f"Erreur validation URL {url}: {e}")
        return False


def is_reachable(url: str, timeout: int = 3) -> bool:
    """
    Verifie qu'une URL est accessible via DNS.

    Args:
        url: URL a verifier
        timeout: Timeout en secondes

    Returns:
        True si l'URL est accessible, False sinon
    """
    try:
        if not is_valid_url(url):
            return False

        # Normaliser l'URL
        if not re.match(r'^[a-zA-Z]+://', url):
            url = 'http://' + url

        parsed_url = urlparse(url)
        host = parsed_url.hostname

        if not host:
            logger.error(f"Pas de hostname dans l'URL: {url}")
            return False

        # Verifier la longueur des labels DNS (max 63 chars par label)
        if any(len(label) > 150 for label in host.split(".")):
            logger.error(f"Label DNS trop long: {host}")
            return False

        # DNS lookup
        socket.setdefaulttimeout(timeout)
        socket.gethostbyname(host)
        return True

    except (UnicodeError, socket.gaierror, socket.timeout, socket.error) as e:
        logger.error(f"URL non accessible: {url} - {e}")
        return False


def probe_url_scheme(url: str, timeout: int = 3) -> str:
    """
    Teste HTTP et HTTPS pour determiner le meilleur schema a utiliser.

    Args:
        url: URL a tester (peut etre sans protocole)
        timeout: Timeout en secondes

    Returns:
        URL avec le bon protocole (https:// ou http://)
    """
    import socket

    # Extraire le host sans protocole
    if re.match(r'^[a-zA-Z]+://', url):
        parsed = urlparse(url)
        host = parsed.hostname
        path = parsed.path or '/'
    else:
        # Supprimer www. temporairement pour le test
        url_clean = url.replace('www.', '', 1) if url.startswith('www.') else url
        parts = url_clean.split('/', 1)
        host = parts[0]
        path = '/' + parts[1] if len(parts) > 1 else '/'

    if not host:
        return url

    # Tester HTTPS en premier (port 443)
    try:
        socket.setdefaulttimeout(timeout)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, 443))
        sock.close()
        if result == 0:
            logger.debug(f"HTTPS disponible pour {host}")
            return f"https://{url.replace('http://', '').replace('https://', '')}"
    except Exception as e:
        logger.debug(f"HTTPS non disponible pour {host}: {e}")

    # Fallback sur HTTP (port 80)
    try:
        socket.setdefaulttimeout(timeout)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, 80))
        sock.close()
        if result == 0:
            logger.debug(f"HTTP disponible pour {host}")
            return f"http://{url.replace('http://', '').replace('https://', '')}"
    except Exception as e:
        logger.debug(f"HTTP non disponible pour {host}: {e}")

    # Si rien ne fonctionne, retourner HTTP par defaut (laissera Playwright gerer la redirection)
    return f"http://{url.replace('http://', '').replace('https://', '')}"


def extract_safelink_url(url: str) -> str:
    """
    Extrait l'URL originale depuis un SafeLink Outlook.

    Args:
        url: URL potentiellement wrapped par SafeLinks

    Returns:
        URL originale ou URL input si pas un SafeLink
    """
    try:
        from urllib.parse import parse_qs, unquote

        parsed = urlparse(url)
        if not parsed.netloc.endswith("safelinks.protection.outlook.com"):
            return url

        query = parse_qs(parsed.query)
        original = query.get("url", [None])[0]
        if original:
            return unquote(original)

    except Exception as e:
        logger.warning(f"Echec extraction SafeLink {url}: {e}")

    return url


def sanitize_selector(selector: str) -> Optional[str]:
    """
    Valide et sanitise un selecteur CSS.

    Args:
        selector: Selecteur CSS

    Returns:
        Selecteur sanitise ou None si invalide
    """
    if not selector:
        return None

    selector = selector.strip()

    if len(selector) > settings.MAX_SELECTOR_LENGTH:
        logger.warning(f"Selecteur trop long: {len(selector)} > {settings.MAX_SELECTOR_LENGTH}")
        return None

    # Pattern CSS valide
    pattern = r'^[a-zA-Z#\.\[\*&][a-zA-Z0-9\s\.\#\-\_\[\]\=\*\^\$\~\:\'\"\>\+\,\|&]*$'
    if not re.match(pattern, selector):
        logger.warning(f"Selecteur CSS invalide: {selector[:100]}")
        return None

    return selector


def validate_dimensions(width: int, height: int) -> tuple[int, int]:
    """
    Valide et ajuste les dimensions.

    Args:
        width: Largeur demandee
        height: Hauteur demandee

    Returns:
        Tuple (width, height) valide

    Raises:
        ValueError: Si dimensions invalides
    """
    if width < settings.MIN_WIDTH or height < settings.MIN_HEIGHT:
        raise ValueError(
            f"Dimensions minimales: {settings.MIN_WIDTH}x{settings.MIN_HEIGHT}"
        )

    if width > settings.MAX_WIDTH or height > settings.MAX_HEIGHT:
        raise ValueError(
            f"Dimensions maximales: {settings.MAX_WIDTH}x{settings.MAX_HEIGHT}"
        )

    return width, height


def parse_device_dimensions(device: str, width: Optional[int], height: Optional[int]) -> tuple[int, int]:
    """
    Parse les dimensions selon le device ou dimensions custom.

    Args:
        device: Type de device (desktop, tablet, phone)
        width: Largeur custom (optionnel)
        height: Hauteur custom (optionnel)

    Returns:
        Tuple (width, height)
    """
    # Si dimensions custom fournies
    if width is not None and height is not None:
        return validate_dimensions(width, height)

    # Sinon utiliser les dimensions du device
    device = device.lower() if device else "desktop"
    default_width, default_height = settings.DEVICE_DIMENSIONS.get(
        device,
        settings.DEVICE_DIMENSIONS["desktop"]
    )

    return default_width, default_height
