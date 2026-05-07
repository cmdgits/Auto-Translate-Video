import asyncio
from httpx import AsyncClient
from app.web.main import app

async def run_test():
    async with AsyncClient(app=app, base_url="http://test") as client:
        files = {"file": ("test.mp4", b"dummy content", "video/mp4")}
        data = {"translator_backend": "gemini"}
        response = await client.post("/api/jobs", files=files, data=data)
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text}")

if __name__ == "__main__":
    asyncio.run(run_test())
