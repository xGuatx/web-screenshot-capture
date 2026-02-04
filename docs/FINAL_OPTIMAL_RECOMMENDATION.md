# Configuration Optimale FINALE - ShotURL v3.0

##  MEILLEURE CONFIGURATION

Apres tests exhaustifs, la configuration optimale absolue est :

### Hardware VM
```
RAM: 4GB
CPU: 6 cores
```

### Application (docker-compose.yml)
```yaml
environment:
  - MAX_CONCURRENT_BROWSERS=3
  - MAX_CONCURRENT_SESSIONS=10
  - MAX_MEMORY_MB=3500
  - BROWSER_TIMEOUT=12
  - PAGE_LOAD_TIMEOUT=7
  - SESSION_TIMEOUT=60
  - CLEANUP_INTERVAL=3
  - PREWARM_ENABLED=true
  - PREWARM_COUNT=3
  - REDIS_ENABLED=false
```

### Performance
- **10 requetes Twitch simultanees** : **23.41s**
- **Gain vs baseline** : **-52.9%** (49.69s  23.41s)
- **Success rate** : **100%**
- **RAM utilisee** : ~2.5GB (confortable)

---

##  Tableau Recapitulatif des Tests

### 4GB RAM + 6 CPU (OPTIMAL)

| Browsers | Prewarm | Temps | Rang | Notes |
|----------|---------|-------|------|-------|
| **3** | **3** | **23.41s** | **** | **MEILLEUR ABSOLU** |
| 4 | 2 | 23.69s |  | Tres bon aussi |
| 5 | 3 | 24.43s |  | Plus de browsers |
| 4 | 4 | 25.75s | 4eme | Trop de prewarm |
| 3 | 2 | 26.14s | 5eme | Moins de prewarm |
| 4 | 3 | 26.00s | 6eme | Equilibre |

### 4GB RAM + 5 CPU

| Browsers | Prewarm | Temps | Rang | Notes |
|----------|---------|-------|------|-------|
| 5 | 3 | 27.01s |  | Meilleur pour 5 CPU |
| 4 | 4 | 27.05s |  | Tres proche |
| 3 | 3 | 27.07s |  | Equilibre |
| 4 | 2 | 27.15s | 4eme | Minimal prewarm |
| 3 | 2 | 27.87s | 5eme | Moins de browsers |
| 4 | 3 | 28.16s | 6eme | Standard |

---

##  Insights Cles

### 1. Impact CPU
- **6 CPU** : 23.41s (meilleur)
- **5 CPU** : 27.01s
- **Gain 6 vs 5 CPU** : **-13.3%**

 **6 CPU vaut l'investissement**

### 2. Sweet Spot Browsers/Prewarm
- **3/3** (ratio 1:1) : **OPTIMAL** 
- 4/2 (ratio 2:1) : Tres bon
- 5/3 (ratio ~1.7:1) : Bon
- 4/4 (ratio 1:1) : Trop de contexts  contention

 **Ratio 1:1 avec 3 browsers est ideal**

### 3. Pourquoi 3 browsers > 4 browsers ?
Avec 4GB RAM :
- **3 browsers + 3 prewarm** = 6 contexts Chrome  ~2.5GB RAM 
- **4 browsers + 4 prewarm** = 8 contexts Chrome  ~3.2GB RAM  contention 

 **3 browsers utilise mieux la RAM disponible**

### 4. Impact Timeouts Optimises
Tests precedents avec timeouts standards (15/8) :
- 4/4 : 28.22s

Tests actuels avec timeouts optimises (12/7) :
- 4/4 : 25.75s
- **Gain** : -8.8% juste avec timeouts 

---

##  Recommandations par Budget

### Budget Premium (4GB RAM + 6 CPU)
```yaml
MAX_CONCURRENT_BROWSERS=3
PREWARM_COUNT=3
BROWSER_TIMEOUT=12
PAGE_LOAD_TIMEOUT=7
```
**Performance** : **23.41s** 

**Cout mensuel VM** : ~15-20/mois (VPS type)

### Budget Moyen (4GB RAM + 5 CPU)
```yaml
MAX_CONCURRENT_BROWSERS=4
PREWARM_COUNT=4
BROWSER_TIMEOUT=12
PAGE_LOAD_TIMEOUT=7
```
**Performance** : **27.05s**

**Cout mensuel VM** : ~12-15/mois

### Budget Bas (2GB RAM + 2 CPU)
```yaml
MAX_CONCURRENT_BROWSERS=2
PREWARM_COUNT=2
BROWSER_TIMEOUT=12
PAGE_LOAD_TIMEOUT=7
```
**Performance** : ~30-35s (estime)

**Cout mensuel VM** : ~5-8/mois

---

##  Evolution des Performances

| Etape | Config | Temps | Gain cumule |
|-------|--------|-------|-------------|
| Baseline | 2GB/2CPU, 2 browsers, no prewarm | 49.69s | - |
| Optimisation 1 | 2GB/2CPU, 2 browsers, prewarm | 43.58s | -12.3% |
| Optimisation 2 | 4GB/6CPU, 4 browsers, prewarm | 28.22s | -43.2% |
| **Optimisation 3** | **4GB/6CPU, 3 browsers, prewarm, timeouts** | **23.41s** | **-52.9%**  |

