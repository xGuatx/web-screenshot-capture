#!/bin/bash

# Test toutes les combinaisons browsers/prewarm
# Format: browsers/prewarm

COMBOS=(
  "1/1" "1/2" "1/3" "1/4"
  "2/1" "2/2" "2/3" "2/4"
  "3/1" "3/2" "3/3" "3/4"
  "4/1" "4/2" "4/3" "4/4"
)

RESULTS_FILE="combo_test_results.txt"
echo "=== Test de toutes les combinaisons browsers/prewarm ===" > $RESULTS_FILE
echo "Date: $(date)" >> $RESULTS_FILE
echo "" >> $RESULTS_FILE

for combo in "${COMBOS[@]}"; do
  browsers=$(echo $combo | cut -d'/' -f1)
  prewarm=$(echo $combo | cut -d'/' -f2)

  echo "----------------------------------------"
  echo "Testing: ${browsers} browsers / ${prewarm} prewarm"
  echo "----------------------------------------"

  # Create docker-compose
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

  # Deploy
  scp /tmp/test-combo.yml shoturl@192.168.56.102:~/docker-compose.yml
  ssh shoturl@192.168.56.102 "docker stop shoturl-v3 && docker rm shoturl-v3 && docker compose up -d" > /dev/null 2>&1

  # Wait for startup
  echo "Waiting 45s for startup..."
  sleep 45

  # Run test
  source venv/bin/activate
  result=$(python3 load_test.py 2>&1 | grep "Total test time")
  total_time=$(echo "$result" | awk '{print $4}')

  # Save result
  echo "${combo} : ${total_time}" >> $RESULTS_FILE
  echo "Result: ${total_time}"
  echo ""
done

echo "=== Tests termines ===" >> $RESULTS_FILE
echo ""
echo "Tous les tests termines ! Voir $RESULTS_FILE"
cat $RESULTS_FILE
