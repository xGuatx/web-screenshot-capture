#!/bin/bash

# Script de test INTELLIGENT - Seulement les configurations optimales
# Base sur les resultats precedents et la logique d'optimisation

set -e

VM_NAME="shoturl"
RESULTS_FILE="OPTIMAL_RESULTS.csv"
LOG_FILE="OPTIMAL_LOG.txt"

# Initialiser CSV
echo "RAM_GB,CPU,Browsers,Prewarm,MAX_MEMORY_MB,Total_Time,Status,Notes" > $RESULTS_FILE

echo "========================================" | tee $LOG_FILE
echo "TEST CONFIGURATIONS OPTIMALES - ShotURL v3.0" | tee -a $LOG_FILE
echo "Date debut: $(date)" | tee -a $LOG_FILE
echo "========================================" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# Configurations optimales a tester (basees sur analyse)
# Format: "RAM_MB:CPU:BROWSERS:PREWARM:MAX_MEM:NOTES"
OPTIMAL_CONFIGS=(
  # === 4GB RAM (Production) ===
  "4096:6:4:4:3500:4GB/6CPU - Config actuelle record (28.22s)"
  "4096:6:4:3:3500:4GB/6CPU - Moins de prewarm"
  "4096:6:4:2:3500:4GB/6CPU - Prewarm minimal (record 20.72s manuel)"
  "4096:6:4:1:3500:4GB/6CPU - Prewarm tres minimal"
  "4096:6:3:3:3500:4GB/6CPU - 3 browsers equilibre"
  "4096:6:3:2:3500:4GB/6CPU - 3 browsers prewarm minimal"
  "4096:6:3:1:3500:4GB/6CPU - 3 browsers 1 prewarm"
  "4096:6:5:5:3500:4GB/6CPU - 5 browsers (test max)"
  "4096:6:5:3:3500:4GB/6CPU - 5 browsers prewarm moyen"
  "4096:6:6:3:3500:4GB/6CPU - 6 browsers (contention attendue)"

  "4096:5:4:4:3500:4GB/5CPU - 5 CPU optimal"
  "4096:5:4:2:3500:4GB/5CPU - 5 CPU prewarm minimal"
  "4096:5:3:3:3500:4GB/5CPU - 5 CPU 3 browsers"

  "4096:4:4:4:3500:4GB/4CPU - 4 CPU equilibre"
  "4096:4:4:2:3500:4GB/4CPU - 4 CPU prewarm minimal"
  "4096:4:3:3:3500:4GB/4CPU - 4 CPU 3 browsers"
  "4096:4:3:2:3500:4GB/4CPU - 4 CPU 3 browsers minimal prewarm"

  "4096:3:3:3:3500:4GB/3CPU - 3 CPU equilibre"
  "4096:3:3:2:3500:4GB/3CPU - 3 CPU prewarm minimal"
  "4096:3:2:2:3500:4GB/3CPU - 3 CPU conservatif"

  "4096:2:2:2:3500:4GB/2CPU - 2 CPU baseline"
  "4096:2:2:1:3500:4GB/2CPU - 2 CPU minimal prewarm"

  # === 3GB RAM (Budget moyen) ===
  "3072:6:4:4:2600:3GB/6CPU - Test limite RAM"
  "3072:6:3:3:2600:3GB/6CPU - 3GB 3 browsers optimal"
  "3072:6:3:2:2600:3GB/6CPU - 3GB 3 browsers minimal"
  "3072:4:3:3:2600:3GB/4CPU - 3GB 4CPU equilibre"
  "3072:4:3:2:2600:3GB/4CPU - 3GB 4CPU minimal"
  "3072:4:2:2:2600:3GB/4CPU - 3GB 2 browsers"

  # === 2GB RAM (Budget bas) ===
  "2048:6:2:2:1700:2GB/6CPU - 2GB max CPU"
  "2048:6:2:1:1700:2GB/6CPU - 2GB max CPU minimal prewarm"
  "2048:6:3:2:1700:2GB/6CPU - 2GB 3 browsers (risque)"
  "2048:4:2:2:1700:2GB/4CPU - 2GB 4CPU equilibre"
  "2048:4:2:1:1700:2GB/4CPU - 2GB 4CPU minimal"
  "2048:2:2:2:1700:2GB/2CPU - 2GB baseline (record 43.58s)"
  "2048:2:2:1:1700:2GB/2CPU - 2GB minimal prewarm"
  "2048:2:1:1:1700:2GB/2CPU - 2GB ultra conservatif"

  # === Configs extremes (curiosite) ===
  "4096:6:2:2:3500:4GB/6CPU - Sous-utilisation (2 browsers 6 CPU)"
  "4096:6:1:1:3500:4GB/6CPU - Minimum browsers"
  "2048:6:1:1:1700:2GB/6CPU - 2GB 1 browser max CPU"
  "4096:1:1:1:3500:4GB/1CPU - 1 CPU test"

  # === Ratios specifiques ===
  "4096:6:6:6:3500:4GB/6CPU - Ratio 1:1:1 (max tout)"
  "4096:6:6:4:3500:4GB/6CPU - 6 browsers moins prewarm"
  "4096:6:6:2:3500:4GB/6CPU - 6 browsers minimal prewarm"
  "3072:6:6:3:2600:3GB/6CPU - 3GB 6 browsers (contention attendue)"
  "2048:4:4:2:1700:2GB/4CPU - 2GB 4 browsers (limite)"
)

