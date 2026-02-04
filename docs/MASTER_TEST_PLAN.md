# Plan de Test Complet - Toutes Configurations

##  Objectif
Tester toutes les combinaisons possibles pour trouver la configuration optimale absolue.

##  Variables a Tester

### VM Hardware (4 configs)
1. **2GB RAM + 2 CPU**
2. **2GB RAM + 6 CPU**
3. **4GB RAM + 2 CPU**
4. **4GB RAM + 6 CPU**  Actuellement en test

### Application (16 combos browsers/prewarm par config VM)
- Browsers: 1, 2, 3, 4
- Prewarm: 1, 2, 3, 4
- Timeouts optimaux: BROWSER_TIMEOUT=12, PAGE_LOAD_TIMEOUT=7

**Total configurations a tester** : **4 VM configs  16 combos = 64 tests**

---

##  Plan de Test Structure

### PHASE 1 : 4GB RAM + 6 CPU (EN COURS)
**Status** :  Tests automatises en cours (script `test_all_combos.sh`)

Tests en cours :
- [x] 1/1 : 39.05s
- [ ] 1/2
- [ ] 1/3
- [ ] 1/4
- [ ] 2/1
- [ ] 2/2
- [ ] 2/3
- [ ] 2/4
- [ ] 3/1
- [ ] 3/2
- [ ] 3/3
- [ ] 3/4
- [ ] 4/1
- [ ] 4/2
- [ ] 4/3
- [ ] 4/4

**Duree estimee** : ~20 minutes (16 tests  1.25min)

---

### PHASE 2 : 4GB RAM + 2 CPU
**Action requise** : Changer VM a 2 CPU (garder 4GB RAM)

```bash
# Une fois VM modifiee
bash test_all_combos.sh
```

Tests a faire :
- [ ] 1/1
- [ ] 1/2
- [ ] 1/3
- [ ] 1/4
- [ ] 2/1
- [ ] 2/2
- [ ] 2/3
- [ ] 2/4
- [ ] 3/1
- [ ] 3/2
- [ ] 3/3
- [ ] 3/4
- [ ] 4/1
- [ ] 4/2
- [ ] 4/3
- [ ] 4/4

**Duree estimee** : ~20 minutes

---

### PHASE 3 : 2GB RAM + 6 CPU
**Action requise** : Changer VM a 2GB RAM + 6 CPU

```bash
# Une fois VM modifiee
bash test_all_combos.sh
```

Tests a faire :
- [ ] 1/1
- [ ] 1/2
- [ ] 1/3
- [ ] 1/4
- [ ] 2/1
- [ ] 2/2
- [ ] 2/3
- [ ] 2/4
- [ ] 3/1
- [ ] 3/2
- [ ] 3/3
- [ ] 3/4
- [ ] 4/1
- [ ] 4/2
- [ ] 4/3
- [ ] 4/4

**Duree estimee** : ~20 minutes

**Note** : Certaines configs peuvent echouer (ex: 4 browsers avec 2GB RAM)

---

### PHASE 4 : 2GB RAM + 2 CPU
**Action requise** : Changer VM a 2GB RAM + 2 CPU

```bash
# Une fois VM modifiee
bash test_all_combos.sh
```

Tests a faire :
- [ ] 1/1
- [ ] 1/2
- [ ] 1/3
- [ ] 1/4
- [ ] 2/1
- [ ] 2/2
- [ ] 2/3
- [ ] 2/4
- [ ] 3/1
- [ ] 3/2
- [ ] 3/3
- [ ] 3/4
- [ ] 4/1
- [ ] 4/2
- [ ] 4/3
- [ ] 4/4

**Duree estimee** : ~20 minutes

**Note** : Configs 3 et 4 browsers peuvent echouer (RAM insuffisante)

---

##  Processus par Phase

### 1. Modifier la VM
- Arreter VM
- Modifier RAM/CPU dans l'hyperviseur
- Demarrer VM

### 2. Lancer les tests
```bash
cd /home/guat/wslRecover/guat/shotURL
bash test_all_combos.sh
```

### 3. Recuperer les resultats
```bash
cat combo_test_results.txt
```

### 4. Sauvegarder les resultats
```bash
cp combo_test_results.txt results_4GB_6CPU.txt  # Exemple pour phase 1
```

---

##  Format de Collecte des Resultats

Creer un fichier `ALL_RESULTS.txt` :

```
=== 4GB RAM + 6 CPU ===
1/1 : 39.05s
1/2 : XX.XXs
...
4/4 : XX.XXs

=== 4GB RAM + 2 CPU ===
1/1 : XX.XXs
...

=== 2GB RAM + 6 CPU ===
1/1 : XX.XXs
...

=== 2GB RAM + 2 CPU ===
1/1 : XX.XXs
...
```

---

##  Analyse Finale

Apres les 64 tests, creer un tableau :

| VM Config | Browsers | Prewarm | Total Time | Rank |
|-----------|----------|---------|------------|------|
| 4GB/6CPU  | 4        | 2       | 20.72s     | 1    |
| ...       | ...      | ...     | ...        | ...  |

Identifier :
1. **Meilleure config absolue**
2. **Meilleure config par budget** (2GB vs 4GB)
3. **Impact CPU** (2 vs 6)
4. **Impact RAM** (2GB vs 4GB)
5. **Ratio optimal browsers/prewarm**

---

##  Duree Totale Estimee

- Phase 1 (4GB/6CPU) : ~20 min
- Phase 2 (4GB/2CPU) : ~20 min
- Phase 3 (2GB/6CPU) : ~20 min
- Phase 4 (2GB/2CPU) : ~20 min

**Total** : ~80 minutes (~1h20)

---

##  Resultats Partiels Deja Obtenus

### 4GB RAM + 6 CPU (Tests manuels precedents)
- 4/4 : 28.22s
- 4/2 : 20.72s  RECORD ACTUEL
- 3/1 : 25.67s
- 2/2 : 28.41s
- 2/1 : 23.68s

### Observations
- **4/2 = meilleur** jusqu'a present (20.72s)
- Trop de prewarm ralentit (contention RAM)
- Equilibre browsers/prewarm important

---

##  Instructions pour l'Utilisateur

### Etape actuelle
 Phase 1 (4GB/6CPU) **EN COURS**

### Prochaine etape
Quand le script actuel termine (~15 min) :
1. Je te dirai "Phase 1 terminee"
2. Tu modifies la VM a **4GB RAM + 2 CPU**
3. Tu me dis "VM modifiee : 4GB/2CPU"
4. Je lance Phase 2

### Apres Phase 2
Meme processus pour Phase 3 (2GB/6CPU) et Phase 4 (2GB/2CPU)

---

**Date** : 2026-01-23
**Phase actuelle** : 1/4 (4GB RAM + 6 CPU)
**Status** : Tests automatises en cours
