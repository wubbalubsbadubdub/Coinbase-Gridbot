from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/control", tags=["control"])

@router.post("/cancel_all")
async def cancel_all(request: Request):
    """
    Emergency Stop: Cancel all open orders.
    """
    if hasattr(request.app.state, "bot_engine") and request.app.state.bot_engine:
        await request.app.state.bot_engine.stop_and_cancel_all()
        return {"status": "triggered", "message": "Emergency cancellation initiated"}
    
    raise HTTPException(status_code=503, detail="Bot engine not ready")
