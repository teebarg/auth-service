import logging
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}

    async def connect(self, id: str, websocket: WebSocket) -> None:
        """
        Establishes a WebSocket connection and adds it to the list of active connections.

        Parameters:
        - websocket: The WebSocket object representing the connection.

        Returns:
        - None
        """
        await websocket.accept()
        self.connections[id] = websocket

    def disconnect(self, id: str) -> None:
        """
        Disconnects a WebSocket connection.

        Parameters:
        - websocket (WebSocket): The WebSocket connection to be disconnected.

        Returns:
        None
        """
        if id in self.connections:
            del self.connections[id]

    async def broadcast(self, id: str, data: dict, type: str = "general") -> None:
        """
        Broadcasts the given data to all active connections.

        Args:
            data (dict): The data to be sent as a JSON object.

        Returns:
            None
        """
        if id in self.connections:
            websocket = self.connections[id]
            await websocket.send_json({**data, "type": type})


manager = ConnectionManager()

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/users/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    Handles the WebSocket endpoint.

    Args:
        websocket (WebSocket): The WebSocket connection.

    Returns:
        None
    """
    await manager.connect(id=user_id, websocket=websocket)
    try:
        await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