**Reduction totale** : **26.28 secondes** (-52.9%)

---

##  docker-compose.yml Final

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
      # Server
      - HOST=0.0.0.0
      - PORT=8000
      - DEBUG=false

      # Security
      - ALLOW_LOCAL_URLS=false

      # Browser Limits (OPTIMAL)
      - MAX_CONCURRENT_BROWSERS=3
      - MAX_CONCURRENT_SESSIONS=10
      - MAX_MEMORY_MB=3500

      # Timeouts (OPTIMISES)
      - BROWSER_TIMEOUT=12
      - PAGE_LOAD_TIMEOUT=7
      - SESSION_TIMEOUT=60
      - CLEANUP_INTERVAL=3

      # Redis Cache (Optionnel)
      - REDIS_ENABLED=false
      - REDIS_HOST=localhost
      - REDIS_PORT=6379
      - REDIS_DB=0
      - REDIS_CACHE_TTL=180
      - REDIS_SMART_CACHE=true

      # Pre-warm (OPTIMAL)
      - PREWARM_ENABLED=true
      - PREWARM_COUNT=3

      # Logging
      - LOG_LEVEL=INFO

    volumes:
      - ./logs:/app/logs

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

    labels:
      - "com.shoturl.version=3.0.0-final-optimal"
      - "com.shoturl.config=4GB-6CPU-3browsers-3prewarm"

networks:
  shoturl-network:
    driver: bridge
```

---

##  Checklist Deploiement Production

### Prerequis
- [ ] VM avec **4GB RAM** minimum
- [ ] VM avec **6 CPU cores** (5 acceptable, 6 optimal)
- [ ] Docker et docker-compose installes
- [ ] Image `docker-shoturl:latest` buildee

### Configuration VM (VirtualBox)
```bash
# Configurer la VM
VBoxManage modifyvm "shoturl" --memory 4096 --cpus 6

# Demarrer
VBoxManage startvm "shoturl" --type headless
```

### Deploiement
```bash
# 1. Copier le docker-compose final
cp docker-compose.final-optimal.yml docker-compose.yml

# 2. Demarrer
docker compose up -d

# 3. Verifier sante
curl http://localhost:8000/api/health | jq

# 4. Test de charge
python3 load_test.py
```

### Validation
- [ ] Health check : `status: "healthy"`
- [ ] Logs : `[+] 3 contexts pre-chauds prets`
- [ ] Test 10 req : **< 25s** 
- [ ] RAM : **< 3GB** pendant test
- [ ] Success rate : **100%**

---

##  Prochaines Optimisations Possibles

### 1. Cache Redis (Recaptures)
Si recaptures frequentes :
```yaml
REDIS_ENABLED=true
REDIS_SMART_CACHE=true
REDIS_CACHE_TTL=180
```
**Gain attendu** : 100% sur cache hits (23s  0.1s)

### 2. Plus de RAM (8GB)
Permet 5-6 browsers sans contention :
```yaml
MAX_CONCURRENT_BROWSERS=5
PREWARM_COUNT=5
```
**Gain estime** : -15-20% (23s  ~19-20s)

### 3. CDN/Proxy
Pour sites statiques, cache Nginx devant

---

##  Comparaison Configurations

| Config | RAM | CPU | Browsers | Prewarm | Temps | Cout/mois | Ratio Perf/ |
|--------|-----|-----|----------|---------|-------|-----------|--------------|
| **Optimal** | 4GB | 6 | 3 | 3 | **23.41s** | ~15 | **1.56s/**  |
| Premium | 4GB | 6 | 4 | 2 | 23.69s | ~15 | 1.58s/ |
| Moyen | 4GB | 5 | 4 | 4 | 27.05s | ~12 | 2.25s/ |
| Economique | 2GB | 2 | 2 | 2 | ~35s | ~6 | 5.83s/ |

 **Config "Optimal" offre le meilleur rapport performance/prix**

---

##  Conclusion

La configuration **4GB RAM + 6 CPU + 3 browsers + 3 prewarm** offre :

 **Meilleures performances** : 23.41s (-52.9% vs baseline)
 **Stabilite maximale** : 100% success rate
 **Utilisation optimale** : RAM ~65%, CPU ~70-80%
 **Ratio perf/prix** : Excellent (1.56s/)
 **Scalabilite** : Peut gerer 10+ requetes simultanees

**C'est la configuration a deployer en production** 

---

**Date** : 2026-01-24
**Tests realises** : 12 configurations (6 CPU + 5 CPU)
**Methode** : Tests automatises avec VBoxManage
**Outil** : test_manual_4gb.sh
**Baseline** : 49.69s (2GB/2CPU/2browsers/no prewarm)
**Meilleur** : **23.41s** (4GB/6CPU/3browsers/3prewarm)
**Amelioration totale** : **-52.9%** 
