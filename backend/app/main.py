from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import SessionLocal, ensure_schema
from app.routers import accounts, cards, items, reports
from app.seed import seed

ensure_schema()
_db = SessionLocal()
try:
    seed(_db)
finally:
    _db.close()

app = FastAPI(title="Cash Flow Tracker")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router, prefix="/api")
app.include_router(items.router, prefix="/api")
app.include_router(cards.router, prefix="/api")
app.include_router(reports.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"ok": True}
