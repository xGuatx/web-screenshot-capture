# ShotURL v3.0 - Optimisations Avancees

##  Nouvelles Fonctionnalites Implementees

### 1. **Parallelisation DOM + Screenshot + HTML**

**Avant** (sequentiel) :
```python
screenshot = await page.screenshot(...)  # 0.5-1s
dom_elements = await DOMExtractor.extract_elements(page)  # 1-2s
html_source = await page.content()  # 0.5s
# Total: 2-3.5s
```

**Apres** (parallele) :
```python
tasks = [
    page.screenshot(...),
    DOMExtractor.extract_elements(page),
    page.content() if grab_html else None
]
results = await asyncio.gather(*tasks)
# Total: ~1-2s (gain 50%)
```

**Gain estime** : **1-1.5s par capture** (50% plus rapide sur extraction donnees)

---

### 2. **Pre-warm Contexts**

**Concept** : Garde toujours N contexts Chrome "chauds" prets a l'emploi

**Fonctionnement** :
1. Au demarrage : Cree 2 contexts pre-chauds
2. Quand une requete arrive : Utilise un context pre-chaud (instantane)
3. En arriere-plan : Recree un nouveau context immediatement
4. Resultat : Toujours 2 contexts prets

**Configuration** :
```yaml
PREWARM_ENABLED=true   # false par defaut
PREWARM_COUNT=2        # Nombre de contexts chauds
```

**Gain estime** : **1-2s** sur premiere capture (skip creation context)

**Impact memoire** : +300-500MB (contexts gardes en RAM)

---

### 3. **Cache Redis (Optionnel)**

**Concept** : Met en cache les captures pour eviter recaptures identiques

**Cle de cache** : Hash SHA256 de `(URL + device + full_page + delay + grab_html)`

**Fonctionnement** :
1. Requete arrive  Check cache Redis
2. Si trouve (HIT) : Retour instantane (0.01-0.1s)
3. Si manquant (MISS) : Capture normale + stockage en cache
4. Expiration : TTL configurable (defaut 3min)

**Configuration** :
```yaml
REDIS_ENABLED=false         # false par defaut (pas de Redis requis)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_CACHE_TTL=180         # Duree cache en secondes
```

**Valeurs TTL recommandees** :
- `30` = 30 secondes (dev/test)
- `180` = 3 minutes (defaut)
- `600` = 10 minutes (pages statiques)
- `3600` = 1 heure (rarement mis a jour)

**Gain** :
- **100% sur recaptures** (de 30s  0.1s)
- Depend du taux de recapture (URLs identiques)

**Installation Redis (si active)** :
```bash
# Docker
docker run -d -p 6379:6379 redis:7-alpine

# OU Arch Linux
sudo pacman -S redis
sudo systemctl start redis
```

---

##  Gains Estimes par Scenario

### Scenario 1 : Sans cache, sans prewarm (defaut)
```
Capture Twitch : ~30s
- Chargement page : 10s
- Extraction : 2s (DOM + screenshot + HTML sequentiel)
- Overhead : 18s (attente queue)

Total 10 requetes : ~50s
```

### Scenario 2 : Parallelisation activee (automatique)
```
Capture Twitch : ~28-29s
- Chargement page : 10s
- Extraction : 1s (parallele)  Gain 1s
- Overhead : 17-18s

Total 10 requetes : ~47-48s (gain ~5%)
```

### Scenario 3 : Prewarm active
```
Capture Twitch (premiere) : ~27s
- Creation context : 0s (pre-chaud)  Gain 1-2s
- Chargement page : 10s
- Extraction : 1s (parallele)
- Overhead : 16s

Total 10 requetes : ~45s (gain ~10%)
```

### Scenario 4 : Prewarm + Cache (meme URL)
```
Premiere capture : ~27s
Captures suivantes (3min) : ~0.1s  Gain 99.6%

Total 10 requetes (meme URL) : ~27s + 90.1s = ~28s
vs 50s sans cache = gain ~44%
```

### Scenario 5 : Prewarm + Cache (URLs variees, 50% recapture)
```
5 nouvelles URLs : 5  27s = 135s
5 recaptures : 5  0.1s = 0.5s

Total : ~135.5s vs 250s = gain ~46%
```

---

##  Configuration Recommandee par Usage

### Dev/Test (local)
```yaml
PREWARM_ENABLED=true      # Activer pour tests
PREWARM_COUNT=2
REDIS_ENABLED=false       # Pas besoin Redis en dev
```

### Production Legere (2GB RAM, faible trafic)
```yaml
PREWARM_ENABLED=false     # Economiser RAM
REDIS_ENABLED=false       # Pas de recaptures frequentes
```
 Config actuelle optimale

### Production Moyenne (4GB RAM, trafic modere)
```yaml
PREWARM_ENABLED=true      # Activer prewarm
PREWARM_COUNT=2
REDIS_ENABLED=true        # Cache pour recaptures
REDIS_CACHE_TTL=180       # 3min
MAX_CONCURRENT_BROWSERS=3 # 3 browsers avec 4GB
```
 Gain ~15-20% vs config actuelle

