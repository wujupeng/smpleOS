from fastapi import FastAPI

from .api.delivery_controller import router as delivery_router

app = FastAPI(title="AeroForge-X Delivery Center", version="0.1.0")
app.include_router(delivery_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "delivery-center"}