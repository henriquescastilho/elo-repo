#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== ELO Assistente Cidadão Setup ===${NC}"

# Check if .env exists
if [ -f .env ]; then
    echo -e "${YELLOW}.env file already exists.${NC}"
    read -p "Do you want to overwrite it? (y/N) " overwrite
    if [[ $overwrite != "y" && $overwrite != "Y" ]]; then
        echo "Skipping .env creation."
        exit 0
    fi
fi

echo "Creating .env from .env.example..."
cp .env.example .env

echo -e "${GREEN}Please enter your API keys (leave blank to skip/edit later):${NC}"

read -p "OpenAI API Key: " openai_key
if [ ! -z "$openai_key" ]; then
    # Escape special characters if needed, but for simple keys sed is usually fine
    # Using a different delimiter for sed to avoid issues with slashes
    sed -i '' "s|OPENAI_API_KEY=.*|OPENAI_API_KEY=$openai_key|" .env
fi

read -p "WAHA API Key (default: 593a815b32df4ce5b31f3ba2d77e75c6): " waha_key
if [ ! -z "$waha_key" ]; then
    sed -i '' "s|WAHA_API_TOKEN=.*|WAHA_API_TOKEN=$waha_key|" .env
fi

echo -e "${GREEN}Setup complete!${NC}"
echo "You can now run 'docker-compose up --build' to start the application."
