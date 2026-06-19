from fastapi import FastAPI

from .api.supplier_controller import router as supplier_router
from .api.purchase_controller import router as purchase_router
from .api.supply_v2_controller import router as supply_v2_router

app = FastAPI(title="AeroForge-X Supply Chain", version="0.2.0")
app.include_router(supplier_router)
app.include_router(purchase_router)
app.include_router(supply_v2_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "supply-chain"}