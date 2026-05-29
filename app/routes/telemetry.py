import asyncio
from logging import getLogger

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlmodel import Session

from app.controllers.telemetry import get_reactor_metrics
from app.security.authorization import authenticate_websocket

from ..db.database import get_session

logger = getLogger(__name__)

router = APIRouter(tags=["Telemetry"])


# TODO Send the token as the first message once the connection is established. Keeps the token out of the URL/logs
# So needs to be changed  to expect an initial JSON message,
@router.websocket("/ws/telemetry")
async def telemetry_stream(websocket: WebSocket, token: str = Query(...), session: Session = Depends(get_session)):
    user_data = await authenticate_websocket(websocket, token, session)
    if user_data is None:
        return

    await websocket.accept()
    try:
        while True:
            metrics = get_reactor_metrics(session)
            await websocket.send_json(metrics)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
