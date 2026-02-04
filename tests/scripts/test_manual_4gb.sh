#!/bin/bash

# Test manuel: 4GB RAM avec 6 CPU puis 5 CPU
# Teste les combinaisons browsers/prewarm les plus prometteuses

VM_NAME="shoturl"
RESULTS="MANUAL_4GB_RESULTS.txt"

echo "=== TEST MANUEL 4GB RAM ===" | tee $RESULTS
echo "Date: $(date)" | tee -a $RESULTS
echo "" | tee -a $RESULTS

# Configs a tester (browsers:prewarm)
COMBOS_TO_TEST=(
  "4:2"  # Record actuel (20.72s)
  "4:3"
  "4:4"  # Config actuelle (28.22s)
  "3:2"
  "3:3"
  "5:3"
)

# Fonction pour configurer VM
setup_vm() {
  local ram_mb=$1
  local cpus=$2

  echo ">>> Configuration VM: ${ram_mb}MB RAM, ${cpus} CPU"

  # Arreter VM
  if VBoxManage list runningvms | grep -q "$VM_NAME"; then
    echo "Arret VM..."
    ssh shoturl@192.168.56.102 "sudo poweroff" 2>/dev/null || true
    sleep 10
  fi

  # Modifier VM
  VBoxManage modifyvm "$VM_NAME" --memory $ram_mb --cpus $cpus
  echo "VM modifiee: ${ram_mb}MB RAM, ${cpus} CPU"

  # Demarrer
  echo "Demarrage VM..."
  VBoxManage startvm "$VM_NAME" --type headless

  # Attendre SSH
  echo "Attente SSH..."
  for i in {1..60}; do
    if ssh -o ConnectTimeout=1 shoturl@192.168.56.102 "echo ok" &>/dev/null 2>&1; then
      echo " VM prete!"
      sleep 10
      return 0
    fi
    sleep 1
  done

  echo " ERREUR: VM ne repond pas"
  return 1
}

# Fonction pour tester une combo
test_combo() {
  local browsers=$1
  local prewarm=$2

  echo "   Testing ${browsers} browsers / ${prewarm} prewarm..."

  # Creer docker-compose
  cat > /tmp/manual-test.yml << EOF
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
  scp /tmp/manual-test.yml shoturl@192.168.56.102:~/docker-compose.yml >/dev/null 2>&1
  ssh shoturl@192.168.56.102 "docker stop shoturl-v3 2>/dev/null || true; docker rm shoturl-v3 2>/dev/null || true; docker compose up -d" >/dev/null 2>&1

  # Attendre
  echo "    Attente demarrage (45s)..."
  sleep 45

  # Tester
  source venv/bin/activate
  result=$(python3 load_test.py 2>&1 | grep "Total test time" | awk '{print $4}')

  if [ -z "$result" ]; then
    result="FAILED"
  fi

  echo "    Result: $result"
  echo "$result"
}

# === PHASE 1: 4GB RAM + 6 CPU ===
echo "========================================" | tee -a $RESULTS
echo "PHASE 1: 4GB RAM + 6 CPU" | tee -a $RESULTS
echo "========================================" | tee -a $RESULTS

if setup_vm 4096 6; then
  for combo in "${COMBOS_TO_TEST[@]}"; do
    browsers=$(echo $combo | cut -d':' -f1)
    prewarm=$(echo $combo | cut -d':' -f2)

    echo "" | tee -a $RESULTS
    echo "Test: ${browsers} browsers / ${prewarm} prewarm" | tee -a $RESULTS

    result=$(test_combo $browsers $prewarm)

    echo "4GB/6CPU | ${browsers}/${prewarm} : ${result}" | tee -a $RESULTS
  done
else
  echo "ERREUR: Impossible de configurer VM pour 4GB/6CPU" | tee -a $RESULTS
fi

# === PHASE 2: 4GB RAM + 5 CPU ===
echo "" | tee -a $RESULTS
echo "========================================" | tee -a $RESULTS
echo "PHASE 2: 4GB RAM + 5 CPU" | tee -a $RESULTS
echo "========================================" | tee -a $RESULTS

if setup_vm 4096 5; then
  for combo in "${COMBOS_TO_TEST[@]}"; do
    browsers=$(echo $combo | cut -d':' -f1)
    prewarm=$(echo $combo | cut -d':' -f2)

    echo "" | tee -a $RESULTS
    echo "Test: ${browsers} browsers / ${prewarm} prewarm" | tee -a $RESULTS

    result=$(test_combo $browsers $prewarm)

    echo "4GB/5CPU | ${browsers}/${prewarm} : ${result}" | tee -a $RESULTS
  done
else
  echo "ERREUR: Impossible de configurer VM pour 4GB/5CPU" | tee -a $RESULTS
fi

# Resume
echo "" | tee -a $RESULTS
echo "========================================" | tee -a $RESULTS
echo "RESULTATS FINAUX" | tee -a $RESULTS
echo "========================================" | tee -a $RESULTS
echo "" | tee -a $RESULTS

echo "Meilleure config 6 CPU:" | tee -a $RESULTS
grep "4GB/6CPU" $RESULTS | grep -v "=" | sort -t':' -k3 -n | head -1 | tee -a $RESULTS

echo "" | tee -a $RESULTS
echo "Meilleure config 5 CPU:" | tee -a $RESULTS
grep "4GB/5CPU" $RESULTS | grep -v "=" | sort -t':' -k3 -n | head -1 | tee -a $RESULTS

echo ""
echo "Tests termines! Resultats dans: $RESULTS"
