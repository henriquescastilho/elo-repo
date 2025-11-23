import asyncio
import httpx
import time

URL = "http://localhost:8000/webhook/whatsapp"
CONCURRENCY = 10
TOTAL_REQUESTS = 100

async def send_request(client, i):
    payload = {
        "event": "message",
        "payload": {
            "from": f"551199999{i:04d}@c.us",
            "to": "bot@c.us",
            "body": "Como tirar o CPF?",
            "fromMe": False
        }
    }
    try:
        start = time.perf_counter()
        resp = await client.post(URL, json=payload)
        elapsed = time.perf_counter() - start
        return resp.status_code, elapsed
    except Exception:
        return "error", 0

async def main():
    print(f"Starting load test: {TOTAL_REQUESTS} requests, concurrency {CONCURRENCY}")
    async with httpx.AsyncClient() as client:
        tasks = []
        for i in range(TOTAL_REQUESTS):
            tasks.append(send_request(client, i))
            if len(tasks) >= CONCURRENCY:
                await asyncio.gather(*tasks)
                tasks = []
        if tasks:
            await asyncio.gather(*tasks)
    print("Load test finished.")

if __name__ == "__main__":
    asyncio.run(main())
