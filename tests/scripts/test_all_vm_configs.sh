#!/bin/bash

# Script de test exhaustif : Toutes les combinaisons VM + browsers/prewarm
# Utilise VBoxManage pour changer automatiquement RAM/CPU

set -e

VM_NAME="shoturl"
FINAL_RESULTS="COMPLETE_TEST_RESULTS.txt"

# Configurations VM a tester
VM_CONFIGS=(
  "4096:6"   # 4GB RAM, 6 CPU
  "4096:2"   # 4GB RAM, 2 CPU
  "2048:6"   # 2GB RAM, 6 CPU
  "2048:2"   # 2GB RAM, 2 CPU
)

# Combinaisons browsers/prewarm
COMBOS=(
  "1:1" "1:2" "1:3" "1:4"
  "2:1" "2:2" "2:3" "2:4"
  "3:1" "3:2" "3:3" "3:4"
  "4:1" "4:2" "4:3" "4:4"
)

echo "========================================" | tee $FINAL_RESULTS
echo "TEST EXHAUSTIF - ShotURL v3.0" | tee -a $FINAL_RESULTS
echo "Date: $(date)" | tee -a $FINAL_RESULTS
echo "Total tests: $((${#VM_CONFIGS[@]} * ${#COMBOS[@]}))" | tee -a $FINAL_RESULTS
echo "========================================" | tee -a $FINAL_RESULTS
echo "" | tee -a $FINAL_RESULTS

# Fonction pour modifier la VM
modify_vm() {
  local ram_mb=$1
  local cpus=$2

  echo ">>> Modification VM: ${ram_mb}MB RAM, ${cpus} CPU"

  # Arreter VM si running
  if VBoxManage list runningvms | grep -q "$VM_NAME"; then
    echo "    Arret de la VM..."
    ssh shoturl@192.168.56.102 "sudo poweroff" 2>/dev/null || true
    sleep 10
  fi

  # Modifier RAM et CPU
  VBoxManage modifyvm "$VM_NAME" --memory $ram_mb --cpus $cpus

  echo "    Configuration appliquee: ${ram_mb}MB RAM, ${cpus} CPU"

  # Demarrer VM
  echo "    Demarrage de la VM..."
  VBoxManage startvm "$VM_NAME" --type headless

  # Attendre que SSH soit disponible
  echo "    Attente SSH (max 60s)..."
  for i in {1..60}; do
    if ssh -o ConnectTimeout=1 shoturl@192.168.56.102 "echo ok" &>/dev/null; then
      echo "     VM prete !"
      sleep 10  # Attente supplementaire pour stabilite
      return 0
    fi
    sleep 1
  done

  echo "     ERREUR: VM ne repond pas"
  return 1
}

# Fonction pour tester une combinaison
test_combo() {
  local browsers=$1
  local prewarm=$2

  echo "   Testing: ${browsers} browsers / ${prewarm} prewarm"

  # Creer docker-compose temporaire
  cat > /tmp/test-combo.yml << EOF
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
      - MAX_MEMORY_MB=3500
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
  scp /tmp/test-combo.yml shoturl@192.168.56.102:~/docker-compose.yml >/dev/null 2>&1
  ssh shoturl@192.168.56.102 "docker stop shoturl-v3 2>/dev/null || true; docker rm shoturl-v3 2>/dev/null || true; docker compose up -d" >/dev/null 2>&1

  # Attendre demarrage
  sleep 45

  # Lancer test
  source venv/bin/activate
  result=$(python3 load_test.py 2>&1 | grep "Total test time" | awk '{print $4}')

  if [ -z "$result" ]; then
    result="FAILED"
  fi

  echo "    Result: $result"
  echo "$result"
}

# Boucle principale sur toutes les configs VM
test_number=1
total_tests=$((${#VM_CONFIGS[@]} * ${#COMBOS[@]}))

for vm_config in "${VM_CONFIGS[@]}"; do
  ram=$(echo $vm_config | cut -d':' -f1)
  cpus=$(echo $vm_config | cut -d':' -f2)
  ram_gb=$((ram / 1024))

  echo "" | tee -a $FINAL_RESULTS
  echo "========================================" | tee -a $FINAL_RESULTS
  echo "CONFIG VM: ${ram_gb}GB RAM + ${cpus} CPU" | tee -a $FINAL_RESULTS
  echo "========================================" | tee -a $FINAL_RESULTS

  # Modifier la VM
  if ! modify_vm $ram $cpus; then
    echo "ERREUR: Impossible de configurer la VM" | tee -a $FINAL_RESULTS
    continue
  fi

  # Tester toutes les combinaisons browsers/prewarm
  for combo in "${COMBOS[@]}"; do
    browsers=$(echo $combo | cut -d':' -f1)
    prewarm=$(echo $combo | cut -d':' -f2)

    echo "" | tee -a $FINAL_RESULTS
    echo "Test $test_number/$total_tests: ${browsers}/${prewarm}" | tee -a $FINAL_RESULTS

    result=$(test_combo $browsers $prewarm)

    echo "${ram_gb}GB/${cpus}CPU | ${browsers}/${prewarm} : ${result}" | tee -a $FINAL_RESULTS

    test_number=$((test_number + 1))
  done
done

echo "" | tee -a $FINAL_RESULTS
echo "========================================" | tee -a $FINAL_RESULTS
echo "TOUS LES TESTS TERMINES !" | tee -a $FINAL_RESULTS
echo "Date fin: $(date)" | tee -a $FINAL_RESULTS
echo "========================================" | tee -a $FINAL_RESULTS

# Analyser les resultats
echo "" | tee -a $FINAL_RESULTS
echo "TOP 10 CONFIGURATIONS:" | tee -a $FINAL_RESULTS
grep -E "[0-9]+GB.*[0-9]+\.[0-9]+s" $FINAL_RESULTS | \
  grep -v "FAILED" | \
  sort -t':' -k3 -n | \
  head -10 | tee -a $FINAL_RESULTS

echo ""
echo "Resultats complets sauvegardes dans: $FINAL_RESULTS"
