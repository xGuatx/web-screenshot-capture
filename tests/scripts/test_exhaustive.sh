#!/bin/bash

# Script de test EXHAUSTIF - TOUTES les combinaisons possibles
# RAM: 1GB, 2GB, 3GB, 4GB (4 valeurs)
# CPU: 1, 2, 3, 4, 5, 6 (6 valeurs)
# Browsers: 1-6 (6 valeurs)
# Prewarm: 1-6 (6 valeurs)
# TOTAL: 4  6  6  6 = 864 tests

set -e

VM_NAME="shoturl"
RESULTS_FILE="EXHAUSTIVE_RESULTS.csv"
LOG_FILE="EXHAUSTIVE_LOG.txt"

# Initialiser fichier CSV
echo "RAM_GB,CPU,Browsers,Prewarm,MAX_MEMORY_MB,Total_Time,Status" > $RESULTS_FILE

echo "========================================" | tee $LOG_FILE
echo "TEST EXHAUSTIF - ShotURL v3.0" | tee -a $LOG_FILE
echo "Total tests: 864 (4 RAM  6 CPU  6 browsers  6 prewarm)" | tee -a $LOG_FILE
echo "Duree estimee: ~18 heures" | tee -a $LOG_FILE
echo "Date debut: $(date)" | tee -a $LOG_FILE
echo "========================================" | tee -a $LOG_FILE
echo "" | tee -a $LOG_FILE

# Configurations VM
RAM_CONFIGS=(1024 2048 3072 4096)    # 1GB, 2GB, 3GB, 4GB
CPU_CONFIGS=(1 2 3 4 5 6)
BROWSER_CONFIGS=(1 2 3 4 5 6)
PREWARM_CONFIGS=(1 2 3 4 5 6)

# Fonction pour calculer MAX_MEMORY_MB selon RAM
get_max_memory() {
  local ram_mb=$1
  # 85% de la RAM pour MAX_MEMORY_MB
  echo $((ram_mb * 85 / 100))
}

# Fonction pour modifier la VM
modify_vm() {
  local ram_mb=$1
  local cpus=$2

  echo ">>> Modification VM: ${ram_mb}MB RAM, ${cpus} CPU" | tee -a $LOG_FILE

  # Arreter VM si running
  if VBoxManage list runningvms | grep -q "$VM_NAME"; then
    ssh shoturl@192.168.56.102 "sudo poweroff" 2>/dev/null || true
    sleep 10
  fi

  # Modifier RAM et CPU
  VBoxManage modifyvm "$VM_NAME" --memory $ram_mb --cpus $cpus

  # Demarrer VM
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

# Fonction pour tester une combinaison
test_combo() {
  local ram_gb=$1
  local cpus=$2
  local browsers=$3
  local prewarm=$4
  local max_mem=$5

  # Verifier si combo est viable
  # Ex: 1 browser ne peut pas avoir 6 prewarm (incoherent)
  if [ $prewarm -gt $browsers ]; then
    echo "SKIP (prewarm > browsers)"
    return 0
  fi

  # Skip si browsers > cpus (pas optimal)
  if [ $browsers -gt $cpus ]; then
    echo "SKIP (browsers > cpus)"
    return 0
  fi

  # Creer docker-compose
  cat > /tmp/test-config.yml << EOF
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
  scp /tmp/test-config.yml shoturl@192.168.56.102:~/docker-compose.yml >/dev/null 2>&1
  ssh shoturl@192.168.56.102 "docker stop shoturl-v3 2>/dev/null || true; docker rm shoturl-v3 2>/dev/null || true; docker compose up -d" >/dev/null 2>&1

  # Attendre demarrage
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

  # Sauvegarder dans CSV
  echo "${ram_gb},${cpus},${browsers},${prewarm},${max_mem},${result},${status}" >> $RESULTS_FILE
}

# Boucle principale
test_count=0
total_tests=864

for ram_mb in "${RAM_CONFIGS[@]}"; do
  ram_gb=$((ram_mb / 1024))
  max_mem=$(get_max_memory $ram_mb)

  for cpus in "${CPU_CONFIGS[@]}"; do

    echo "" | tee -a $LOG_FILE
    echo "========================================" | tee -a $LOG_FILE
    echo "CONFIG VM: ${ram_gb}GB RAM + ${cpus} CPU" | tee -a $LOG_FILE
    echo "========================================" | tee -a $LOG_FILE

    # Modifier VM
    if ! modify_vm $ram_mb $cpus; then
      echo "ERREUR: VM config failed" | tee -a $LOG_FILE
      continue
    fi

    # Tester toutes les combinaisons browsers/prewarm
    for browsers in "${BROWSER_CONFIGS[@]}"; do
      for prewarm in "${PREWARM_CONFIGS[@]}"; do
        test_count=$((test_count + 1))

        echo "" | tee -a $LOG_FILE
        echo "Test $test_count/$total_tests: ${ram_gb}GB/${cpus}CPU B${browsers}/P${prewarm}" | tee -a $LOG_FILE

        result=$(test_combo $ram_gb $cpus $browsers $prewarm $max_mem)

        echo "   Result: $result" | tee -a $LOG_FILE

        # Sauvegarder progression tous les 10 tests
        if [ $((test_count % 10)) -eq 0 ]; then
          echo "Progression: $test_count/$total_tests ($(( test_count * 100 / total_tests ))%)" | tee -a $LOG_FILE
        fi
      done
    done
  done
done

echo "" | tee -a $LOG_FILE
echo "========================================" | tee -a $LOG_FILE
echo "TOUS LES TESTS TERMINES !" | tee -a $LOG_FILE
echo "Date fin: $(date)" | tee -a $LOG_FILE
echo "Resultats dans: $RESULTS_FILE" | tee -a $LOG_FILE
echo "========================================" | tee -a $LOG_FILE

# Analyser les resultats
echo "" | tee -a $LOG_FILE
echo "TOP 20 CONFIGURATIONS:" | tee -a $LOG_FILE
echo "Rank,RAM_GB,CPU,Browsers,Prewarm,Time" | tee -a $LOG_FILE

grep -v "FAILED\|SKIP" $RESULTS_FILE | \
  grep -E "^[0-9]" | \
  sort -t',' -k6 -n | \
  head -20 | \
  nl -s',' | \
  tee -a $LOG_FILE

echo ""
echo "Analyse complete sauvegardee !"
