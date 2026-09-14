import os
import tempfile
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.data_migrate import (
    MAX_UPLOAD_BYTES,
    LedgerDataError,
    migrate_ledger_data,
)
from app.database import DB_PATH, engine, ensure_schema, get_db
from app.security import current_user

router = APIRouter(dependencies=[Depends(current_user)])


def _checkpoint() -> None:
    with engine.connect() as conn:
        conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
        conn.commit()


@router.get("/data/database")
def download_database():
    if not DB_PATH.is_file():
        raise HTTPException(status_code=404, detail="Database file was not found")
    _checkpoint()
    stamp = date.today().isoformat()
    return FileResponse(
        path=DB_PATH,
        filename=f"ledger-{stamp}.db",
        media_type="application/vnd.sqlite3",
    )


@router.post("/data/database")
async def upload_database(
    file: UploadFile = File(...),
    confirm: bool = Query(False),
    db: Session = Depends(get_db),
):
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Confirm overwrite to replace ledger data on this server.",
        )
    db.close()
    ensure_schema()

    handle, tmp_name = tempfile.mkstemp(suffix=".db", prefix="ledger-upload-", dir=str(DB_PATH.parent))
    os.close(handle)
    tmp_path = Path(tmp_name)
    try:
        size = 0
        with tmp_path.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="Database file is too large (32 MB max).",
                    )
                out.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        try:
            imported = migrate_ledger_data(tmp_path)
        except LedgerDataError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail="Could not read that database file.",
            ) from exc
        return {"ok": True, "imported": imported}
    finally:
        tmp_path.unlink(missing_ok=True)