TOTAL_TESTS=${#OPTIMAL_CONFIGS[@]}

echo "Total configurations optimales a tester: $TOTAL_TESTS" | tee -a $LOG_FILE
echo "Duree estimee: ~$(( TOTAL_TESTS * 75 / 60 )) minutes" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# Fonction pour modifier la VM
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
  local notes=$6

  # Creer docker-compose
  cat > /tmp/test-optimal.yml << EOF
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
  scp /tmp/test-optimal.yml shoturl@192.168.56.102:~/docker-compose.yml >/dev/null 2>&1
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
  echo "${ram_gb},${cpus},${browsers},${prewarm},${max_mem},${result},${status},${notes}" >> $RESULTS_FILE
}

# Boucle principale
test_count=0
current_vm_config=""

for config in "${OPTIMAL_CONFIGS[@]}"; do
  test_count=$((test_count + 1))

  # Parser config
  IFS=':' read -r ram_mb cpus browsers prewarm max_mem notes <<< "$config"

  echo "" | tee -a $LOG_FILE
  echo "========================================" | tee -a $LOG_FILE
  echo "Test $test_count/$TOTAL_TESTS" | tee -a $LOG_FILE
  echo "$notes" | tee -a $LOG_FILE
  echo "========================================" | tee -a $LOG_FILE

  # Modifier VM si necessaire
  vm_config="${ram_mb}:${cpus}"
  if [ "$vm_config" != "$current_vm_config" ]; then
    if ! modify_vm $ram_mb $cpus; then
      echo "ERREUR: VM config failed" | tee -a $LOG_FILE
      echo "$((ram_mb/1024)),${cpus},${browsers},${prewarm},${max_mem},FAILED,VM_ERROR,${notes}" >> $RESULTS_FILE
      continue
    fi
    current_vm_config="$vm_config"
  fi

  # Tester
  echo "  Config: ${browsers} browsers / ${prewarm} prewarm" | tee -a $LOG_FILE
  result=$(test_config $ram_mb $cpus $browsers $prewarm $max_mem "$notes")
  echo "   Result: $result" | tee -a $LOG_FILE

  # Progression
  progress=$(( test_count * 100 / TOTAL_TESTS ))
  echo "Progression: $test_count/$TOTAL_TESTS ($progress%)" | tee -a $LOG_FILE
done

echo "" | tee -a $LOG_FILE
echo "========================================" | tee -a $LOG_FILE
echo "TESTS TERMINES !" | tee -a $LOG_FILE
echo "Date fin: $(date)" | tee -a $LOG_FILE
echo "========================================" | tee -a $LOG_FILE

# Analyser resultats
echo "" | tee -a $LOG_FILE
echo "TOP 10 CONFIGURATIONS:" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

grep -v "FAILED\|Status" $RESULTS_FILE | \
  sort -t',' -k6 -n | \
  head -10 | \
  awk -F',' '{printf "%s. %sGB/%sCPU B%s/P%s : %s (%s)\n", NR, $1, $2, $3, $4, $6, $8}' | \
  tee -a $LOG_FILE

echo ""
echo "Resultats complets: $RESULTS_FILE"
echo "Logs: $LOG_FILE"
