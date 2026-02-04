# ShotURL v3.0 - Website Screenshot & Analysis Tool

Outil securise de capture de screenshots et d'analyse de sites web, optimise pour 4GB RAM.

## Caracteristiques

- **Capture de screenshots** - Page complete ou viewport personnalise
- **Analyse reseau** - Capture toutes les requetes HTTP
- **Extraction DOM** - Elements cliquables, formulaires, scripts
- **Source HTML** - Option de recuperation du code source
- **Selecteurs CSS** - Cliquer ou masquer des elements
- **Anti-SSRF** - Protection complete contre les attaques SSRF
- **Optimise RAM** - Fonctionne efficacement avec 4GB de RAM
- **Interface moderne** - React + TypeScript + Tailwind CSS
- **API rapide** - FastAPI avec validation Pydantic
- **Mode sombre** - Interface claire/sombre

---

## Installation Rapide

### Option 1: Installation Automatique (Production)

Pour une installation complete sur serveur (bare metal/VM):

```bash
# Cloner le projet
cd /path/to/shotURL

# Lancer l'installation automatique
sudo ./install.sh

# Configurer
sudo nano /opt/shoturl/.env

# Demarrer le service
sudo systemctl start shoturl
sudo systemctl enable shoturl

# Configurer le reverse proxy (choisir UN des deux):
# - Nginx (recommande) : Voir config/nginx-shoturl.conf
# - Apache : Voir config/apache-shoturl.conf
```

### Option 2: Developpement Local

Pour tester en local sans installation complete:

```bash
# Setup rapide
./quick-start.sh

# Demarrer le backend
source venv/bin/activate
uvicorn api.main:app --reload

# Demarrer le frontend (nouveau terminal)
cd web
npm install
npm run dev
```

Acces:
- Frontend: http://localhost:5173
- API: http://localhost:8000/api/docs

### Option 3: Docker

Pour un deploiement conteneurise:

```bash
# Build et lancer
docker-compose -f docker/docker-compose-v3.yml up -d

# Voir les logs
docker-compose -f docker/docker-compose-v3.yml logs -f
```

Acces: http://localhost:8000

---

## Architecture

### Backend (FastAPI + Playwright)

```
api/
 main.py          # Point d'entree FastAPI
 config.py        # Configuration centralisee
 security.py      # Anti-SSRF et validation
 browser.py       # Pool Playwright optimise
 capture.py       # Logique de capture
 session.py       # Gestion des sessions
 models.py        # Modeles Pydantic
 routes.py        # Endpoints API
```

**8 fichiers** - Architecture modulaire et simple

### Frontend (React + TypeScript)

```
web/src/
 App.tsx          # Composant principal
 main.tsx         # Point d'entree
 index.css        # Styles + animations
```

Interface complete avec:
- Formulaire de capture avec toutes les options
- Affichage screenshot avec telechargement
- Tables pliables (reseau, DOM, HTML)
- Mode sombre avec persistance

---

## Configuration

### Variables d'Environnement (.env)

```env
# Serveur
HOST=0.0.0.0
PORT=8000
DEBUG=False
SECRET_KEY=changez-cette-cle

# Pool de navigateurs (optimise 4GB RAM)
MAX_CONCURRENT_BROWSERS=4     # 4 contextes max = ~1GB
MAX_CONCURRENT_SESSIONS=10    # Sessions simultanees
MAX_MEMORY_MB=3500            # Alerte a 3.5GB

# Timeouts (secondes)
BROWSER_TIMEOUT=20            # Timeout par navigateur
PAGE_LOAD_TIMEOUT=10          # Timeout chargement page
SESSION_TIMEOUT=300           # 5 minutes
CLEANUP_INTERVAL=30           # Nettoyage toutes les 30s

# Logs
LOG_LEVEL=INFO
LOG_FILE=/var/log/shoturl/shoturl.log
```

### Adapter selon la RAM disponible

**2GB RAM (Minimal):**
```env
MAX_CONCURRENT_BROWSERS=2
MAX_MEMORY_MB=1800
```

**8GB+ RAM (Performance):**
```env
MAX_CONCURRENT_BROWSERS=8
MAX_MEMORY_MB=7000
```

---

## API Endpoints

### POST /api/capture

Capture complete d'un site web.

**Requete:**
```json
{
  "url": "https://example.com",
  "full_page": true,
  "device": "desktop",
  "width": 1920,
  "height": 1080,
  "delay": 2,
  "click": ".accept-cookies",
  "hide": ".popup, .banner",
  "grab_html": true
}
```

