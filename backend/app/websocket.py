"""WebSocket endpoint for real-time event streaming."""
import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger("2to-eos.websocket")

router = APIRouter(tags=["websocket"])

# Connected clients per tenant
_connections: dict[str, list[WebSocket]] = {}


async def broadcast_event(tenant_id: str, event_type: str, data: dict[str, Any]) -> None:
    """Broadcast an event to all connected clients for a tenant."""
    if tenant_id not in _connections:
        return

    message = json.dumps({
        "type": "event",
        "event_type": event_type,
        "data": data,
    })

    dead = []
    for ws in _connections[tenant_id]:
        try:
            if ws.client_state == WebSocketState.CONNECTED:
                await ws.send_text(message)
            else:
                dead.append(ws)
        except Exception:
            dead.append(ws)

    for ws in dead:
        _connections[tenant_id].remove(ws)


def sync_broadcast(tenant_id: str, event_type: str, data: dict[str, Any]) -> None:
    """Synchronous wrapper for broadcast (for non-async contexts)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(broadcast_event(tenant_id, event_type, data))
        else:
            loop.run_until_complete(broadcast_event(tenant_id, event_type, data))
    except RuntimeError:
        pass


@router.websocket("/ws/{tenant_id}")
async def websocket_endpoint(websocket: WebSocket, tenant_id: str) -> None:
    """WebSocket endpoint for real-time events.

    Connect: ws://host/ws/{tenant_id}?token=xxx
    Receive: {"type":"event","event_type":"invoice.created","data":{...}}
    """
    await websocket.accept()

    if tenant_id not in _connections:
        _connections[tenant_id] = []
    _connections[tenant_id].append(websocket)

    logger.info("WebSocket connected: tenant=%s (total: %d)", tenant_id, len(_connections[tenant_id]))

    try:
        await websocket.send_text(json.dumps({
            "type": "connected",
            "message": "Connected to EOS event stream",
            "tenant_id": tenant_id,
        }))

        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif msg.get("type") == "subscribe":
                await websocket.send_text(json.dumps({
                    "type": "subscribed",
                    "channels": msg.get("channels", []),
                }))

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected: tenant=%s", tenant_id)
    except Exception as e:
        logger.warning("WebSocket error: tenant=%s error=%s", tenant_id, e)
    finally:
        if tenant_id in _connections:
            _connections[tenant_id] = [ws for ws in _connections[tenant_id] if ws != websocket]
            if not _connections[tenant_id]:
                del _connections[tenant_id]