### Production Haute Performance (8GB+ RAM, fort trafic)
```yaml
PREWARM_ENABLED=true
PREWARM_COUNT=4           # 4 contexts chauds
REDIS_ENABLED=true
REDIS_CACHE_TTL=600       # 10min
MAX_CONCURRENT_BROWSERS=6 # 6 browsers
```
 Gain ~30-40% vs config actuelle

---

##  Monitoring & Debugging

### Health Endpoint Stats
```json
GET /api/health

{
  "status": "healthy",
  "browser_pool": {
    "active_contexts": 2,
    "prewarm_contexts": 2,
    "prewarm_enabled": true,
    "max_contexts": 2
  },
  "cache": {
    "enabled": true,
    "status": "connected",
    "host": "localhost:6379",
    "ttl_seconds": 180,
    "cached_captures": 15,
    "keyspace_hits": 42,
    "keyspace_misses": 18
  }
}
```

### Logs a surveiller
```
[PREWARM] Creation de 2 contexts pre-chauds...
[+] 2 contexts pre-chauds prets

[PREWARM] Utilisation context pre-chaud (1 restants)
[PREWARM] Context recharge (2/2)

[CACHE HIT] Serving cached capture for https://...
[CACHE MISS] https://...
[CACHE SET] https://... (TTL: 180s)
```

---

##  Troubleshooting

### Prewarm ne fonctionne pas
```bash
# Verifier les logs
docker logs shoturl-v3 | grep PREWARM

# Si aucun log  verifier variable
docker exec shoturl-v3 env | grep PREWARM
```

### Redis ne se connecte pas
```bash
# Tester connexion
redis-cli ping  # Doit retourner PONG

# Verifier depuis container
docker exec shoturl-v3 curl -v telnet://localhost:6379
```

### Cache ne fonctionne pas
```bash
# Verifier cles Redis
redis-cli KEYS "shoturl:capture:*"

# Voir stats
redis-cli INFO stats | grep keyspace
```

---

##  Metriques de Performance

### Tests avec Twitch (10 requetes simultanees)

| Config | Prewarm | Cache | Premiere | Moyenne | Total | Gain |
|--------|---------|-------|----------|---------|-------|------|
| Baseline |  |  | 11.83s | 33.16s | 55.45s | - |
| Parallelisation |  |  | 10.24s | 29.75s | 49.69s | 10% |
| + Prewarm |  |  | 9s* | 28s* | 45s* | 19%* |
| + Cache (50% hit) |  |  | 9s* | 14s* | 27s* | 51%* |

*Estimations basees sur gains theoriques

---

##  Implementation Technique

### Fichiers modifies

1. **`api/config.py`**
   - Ajout variables Redis (REDIS_ENABLED, REDIS_HOST, etc.)
   - Ajout variables Prewarm (PREWARM_ENABLED, PREWARM_COUNT)

2. **`api/cache.py`** (nouveau)
   - Module cache Redis complet
   - `get_cached_capture()` / `set_cached_capture()`
   - `get_cache_stats()` pour monitoring

3. **`api/browser.py`**
   - Ajout `prewarm_contexts` list
   - `_prewarm_contexts()` au demarrage
   - `_refill_prewarm()` pour recharger contexts
   - Logique pour utiliser/refill contexts chauds

4. **`api/capture.py`**
   - Parallelisation avec `asyncio.gather()`
   - Screenshot + DOM + HTML en parallele

5. **`api/routes.py`**
   - Check cache avant capture
   - Set cache apres capture reussie
   - Ajout cache stats dans `/api/health`

6. **`requirements.txt`**
   - Ajout `redis==5.0.1`

7. **`docker-compose.*.yml`**
   - Ajout variables d'environnement

---

##  Checklist Deploiement

### Sans Redis (defaut)
- [ ] Verifier `REDIS_ENABLED=false`
- [ ] Decider si activer `PREWARM_ENABLED`
- [ ] Deploy avec `docker-compose.final.yml`
- [ ] Verifier `/api/health` : cache.enabled = false

### Avec Redis
- [ ] Installer/demarrer Redis
- [ ] Set `REDIS_ENABLED=true`
- [ ] Set `REDIS_HOST` et `REDIS_PORT`
- [ ] Choisir `REDIS_CACHE_TTL`
- [ ] Deploy avec `docker-compose.optimized-v2.yml`
- [ ] Verifier `/api/health` : cache.status = "connected"
- [ ] Tester cache hit/miss dans logs

### Tests de validation
- [ ] Test 10 requetes simultanees < 50s
- [ ] Si prewarm: verifier logs "context pre-chaud"
- [ ] Si cache: 2eme capture meme URL < 1s
- [ ] RAM < 90% pendant test
- [ ] Aucun swap excessif

---

**Date** : 2026-01-23
**Version** : ShotURL v3.0.0-optimized-v2
