#!/usr/bin/env python3
"""Seed AeroForge-X database with initial reference data."""

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

DATABASE_URL = "postgresql+asyncpg://aeroforge:aeroforge_dev@localhost:5432/aeroforge_x"

MATERIALS = [
    {"id": str(uuid.uuid4()), "code": "MAT-CFRP-T700", "name": "T700碳纤维预浸料", "category": "composite", "density": 1600.0, "tensile_strength": 2550.0, "elastic_modulus": 135.0},
    {"id": str(uuid.uuid4()), "code": "MAT-CFRP-T300", "name": "T300碳纤维预浸料", "category": "composite", "density": 1600.0, "tensile_strength": 3530.0, "elastic_modulus": 230.0},
    {"id": str(uuid.uuid4()), "code": "MAT-AL6061", "name": "6061铝合金", "category": "metal", "density": 2700.0, "tensile_strength": 310.0, "elastic_modulus": 68.9},
    {"id": str(uuid.uuid4()), "code": "MAT-AL7075", "name": "7075铝合金", "category": "metal", "density": 2810.0, "tensile_strength": 572.0, "elastic_modulus": 71.7},
    {"id": str(uuid.uuid4()), "code": "MAT-GLASS-FIBER", "name": "玻璃纤维复合材料", "category": "composite", "density": 2000.0, "tensile_strength": 1200.0, "elastic_modulus": 45.0},
]

CERT_LEVELS = [
    {"id": str(uuid.uuid4()), "code": "CERT-EXPERIMENTAL", "name": "试验类", "description": "用于实验和研发目的的飞行器认证"},
    {"id": str(uuid.uuid4()), "code": "CERT-LSA", "name": "轻型运动类", "description": "轻型运动飞行器认证"},
    {"id": str(uuid.uuid4()), "code": "CERT-VLA", "name": "甚轻型类", "description": "甚轻型飞行器认证"},
    {"id": str(uuid.uuid4()), "code": "CERT-NORMAL", "name": "正常类", "description": "正常类飞行器认证"},
    {"id": str(uuid.uuid4()), "code": "CERT-UTILITY", "name": "实用类", "description": "实用类飞行器认证"},
]

USERS = [
    {"id": str(uuid.uuid4()), "username": "chief_designer", "email": "chief@aeroforge.dev", "full_name": "总设计师", "role": "chief_designer"},
    {"id": str(uuid.uuid4()), "username": "struct_engineer", "email": "struct@aeroforge.dev", "full_name": "结构工程师", "role": "structural_engineer"},
    {"id": str(uuid.uuid4()), "username": "aero_engineer", "email": "aero@aeroforge.dev", "full_name": "气动工程师", "role": "aerodynamic_engineer"},
    {"id": str(uuid.uuid4()), "username": "process_engineer", "email": "process@aeroforge.dev", "full_name": "工艺工程师", "role": "process_engineer"},
    {"id": str(uuid.uuid4()), "username": "quality_engineer", "email": "quality@aeroforge.dev", "full_name": "质量工程师", "role": "quality_engineer"},
    {"id": str(uuid.uuid4()), "username": "prod_manager", "email": "prod@aeroforge.dev", "full_name": "生产管理员", "role": "production_manager"},
]

STATIONS = [
    {"id": str(uuid.uuid4()), "name": "碳纤维铺层工位", "equipment": "自动铺层机", "status": "idle"},
    {"id": str(uuid.uuid4()), "name": "热压罐固化工位", "equipment": "热压罐", "status": "idle"},
    {"id": str(uuid.uuid4()), "name": "CNC加工工位", "equipment": "5轴CNC", "status": "idle"},
    {"id": str(uuid.uuid4()), "name": "总装工位", "equipment": "装配夹具", "status": "idle"},
    {"id": str(uuid.uuid4()), "name": "检测工位", "equipment": "三坐标测量机", "status": "idle"},
]


async def seed() -> None:
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        now = datetime.now(timezone.utc)

        for m in MATERIALS:
            await session.execute(
                __import__("sqlalchemy").text(
                    "INSERT INTO materials (id, code, name, category, density, tensile_strength, elastic_modulus, created_at) "
                    "VALUES (:id, :code, :name, :category, :density, :tensile_strength, :elastic_modulus, :created_at) "
                    "ON CONFLICT (code) DO NOTHING"
                ),
                {**m, "created_at": now},
            )

        for c in CERT_LEVELS:
            await session.execute(
                __import__("sqlalchemy").text(
                    "INSERT INTO certification_levels (id, code, name, description) "
                    "VALUES (:id, :code, :name, :description) "
                    "ON CONFLICT (code) DO NOTHING"
                ),
                c,
            )

        for u in USERS:
            await session.execute(
                __import__("sqlalchemy").text(
                    "INSERT INTO users (id, username, email, full_name, role, is_active, created_at, updated_at) "
                    "VALUES (:id, :username, :email, :full_name, :role, true, :now, :now) "
                    "ON CONFLICT (username) DO NOTHING"
                ),
                {**u, "now": now},
            )

        for s in STATIONS:
            await session.execute(
                __import__("sqlalchemy").text(
                    "INSERT INTO stations (id, name, equipment, status, created_at) "
                    "VALUES (:id, :name, :equipment, :status, :now) "
                    "ON CONFLICT DO NOTHING"
                ),
                {**s, "now": now},
            )

        await session.commit()

    await engine.dispose()
    print("Seed data inserted successfully.")


if __name__ == "__main__":
    asyncio.run(seed())