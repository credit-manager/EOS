import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from starlette.responses import StreamingResponse

logger = logging.getLogger("2to-eos.streaming")


@dataclass
class StreamConfig:
    chunk_size: int = 1024
    buffer_size: int = 8192
    timeout: float = 30.0


class StreamingEncoder:
    def __init__(self, config: StreamConfig | None = None):
        self.config = config or StreamConfig()
    
    async def stream_json(
        self,
        data: AsyncIterator[Any],
        status_code: int = 200,
        headers: dict | None = None,
    ) -> StreamingResponse:
        async def generate():
            yield b"["
            first = True
            async for item in data:
                if not first:
                    yield b","
                first = False
                yield json.dumps(item, ensure_ascii=False).encode("utf-8")
            yield b"]"
        
        response_headers = headers or {}
        response_headers["Content-Type"] = "application/json"
        response_headers["Transfer-Encoding"] = "chunked"
        
        return StreamingResponse(
            generate(),
            status_code=status_code,
            headers=response_headers,
        )
    
    async def stream_ndjson(
        self,
        data: AsyncIterator[Any],
        status_code: int = 200,
        headers: dict | None = None,
    ) -> StreamingResponse:
        async def generate():
            async for item in data:
                yield json.dumps(item, ensure_ascii=False).encode("utf-8") + b"\n"
        
        response_headers = headers or {}
        response_headers["Content-Type"] = "application/x-ndjson"
        response_headers["Transfer-Encoding"] = "chunked"
        
        return StreamingResponse(
            generate(),
            status_code=status_code,
            headers=response_headers,
        )
    
    async def stream_csv(
        self,
        data: AsyncIterator[dict],
        columns: list[str] | None = None,
        status_code: int = 200,
        headers: dict | None = None,
    ) -> StreamingResponse:
        async def generate():
            first_row = True
            async for row in data:
                if first_row:
                    cols = columns or list(row.keys())
                    yield ",".join(cols).encode("utf-8") + b"\n"
                    first_row = False
                
                values = [str(row.get(col, "")) for col in (columns or list(row.keys()))]
                yield ",".join(values).encode("utf-8") + b"\n"
        
        response_headers = headers or {}
        response_headers["Content-Type"] = "text/csv"
        response_headers["Transfer-Encoding"] = "chunked"
        
        return StreamingResponse(
            generate(),
            status_code=status_code,
            headers=response_headers,
        )
    
    def stream_file(
        self,
        file_path: str,
        filename: str,
        content_type: str = "application/octet-stream",
        chunk_size: int | None = None,
    ) -> StreamingResponse:
        chunk_size = chunk_size or self.config.chunk_size
        
        def generate():
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
        
        return StreamingResponse(
            generate(),
            media_type=content_type,
            headers=headers,
        )


encoder = StreamingEncoder()


async def stream_json_response(
    data: AsyncIterator[Any],
    status_code: int = 200,
    headers: dict | None = None,
) -> StreamingResponse:
    return await encoder.stream_json(data, status_code, headers)


async def stream_ndjson_response(
    data: AsyncIterator[Any],
    status_code: int = 200,
    headers: dict | None = None,
) -> StreamingResponse:
    return await encoder.stream_ndjson(data, status_code, headers)


async def stream_csv_response(
    data: AsyncIterator[dict],
    columns: list[str] | None = None,
    status_code: int = 200,
    headers: dict | None = None,
) -> StreamingResponse:
    return await encoder.stream_csv(data, columns, status_code, headers)


def stream_file_response(
    file_path: str,
    filename: str,
    content_type: str = "application/octet-stream",
    chunk_size: int | None = None,
) -> StreamingResponse:
    return encoder.stream_file(file_path, filename, content_type, chunk_size)
