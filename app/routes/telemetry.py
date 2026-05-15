import asyncio
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.controllers.telemetry import get_reactor_metrics
from app.security.jwt import decode_jwt

from logging import getLogger
from sqlmodel import Session
from ..db.database import get_session

# Set up logger
logger = getLogger(__name__)

router = APIRouter(tags=["Telemetry"])


# TODO Send the token as the first message once the connection is established. Keeps the token out of the URL/logs
# So needs to be changed  to expect an initial JSON message,
@router.websocket("/ws/telemetry")
async def telemetry_stream(websocket: WebSocket, token: str = Query(...), session: Session = Depends(get_session)):
    payload = decode_jwt(token)
    if not payload:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    try:
        while True:
            metrics = get_reactor_metrics(session)
            await websocket.send_json(metrics)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
