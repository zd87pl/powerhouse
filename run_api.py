"""Lightweight ASGI runner using aiohttp — avoids uvicorn detection issues."""
import asyncio
import os
import sys

sys.path.insert(0, '/workspace/powerhouse')
os.environ['DATABASE_URL'] = 'sqlite:///instill.db'

from aiohttp import web
from services.instill_api.main import app as fastapi_app


async def handle(request):
    """Bridge aiohttp requests to FastAPI ASGI app."""
    scope = {
        "type": "http",
        "method": request.method,
        "path": request.path,
        "raw_path": request.path.encode(),
        "query_string": request.query_string.encode(),
        "headers": [(k.encode(), v.encode()) for k, v in request.headers.items()],
        "client": (request.remote or "127.0.0.1", 0),
        "server": ("0.0.0.0", 8080),
        "http_version": "1.1",
        "scheme": "http",
    }

    async def receive():
        body = await request.read()
        return {"type": "http.request", "body": body, "more_body": False}

    response_body = []
    response_status = 500
    response_headers = []

    async def send(message):
        nonlocal response_status, response_headers
        if message["type"] == "http.response.start":
            response_status = message["status"]
            response_headers = [(k.decode(), v.decode()) for k, v in message.get("headers", [])]
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))

    await fastapi_app(scope, receive, send)

    resp = web.Response(
        body=b"".join(response_body),
        status=response_status,
    )
    for k, v in response_headers:
        if k.lower() not in ("content-type", "content-length"):
            resp.headers[k] = v
    return resp


async def main():
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("✅ Instill API running on http://0.0.0.0:8080")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
