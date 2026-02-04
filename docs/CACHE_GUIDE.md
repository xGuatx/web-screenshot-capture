# ShotURL - Guide du Cache Redis Intelligent

##  Probleme : Cache et Captures Incompletes

### Scenario Problematique
```
User: Capture Twitch sans delay
 Page charge 50% seulement
 Screenshot partiel mis en cache (3 min)
 Requetes suivantes  servent le cache 

Resultat: Screenshots incomplets pendant 3 minutes
```

---

##  Solution : Cache Intelligent

### Regles Implementees (REDIS_SMART_CACHE=true)

####  Regle 1 : Skip si delay=0
**Pourquoi** : Sans delay, la page n'a peut-etre pas fini de charger

```yaml
delay=0  PAS DE CACHE 
delay1  OK CACHE 
```

**Exemple** :
```
Twitch delay=0 : Screenshot a 2s de chargement  SKIP CACHE
Twitch delay=5 : Page completement chargee  CACHE OK
```

####  Regle 2 : Skip domaines dynamiques
**Pourquoi** : Contenu change constamment (live streams, posts, etc.)

**Liste noire** :
- twitch.tv
- youtube.com
- instagram.com
- twitter.com / x.com
- facebook.com

```yaml
https://twitch.tv/gotaga  SKIP CACHE 
https://example.com  OK CACHE 
```

####  Regle 3 : Skip si < 5 requetes reseau
**Pourquoi** : Trop peu de requetes = page n'a pas charge ses ressources

```
network_logs: 2 requetes  SKIP CACHE 
network_logs: 50 requetes  OK CACHE 
```

---

##  Configuration

### Variables d'environnement

```yaml
# Activer Redis
REDIS_ENABLED=true/false           # Defaut: false

# Configuration Redis
REDIS_HOST=localhost               # Defaut: localhost
REDIS_PORT=6379                    # Defaut: 6379
REDIS_DB=0                         # Defaut: 0

# Duree de vie du cache
REDIS_CACHE_TTL=180               # Defaut: 180s (3 min)
                                  # Valeurs: 30, 60, 180, 600, 3600

# Cache intelligent (IMPORTANT)
REDIS_SMART_CACHE=true/false      # Defaut: true
```

### Modes de Cache

#### Mode 1 : Cache Intelligent (recommande)
```yaml
REDIS_ENABLED=true
REDIS_SMART_CACHE=true           #  Important !
REDIS_CACHE_TTL=180
```

**Comportement** :
-  Cache uniquement les captures "sures"
-  Skip delay=0
-  Skip Twitch/YouTube/etc
-  Skip pages avec < 5 requetes

**Usage** : Production avec contenu mixte

#### Mode 2 : Cache Agressif
```yaml
REDIS_ENABLED=true
REDIS_SMART_CACHE=false          # Cache TOUT
REDIS_CACHE_TTL=60               # TTL court
```

**Comportement** :
-  Cache TOUTES les captures
-  Risque de servir du contenu incomplet

**Usage** : Dev/test uniquement, sites statiques

#### Mode 3 : Pas de cache (defaut)
```yaml
REDIS_ENABLED=false
```

**Comportement** :
- Chaque capture est fraiche
- Pas besoin de Redis

**Usage** : Production simple, faible trafic

---

##  Impact Performance

### Sans Cache
```
Requete 1 : 4.5s
Requete 2 (meme URL) : 4.5s
Requete 3 (meme URL) : 4.5s

Total : 13.5s
```

### Avec Cache (smart)
```
Requete 1 : 4.5s (MISS  cache)
Requete 2 (delay=0) : 4.5s (SKIP cache car delay=0)
Requete 3 (delay=2) : 4.5s (MISS car req2 pas cachee)

Total : 13.5s (pas de gain, mais coherence )
```

### Avec Cache (agressif, sites statiques)
```
Requete 1 : 4.5s (MISS  cache)
Requete 2 (meme URL) : 0.1s (HIT)
Requete 3 (meme URL) : 0.1s (HIT)

Total : 4.7s (gain 71% )
```

---

##  Monitoring

### Logs a surveiller

```bash
# Cache active
[+] Redis cache active: localhost:6379 (TTL: 180s)

# Cache hit
[CACHE HIT] Serving cached capture for https://example.com

# Cache miss
[CACHE MISS] https://example.com

# Cache set (accepte)
[CACHE SET] https://example.com (TTL: 180s)

# Cache skip (regles smart)
[CACHE SKIP] https://twitch.tv/gotaga - delay=0 (page possiblement incomplete)
[CACHE SKIP] https://twitch.tv/gotaga - domaine dynamique
[CACHE SKIP] https://example.com - trop peu de requetes reseau (2)
```

