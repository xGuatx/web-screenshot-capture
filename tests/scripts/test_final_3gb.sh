#!/bin/bash

# Test Final - Configuration Optimale 3GB/6CPU/3/3
# ShotURL v3.0 - Validation Production

VM_NAME="shoturl"
VM_USER="guat"
VM_IP="192.168.56.101"

echo "=========================================="
echo "Test Final ShotURL v3.0"
echo "Configuration: 3GB RAM / 6 CPU / 3 browsers / 3 prewarm"
echo "=========================================="
echo ""

# Arreter la VM
echo "[1/6] Arret de la VM..."
VBoxManage controlvm "$VM_NAME" poweroff 2>/dev/null
sleep 5

# Configurer 3GB RAM / 6 CPU
echo "[2/6] Configuration VM: 3GB RAM + 6 CPU cores"
VBoxManage modifyvm "$VM_NAME" --memory 3072 --cpus 6

# Demarrer la VM
echo "[3/6] Demarrage de la VM..."
VBoxManage startvm "$VM_NAME" --type headless

# Attendre que SSH soit disponible
echo "[4/6] Attente SSH (max 60s)..."
for i in {1..30}; do
    if ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no ${VM_USER}@${VM_IP} "echo 'SSH OK'" &>/dev/null; then
        echo "SSH disponible apres ${i}s"
        break
    fi
    sleep 2
done

# Attendre que Docker soit pret
echo "[5/6] Attente Docker + container..."
sleep 10

# Verifier la config Docker
echo ""
echo "Configuration Docker actuelle:"
ssh ${VM_USER}@${VM_IP} "docker exec shoturl-v3 printenv | grep -E 'MAX_CONCURRENT_BROWSERS|PREWARM_COUNT|MAX_MEMORY_MB|BROWSER_TIMEOUT|PAGE_LOAD_TIMEOUT'"

# Lancer le test de charge
echo ""
echo "[6/6] Lancement test de charge (10 requetes Twitch)..."
echo "----------------------------------------------"

cd "$(dirname "$0")"
python3 load_test.py --url "http://${VM_IP}:8000" --requests 10 --target "https://www.twitch.tv/directory"

echo ""
echo "=========================================="
echo "Test Final Termine"
echo "=========================================="
echo ""
echo "Configuration VM:"
VBoxManage showvminfo "$VM_NAME" | grep -E "Memory size|Number of CPUs"
