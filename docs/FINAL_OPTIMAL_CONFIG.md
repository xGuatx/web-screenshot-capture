# Configuration OPTIMALE - ShotURL v3.0

##  Meilleure Performance : 4GB RAM + 4 CPU + 4 Browsers

Apres tests exhaustifs de 8 configurations differentes, voici la configuration optimale.

---

##  Resultats des Tests Complets

| Config | RAM | CPU | Browsers | Prewarm | Total | Moyenne | Premiere | Gain |
|--------|-----|-----|----------|---------|-------|---------|----------|------|
| **4GB + 4 CPU**  | 4GB | 4 | 4 | 4 | **30.50s** | **20.16s** | **8.46s** | **-38.6%** |
| 4GB + 6 CPU | 4GB | 6 | 6 | 6 | 37.58s | 28.96s | 24.04s | -24.4% |
| 2GB + 2 CPU optimise | 2GB | 2 | 2 | 2 | 43.58s | 26.19s | ~9s | -12.3% |
| 4GB + 2 CPU + 4 browsers | 4GB | 2 | 4 | 4 | 46.86s | 32.33s | 15.27s | -5.7% |
| Baseline | 2GB | 2 | 2 | 0 | 49.69s | 29.75s | ~11s | - |
| 4GB + 2 CPU + 2 browsers | 4GB | 2 | 2 | 2 | 51.99s | 30.77s | 10.66s | -4.6% |
| 4GB + 2 CPU + 3 browsers | 4GB | 2 | 3 | 3 | 52.54s | 33.97s | 16.71s | -5.7% |
| 2GB + 4 CPU | 2GB | 4 | 2 | 2 | 58.19s | 35.21s | 12.44s | +17.1% |

---

##  Configuration Optimale

### Ressources VM
```
RAM: 4GB
CPU: 4 cores (minimum)
```

### docker-compose.yml
```yaml
version: '3.8'

services:
  shoturl:
    image: docker-shoturl:latest
    container_name: shoturl-v3
    restart: unless-stopped

    ports:
      - "8000:8000"

    environment:
      # Browser Limits (OPTIMAL)
      - MAX_CONCURRENT_BROWSERS=4
      - MAX_CONCURRENT_SESSIONS=10
      - MAX_MEMORY_MB=3500

      # Pre-warm (Performance)
      - PREWARM_ENABLED=true
      - PREWARM_COUNT=4

      # Redis Cache (Optionnel)
      - REDIS_ENABLED=false

      # Autres configs...
      - HOST=0.0.0.0
      - PORT=8000
      - DEBUG=false
      - ALLOW_LOCAL_URLS=false
      - BROWSER_TIMEOUT=15
      - PAGE_LOAD_TIMEOUT=8
      - SESSION_TIMEOUT=90
      - CLEANUP_INTERVAL=5
      - LOG_LEVEL=INFO

    volumes:
      - ./logs:/app/logs

    # PAS de limites Docker
    # La VM gere deja les ressources
    # Les vraies limites sont dans le code (MAX_CONCURRENT_BROWSERS, MAX_MEMORY_MB)

    security_opt:
      - seccomp:unconfined

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

    networks:
      - shoturl-network

networks:
  shoturl-network:
    driver: bridge
```

---

##  Performance Attendue

### 10 Requetes Twitch Simultanees
- **Total** : **30.50s**
- **Moyenne** : **20.16s par requete**
- **Premiere** : **8.46s** (grace au prewarm)
- **Pattern** : 3 vagues (4+4+2)
  - Vague 1 : 4 captures  8-14s
  - Vague 2 : 4 captures  18-26s
  - Vague 3 : 2 captures  28-30s

### 1 Requete Twitch
- **~8-9 secondes** (prewarm context immediatement disponible)

### Success Rate
- **100%** sur tous les tests

---

##  Pourquoi cette Config est Optimale ?

###  Equilibre Parfait RAM/CPU/Browsers

1. **4 CPU cores** : Chaque browser Chrome a ~1 CPU dedie
2. **4GB RAM** : ~1GB par browser + contexts (confortable)
3. **4 browsers** : Parallelisme maximal sans contention
4. **4 prewarm** : Contexts toujours prets, pas de latence

###  Evite les Problemes des Autres Configs

**Trop de browsers (6)** :
- 6 browsers + 6 prewarm = 12 contexts Chrome
- Consommation RAM : 3.5-3.8GB (trop proche limite 4GB)
- **Contention RAM**  premiere capture en 24s vs 8s 
- Total : 37.58s (23% plus lent que 4 browsers)

**Pas assez de CPU (2)** :
- 4 browsers avec seulement 2 CPU = contention CPU
- Chaque capture : 15-22s vs 8-14s avec 4 CPU 
- Total : 46.86s (54% plus lent que 4 CPU)

**Pas assez de RAM (2GB)** :
- 4 browsers impossible (swap excessif)
- Maximum 2 browsers : 43.58s (43% plus lent)

---

##  Pourquoi PAS de Limites Docker ?

### Question
> Pourquoi pas de `deploy: resources: limits` dans docker-compose.yml ?

### Reponse

**Les limites Docker sont redondantes** quand la VM a deja des limites strictes.

#### Limites a 3 Niveaux