### Stats via API

```bash
curl http://localhost:8000/api/health | jq '.cache'
```

```json
{
  "enabled": true,
  "status": "connected",
  "host": "localhost:6379",
  "ttl_seconds": 180,
  "cached_captures": 15,
  "keyspace_hits": 42,
  "keyspace_misses": 18
}
```

**Hit rate** : 42/(42+18) = **70%**

---

##  Tests de Validation

### Test 1 : Cache skip delay=0
```bash
# Requete avec delay=0 (2 fois meme URL)
curl -X POST http://localhost:8000/api/capture \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "delay": 0}'

curl -X POST http://localhost:8000/api/capture \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "delay": 0}'

# Logs attendus:
# [CACHE SKIP] ... delay=0
# [CACHE SKIP] ... delay=0
#  Pas de cache HIT 
```

### Test 2 : Cache OK avec delay
```bash
# Requete avec delay=2 (2 fois)
curl -X POST http://localhost:8000/api/capture \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "delay": 2}'

curl -X POST http://localhost:8000/api/capture \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "delay": 2}'

# Logs attendus:
# 1ere: [CACHE SET] ... (TTL: 180s)
# 2eme: [CACHE HIT] Serving cached capture
#  Cache fonctionne 
```

### Test 3 : Skip domaines dynamiques
```bash
curl -X POST http://localhost:8000/api/capture \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.twitch.tv/gotaga", "delay": 5}'

# Logs attendus:
# [CACHE SKIP] ... domaine dynamique
#  Twitch jamais cache 
```

---

##  Recommandations par Usage

### Usage 1 : Site E-commerce / Catalogue
```yaml
REDIS_ENABLED=true
REDIS_SMART_CACHE=false   # Pages statiques OK
REDIS_CACHE_TTL=3600      # 1 heure
```
**Gain** : 90%+ sur recaptures

### Usage 2 : Monitoring / Phishing
```yaml
REDIS_ENABLED=true
REDIS_SMART_CACHE=true    # Important : contenu dynamique
REDIS_CACHE_TTL=60        # TTL court
```
**Gain** : 30-50% sur recaptures

### Usage 3 : Analyse Malware / Forensics
```yaml
REDIS_ENABLED=false        # Toujours fresh
```
**Gain** : 0%, mais garantie de fraicheur 

### Usage 4 : Dev/Test
```yaml
REDIS_ENABLED=true
REDIS_SMART_CACHE=false
REDIS_CACHE_TTL=30         # 30s pour tests rapides
```
**Gain** : Tests 10x plus rapides

---

##  Limitations

### Ce que le cache intelligent NE fait PAS

1. **Ne detecte pas les erreurs JS**
   - Si la page a des erreurs  peut quand meme cacher

2. **Ne verifie pas le contenu visuel**
   - Screenshot peut etre blanc/incomplet

3. **Ne gere pas les authentifications**
   - Page "login required" peut etre cachee

4. **Ne detecte pas les bots blocks**
   - Captcha/block peut etre cache

### Recommandation

Pour usage critique  **desactiver le cache** :
```yaml
REDIS_ENABLED=false
```

Chaque capture sera toujours fraiche et complete.

---

##  Depannage

### Cache ne fonctionne jamais
```bash
# Verifier que smart cache n'est pas trop strict
docker logs shoturl-v3 | grep "CACHE SKIP"

# Si beaucoup de SKIP  desactiver smart cache
REDIS_SMART_CACHE=false
```

### Cache sert du contenu incomplet
```bash
# Activer smart cache
REDIS_SMART_CACHE=true

# OU reduire TTL
REDIS_CACHE_TTL=30
```

### Redis connexion echoue
```bash
# Verifier Redis running
redis-cli ping  #  PONG

# Verifier depuis container
docker exec shoturl-v3 curl telnet://localhost:6379
```

---

##  Checklist Deploiement Cache

### Avant d'activer le cache

- [ ] Redis installe et running
- [ ] Tests avec delay=0  verifier SKIP
- [ ] Tests avec delay1  verifier CACHE SET
- [ ] Tests domaines dynamiques  verifier SKIP
- [ ] Verifier hit rate > 30% sur `/api/health`
- [ ] Confirmer pas de screenshots incomplets

### En production

- [ ] Monitoring hit rate regulier
- [ ] Alertes si hit rate < 10% (cache inutile)
- [ ] Review logs CACHE SKIP regulierement
- [ ] Ajuster TTL selon usage
- [ ] Documenter quels domaines sont caches

---

**Date** : 2026-01-23
**Version** : ShotURL v3.0.0-optimized-v2
**Cache** : Smart cache avec regles de coherence
