import asyncio
import httpx
import os

WAHA_BASE_URL = os.getenv("WAHA_BASE_URL", "http://localhost:3000")
WAHA_API_TOKEN = os.getenv("WAHA_API_TOKEN", "")

async def reset_session():
    headers = {"X-Api-Key": WAHA_API_TOKEN}
    async with httpx.AsyncClient() as client:
        # Stop session
        print("Stopping session...")
        await client.post(f"{WAHA_BASE_URL}/api/sessions/stop", json={"name": "default"}, headers=headers)
        
        # Start session
        print("Starting session...")
        await client.post(f"{WAHA_BASE_URL}/api/sessions/start", json={"name": "default"}, headers=headers)
        
        print("Session reset complete.")

if __name__ == "__main__":
    asyncio.run(reset_session())
