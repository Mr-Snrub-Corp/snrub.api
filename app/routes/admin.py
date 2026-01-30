import subprocess

from fastapi import APIRouter, Depends, HTTPException

from app.security.authorization import verify_super_admin_access

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/migrate", dependencies=[Depends(verify_super_admin_access)])
async def run_migrations():
    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True)
        return {"status": "migrations completed"}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {e}") from e