```
Niveau 1 (VM) : 4GB RAM, 4 CPU
    
Niveau 2 (Docker) : limits: memory: 4G, cpus: '4'   REDONDANT
    
Niveau 3 (Application) : MAX_CONCURRENT_BROWSERS=4   VRAIE LIMITE
```

#### Cas d'Usage des Limites Docker

**Utile quand** :
- Plusieurs containers sur la meme VM (partage ressources)
- Proteger contre runaway processes
- Enforcer des quotas stricts

**Pas utile quand** :
- **1 seul container sur la VM**  TON CAS
- VM deja limitee a 4GB/4 CPU
- Limites applicatives dans le code

#### Avantage Sans Limites Docker

 **Flexibilite** : Si VM upgrade 6 CPU, Docker utilise automatiquement
 **Simplicite** : Moins de configuration a maintenir
 **Performance** : Pas d'overhead de monitoring Docker limits

**Les VRAIES limites** sont dans le code :
```python
MAX_CONCURRENT_BROWSERS=4   # Limite nombre de Chrome instances
MAX_MEMORY_MB=3500          # Alerte si RAM > 3.5GB
```

---

##  Gains Obtenus

### vs Baseline (2GB/2 CPU/2 browsers/no prewarm)
- **Temps** : 49.69s  30.50s
- **Gain** : **-38.6%** (19.19s economises)
- **Premiere capture** : ~11s  8.46s (-23%)

### Optimisations Cles
1. **+2GB RAM** : Permet 4 browsers au lieu de 2  -30% temps
2. **+2 CPU** : Reduit contention, captures 50% plus rapides
3. **Prewarm** : Skip creation context  -2-3s premiere capture
4. **Parallelisation** : asyncio.gather() DOM+screenshot+HTML  -1s/capture

---

##  Checklist Deploiement

### Prerequis
- [ ] VM avec **4GB RAM** (minimum)
- [ ] VM avec **4 CPU cores** (minimum, 6+ OK mais pas necessaire)
- [ ] Docker installe
- [ ] Image `docker-shoturl:latest` buildee

### Deploiement
```bash
# 1. Copier docker-compose.optimal.yml
cp docker-compose.optimal.yml docker-compose.yml

# 2. Demarrer
docker compose up -d

# 3. Verifier sante
curl http://localhost:8000/api/health

# 4. Tester
python3 load_test.py
```

### Validation
- [ ] Health check : `status: "healthy"`
- [ ] Logs : `[+] 4 contexts pre-chauds prets`
- [ ] Test 10 req : **< 35s**
- [ ] RAM : **< 3.5GB** pendant test
- [ ] Success rate : **100%**

---

##  Monitoring

### Health Endpoint
```bash
curl http://localhost:8000/api/health | jq
```

```json
{
  "status": "healthy",
  "browser_pool": {
    "active_contexts": 4,
    "prewarm_contexts": 4,
    "prewarm_enabled": true,
    "max_contexts": 4
  },
  "sessions": {
    "active": 0,
    "max": 10
  },
  "memory": {
    "current_mb": 1756,
    "limit_mb": 3500,
    "percent": 50.2
  }
}
```

### Logs Prewarm
```bash
docker logs shoturl-v3 | grep PREWARM
```

```
[PREWARM] Creation de 4 contexts pre-chauds...
[+] 4 contexts pre-chauds prets
[PREWARM] Utilisation context pre-chaud (3 restants)
[PREWARM] Context recharge (4/4)
```

---

##  Si Besoin de Plus de Performance

### Option 1 : Cache Redis (Recaptures)
```yaml
environment:
  - REDIS_ENABLED=true
  - REDIS_CACHE_TTL=180
  - REDIS_SMART_CACHE=true
```

**Gain** : 100% sur recaptures identiques (30s  0.1s)

### Option 2 : Plus de RAM (8GB)
Permet 6 browsers sans contention :
```yaml
environment:
  - MAX_CONCURRENT_BROWSERS=6
  - PREWARM_COUNT=6
  - MAX_MEMORY_MB=7000
```

**Performance estimee** : ~22-25s (10 requetes)
**Attention** : Besoin aussi 6 CPU minimum

### Option 3 : CDN/Proxy Cache
Pour sites statiques, mettre un cache Nginx/Varnish devant

---

##  Configurations a EVITER

###  6 browsers avec 4GB RAM
- Contention RAM excessive
- Premiere capture : 24s vs 8s (3x plus lent)
- Total : 37.58s vs 30.50s

###  4 browsers avec 2 CPU
- Contention CPU
- Captures 2x plus lentes
- Total : 46.86s vs 30.50s

###  2GB RAM avec 4 CPU
- RAM insuffisante
- Swap excessif
- Total : 58.19s (pire config)

---

##  Documentation Complete

- **[COMPARISON_4GB_TESTS.md](./COMPARISON_4GB_TESTS.md)** : Tests 2GB vs 4GB
- **[README_OPTIMIZATIONS.md](./README_OPTIMIZATIONS.md)** : Guide optimisations
- **[CACHE_GUIDE.md](./CACHE_GUIDE.md)** : Cache Redis intelligent
- **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** : Commandes rapides

---

**Version** : v3.0.0-optimal
**Date** : 2026-01-23
**Performance** : **30.50s** pour 10 requetes Twitch (-38.6% vs baseline)
**Config** : **4GB RAM + 4 CPU + 4 browsers + 4 prewarm** 
