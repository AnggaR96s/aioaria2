# -*- coding: utf-8 -*-
import asyncio
import logging
from typing import Optional, Dict

from aiohttp import web
from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)

class Aria2BrowserProxy:
    """
    A local proxy server that intercepts requests and forwards them using curl_cffi
    to simulate browser TLS (JA3/JA4) and HTTP/2 fingerprints.

    This implementation creates a FRESH session for every request to ensure
    clean cookies and TLS state, which is often required to bypass anti-bot systems.
    """

    def __init__(self,
                 port: int = 0,
                 host: str = "127.0.0.1",
                 impersonate: str = "chrome",
                 default_headers: Optional[Dict[str, str]] = None):
        """
        :param port: Port to listen on (0 for random)
        :param host: Host to bind to (default localhost)
        :param impersonate: Browser to impersonate (e.g., "chrome", "safari")
        :param default_headers: Headers to include in every request
        """
        self.port = port
        self.host = host
        self.impersonate = impersonate
        self.default_headers = default_headers or {}
        self._server: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None

    async def start(self):
        """Starts the proxy server."""
        if self._server:
            return

        app = web.Application()
        app.router.add_route('*', '/{tail:.*}', self.handle_request)

        self._server = web.AppRunner(app)
        await self._server.setup()

        self._site = web.TCPSite(self._server, self.host, self.port)
        await self._site.start()

        # Update port if it was 0
        if isinstance(self._site._server.sockets[0].getsockname(), tuple):
             self.port = self._site._server.sockets[0].getsockname()[1]

        logger.info(f"Aria2BrowserProxy started on http://{self.host}:{self.port}")

    async def stop(self):
        """Stops the proxy server."""
        if self._server:
            await self._server.cleanup()
            self._server = None

    @property
    def address(self) -> str:
        return f"http://{self.host}:{self.port}"

    async def handle_request(self, request: web.Request) -> web.StreamResponse:
        """
        Handles incoming proxy requests.
        """
        # 1. Determine Target URL
        target_url = str(request.url)

        # 2. Check for Scheme Override
        target_scheme = request.headers.get("X-Target-Scheme")
        if target_scheme == "https" and target_url.startswith("http:"):
            target_url = "https" + target_url[4:]

        # 3. Filter Headers
        headers = self.default_headers.copy()

        ignore_headers = {
            "host", "proxy-connection", "connection", "keep-alive",
            "transfer-encoding", "te", "trailer", "proxy-authorization",
            "proxy-authenticate", "upgrade", "x-target-scheme",
            "user-agent"
        }

        for k, v in request.headers.items():
            if k.lower() not in ignore_headers:
                headers[k] = v

        method = request.method

        logger.debug(f"Proxying {method} {target_url} (impersonate={self.impersonate})")

        try:
            # 4. Make Request using curl_cffi
            # We use a FRESH session for every request to avoid state/cookie pollution
            async with AsyncSession(impersonate=self.impersonate) as session:
                data = None
                if request.can_read_body:
                    data = await request.read()

                resp = await session.request(
                    method=method,
                    url=target_url,
                    headers=headers,
                    data=data,
                    stream=True,
                    allow_redirects=True
                )

                # 5. Send Response Headers to Client
                client_headers = {}
                for k, v in resp.headers.items():
                    if k.lower() not in ignore_headers:
                        client_headers[k] = v

                response = web.StreamResponse(
                    status=resp.status_code,
                    reason=resp.reason,
                    headers=client_headers
                )

                await response.prepare(request)

                # 6. Stream Body
                try:
                    async for chunk in resp.aiter_content():
                        await response.write(chunk)
                    await response.write_eof()
                except Exception:
                    # Client disconnected or error writing response
                    pass

                return response

        except Exception as e:
            logger.error(f"Proxy error: {e}")
            return web.Response(status=502, text=f"Proxy Error: {e}")

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
