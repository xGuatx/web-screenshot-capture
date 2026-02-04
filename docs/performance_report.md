# ShotURL - Performance Test Report

## Environment
- **VM**: VirtualBox (2 CPU cores, 2GB RAM)
- **Host**: 192.168.56.102:8000
- **Test**: 10 concurrent capture requests

## Results Comparison

### Configuration Originale (4GB optimized)
```
MAX_CONCURRENT_BROWSERS=4
MAX_CONCURRENT_SESSIONS=10
MAX_MEMORY_MB=3500
BROWSER_TIMEOUT=20
PAGE_LOAD_TIMEOUT=10
```

**Resultats:**
-  Success: 10/10 (100%)
-  First completed: **3.18s**
-  Last completed: **28.09s**
-  Average: **17.39s**
-  Total test time: **28.10s**

### Configuration Optimisee (2GB VM)
```
MAX_CONCURRENT_BROWSERS=2
MAX_CONCURRENT_SESSIONS=5
MAX_MEMORY_MB=1800
BROWSER_TIMEOUT=15
PAGE_LOAD_TIMEOUT=8
```

**Resultats:**
-  Success: 10/10 (100%)
-  First completed: **1.66s** ( 47% faster)
-  Last completed: **20.24s** ( 28% faster)
-  Average: **10.48s** ( 40% faster)
-  Total test time: **20.24s** ( 28% faster)

## Amelioration Globale

| Metrique | Avant | Apres | Amelioration |
|----------|-------|-------|--------------|
| First request | 3.18s | 1.66s | **-47.8%**  |
| Last request | 28.09s | 20.24s | **-27.9%**  |
| Average time | 17.39s | 10.48s | **-39.7%**  |
| Total time | 28.10s | 20.24s | **-28.0%**  |

## Analyse

### Pourquoi c'est plus rapide?

1. **Moins de contention memoire**
   - Avec 4 browsers sur 2GB, le systeme swappait probablement
   - Avec 2 browsers, tout reste en RAM

2. **Timeouts plus courts**
   - PAGE_LOAD_TIMEOUT reduit de 10s  8s
   - Evite d'attendre trop longtemps les pages lentes

3. **Cleanup plus frequent**
   - CLEANUP_INTERVAL: 30s  20s
   - Libere la memoire plus rapidement

4. **Moins de sessions**
   - MAX_CONCURRENT_SESSIONS: 10  5
   - Reduit l'overhead de gestion

## Detail des captures (optimise)

| # | URL | Temps |
|---|-----|-------|
| 1 | example.com | 1.66s  |
| 2 | stackoverflow.com | 3.09s  |
| 3 | github.com | 5.43s |
| 4 | wikipedia.org | 7.24s |
| 5 | reddit.com | 8.79s |
| 6 | amazon.com | 11.71s |
| 7 | twitter.com | 14.53s |
| 8 | linkedin.com | 14.67s |
| 9 | instagram.com | 17.45s |
| 10 | youtube.com | 20.24s |

## Recommandations

### Pour production avec 2GB RAM:
 Utiliser `docker-compose.optimized.yml`

### Pour ameliorer encore:
1. **Augmenter la RAM a 4GB**  permettrait 4 browsers concurrents
2. **Ajouter un cache Redis**  eviter recaptures identiques
3. **Implementer queue systeme**  mieux gerer pics de charge
4. **Monitoring avec Prometheus**  identifier bottlenecks

### Limite theorique:
Avec la config actuelle (2 browsers simultanes):
- **Debit max**: ~6 captures/minute (10s avg)
- **Pour 10 req simultanees**: 20-30s est optimal

## Conclusion

La configuration optimisee reduit le temps moyen de **40%** tout en maintenant 100% de succes.

Le goulot d'etranglement principal est maintenant la limite de 2 browsers concurrents, ce qui est approprie pour une VM avec 2GB RAM.

**Verdict**:  Configuration optimale pour les ressources disponibles
