from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.domain.enums import ReductionMethod
from src.domain.services.model_reduction_service import ModelReductionService
from src.infrastructure.database import get_pg_pool

router = APIRouter()


class GenerateROMRequest(BaseModel):
    source_model_id: str
    method: ReductionMethod


class DeployROMRequest(BaseModel):
    runtime_id: str


@router.post("/reduced-models")
async def generate_rom(req: GenerateROMRequest):
    pool = await get_pg_pool()
    try:
        rom = await ModelReductionService.generate_rom(req.source_model_id, req.method, pool=pool)
        return rom.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reduced-models/{rom_id}")
async def get_rom(rom_id: str):
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM physics_twin.reduced_order_models WHERE rom_id = $1", rom_id)
        if row is None:
            raise HTTPException(status_code=404, detail="ROM not found")
        return dict(row)


@router.post("/reduced-models/{rom_id}/deploy")
async def deploy_rom(rom_id: str, req: DeployROMRequest):
    pool = await get_pg_pool()
    result = await ModelReductionService.deploy_rom(rom_id, req.runtime_id, pool=pool)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/reduced-models/{rom_id}/hot-swap")
async def hot_swap_rom(rom_id: str, req: DeployROMRequest):
    pool = await get_pg_pool()
    result = await ModelReductionService.hot_swap_rom(rom_id, req.runtime_id, pool=pool)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result