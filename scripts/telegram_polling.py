import os
import json
import time
import urllib.request
import urllib.error
import sys

# Tenta carregar variáveis do .env (simples)
def load_env():
    try:
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    if key == "TELEGRAM_BOT_TOKEN":
                        return value
    except FileNotFoundError:
        pass
    return None

TOKEN = load_env()
# Fallback se não achar no .env (mas deve achar)
if not TOKEN:
    print("Erro: TELEGRAM_BOT_TOKEN não encontrado no .env")
    # Tenta pegar do argumento ou hardcoded se necessário (mas melhor não hardcodar aqui para não vazar se o user mudar)
    sys.exit(1)

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"
LOCAL_WEBHOOK_URL = "http://localhost:8000/webhook/telegram"

def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates?timeout=30"
    if offset:
        url += f"&offset={offset}"
    try:
        with urllib.request.urlopen(url) as response:
            return json.loads(response.read().decode())
    except urllib.error.URLError as e:
        print(f"Erro ao conectar com Telegram: {e}")
        return None

def forward_to_webhook(update):
    try:
        data = json.dumps(update).encode("utf-8")
        req = urllib.request.Request(
            LOCAL_WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as response:
            print(f"Update {update['update_id']} encaminhado: {response.status}")
            return True
    except urllib.error.URLError as e:
        print(f"Erro ao encaminhar para webhook local ({LOCAL_WEBHOOK_URL}): {e}")
        return False

def main():
    print(f"Iniciando Polling para o Bot...")
    print(f"Token: {TOKEN[:5]}...{TOKEN[-5:]}")
    print(f"Encaminhando para: {LOCAL_WEBHOOK_URL}")
    
    offset = None
    
    # Primeiro, limpa webhook se houver
    try:
        urllib.request.urlopen(f"{BASE_URL}/deleteWebhook")
        print("Webhook anterior removido (necessário para polling).")
    except:
        pass

    print("\n" + "="*40)
    print("🤖 BOT ESTÁ OUVINDO! PODE FALAR NO TELEGRAM.")
    print("="*40 + "\n")

    while True:
        try:
            updates = get_updates(offset)
            if updates and updates.get("ok"):
                for update in updates["result"]:
                    update_id = update["update_id"]
                    print(f"Recebido update: {update_id}")
                    
                    # Encaminha para o backend local
                    if forward_to_webhook(update):
                        offset = update_id + 1
                    else:
                        print("Falha ao entregar ao backend. Tentando novamente em 5s...")
                        time.sleep(5)
            else:
                # Timeout ou sem mensagens, normal
                pass
                
        except KeyboardInterrupt:
            print("\nParando polling...")
            break
        except Exception as e:
            print(f"Erro no loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
