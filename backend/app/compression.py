import gzip
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("2to-eos.compression")


class ResponseCompressionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, min_size: int = 1000, compress_level: int = 6):
        super().__init__(app)
        self.min_size = min_size
        self.compress_level = compress_level
        self.compressible_types = {
            "application/json",
            "application/javascript",
            "application/xml",
            "text/html",
            "text/css",
            "text/javascript",
            "text/plain",
            "text/xml",
        }

    def _is_compressible(self, content_type: str) -> bool:
        if not content_type:
            return False
        
        main_type = content_type.split(";")[0].strip()
        return main_type in self.compressible_types

    def _get_accept_encoding(self, request: Request) -> str:
        accept_encoding = request.headers.get("accept-encoding", "")
        return accept_encoding.lower()

    async def dispatch(self, request: Request, call_next):
        accept_encoding = self._get_accept_encoding(request)
        
        if "gzip" not in accept_encoding:
            return await call_next(request)
        
        response = await call_next(request)
        
        content_type = response.headers.get("content-type", "")
        if not self._is_compressible(content_type):
            return response
        
        if hasattr(response, "body"):
            body = response.body
            if len(body) < self.min_size:
                return response
            
            compressed_body = gzip.compress(body, compresslevel=self.compress_level)
            
            if len(compressed_body) >= len(body):
                return response
            
            response.headers["content-encoding"] = "gzip"
            response.headers["content-length"] = str(len(compressed_body))
            response.headers["vary"] = "Accept-Encoding"
            
            return Response(
                content=compressed_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        
        return response
