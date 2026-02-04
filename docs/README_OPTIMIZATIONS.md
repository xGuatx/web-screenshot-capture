# ShotURL v3.0 - Guide des Optimisations 

##  Documentation Disponible

Ce projet inclut une documentation complete sur les optimisations de performance :

### 1. [OPTIMIZATIONS_V2.md](./OPTIMIZATIONS_V2.md) - Guide Principal
** Vue d'ensemble des 3 optimisations implementees**
-  Parallelisation (DOM + Screenshot + HTML)
-  Pre-warm Contexts (contexts Chrome pre-chauds)
-  Cache Redis (optionnel)
- Configuration recommandee par usage (dev/prod/haute-perf)
- Troubleshooting et monitoring

### 2. [FINAL_RESULTS.md](./FINAL_RESULTS.md) - Resultats des Tests
** Metriques reelles de performance**
- Tests avec 10 requetes Twitch simultanees
- Baseline: 49.69s  Optimise: 43.58s (**-12% gain**)
- Consommation RAM et CPU
- Configuration recommandee par hardware (2GB, 4GB, 8GB, 16GB)

### 3. [CACHE_GUIDE.md](./CACHE_GUIDE.md) - Guide du Cache Intelligent
** Systeme de cache Redis avec regles strictes**
-  Skip si `delay=0` (page possiblement incomplete)
-  Skip domaines dynamiques (Twitch, YouTube, Instagram, etc.)
-  Skip si < 5 requetes reseau
- Configuration TTL (30s, 3min, 10min, 1h)
- Tests de validation et monitoring

### 4. [HARDWARE_SCALING.md](./HARDWARE_SCALING.md) - Impact Hardware
** Analyse RAM/CPU vs Performance**
- RAM seule: < 1% gain 
- CPU seul: ~8% gain 
- RAM+CPU+config: **54% gain** 
- Formule optimale pour calcul `MAX_CONCURRENT_BROWSERS`
- Projections de performance par configuration

---

##  Quick Start

### Configuration par Defaut (2GB RAM)
```yaml
# docker-compose.final.yml
MAX_CONCURRENT_BROWSERS=2
PREWARM_ENABLED=false
REDIS_ENABLED=false
```
**Performance**: 43.58s pour 10 requetes Twitch

### Configuration Optimisee (4GB RAM)
```yaml
# docker-compose.optimized-v2.yml
MAX_CONCURRENT_BROWSERS=4
PREWARM_ENABLED=true
PREWARM_COUNT=4
REDIS_ENABLED=true
REDIS_CACHE_TTL=180
REDIS_SMART_CACHE=true
```
**Performance estimee**: ~20s pour 10 requetes Twitch (**-54%**)

---

##  Gains par Optimisation

| Optimisation | Activation | Gain | Impact RAM |
|--------------|------------|------|------------|
| **Parallelisation** | Automatique | 1-1.5s/capture | Aucun |
| **Pre-warm** | `PREWARM_ENABLED=true` | 1-2s (premiere capture) | +300-500MB |
| **Cache Redis** | `REDIS_ENABLED=true` | 100% sur recaptures | Minimal |

**Gain cumule observe**: **-12%** sur 10 requetes (49.69s  43.58s)

---

##  Scenarios d'Usage

### Cas 1 : Sites Legers (E-commerce, Blogs)
```yaml
PREWARM_ENABLED=false
REDIS_ENABLED=true
REDIS_CACHE_TTL=3600  # 1h
REDIS_SMART_CACHE=false  # Pages statiques OK
```
 Cache tres efficace (70%+ hit rate)

### Cas 2 : Sites Dynamiques (Twitch, YouTube)
```yaml
PREWARM_ENABLED=true
PREWARM_COUNT=2
REDIS_ENABLED=true
REDIS_SMART_CACHE=true  #  Important !
REDIS_CACHE_TTL=60  # TTL court
```
 Cache intelligent evite captures incompletes

### Cas 3 : Analyse Forensics (Fraicheur critique)
```yaml
PREWARM_ENABLED=false
REDIS_ENABLED=false
```
 Chaque capture est fraiche, pas de cache

---

##  Variables d'Environnement

### Pre-warm Contexts
```bash
PREWARM_ENABLED=false        # Activer pre-warm (defaut: false)
PREWARM_COUNT=2              # Nombre de contexts chauds (defaut: 2)
```

### Cache Redis
```bash
REDIS_ENABLED=false          # Activer Redis (defaut: false)
REDIS_HOST=localhost         # Hote Redis (defaut: localhost)
REDIS_PORT=6379              # Port Redis (defaut: 6379)
REDIS_DB=0                   # Base Redis (defaut: 0)
REDIS_CACHE_TTL=180          # Duree cache en secondes (defaut: 180s = 3min)
REDIS_SMART_CACHE=true       # Regles intelligentes (defaut: true)
```

