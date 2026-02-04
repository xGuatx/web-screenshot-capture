# ShotURL v3.0 - Quick Reference Card 

##  Resume Ultra-Rapide

| Metrique | Valeur |
|----------|--------|
| **Version** | v3.0.0-optimized-v2 |
| **Gain observe** | -12% (49.69s  43.58s) |
| **RAM actuelle** | 2GB |
| **Browsers actifs** | 2 |
| **Optimisations** | Parallelisation + Pre-warm + Cache |
| **Production ready** |  Oui |

---

##  Commandes Rapides

### Demarrage
```bash
# Sans cache (defaut)
docker compose -f docker-compose.final.yml up -d

# Avec cache + pre-warm
docker compose -f docker-compose.optimized-v2.yml up -d
```

### Monitoring
```bash
# Health check
curl http://localhost:8000/api/health | jq

# Logs pre-warm
docker logs shoturl-v3 | grep PREWARM

# Logs cache
docker logs shoturl-v3 | grep "CACHE"

# RAM usage
docker stats shoturl-v3 --no-stream
```

### Tests
```bash
# Load test (10 requetes)
python3 load_test.py

# Single capture
curl -X POST http://localhost:8000/api/capture \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.twitch.tv/gotaga", "delay": 2}'
```

---

##  Variables Cles

### Browsers
```bash
MAX_CONCURRENT_BROWSERS=2    # 2GB: 2 | 4GB: 4 | 8GB: 6
MAX_CONCURRENT_SESSIONS=10   # Sessions max simultanees
MAX_MEMORY_MB=3500           # Alerte RAM (70% de total)
```

### Pre-warm (Performance)
```bash
PREWARM_ENABLED=false        # true = +1-2s gain premiere capture
PREWARM_COUNT=2              # Contexts chauds (impact: +300-500MB RAM/context)
```

### Cache Redis (Recaptures)
```bash
REDIS_ENABLED=false          # true = gain 100% sur recaptures
REDIS_CACHE_TTL=180          # 30s | 180s | 600s | 3600s
REDIS_SMART_CACHE=true       # true = skip delay=0, Twitch, etc.
```

---

##  Performance par Config

| Config | RAM | CPU | Browsers | Prewarm | Cache | Temps 10 req | Gain |
|--------|-----|-----|----------|---------|-------|--------------|------|
| **Actuel** | 2GB | 2 | 2 |  |  | **43.58s** | -12% |
| 4GB opt | 4GB | 4 | 4 |  |  | ~20s | **-54%** |
| 8GB perf | 8GB | 4 | 6 |  |  | ~14s | **-68%** |

---

##  Recommandations par RAM

### 2GB (actuel) 
```yaml
MAX_CONCURRENT_BROWSERS=2
PREWARM_ENABLED=true
PREWARM_COUNT=2
REDIS_ENABLED=false
```

### 4GB (upgrade recommande) 
```yaml
MAX_CONCURRENT_BROWSERS=4
PREWARM_ENABLED=true
PREWARM_COUNT=4
REDIS_ENABLED=true
```

### 8GB (haute performance) 
```yaml
MAX_CONCURRENT_BROWSERS=6
PREWARM_ENABLED=true
PREWARM_COUNT=4
REDIS_ENABLED=true
MAX_MEMORY_MB=7000
```

---

##  Troubleshooting Express

### Logs montrent "CACHE SKIP" trop souvent
```bash
# Desactiver smart cache
REDIS_SMART_CACHE=false
```

### RAM > 90%
```bash
# Reduire browsers ou prewarm
MAX_CONCURRENT_BROWSERS=2
PREWARM_COUNT=2
```

### Cache ne marche pas
```bash
# Verifier Redis running
redis-cli ping  #  PONG

# Verifier logs connexion
docker logs shoturl-v3 | grep "Redis cache"
```

### Premiere capture lente
```bash
# Activer pre-warm
PREWARM_ENABLED=true
PREWARM_COUNT=2
```

---

##  Docs Completes

- **[README_OPTIMIZATIONS.md](./README_OPTIMIZATIONS.md)** - Guide principal
- **[OPTIMIZATIONS_V2.md](./OPTIMIZATIONS_V2.md)** - Details techniques
- **[FINAL_RESULTS.md](./FINAL_RESULTS.md)** - Tests de performance
- **[CACHE_GUIDE.md](./CACHE_GUIDE.md)** - Cache intelligent
- **[HARDWARE_SCALING.md](./HARDWARE_SCALING.md)** - Scaling RAM/CPU

---

##  Gains par Optimisation

| Optimisation | Quand l'utiliser | Gain | Cout RAM |
|--------------|------------------|------|----------|
| **Parallelisation** | Toujours (auto) | 1-1.5s/capture | 0MB |
| **Pre-warm** | RAM  2GB | 1-2s premiere capture | +500MB |
| **Cache Redis** | Recaptures frequentes | 100% sur hit | +50MB |

---

##  Production Checklist

- [ ] RAM disponible  2GB
- [ ] Config adaptee a RAM (voir tableau ci-dessus)
- [ ] Si cache : Redis installe et running
- [ ] Test 10 requetes < 50s (2GB) ou < 25s (4GB)
- [ ] `/api/health` status = healthy
- [ ] RAM < 90% pendant load test
- [ ] Logs sans erreurs critiques

---

**Version** : v3.0.0-optimized-v2
**Date** : 2026-01-23
**Status** :  Production Ready
