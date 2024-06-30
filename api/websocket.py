import logging
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect


class ConnectionManager:
    def __init__(self):
        self.connections: Dict[str, list[WebSocket]] = {}

    async def connect(self, id: str, websocket: WebSocket) -> None:
        """
        Establishes a WebSocket connection and adds it to the list of active connections.

        Parameters:
        - websocket: The WebSocket object representing the connection.

        Returns:
        - None
        """
        await websocket.accept()
        conns = self.connections.get(id, [])
        conns.append(websocket)
        self.connections.update({id: conns})

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Disconnects a WebSocket connection.

        Parameters:
        - websocket (WebSocket): The WebSocket connection to be disconnected.

        Returns:
        None
        """
        for key in self.connections:
            self.connections[key].remove(websocket)

    async def broadcast(self, id: str, data: dict) -> None:
        """
        Broadcasts the given data to all active connections.

        Args:
            data (dict): The data to be sent as a JSON object.

        Returns:
            None
        """
        for connection in self.connections.get(id, []):
            await connection.send_json(data)


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