**Reponse:**
```json
{
  "screenshot": "data:image/png;base64,...",
  "network_logs": [
    {
      "method": "GET",
      "url": "https://example.com",
      "status": 200,
      "type": "document"
    }
  ],
  "dom_elements": {
    "clickable": ["button.submit", "a.link"],
    "forms": ["form#login"],
    "scripts": 12
  },
  "html_source": "<!DOCTYPE html>...",
  "timestamp": "2026-01-19T10:30:00Z"
}
```

### GET /api/health

Verification de sante du service.

### GET /api/sessions

Liste des sessions actives.

### GET /api/stats

Statistiques detaillees.

**Documentation interactive:** http://localhost:8000/api/docs

---

## Reverse Proxy (Production)

**IMPORTANT:** Choisir **UN SEUL** serveur web (Nginx OU Apache, pas les deux).

### Option A: Nginx (Recommande)

Plus leger et performant pour le reverse proxy.

```bash
# Installer Nginx
sudo apt install nginx

# Copier la configuration
sudo cp config/nginx-shoturl.conf /etc/nginx/sites-available/shoturl

# Editer le nom de domaine
sudo nano /etc/nginx/sites-available/shoturl
# Modifier: server_name votredomaine.com

# Activer le site
sudo ln -s /etc/nginx/sites-available/shoturl /etc/nginx/sites-enabled/

# Tester et recharger
sudo nginx -t
sudo systemctl reload nginx

# SSL avec Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d votredomaine.com
```

### Option B: Apache

Alternative si vous preferez Apache.

```bash
# Installer Apache
sudo apt install apache2

# Copier la configuration
sudo cp config/apache-shoturl.conf /etc/apache2/sites-available/shoturl.conf

# Editer le nom de domaine
sudo nano /etc/apache2/sites-available/shoturl.conf
# Modifier: ServerName votredomaine.com

# Activer les modules necessaires
sudo a2enmod ssl rewrite proxy proxy_http headers deflate expires

# Activer le site
sudo a2ensite shoturl.conf

# Tester et recharger
sudo apachectl configtest
sudo systemctl reload apache2

# SSL avec Let's Encrypt
sudo apt install certbot python3-certbot-apache
sudo certbot --apache -d votredomaine.com
```

---

## Securite

### Protection Anti-SSRF

