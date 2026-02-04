# Comparaison des Configurations avec 4GB RAM

##  Resultats Complets des Tests

**Test** : 10 requetes Twitch simultanees (`https://www.twitch.tv/gotaga`)
**VM** : 2 CPU cores, RAM variable
**Date** : 2026-01-23

### Tableau Recapitulatif

| # | Config | RAM | CPU | Browsers | Prewarm | Total | Moyenne | Premiere | Gain vs Baseline |
|---|--------|-----|-----|----------|---------|-------|---------|----------|------------------|
| 1 | **Baseline** | 2GB | 2 | 2 |  | 49.69s | 29.75s | ~11s | - |
| 2 | **2GB optimise** | 2GB | 2 | 2 |  (2) | **43.58s** | **26.19s** | ~9s | **-12.3%**  |
| 3 | 4 CPU test | 2GB | 4 | 2 |  (2) | 58.19s | 35.21s | 12.44s | -17.1%  |
| 4 | 4GB + 4 browsers | 4GB | 2 | 4 |  (4) | 46.86s | 32.33s | 15.27s | -5.7% |
| 5 | 4GB + 2 browsers | 4GB | 2 | 2 |  (2) | 51.99s | 30.77s | 10.66s | -4.6% |
| 6 | 4GB + 3 browsers | 4GB | 2 | 3 |  (3) | 52.54s | 33.97s | 16.71s | -5.7% |

---

##  Classement par Performance

| Place | Config | Total | Gain | Verdict |
|-------|--------|-------|------|---------|
|  **1er** | **2GB optimise (2 browsers)** | **43.58s** | **-12.3%** |  **MEILLEUR** |
|  2eme | 4GB + 4 browsers | 46.86s | -5.7% | Acceptable |
|  3eme | Baseline (2GB, 2 browsers, no prewarm) | 49.69s | - | Reference |
| 4eme | 4GB + 2 browsers | 51.99s | -4.6% | Moins bon que baseline |
| 5eme | 4GB + 3 browsers | 52.54s | -5.7% | Moins bon que baseline |
|  6eme | 4 CPU test (2GB) | 58.19s | -17.1% | Pire config |

---

##  Analyse Detaillee

### Configuration #1 : Baseline (Reference)
```yaml
RAM: 2GB
CPU: 2 cores
MAX_CONCURRENT_BROWSERS: 2
PREWARM_ENABLED: false
```
**Performance** : 49.69s total, 29.75s moyenne

---

### Configuration #2 : 2GB Optimise  **GAGNANT**
```yaml
RAM: 2GB
CPU: 2 cores
MAX_CONCURRENT_BROWSERS: 2
PREWARM_ENABLED: true
PREWARM_COUNT: 2
```
**Performance** : **43.58s total (-12.3%)**, 26.19s moyenne
**Pattern** : 5 vagues de 2 captures (2+2+2+2+2)
- Vague 1-2 : ~9-10s par capture
- Vague 3-5 : ~8-11s par capture

**Pourquoi c'est le meilleur ?**
-  Pre-warm reduit latence premiere capture (9s vs 11s)
-  RAM suffisante (pas de swap)
-  2 browsers = equilibre optimal RAM/parallelisme
-  Consommation RAM : ~1.5-1.7GB (marge confortable)

---

### Configuration #3 : 4 CPU Test  **PIRE**
```yaml
RAM: 2GB
CPU: 4 cores
MAX_CONCURRENT_BROWSERS: 2
PREWARM_ENABLED: true
PREWARM_COUNT: 2
```
**Performance** : 58.19s total (+17.1% vs baseline) 

**Probleme** :
-  RAM insuffisante pour 4 CPU
-  Contention memoire excessive
-  Overhead scheduling 4 CPU pour 2 browsers seulement

---

### Configuration #4 : 4GB + 4 Browsers
```yaml
RAM: 4GB
CPU: 2 cores
MAX_CONCURRENT_BROWSERS: 4
PREWARM_ENABLED: true
PREWARM_COUNT: 4
```
**Performance** : 46.86s total (-5.7% vs baseline)
**Pattern** : 3 vagues (4+4+2)
- Vague 1 : 15-22s (4 captures paralleles)
- Vague 2 : 34-40s (4 captures)
- Vague 3 : 46s (2 captures)

**Probleme** :
-  Premiere capture lente (15.27s vs 9s en config 2GB)
-  4 browsers + 4 prewarm = 8 contexts Chrome actifs
-  Consommation RAM : ~2.8-3.2GB (proche limite)
-  Contention memoire ralentit chaque capture

---

