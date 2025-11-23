import asyncio
import httpx

URL = "http://localhost:8000/webhook/whatsapp"

async def send_multimedia(type_):
    payload = {
        "event": "message",
        "payload": {
            "from": "5511999999999@c.us",
            "to": "bot@c.us",
            "body": "",
            "fromMe": False,
            "mediaUrl": "https://example.com/media",
            "_media": {
                "mimetype": "image/jpeg" if type_ == "image" else "audio/ogg"
            }
        }
    }
    # Note: Our webhook currently checks 'body'. For multimedia, we might need to adjust webhook or send body with media.
    # The current webhook implementation expects 'body' to be present for text processing.
    # If body is empty, it returns "ignored".
    # Let's add a body to simulate caption.
    payload["payload"]["body"] = f"Check this {type_}"
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(URL, json=payload)
        print(f"Sent {type_}: {resp.status_code} {resp.json()}")

async def main():
    await send_multimedia("image")
    await send_multimedia("audio")

if __name__ == "__main__":
    asyncio.run(main())
