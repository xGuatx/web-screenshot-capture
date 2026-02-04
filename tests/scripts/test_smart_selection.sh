#!/bin/bash

# Script INTELLIGENT - Selection des configurations les plus prometteuses
# Exclut les configs non viables et peu susceptibles d'etre efficaces

set -e

VM_NAME="shoturl"
RESULTS_FILE="SMART_SELECTION_RESULTS.csv"
LOG_FILE="SMART_SELECTION_LOG.txt"

# Initialiser CSV
echo "RAM_GB,CPU,Browsers,Prewarm,MAX_MEMORY_MB,Total_Time,Status,Category" > $RESULTS_FILE

echo "========================================" | tee $LOG_FILE
echo "TEST INTELLIGENT - Configurations Prometteuses" | tee -a $LOG_FILE
echo "Date: $(date)" | tee -a $LOG_FILE
echo "========================================" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# Configurations intelligemment selectionnees
# Format: "RAM_MB:CPU:BROWSERS:PREWARM:MAX_MEM:CATEGORY"

SMART_CONFIGS=(
  # === CATEGORIE: Premium Performance (4GB RAM) ===
  "4096:6:3:3:3500:Premium - Sweet spot 1:1 ratio"
  "4096:6:3:2:3500:Premium - Minimal prewarm"
  "4096:6:4:2:3500:Premium - Plus de browsers"
  "4096:6:4:3:3500:Premium - Equilibre"
  "4096:6:5:3:3500:Premium - Max browsers viable"
  "4096:6:5:4:3500:Premium - 5 browsers ratio optimal"
  "4096:6:2:2:3500:Premium - Conservatif"

  "4096:5:3:3:3500:Premium 5CPU - Sweet spot"
  "4096:5:4:3:3500:Premium 5CPU - Standard"
  "4096:5:4:2:3500:Premium 5CPU - Minimal prewarm"
  "4096:5:5:3:3500:Premium 5CPU - Max browsers"

  "4096:4:3:3:3500:Premium 4CPU - Equilibre"
  "4096:4:4:2:3500:Premium 4CPU - Standard"
  "4096:4:4:3:3500:Premium 4CPU - Plus prewarm"

  "4096:3:3:2:3500:Premium 3CPU - Sweet spot"
  "4096:3:3:3:3500:Premium 3CPU - Ratio 1:1"

  # === CATEGORIE: Equilibre (3GB RAM) ===
  "3072:6:3:3:2600:Equilibre - 3GB sweet spot"
  "3072:6:3:2:2600:Equilibre - 3GB minimal"
  "3072:6:4:2:2600:Equilibre - 3GB 4 browsers (risque)"
  "3072:6:2:2:2600:Equilibre - 3GB conservatif"

  "3072:5:3:3:2600:Equilibre 5CPU"
  "3072:5:3:2:2600:Equilibre 5CPU minimal"

  "3072:4:3:2:2600:Equilibre 4CPU - Optimal"
  "3072:4:3:3:2600:Equilibre 4CPU - Ratio 1:1"
  "3072:4:2:2:2600:Equilibre 4CPU - Securise"

  "3072:3:3:2:2600:Equilibre 3CPU"
  "3072:3:2:2:2600:Equilibre 3CPU conservatif"

  # === CATEGORIE: Budget (2GB RAM) ===
  "2048:6:2:2:1700:Budget - 2GB max CPU"
  "2048:6:2:1:1700:Budget - 2GB 6CPU minimal"
  "2048:6:3:2:1700:Budget - 2GB 3 browsers (limite)"

  "2048:5:2:2:1700:Budget 5CPU"
  "2048:5:2:1:1700:Budget 5CPU minimal"

  "2048:4:2:2:1700:Budget 4CPU - Equilibre"
  "2048:4:2:1:1700:Budget 4CPU - Minimal"
  "2048:4:3:2:1700:Budget 4CPU - 3 browsers (risque)"

  "2048:3:2:2:1700:Budget 3CPU"
  "2048:3:2:1:1700:Budget 3CPU minimal"

  "2048:2:2:2:1700:Budget 2CPU - Baseline optimise"
  "2048:2:2:1:1700:Budget 2CPU - Ultra minimal"

  # === CATEGORIE: Economique (1.5GB RAM) - Test limite ===
  "1536:6:2:1:1300:Economique - Test limite max CPU"
  "1536:4:2:1:1300:Economique - Test limite 4CPU"
  "1536:2:2:1:1300:Economique - Test limite minimal"
  "1536:2:1:1:1300:Economique - Ultra economique"

  # === CATEGORIE: Curiosite (Configs extremes) ===
  "4096:6:6:3:3500:Curiosite - Max browsers 6CPU"
  "4096:6:6:4:3500:Curiosite - 6 browsers ratio optimal"
  "4096:6:1:1:3500:Curiosite - 1 browser 6CPU (waste)"
  "2048:6:1:1:1700:Curiosite - 1 browser 2GB (minimal)"
  "4096:1:1:1:3500:Curiosite - 1 CPU test"
  "4096:2:2:1:3500:Curiosite - 2 CPU avec 4GB"
)