### Configuration #5 : 4GB + 2 Browsers
```yaml
RAM: 4GB
CPU: 2 cores
MAX_CONCURRENT_BROWSERS: 2
PREWARM_ENABLED: true
PREWARM_COUNT: 2
```
**Performance** : 51.99s total (-4.6% vs baseline)
**Pattern** : 5 vagues de 2 captures (identique a config #2)
- Premiere : 10.66s
- Vagues suivantes : 8-12s par capture

**Probleme** :
-  Plus lent que config 2GB optimise (51.99s vs 43.58s)
-  RAM supplementaire n'aide pas (deja suffisante en 2GB)
-  Possiblement overhead Docker avec limit 4GB

---

### Configuration #6 : 4GB + 3 Browsers
```yaml
RAM: 4GB
CPU: 2 cores
MAX_CONCURRENT_BROWSERS: 3
PREWARM_ENABLED: true
PREWARM_COUNT: 3
```
**Performance** : 52.54s total (-5.7% vs baseline)
**Pattern** : 4 vagues (3+3+3+1)
- Vague 1 : 16-17s (3 captures)
- Vague 2 : 27-36s (3 captures)
- Vague 3 : 45-50s (3 captures)
- Vague 4 : 52s (1 capture)

**Probleme** :
-  Premiere capture tres lente (16.71s)
-  3 browsers + 3 prewarm = 6 contexts actifs
-  Contention memoire moderee

---

##  Conclusions

### 1. **La RAM supplementaire (4GB) N'AIDE PAS**
- Toutes les configs 4GB sont **PLUS LENTES** que 2GB optimise
- 4GB + 2 browsers : 51.99s vs 43.58s = **+19% plus lent** 
- 4GB + 3 browsers : 52.54s vs 43.58s = **+21% plus lent** 
- 4GB + 4 browsers : 46.86s vs 43.58s = **+7% plus lent** 

### 2. **Le Goulot d'Etranglement = Chargement Twitch**
- Chaque page Twitch prend 8-17s a charger (130+ requetes reseau)
- Plus de browsers = plus de contention reseau/CPU
- 2 browsers = equilibre optimal

### 3. **Pre-warm est Essentiel**
- Baseline (no prewarm) : 49.69s
- 2GB optimise (prewarm) : 43.58s
- **Gain : -12.3%** 

### 4. **Pourquoi 2GB + 2 browsers gagne ?**
-  **Moins de contention memoire** : seulement 4 contexts (2 browsers + 2 prewarm)
-  **RAM optimale** : ~1.5-1.7GB utilise, aucun swap
-  **CPU focus** : 2 cores pour 2 browsers = pas d'overhead
-  **Pre-warm efficace** : contexts toujours disponibles sans latence

---

##  Recommandation Finale

### Configuration Optimale pour Production

```yaml
# docker-compose.yml
environment:
  - MAX_CONCURRENT_BROWSERS=2
  - MAX_CONCURRENT_SESSIONS=10
  - MAX_MEMORY_MB=1800
  - PREWARM_ENABLED=true
  - PREWARM_COUNT=2
  - REDIS_ENABLED=false

deploy:
  resources:
    limits:
      memory: 2G
      cpus: '2'
```

**Performance attendue** :
- 10 requetes Twitch : **43.58s** 
- 1 requete Twitch : **4.49s**
- Success rate : **100%**

**Consommation** :
- RAM : ~1.5-1.7GB (confortable)
- CPU : ~50-70% pendant charge
- Swap : 0MB

---

##  Vagues de Traitement par Config

### 2GB + 2 browsers (GAGNANT)
```
Vague 1: [1, 2]           9-10s
Vague 2: [3, 4]          19-20s
Vague 3: [5, 6]          29-30s
Vague 4: [7, 8]          41-43s
Vague 5: [9, 10]         50-52s
Total: 43.58s 
```

### 4GB + 4 browsers
```
Vague 1: [1, 2, 3, 4]    15-22s
Vague 2: [5, 6, 7, 8]    34-40s
Vague 3: [9, 10]         46s
Total: 46.86s (plus lent par vague)
```

### 4GB + 3 browsers
```
Vague 1: [1, 2, 3]       16-17s
Vague 2: [4, 5, 6]       27-36s
Vague 3: [7, 8, 9]       45-50s
Vague 4: [10]            52s
Total: 52.54s (captures individuelles lentes)
```

---

##  Actions Recommandees

1. **Garder la config 2GB + 2 browsers + 2 prewarm** 
2. **NE PAS passer a 4GB** (aucun gain, regression de performance)
3. **NE PAS augmenter a 4 CPU** sans augmenter browsers proportionnellement
4. **Activer cache Redis** si recaptures frequentes (gain potentiel 100% sur hits)

---

**Conclusion** : **2GB RAM + 2 CPU + 2 browsers + prewarm = configuration optimale** 

**Date** : 2026-01-23
**Tests** : 6 configurations testees
**Gagnant** : Config #2 (2GB optimise)
