"""
P74.3 WebSocket Connection Manager
Real-time notification delivery via WebSocket.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Dict, Set, Optional
import asyncio

from core.auth import get_current_user

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.connection_info: Dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket, user_id: str, tenant_id: str = None):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        self.connection_info[websocket] = {"user_id": user_id, "tenant_id": tenant_id}

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        self.connection_info.pop(websocket, None)

    async def send_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            dead = set()
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.add(ws)
            for ws in dead:
                self.active_connections[user_id].discard(ws)

    async def broadcast(self, message: dict, tenant_id: str = None):
        dead = []
        for user_id, connections in self.active_connections.items():
            for ws in connections.copy():
                info = self.connection_info.get(ws, {})
                if tenant_id and info.get("tenant_id") != tenant_id:
                    continue
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append((user_id, ws))
        for user_id, ws in dead:
            self.active_connections.get(user_id, set()).discard(ws)
            self.connection_info.pop(ws, None)

    def get_online_users(self) -> list:
        return list(self.active_connections.keys())


manager = ConnectionManager()


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    user_id = None
    tenant_id = None
    try:
        if token:
            from core.production_auth import verify_token as prod_verify
            try:
                payload = prod_verify(token)
                user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
                tenant_id = payload.get("tenant_id")
            except Exception:
                pass

        if not user_id:
            await websocket.close(code=4001, reason="Authentication required")
            return

        await manager.connect(websocket, user_id, tenant_id)
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connected",
            "user_id": user_id
        })

        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg.get("type") == "subscribe":
                await websocket.send_json({
                    "type": "subscribed",
                    "channel": msg.get("channel", "general")
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception:
        manager.disconnect(websocket, user_id)


@router.get("/ws/online")
async def get_online_users():
    return {"online_users": manager.get_online_users(), "count": len(manager.get_online_users())}