TOTAL_TESTS=${#SMART_CONFIGS[@]}

echo "Configurations selectionnees intelligemment: $TOTAL_TESTS" | tee -a $LOG_FILE
echo "Duree estimee: ~$(( TOTAL_TESTS * 75 / 60 )) minutes (~$(( TOTAL_TESTS * 75 / 3600 + 1 ))h)" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# === LOGIQUE D'EXCLUSION ===
echo "Regles d'exclusion appliquees:" | tee -a $LOG_FILE
echo "   Prewarm > Browsers (incoherent)" | tee -a $LOG_FILE
echo "   Browsers > CPU + 2 (surcharge CPU)" | tee -a $LOG_FILE
echo "   RAM < 1GB (insuffisant pour Chrome)" | tee -a $LOG_FILE
echo "   Browsers > 6 (contention excessive)" | tee -a $LOG_FILE
echo "   Prewarm > 6 (inutile)" | tee -a $LOG_FILE
echo "   1GB RAM + browsers > 1 (crash attendu)" | tee -a $LOG_FILE
echo "   2GB RAM + browsers > 3 (swap excessif)" | tee -a $LOG_FILE
echo "   3GB RAM + browsers > 4 (limite)" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# Fonction pour modifier VM
modify_vm() {
  local ram_mb=$1
  local cpus=$2

  echo ">>> Modification VM: ${ram_mb}MB RAM, ${cpus} CPU" | tee -a $LOG_FILE

  # Arreter VM
  if VBoxManage list runningvms | grep -q "$VM_NAME"; then
    ssh shoturl@192.168.56.102 "sudo poweroff" 2>/dev/null || true
    sleep 10
  fi

  # Modifier
  VBoxManage modifyvm "$VM_NAME" --memory $ram_mb --cpus $cpus

  # Demarrer
  VBoxManage startvm "$VM_NAME" --type headless

  # Attendre SSH
  for i in {1..60}; do
    if ssh -o ConnectTimeout=1 shoturl@192.168.56.102 "echo ok" &>/dev/null; then
      sleep 10
      return 0
    fi
    sleep 1
  done

  echo " ERREUR: VM ne repond pas" | tee -a $LOG_FILE
  return 1
}

# Fonction de test
test_config() {
  local ram_mb=$1
  local cpus=$2
  local browsers=$3
  local prewarm=$4
  local max_mem=$5
  local category=$6

  # Creer docker-compose
  cat > /tmp/smart-test.yml << EOF
version: '3.8'
services:
  shoturl:
    image: docker-shoturl:latest
    container_name: shoturl-v3
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - HOST=0.0.0.0
      - PORT=8000
      - DEBUG=false
      - ALLOW_LOCAL_URLS=false
      - MAX_CONCURRENT_BROWSERS=${browsers}
      - MAX_CONCURRENT_SESSIONS=10
      - MAX_MEMORY_MB=${max_mem}
      - BROWSER_TIMEOUT=12
      - PAGE_LOAD_TIMEOUT=7
      - SESSION_TIMEOUT=60
      - CLEANUP_INTERVAL=3
      - REDIS_ENABLED=false
      - PREWARM_ENABLED=true
      - PREWARM_COUNT=${prewarm}
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
networks:
  shoturl-network:
    driver: bridge
EOF

  # Deployer
  scp /tmp/smart-test.yml shoturl@192.168.56.102:~/docker-compose.yml >/dev/null 2>&1
  ssh shoturl@192.168.56.102 "docker stop shoturl-v3 2>/dev/null || true; docker rm shoturl-v3 2>/dev/null || true; docker compose up -d" >/dev/null 2>&1

  # Attendre
  sleep 45

  # Tester
  source venv/bin/activate
  result=$(timeout 120 python3 load_test.py 2>&1 | grep "Total test time" | awk '{print $4}')

  if [ -z "$result" ]; then
    result="FAILED"
    status="FAILED"
  else
    status="OK"
  fi

  echo "$result"

  # Sauvegarder CSV
  ram_gb=$((ram_mb / 1024))
  echo "${ram_gb},${cpus},${browsers},${prewarm},${max_mem},${result},${status},${category}" >> $RESULTS_FILE
}

# Boucle principale
test_count=0
current_vm_config=""

for config in "${SMART_CONFIGS[@]}"; do
  test_count=$((test_count + 1))

  # Parser config
  IFS=':' read -r ram_mb cpus browsers prewarm max_mem category <<< "$config"

  echo "" | tee -a $LOG_FILE
  echo "========================================" | tee -a $LOG_FILE
  echo "Test $test_count/$TOTAL_TESTS" | tee -a $LOG_FILE
  echo "$category" | tee -a $LOG_FILE
  echo "Config: ${ram_mb}MB RAM / ${cpus} CPU / ${browsers} browsers / ${prewarm} prewarm" | tee -a $LOG_FILE
  echo "========================================" | tee -a $LOG_FILE

  # Modifier VM si necessaire
  vm_config="${ram_mb}:${cpus}"
  if [ "$vm_config" != "$current_vm_config" ]; then
    if ! modify_vm $ram_mb $cpus; then
      echo "ERREUR: VM config failed" | tee -a $LOG_FILE
      echo "$((ram_mb/1024)),${cpus},${browsers},${prewarm},${max_mem},FAILED,VM_ERROR,${category}" >> $RESULTS_FILE
      continue
    fi
    current_vm_config="$vm_config"
  fi

  # Tester
  result=$(test_config $ram_mb $cpus $browsers $prewarm $max_mem "$category")
  echo "   Result: $result" | tee -a $LOG_FILE

  # Progression
  progress=$(( test_count * 100 / TOTAL_TESTS ))
  elapsed_min=$(( test_count * 75 / 60 ))
  remaining_min=$(( (TOTAL_TESTS - test_count) * 75 / 60 ))
  echo "Progression: $test_count/$TOTAL_TESTS ($progress%) - Temps ecoule: ${elapsed_min}min - Restant: ${remaining_min}min" | tee -a $LOG_FILE
done

echo "" | tee -a $LOG_FILE
echo "========================================" | tee -a $LOG_FILE
echo "TESTS TERMINES !" | tee -a $LOG_FILE
echo "Date fin: $(date)" | tee -a $LOG_FILE
echo "========================================" | tee -a $LOG_FILE

# Analyser resultats
echo "" | tee -a $LOG_FILE
echo "=== TOP 10 GLOBAL ===" | tee -a $LOG_FILE
grep -v "FAILED\|Status" $RESULTS_FILE | \
  sort -t',' -k6 -n | \
  head -10 | \
  awk -F',' '{printf "%2d. %sGB/%sCPU B%s/P%s : %8s (%s)\n", NR, $1, $2, $3, $4, $6, $8}' | \
  tee -a $LOG_FILE

echo "" | tee -a $LOG_FILE
echo "=== TOP 3 par CATEGORIE ===" | tee -a $LOG_FILE

for cat in "Premium" "Equilibre" "Budget" "Economique"; do
  echo "" | tee -a $LOG_FILE
  echo "[$cat]" | tee -a $LOG_FILE
  grep "$cat" $RESULTS_FILE | grep -v "FAILED" | \
    sort -t',' -k6 -n | \
    head -3 | \
    awk -F',' '{printf "  %sGB/%sCPU B%s/P%s : %s\n", $1, $2, $3, $4, $6}' | \
    tee -a $LOG_FILE
done

echo ""
echo "Resultats complets: $RESULTS_FILE"
echo "Logs: $LOG_FILE"
