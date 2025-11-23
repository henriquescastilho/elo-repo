#!/bin/bash

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Iniciando serviços Docker...${NC}"
docker-compose up -d --remove-orphans

echo -e "${YELLOW}Aguardando backend iniciar (pode levar alguns segundos)...${NC}"
# Loop simples de health check
MAX_RETRIES=30
COUNT=0
while ! curl -s http://localhost:8000/health > /dev/null; do
    sleep 1
    COUNT=$((COUNT+1))
    if [ $COUNT -ge $MAX_RETRIES ]; then
        echo -e "${RED}Erro: Backend demorou muito para responder.${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ Backend online!${NC}"
echo -e "${GREEN}Iniciando Polling do Telegram...${NC}"
echo -e "${GREEN}>>> SISTEMA PRONTO PARA USO! <<<${NC}"
echo -e "Abra o Telegram e mande /start para testar."
echo -e "Pressione Ctrl+C para parar."

python3 scripts/telegram_polling.py