- Blocage IPs privees (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
- Blocage localhost et loopback (127.0.0.0/8)
- Blocage domaines .local, .lan
- Detection obfuscation IP (hex, octal)
- Validation DNS
- Extraction SafeLinks Outlook

### Isolation des Navigateurs

- Contextes Playwright isoles
- Telechargements bloques
- Pas de stockage persistant
- Blocage ressources (fonts, media, CSS)
- Cleanup automatique

### Headers de Securite

- Strict-Transport-Security (HSTS)
- X-Content-Type-Options: nosniff
- X-Frame-Options: SAMEORIGIN
- X-XSS-Protection
- Content-Security-Policy

### Rate Limiting (Nginx)

**Important:** Une capture = UNE seule requete qui retourne TOUT :
- Screenshot (full_page ou viewport)
- Network logs complets (avant ET apres le click si specifie)
- DOM elements
- HTML source (si `grab_html=true`)

Limites par defaut :
- API generale: 20 req/s par IP (burst 40)
- Endpoint `/api/capture`: 10 req/s par IP (burst 10)

---

## Gestion du Service

### Commandes Systemd

```bash
# Demarrer
sudo systemctl start shoturl

# Arreter
sudo systemctl stop shoturl

# Redemarrer
sudo systemctl restart shoturl

# Status
sudo systemctl status shoturl

# Auto-demarrage
sudo systemctl enable shoturl

# Logs en temps reel
sudo journalctl -u shoturl -f
```

### Logs

```bash
# Application
tail -f /var/log/shoturl/shoturl.log

# Acces HTTP
tail -f /var/log/shoturl/access.log

# Erreurs
tail -f /var/log/shoturl/error.log
```

---

## Optimisations RAM 4GB

| Composant | Consommation | Configuration |
|-----------|--------------|---------------|
| Playwright contextes | ~250MB/contexte | Max 4 = 1GB |
| FastAPI + Python | ~300MB | - |
| OS (Linux) | ~1.5GB | - |
| Marge securite | ~1GB | - |
| **TOTAL** | **~3.8GB** | **< 4GB** |

### Strategies d'optimisation

1. **Pool unique** - Un seul navigateur Playwright reutilise
2. **Contextes isoles** - Au lieu de multiples browsers
3. **Semaphore** - Limite stricte a 4 contextes simultanes
4. **Cleanup auto** - Toutes les 30 secondes
5. **Monitoring RAM** - Alerte a 85%, force cleanup a 90%
6. **Timeouts agressifs** - 20s max par page
7. **Blocage ressources** - Fonts, media, CSS non essentiels

---

## Performances

### Benchmarks (4GB RAM)

- **Captures simultanees:** 4 max
- **Temps de capture:** 3-8 secondes (moyenne)
- **Usage RAM:** 2-3.5GB (4 actifs)
- **Usage CPU:** 50-150% (2 cores)

### Comparaison v2.0 vs v3.0

| Metrique | v2.0 (Flask+Selenium) | v3.0 (FastAPI+Playwright) |
|----------|----------------------|---------------------------|
| RAM/instance | ~500MB | ~250MB (**-50%**) |
| Instances max (4GB) | 6 | 12 (**+100%**) |
| API req/s | ~1000 | ~3000 (**+200%**) |
| Fichiers code | 30+ | 8 (**-70%**) |
| Async natif |  |  |
| Swagger auto |  |  |
| Validation auto |  |  (Pydantic) |

---

## Depannage

### Service ne demarre pas

```bash
sudo systemctl status shoturl
sudo journalctl -u shoturl -n 50
```

### Port deja utilise

```bash
sudo lsof -i :8000
sudo kill -9 <PID>
```

### Probleme Playwright

```bash
cd /opt/shoturl
source venv/bin/activate
playwright install chromium --force
```

### Usage RAM eleve

```bash
# Verifier
free -h
ps aux | grep shoturl

# Redemarrer
sudo systemctl restart shoturl

# Reduire dans .env
MAX_CONCURRENT_BROWSERS=2
```

---

## Documentation

- **INSTALLATION.md** - Guide d'installation detaille
- **DEPLOYMENT.md** - Guide de deploiement et scaling
- **README-V3.md** - Notes de version v3.0
- **ARCHITECTURE_V3_PROPOSAL.md** - Analyse et justifications
- **Swagger API** - http://localhost:8000/api/docs

---

## Structure du Projet

```
shotURL/
 api/                      # Backend FastAPI
    main.py
    config.py
    security.py
    browser.py
    capture.py
    session.py
    models.py
    routes.py
 web/                      # Frontend React
    src/
       App.tsx
       main.tsx
       index.css
    package.json
    vite.config.ts
 config/                   # Configurations serveurs
    nginx-shoturl.conf   # Config Nginx
    apache-shoturl.conf  # Config Apache
 docker/                   # Docker (optionnel)
    Dockerfile-v3
    docker-compose-v3.yml
 install.sh               # Installation auto
 quick-start.sh           # Setup dev rapide
 requirements-v3.txt      # Dependances Python
 .env-v3.example          # Template config
 README.md                # Ce fichier
 INSTALLATION.md          # Guide installation
 DEPLOYMENT.md            # Guide deploiement
 README-V3.md             # Notes version
```

---

## Prerequis

### Systeme

- OS: Ubuntu 20.04+, Debian 11+, RHEL/CentOS 8+
- RAM: 4GB minimum
- CPU: 2 cores minimum
- Disk: 5GB espace libre

### Logiciels

- Python 3.10+
- Node.js 18+
- Nginx OU Apache (production)
- Git (pour cloner)

---

## Exemples d'Usage

### Capture Simple

```bash
curl -X POST http://localhost:8000/api/capture \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "full_page": true
  }'
```

### Capture Avancee

```bash
curl -X POST http://localhost:8000/api/capture \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://site-with-popup.com",
    "full_page": false,
    "width": 1920,
    "height": 1080,
    "delay": 3,
    "click": ".accept-cookies",
    "hide": ".popup, .banner, .overlay",
    "grab_html": true
  }'
```

### Health Check

```bash
curl http://localhost:8000/api/health
```

---

## License

Proprietaire - Tous droits reserves

---

## Support

Pour des questions ou problemes:

1. Verifier les logs: `/var/log/shoturl/`
2. Consulter `INSTALLATION.md` pour le depannage
3. Verifier l'API Swagger: `/api/docs`
4. Status du service: `systemctl status shoturl`

---

**Version:** 3.0.0
**Date:** 2026-01-19
**Optimise pour:** 4GB RAM
**Status:** Production Ready
**Backend:** FastAPI + Playwright
**Frontend:** React + TypeScript + Tailwind CSS