**Valeurs TTL recommandees**:
- `30` = 30 secondes (dev/test)
- `180` = 3 minutes (defaut, contenu mixte)
- `600` = 10 minutes (pages semi-statiques)
- `3600` = 1 heure (pages statiques)

---

##  Monitoring

### Health Endpoint
```bash
curl http://localhost:8000/api/health | jq
```

```json
{
  "browser_pool": {
    "prewarm_contexts": 2,
    "prewarm_enabled": true
  },
  "cache": {
    "enabled": true,
    "status": "connected",
    "cached_captures": 15,
    "keyspace_hits": 42,
    "keyspace_misses": 18
  }
}
```

**Hit rate** = hits / (hits + misses) = 42/(42+18) = **70%**

### Logs Utiles
```bash
# Pre-warm
docker logs shoturl-v3 | grep PREWARM

# Cache
docker logs shoturl-v3 | grep -E "CACHE (HIT|MISS|SET|SKIP)"
```

---

##  Points d'Attention

### Cache Intelligent (REDIS_SMART_CACHE=true)
Le cache **ne stocke PAS** les captures si :
1. `delay=0` (page possiblement incomplete)
2. Domaine dynamique (twitch.tv, youtube.com, etc.)
3. < 5 requetes reseau (page incomplete)

 **Garantit coherence** mais reduit hit rate (~30-50% vs 70%+ en mode agressif)

### Pre-warm Contexts
- Consomme **300-500MB RAM par context**
- Avec `PREWARM_COUNT=2` sur 2GB RAM : OK 
- Avec `PREWARM_COUNT=4` sur 2GB RAM : Risque swap 

---

##  Deploiement

### Sans Redis (Production Simple)
```bash
docker compose -f docker-compose.final.yml up -d
```

### Avec Redis (Production Optimisee)
```bash
# 1. Demarrer Redis
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 2. Demarrer ShotURL avec cache
docker compose -f docker-compose.optimized-v2.yml up -d

# 3. Verifier cache connecte
curl http://localhost:8000/api/health | jq '.cache.status'
#  "connected"
```

---

##  Lectures Recommandees

1. **Debuter** : Lire [OPTIMIZATIONS_V2.md](./OPTIMIZATIONS_V2.md) pour comprendre les 3 optimisations
2. **Tests** : Lire [FINAL_RESULTS.md](./FINAL_RESULTS.md) pour les resultats reels
3. **Cache** : Lire [CACHE_GUIDE.md](./CACHE_GUIDE.md) pour configurer Redis correctement
4. **Scaling** : Lire [HARDWARE_SCALING.md](./HARDWARE_SCALING.md) avant d'augmenter RAM/CPU

---

##  Recommandations Finales

### Pour 2GB RAM (actuel)
```yaml
MAX_CONCURRENT_BROWSERS=2
PREWARM_ENABLED=true
PREWARM_COUNT=2
REDIS_ENABLED=false  # Optionnel
```
**Performance**: 43.58s/10 req Twitch (-12% vs baseline)

### Pour 4GB RAM (recommande)
```yaml
MAX_CONCURRENT_BROWSERS=4
PREWARM_ENABLED=true
PREWARM_COUNT=4
REDIS_ENABLED=true
REDIS_SMART_CACHE=true
```
**Performance estimee**: ~20s/10 req Twitch (-54% vs baseline)

### Pour 8GB RAM (haute performance)
```yaml
MAX_CONCURRENT_BROWSERS=6
PREWARM_ENABLED=true
PREWARM_COUNT=4
REDIS_ENABLED=true
MAX_MEMORY_MB=7000
```
**Performance estimee**: ~14s/10 req Twitch (-68% vs baseline)

---

##  Checklist Production

- [ ] Lire la documentation (OPTIMIZATIONS_V2.md minimum)
- [ ] Choisir configuration selon RAM disponible
- [ ] Si Redis : installer Redis et tester connexion
- [ ] Deployer avec docker-compose approprie
- [ ] Verifier `/api/health` apres demarrage
- [ ] Tester avec 10 requetes simultanees
- [ ] Monitorer RAM < 90% et swap minimal
- [ ] Si cache : verifier hit rate > 30%

---

**Version** : ShotURL v3.0.0-optimized-v2
**Date** : 2026-01-23
**Optimisations** : Parallelisation + Pre-warm + Cache Redis Intelligent
**Tests** : 10 requetes Twitch simultanees, VM 2GB RAM
**Gain observe** : -12% (49.69s  43.58s)
**Gain potentiel (4GB)** : -54% (49.69s  ~20s)
