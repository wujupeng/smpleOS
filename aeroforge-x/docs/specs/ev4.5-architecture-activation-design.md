# AeroForge-X EV-4.5 Architecture Activation — 技术架构设计文档

**项目**: AeroForge-X v6.0 "Project Valkyrie"  
**Sprint**: EV-4.5 Architecture Activation  
**目标 TRL**: 5.5 → 6.0  
**日期**: 2026-06-22  
**状态**: DRAFT  
**关联需求文档**: `ev4.5-architecture-activation-spec.md`

---

# 1. 实现模型

## 1.1 上下文视图

EV-4.5 将 AeroForge-X 从 EV-4 的单服务闭环（React → FastAPI → PostgreSQL）升级为多服务事件驱动架构。系统边界包含 3 个 FastAPI 服务 + 4 个基础设施组件，通过 Docker Compose 统一编排。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AeroForge-X EV-4.5 System                         │
│                                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                    │
│  │ Aircraft Core │   │Workflow Engine│   │ Physics Twin │                    │
│  │  (FastAPI)    │   │  (FastAPI)    │   │  (FastAPI)   │                    │
│  │  Port 8001    │   │  Port 8002    │   │  Port 8003   │                    │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘                    │
│         │                  │                   │                            │
│         │    publish       │    subscribe      │    subscribe               │
│         ├─────────────────►│───────────────────┤                            │
│         │                  │                   │                            │
│  ┌──────▼───────┐   ┌──────▼───────┐   ┌──────▼───────┐                    │
│  │ PostgreSQL 16│   │NATS JetStream│   │   Neo4j 5    │   ┌──────────┐    │
│  │  Port 5432   │   │ 4222 / 8222  │   │7474 / 7687  │   │  MinIO   │    │
│  │              │   │              │   │              │   │9000/9001 │    │
│  └──────────────┘   └──────────────┘   └──────────────┘   └──────────┘    │
│                                                                             │
│  ┌──────────────┐                                                          │
│  │   Frontend   │  (EV-4 遗留，EV-4.5 不变更)                               │
│  │  Port 80     │                                                          │
│  └──────────────┘                                                          │
└─────────────────────────────────────────────────────────────────────────────┘

外部系统:
  - 远程部署服务器: 8.210.239.214:6000 (Debian 13, Docker 26.1.5)
  - React 前端浏览器客户端 (通过 nginx 反向代理访问)
```

### 系统交互关系

| 发布方 | 消息通道 | 消费方 | 事件类型 |
|--------|----------|--------|----------|
| Aircraft Core | NATS `aeroforge.config.block.updated` | Workflow Engine | `BlockUpdatedEvent` |
| Aircraft Core | NATS `aeroforge.config.configuration.updated` | Physics Twin | `ConfigurationUpdatedEvent` |
| Aircraft Core | Neo4j bolt:// | — (直接写入) | Configuration Identity Node |
| Aircraft Core | MinIO HTTP | — (直接写入) | Evidence Object |
| Aircraft Core | PostgreSQL | — (直接读写) | Block/SN Configuration |
| Workflow Engine | PostgreSQL | — (直接读写) | Workflow State |
| Physics Twin | PostgreSQL | — (直接读写) | Twin State |

## 1.2 服务/组件总体架构

### 1.2.1 容器编排架构 (docker-compose.ev45.yml)

```
                    ┌─────────────┐
                    │  PostgreSQL │
                    │  (Layer 0)  │
                    └──────┬──────┘
                           │ service_healthy
              ┌────────────┼────────────────┐
              │            │                │
     ┌────────▼───┐  ┌────▼─────┐  ┌──────▼─────┐
     │    NATS    │  │  Neo4j   │  │   MinIO    │
     │ (Layer 1)  │  │(Layer 1) │  │ (Layer 1)  │
     └─────┬──────┘  └────┬─────┘  └──────┬─────┘
           │              │               │
     ┌─────▼──────┐  ┌───▼──────┐  ┌─────▼──────┐
     │  init-nats │  │init-neo4j│  │ init-minio │
     │ (Layer 1.5)│  │(Layer 1.5)│  │(Layer 1.5) │
     └─────┬──────┘  └───┬──────┘  └─────┬──────┘
           │              │               │
     ┌─────┴──────────────┴───────────────┘
     │           service_completed_successfully
     │
     ├──────────────┬────────────────────┐
     │              │                    │
┌────▼────────┐ ┌──▼──────────┐ ┌──────▼───────┐
│Aircraft Core│ │Workflow Eng.│ │ Physics Twin │
│ (Layer 2)   │ │ (Layer 2)   │ │  (Layer 2)   │
│  Port 8001  │ │  Port 8002  │ │  Port 8003   │
└─────────────┘ └─────────────┘ └──────────────┘
```

**启动依赖链**:
- **Layer 0**: `postgres` — 无依赖，最先启动
- **Layer 1**: `nats`, `neo4j`, `minio` — 依赖 `postgres:service_healthy`
- **Layer 1.5**: `init-nats`, `init-neo4j`, `init-minio` — 依赖对应 Layer 1 服务 `service_healthy`
- **Layer 2**: `aircraft-core`, `workflow-engine`, `physics-twin` — 依赖 Layer 1 服务 `service_healthy` + Layer 1.5 init 容器 `service_completed_successfully`

### 1.2.2 服务内部架构

#### Aircraft Core Service (事件发布方 + Neo4j/MinIO 写入方)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Aircraft Core Service                         │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                     API Layer (FastAPI)                    │   │
│  │  ┌──────────────────┐  ┌───────────────┐  ┌───────────┐  │   │
│  │  │configuration_    │  │evidence_      │  │config_    │  │   │
│  │  │controller.py     │  │controller.py  │  │identity_  │  │   │
│  │  │(现有 + PATCH事件) │  │(新增 Sprint-D)│  │controller │  │   │
│  │  └────────┬─────────┘  └───────┬───────┘  │(新增SprintC)│  │   │
│  │           │                    │           └─────┬─────┘  │   │
│  └───────────┼────────────────────┼─────────────────┼────────┘   │
│              │                    │                 │            │
│  ┌───────────▼────────────────────▼─────────────────▼────────┐   │
│  │                    Domain Service Layer                     │   │
│  │  ┌──────────────────┐  ┌──────────────┐  ┌──────────────┐│   │
│  │  │Configuration     │  │Evidence      │  │ConfigIdentity││   │
│  │  │Manager Service   │  │Storage       │  │Graph Service ││   │
│  │  │(现有 + 事件发布)  │  │Service       │  │(新增Sprint-C)││   │
│  │  └────────┬─────────┘  │(新增Sprint-D)│  └──────┬───────┘│   │
│  │           │            └──────┬───────┘         │        │   │
│  └───────────┼───────────────────┼─────────────────┼────────┘   │
│              │                   │                 │            │
│  ┌───────────▼───────────────────▼─────────────────▼────────┐   │
│  │                 Infrastructure Layer                        │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │   │
│  │  │event_bus │  │database  │  │object_   │  │graph_    │ │   │
│  │  │.py       │  │.py       │  │storage   │  │client    │ │   │
│  │  │(现有→升级│  │(现有→扩展│  │.py       │  │.py       │ │   │
│  │  │JetStream)│  │Neo4j连接)│  │(新增)    │  │(新增)    │ │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │   │
│  └───────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

#### Workflow Engine Service (NATS 事件消费方)

```
┌──────────────────────────────────────────────────┐
│           Workflow Engine Service                 │
│                                                   │
│  ┌────────────────────────────────────────────┐  │
│  │              API Layer (FastAPI)             │  │
│  │  ┌──────────────────────────────────────┐  │  │
│  │  │config_change_controller.py (现有)     │  │  │
│  │  └──────────────────┬───────────────────┘  │  │
│  └─────────────────────┼──────────────────────┘  │
│                        │                          │
│  ┌─────────────────────▼──────────────────────┐  │
│  │           Domain Service Layer               │  │
│  │  ┌──────────────────────────────────────┐  │  │
│  │  │ConfigurationChangeControlService      │  │  │
│  │  │(现有 + NATS 消费者注册)               │  │  │
│  │  └──────────────────┬───────────────────┘  │  │
│  └─────────────────────┼──────────────────────┘  │
│                        │                          │
│  ┌─────────────────────▼──────────────────────┐  │
│  │          Infrastructure Layer                │  │
│  │  ┌──────────┐  ┌──────────────────────┐    │  │
│  │  │event_bus │  │nats_consumer.py      │    │  │
│  │  │.py       │  │(新增: JetStream消费) │    │  │
│  │  │(现有→升级│  └──────────────────────┘    │  │
│  │  │subscribe)│  ┌──────────────────────┐    │  │
│  │  └──────────┘  │database.py (现有)    │    │  │
│  │                └──────────────────────┘    │  │
│  └───────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

#### Physics Twin Service (NATS 事件消费方)

```
┌──────────────────────────────────────────────────┐
│            Physics Twin Service                   │
│                                                   │
│  ┌────────────────────────────────────────────┐  │
│  │              API Layer (FastAPI)             │  │
│  │  ┌──────────────────────────────────────┐  │  │
│  │  │digital_twin_controller.py (现有)      │  │  │
│  │  └──────────────────┬───────────────────┘  │  │
│  └─────────────────────┼──────────────────────┘  │
│                        │                          │
│  ┌─────────────────────▼──────────────────────┐  │
│  │           Domain Service Layer               │  │
│  │  ┌──────────────────────────────────────┐  │  │
│  │  │DigitalTwinSynchronizerService         │  │  │
│  │  │(现有 + NATS 消费者注册)               │  │  │
│  │  └──────────────────┬───────────────────┘  │  │
│  └─────────────────────┼──────────────────────┘  │
│                        │                          │
│  ┌─────────────────────▼──────────────────────┐  │
│  │          Infrastructure Layer                │  │
│  │  ┌──────────┐  ┌──────────────────────┐    │  │
│  │  │event_bus │  │nats_consumer.py      │    │  │
│  │  │.py       │  │(新增: JetStream消费) │    │  │
│  │  │(现有→升级│  └──────────────────────┘    │  │
│  │  │subscribe)│  ┌──────────────────────┐    │  │
│  │  └──────────┘  │database.py (现有)    │    │  │
│  │                └──────────────────────┘    │  │
│  └───────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

## 1.3 实现设计文档

### 1.3.1 Sprint-A: Infrastructure Bring-up

#### Docker Compose 结构设计

基于 `docker-compose.v61.yml` 模板，移除 TimescaleDB（EV-4.5 约束），调整依赖关系：

```yaml
# docker-compose.ev45.yml — 核心结构设计
version: "3.9"

services:
  # === Layer 0: 数据库 ===
  postgres:
    image: postgres:16
    container_name: aeroforge-postgres
    ports: ["5432:5432"]
    environment:
      POSTGRES_PASSWORD: ${PG_PASSWORD:-aeroforge}
      POSTGRES_DB: aeroforge
    volumes:
      - pg_data:/var/lib/postgresql/data
      # 所有 SQL migration 文件 (沿用 EV-4)
      - ./migrations/v2_0/001_aircraft_core_tables.sql:/docker-entrypoint-initdb.d/001.sql:ro
      - ./migrations/v2_0/002_workflow_engine_tables.sql:/docker-entrypoint-initdb.d/002.sql:ro
      - ./migrations/v2_0/003_physics_twin_tables.sql:/docker-entrypoint-initdb.d/003.sql:ro
      - ./migrations/v6_0/001_physics_twin_v6_tables.sql:/docker-entrypoint-initdb.d/004.sql:ro
      - ./migrations/v6_0/002_aircraft_core_v6_tables.sql:/docker-entrypoint-initdb.d/005.sql:ro
      - ./migrations/v6_1/004_v61_physics_twin_tables.sql:/docker-entrypoint-initdb.d/006.sql:ro
      - ./migrations/v6_1/005_v61_aircraft_core_tables.sql:/docker-entrypoint-initdb.d/007.sql:ro
      - ./migrations/v6_2/006_configuration_uuid_tables.sql:/docker-entrypoint-initdb.d/008.sql:ro
      - ./migrations/v6_3/007_optimistic_lock_version.sql:/docker-entrypoint-initdb.d/009.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 10
    networks: [aeroforge-net]

  # === Layer 1: 基础设施服务 ===
  nats:
    image: nats:alpine
    container_name: aeroforge-nats
    ports: ["4222:4222", "8222:8222"]
    command: --jetstream --store_dir /data
    volumes: [nats_data:/data]
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8222/healthz || exit 1"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks: [aeroforge-net]

  neo4j:
    image: neo4j:5
    container_name: aeroforge-neo4j
    ports: ["7474:7474", "7687:7687"]
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-aeroforge_neo4j}
      NEO4J_PLUGINS: '["apoc"]'
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:7474 || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10
    networks: [aeroforge-net]

  minio:
    image: minio/minio:latest
    container_name: aeroforge-minio
    ports: ["9000:9000", "9001:9001"]
    environment:
      MINIO_ROOT_USER: ${MINIO_USER:-aeroforge}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET:-aeroforge123}
    command: server /data --console-address ":9001"
    volumes: [minio_data:/data]
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:9000/minio/health/live || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks: [aeroforge-net]

  # === Layer 1.5: Init 容器 ===
  init-nats:
    image: python:3.12-slim
    container_name: aeroforge-init-nats
    environment:
      NATS_URL: nats://nats:4222
    depends_on:
      nats: { condition: service_healthy }
    volumes:
      - ../scripts/init_nats_streams.py:/init_nats_streams.py:ro
    entrypoint: ["python", "/init_nats_streams.py"]
    restart: "no"
    networks: [aeroforge-net]

  init-neo4j:
    image: neo4j:5
    container_name: aeroforge-init-neo4j
    environment:
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: ${NEO4J_PASSWORD:-aeroforge_neo4j}
    depends_on:
      neo4j: { condition: service_healthy }
    volumes:
      - ../scripts/init_neo4j_schema.py:/init_neo4j_schema.py:ro
    entrypoint: ["python", "/init_neo4j_schema.py"]
    restart: "no"
    networks: [aeroforge-net]

  init-minio:
    image: minio/mc:latest
    container_name: aeroforge-init-minio
    environment:
      MINIO_ENDPOINT: minio:9000
      MINIO_USER: ${MINIO_USER:-aeroforge}
      MINIO_SECRET: ${MINIO_SECRET:-aeroforge123}
    depends_on:
      minio: { condition: service_healthy }
    volumes:
      - ../scripts/init_minio_buckets.sh:/init_minio_buckets.sh:ro
    entrypoint: ["sh", "/init_minio_buckets.sh"]
    restart: "no"
    networks: [aeroforge-net]

  # === Layer 2: 应用服务 ===
  aircraft-core:
    build:
      context: ../services/aircraft-core-service
      dockerfile: Dockerfile
    container_name: aeroforge-aircraft-core
    ports: ["8001:8001"]
    environment:
      DATABASE_URL: postgresql://postgres:${PG_PASSWORD:-aeroforge}@postgres:5432/aeroforge
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: ${NEO4J_PASSWORD:-aeroforge_neo4j}
      NATS_SERVERS: nats://nats:4222
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_USER:-aeroforge}
      MINIO_SECRET_KEY: ${MINIO_SECRET:-aeroforge123}
      ENCRYPTION_MASTER_KEY: ${ENCRYPTION_MASTER_KEY:-aeroforge-master-key-32bytes!!}
    depends_on:
      postgres: { condition: service_healthy }
      neo4j: { condition: service_healthy }
      nats: { condition: service_healthy }
      init-nats: { condition: service_completed_successfully }
      init-neo4j: { condition: service_completed_successfully }
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8001/api/v6/aircraft-core/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks: [aeroforge-net]

  workflow-engine:
    build:
      context: ../services/workflow-engine-service
      dockerfile: Dockerfile
    container_name: aeroforge-workflow-engine
    ports: ["8002:8002"]
    environment:
      DATABASE_URL: postgresql://postgres:${PG_PASSWORD:-aeroforge}@postgres:5432/aeroforge
      NATS_SERVERS: nats://nats:4222
    depends_on:
      postgres: { condition: service_healthy }
      nats: { condition: service_healthy }
      init-nats: { condition: service_completed_successfully }
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8002/api/v6/workflow-engine/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks: [aeroforge-net]

  physics-twin:
    build:
      context: ../services/physics-twin-service
      dockerfile: Dockerfile
    container_name: aeroforge-physics-twin
    ports: ["8003:8003"]
    environment:
      DATABASE_URL: postgresql://postgres:${PG_PASSWORD:-aeroforge}@postgres:5432/aeroforge
      NATS_SERVERS: nats://nats:4222
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_USER:-aeroforge}
      MINIO_SECRET_KEY: ${MINIO_SECRET:-aeroforge123}
    depends_on:
      postgres: { condition: service_healthy }
      nats: { condition: service_healthy }
      minio: { condition: service_healthy }
      init-nats: { condition: service_completed_successfully }
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8003/api/v6/physics-twin/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    networks: [aeroforge-net]

volumes:
  pg_data:
  neo4j_data:
  nats_data:
  minio_data:

networks:
  aeroforge-net:
    driver: bridge
```

**与 v61.yml 的关键差异**:
1. 移除 `timescaledb` 服务及 `ts_data` volume
2. 移除 physics-twin 对 timescaledb 的依赖
3. 移除 physics-twin 的 `TIMESCALEDB_URL` 环境变量
4. init-nats 改用 Python 脚本（替代 shell 脚本，确保幂等性）
5. init-neo4j 改用 Python 脚本（使用 neo4j Python driver）
6. 新增 `MINIO_ENDPOINT` / `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` 到 aircraft-core 和 physics-twin
7. 新增 `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` 到 aircraft-core

#### Init 容器设计

**init-nats (Python)** — 创建 JetStream Stream + Consumer:

```python
# scripts/init_nats_streams.py — 结构设计
import asyncio
import nats

async def main():
    nc = await nats.connect(os.getenv("NATS_URL", "nats://localhost:4222"))
    js = nc.jetstream()
    
    # 创建 Stream (幂等: 如果已存在则跳过)
    try:
        await js.add_stream(
            name="AEROFORGE_CONFIG",
            subjects=["aeroforge.config.>"],
            retention="limits",
            max_msgs=100000,
            max_age=168 * 3600 * 1_000_000_000,  # 168h in nanoseconds
        )
    except nats.js.errors.StreamAlreadyExistsError:
        pass  # 幂等: 已存在则跳过
    
    # 创建 Durable Consumers (幂等)
    for consumer_name, filter_subject in [
        ("workflow-engine-config-consumer", "aeroforge.config.>"),
        ("physics-twin-config-consumer", "aeroforge.config.configuration.updated"),
    ]:
        try:
            await js.add_consumer(
                stream="AEROFORGE_CONFIG",
                name=consumer_name,
                durable_name=consumer_name,
                filter_subject=filter_subject,
                ack_policy="explicit",
                max_deliver=3,
                ack_wait=30 * 1_000_000_000,  # 30s in nanoseconds
            )
        except nats.js.errors.ConsumerAlreadyExistsError:
            pass  # 幂等
    
    await nc.close()

asyncio.run(main())
```

**init-neo4j (Python)** — 创建 Schema 约束 + 种子数据:

```python
# scripts/init_neo4j_schema.py — 结构设计
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "aeroforge_neo4j"))
)

with driver.session() as session:
    # UNIQUE 约束 (幂等: IF NOT EXISTS)
    session.run("CREATE CONSTRAINT node_id_unique IF NOT EXISTS FOR (n:ConfigurationIdentity) REQUIRE n.node_id IS UNIQUE")
    session.run("CREATE CONSTRAINT aircraft_type_unique IF NOT EXISTS FOR (a:Aircraft) REQUIRE a.aircraft_type IS UNIQUE")
    session.run("CREATE CONSTRAINT block_node_id_unique IF NOT EXISTS FOR (b:Block) REQUIRE b.node_id IS UNIQUE")
    session.run("CREATE CONSTRAINT sn_node_id_unique IF NOT EXISTS FOR (s:SN) REQUIRE s.node_id IS UNIQUE")
    
    # EV-5 预留约束 (仅创建约束，不写入数据)
    session.run("CREATE CONSTRAINT requirement_id_unique IF NOT EXISTS FOR (r:Requirement) REQUIRE r.node_id IS UNIQUE")
    session.run("CREATE CONSTRAINT design_element_id_unique IF NOT EXISTS FOR (d:DesignElement) REQUIRE d.node_id IS UNIQUE")
    
    # B737 种子数据 (幂等: MERGE 而非 CREATE)
    session.run("""
        MERGE (a:Aircraft {aircraft_type: 'B737'})
        MERGE (wing:Block {node_id: 'B737-WING-001', block_name: 'Wing', aircraft_type: 'B737'})
        MERGE (fuse:Block {node_id: 'B737-FUSE-001', block_name: 'Fuselage', aircraft_type: 'B737'})
        MERGE (eng:Block {node_id: 'B737-ENG-001', block_name: 'Engine', aircraft_type: 'B737'})
        MERGE (a)-[:HAS_BLOCK]->(wing)
        MERGE (a)-[:HAS_BLOCK]->(fuse)
        MERGE (a)-[:HAS_BLOCK]->(eng)
    """)

driver.close()
```

**init-minio (Shell)** — 创建 Buckets:

```bash
# scripts/init_minio_buckets.sh — 结构设计
#!/bin/sh
mc alias set aeroforge http://${MINIO_ENDPOINT} ${MINIO_USER} ${MINIO_SECRET}

for bucket in \
  aeroforge-cert-evidence \
  aeroforge-dataset-artifacts \
  aeroforge-mdo-results \
  aeroforge-phm-models \
  aeroforge-uq-reports \
  aeroforge-gdt-annotations \
  aeroforge-export-packages \
  aeroforge-backups; do
  mc mb aeroforge/${bucket} --ignore-existing  # 幂等: --ignore-existing
done
```

### 1.3.2 Sprint-B: NATS JetStream Event Bus

#### EventBus 升级设计

现有 `aircraft-core-service/src/infrastructure/event_bus.py` 使用 Core NATS 的 `publish`/`subscribe`，需升级为 JetStream 模式。

**升级策略**: 在现有 `EventBus` 类中新增 `publish_jetstream` 和 `subscribe_jetstream` 方法，保留原有 `publish`/`subscribe` 方法不变（向后兼容）。

```python
# aircraft-core-service/src/infrastructure/event_bus.py — 升级设计

import json
import os
import logging
from typing import Any, Callable

try:
    import nats as nats_lib
    _HAS_NATS = True
except ImportError:
    _HAS_NATS = False

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self):
        self._nc = None
        self._js = None  # JetStream context
        self._servers = os.getenv('NATS_SERVERS', 'nats://localhost:4222')

    async def connect(self):
        if not _HAS_NATS:
            logger.warning('NATS library not available, event_bus disabled')
            return
        try:
            self._nc = await nats_lib.connect(self._servers)
            self._js = self._nc.jetstream()  # 获取 JetStream context
            logger.info(f'NATS JetStream connected to {self._servers}')
        except Exception as e:
            logger.warning(f'NATS connection failed: {e}, event_bus disabled')
            self._nc = None
            self._js = None

    async def close(self):
        if self._nc:
            await self._nc.close()
            self._nc = None
            self._js = None

    async def publish(self, subject: str, data: dict[str, Any]) -> None:
        """Core NATS publish (保留向后兼容)"""
        if not _HAS_NATS or self._nc is None:
            return
        payload = json.dumps(data, default=str).encode()
        await self._nc.publish(subject, payload)

    async def publish_jetstream(self, subject: str, data: dict[str, Any]) -> None:
        """JetStream publish — 事件持久化到 Stream"""
        if not _HAS_NATS or self._js is None:
            logger.warning(f'NATS JetStream not available, skipping publish to {subject}')
            return
        payload = json.dumps(data, default=str).encode()
        ack = await self._js.publish(subject, payload)
        logger.info(f'Published to {subject}, seq={ack.seq}')

    async def subscribe(self, subject: str, callback: Callable) -> None:
        """Core NATS subscribe (保留向后兼容)"""
        if not _HAS_NATS or self._nc is None:
            return
        await self._nc.subscribe(subject, cb=callback)

    async def subscribe_jetstream(
        self,
        subject: str,
        durable_name: str,
        callback: Callable,
        stream: str = "AEROFORGE_CONFIG",
    ) -> None:
        """JetStream durable consumer subscribe — 持久订阅"""
        if not _HAS_NATS or self._js is None:
            logger.warning(f'NATS JetStream not available, skipping subscribe to {subject}')
            return
        # 使用 push consumer 模式，绑定 durable consumer
        await self._js.subscribe(
            subject=subject,
            queue=durable_name,
            cb=callback,
            durable=durable_name,
            stream=stream,
            manual_ack=True,  # 手动 ACK
        )
        logger.info(f'Subscribed to {subject} with durable={durable_name}')


event_bus = EventBus()
```

#### 事件发布集成点

在 `configuration_controller.py` 的 `update_block_config` 中，PATCH 成功后发布事件：

```python
# configuration_controller.py — PATCH 端点事件发布集成

@router.patch("/block-configurations/{block_id}")
async def update_block_config(block_id: str, body: dict[str, Any]):
    # ... 现有逻辑: repo.update_block + invalidate_cache ...
    
    # 新增: 发布 BlockUpdatedEvent
    from src.infrastructure.event_bus import event_bus
    from src.domain.events.block_updated_event import BlockUpdatedEvent
    
    event = BlockUpdatedEvent(
        block_id=block_id,
        aircraft_type=updated_db.get("aircraft_type", ""),
        version=updated_db.get("version", 1),
        changed_fields=list(body.keys()),
    )
    await event_bus.publish_jetstream(
        subject="aeroforge.config.block.updated",
        data=event.to_dict(),
    )
    
    # 新增: 发布 ConfigurationUpdatedEvent (Sprint-E)
    from src.domain.events.configuration_updated_event import ConfigurationUpdatedEvent
    
    config_event = ConfigurationUpdatedEvent(
        configuration_id=block_id,
        block_id=block_id,
        aircraft_type=updated_db.get("aircraft_type", ""),
        change_type="UPDATED",
    )
    await event_bus.publish_jetstream(
        subject="aeroforge.config.configuration.updated",
        data=config_event.to_dict(),
    )
    
    return resp
```

#### Workflow Engine 消费者设计

在 `workflow-engine-service` 的 `main.py` lifespan 中注册 NATS 消费者：

```python
# workflow-engine-service/src/main.py — 消费者注册设计

from src.infrastructure.nats_consumer import register_config_consumer

@asynccontextmanager
async def lifespan(app: FastAPI):
    await event_bus.connect()
    await register_config_consumer(event_bus)  # 新增
    yield
    await event_bus.close()
    await close_connections()
```

```python
# workflow-engine-service/src/infrastructure/nats_consumer.py — 新增文件

import json
import logging
from datetime import datetime

from src.infrastructure.event_bus import event_bus

logger = logging.getLogger(__name__)


async def handle_block_updated_event(msg):
    """处理 BlockUpdatedEvent"""
    try:
        data = json.loads(msg.data.decode())
        event_id = data.get("event_id", "")
        block_id = data.get("block_id", "")
        received_at = datetime.utcnow().isoformat()
        
        logger.info(
            f"BlockUpdatedEvent consumed: event_id={event_id}, "
            f"block_id={block_id}, received_at={received_at}"
        )
        
        await msg.ack()  # 手动 ACK
    except Exception as e:
        logger.error(f"Error processing BlockUpdatedEvent: {e}")
        await msg.nak()  # NACK，触发重发


async def register_config_consumer(bus: EventBus):
    """注册 JetStream 消费者"""
    await bus.subscribe_jetstream(
        subject="aeroforge.config.>",
        durable_name="workflow-engine-config-consumer",
        callback=handle_block_updated_event,
        stream="AEROFORGE_CONFIG",
    )
```

### 1.3.3 Sprint-C: Neo4j Configuration Identity Graph

#### Neo4j 连接管理

现有 `aircraft-core-service/src/infrastructure/database.py` 已包含 `get_neo4j_driver()` 函数。需扩展为支持连接健康检查和降级模式：

```python
# aircraft-core-service/src/infrastructure/database.py — 扩展设计

import asyncpg
import os
import logging

try:
    from neo4j import AsyncGraphDatabase
    _HAS_NEO4J = True
except ImportError:
    _HAS_NEO4J = False

logger = logging.getLogger(__name__)


class DatabaseConfig:
    POSTGRES_DSN = os.getenv('DATABASE_URL', os.getenv('POSTGRES_DSN', 'postgresql://postgres:aeroforge@localhost:5432/aeroforge'))
    NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'aeroforge123')


_pg_pool: asyncpg.Pool | None = None
_neo4j_driver = None


async def get_pg_pool() -> asyncpg.Pool:
    global _pg_pool
    if _pg_pool is None:
        _pg_pool = await asyncpg.create_pool(
            DatabaseConfig.POSTGRES_DSN,
            min_size=5,
            max_size=20,
            server_settings={'search_path': 'aircraft_core,public'},
        )
    return _pg_pool


async def get_neo4j_driver():
    """获取 Neo4j AsyncDriver — 降级模式: 不可用时返回 None"""
    global _neo4j_driver
    if not _HAS_NEO4J:
        logger.warning('Neo4j library not available, graph operations disabled')
        return None
    if _neo4j_driver is None:
        try:
            _neo4j_driver = AsyncGraphDatabase.driver(
                DatabaseConfig.NEO4J_URI,
                auth=(DatabaseConfig.NEO4J_USER, DatabaseConfig.NEO4J_PASSWORD)
            )
            # 验证连接
            await _neo4j_driver.verify_connectivity()
            logger.info(f'Neo4j connected to {DatabaseConfig.NEO4J_URI}')
        except Exception as e:
            logger.warning(f'Neo4j connection failed: {e}, graph operations disabled')
            _neo4j_driver = None
    return _neo4j_driver


async def close_connections():
    global _pg_pool, _neo4j_driver
    if _pg_pool:
        await _pg_pool.close()
        _pg_pool = None
    if _neo4j_driver:
        await _neo4j_driver.close()
        _neo4j_driver = None
```

#### Graph Client 封装

```python
# aircraft-core-service/src/infrastructure/graph_client.py — 新增文件

import logging
import uuid
from typing import Any

from src.infrastructure.database import get_neo4j_driver

logger = logging.getLogger(__name__)


class Neo4jGraphClient:
    """Neo4j 图谱操作客户端 — 降级模式: driver 为 None 时所有操作为 no-op"""

    async def create_configuration_identity(
        self,
        node_id: str,
        block_name: str,
        aircraft_type: str,
        configuration_type: str = "Design",
        version: int = 1,
    ) -> bool:
        """创建 Configuration Identity 节点 + 层级关系"""
        driver = await get_neo4j_driver()
        if driver is None:
            logger.warning('Neo4j unavailable, skipping create_configuration_identity')
            return False

        async with driver.session() as session:
            # 创建 Block 节点 (MERGE 幂等)
            await session.run("""
                MERGE (b:Block {node_id: $node_id})
                SET b.block_name = $block_name,
                    b.aircraft_type = $aircraft_type,
                    b.configuration_type = $configuration_type,
                    b.version = $version
            """, node_id=node_id, block_name=block_name,
                aircraft_type=aircraft_type,
                configuration_type=configuration_type,
                version=version)

            # 创建 Aircraft 节点并建立 HAS_BLOCK 关系
            await session.run("""
                MERGE (a:Aircraft {aircraft_type: $aircraft_type})
                MERGE (a)-[:HAS_BLOCK]->(b:Block {node_id: $node_id})
            """, aircraft_type=aircraft_type, node_id=node_id)

            # 创建 ConfigurationIdentity 节点
            await session.run("""
                MERGE (ci:ConfigurationIdentity {node_id: $node_id})
                SET ci.block_name = $block_name,
                    ci.aircraft_type = $aircraft_type,
                    ci.configuration_type = $configuration_type,
                    ci.version = $version
            """, node_id=node_id, block_name=block_name,
                aircraft_type=aircraft_type,
                configuration_type=configuration_type,
                version=version)

        return True

    async def create_sn_node(
        self,
        sn_node_id: str,
        tail_number: str,
        block_node_id: str,
    ) -> bool:
        """创建 SN 节点并建立 HAS_SN 关系"""
        driver = await get_neo4j_driver()
        if driver is None:
            return False

        async with driver.session() as session:
            await session.run("""
                MERGE (s:SN {node_id: $sn_node_id})
                SET s.tail_number = $tail_number
                WITH s
                MATCH (b:Block {node_id: $block_node_id})
                MERGE (b)-[:HAS_SN]->(s)
            """, sn_node_id=sn_node_id, tail_number=tail_number,
                block_node_id=block_node_id)

        return True

    async def query_identity_graph(
        self,
        aircraft_type: str,
    ) -> list[dict[str, Any]]:
        """查询指定 aircraft_type 的完整层级结构"""
        driver = await get_neo4j_driver()
        if driver is None:
            return []

        async with driver.session() as session:
            result = await session.run("""
                MATCH (a:Aircraft {aircraft_type: $aircraft_type})
                OPTIONAL MATCH (a)-[:HAS_BLOCK]->(b:Block)
                OPTIONAL MATCH (b)-[:HAS_SN]->(s:SN)
                RETURN a.aircraft_type AS aircraft_type,
                       collect(DISTINCT {
                           node_id: b.node_id,
                           block_name: b.block_name,
                           configuration_type: b.configuration_type,
                           version: b.version,
                           sns: collect(DISTINCT {
                               node_id: s.node_id,
                               tail_number: s.tail_number
                           })
                       }) AS blocks
            """, aircraft_type=aircraft_type)

            records = await result.data()
            return records if records else []


graph_client = Neo4jGraphClient()
```

#### 图谱查询 API

```python
# aircraft-core-service/src/api/v6/config_identity_controller.py — 新增文件

from fastapi import APIRouter, HTTPException

from src.infrastructure.graph_client import graph_client

router = APIRouter(prefix="/api/v6/aircraft-core", tags=["Configuration Identity Graph"])


@router.get("/config-identity-graphs/{aircraft_type}")
async def get_config_identity_graph(aircraft_type: str):
    """查询指定 aircraft_type 的 Configuration Identity Graph 层级结构"""
    try:
        result = await graph_client.query_identity_graph(aircraft_type)
        if not result:
            return {"aircraft_type": aircraft_type, "blocks": []}
        return result
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Graph query failed: {e}")
```

#### 集成点: Block 创建时写入 Neo4j

在 `configuration_controller.py` 的 `create_block_config` 中，创建 Block 后同步写入 Neo4j：

```python
# configuration_controller.py — create_block_config Neo4j 集成

@router.post("/block-configurations")
async def create_block_config(body: dict[str, Any]):
    await _ensure_repo()
    aircraft_type = body.get("aircraft_type", "")
    block_name = body.get("block_name", "")
    block = await _config_service.createBlockConfig(aircraft_type=aircraft_type, block_name=block_name)
    
    # 新增: 写入 Neo4j Configuration Identity Graph
    from src.infrastructure.graph_client import graph_client
    await graph_client.create_configuration_identity(
        node_id=block.block_id,
        block_name=block_name,
        aircraft_type=aircraft_type,
    )
    
    return block.to_dict()
```

### 1.3.4 Sprint-D: MinIO Object Storage

#### Object Storage Client 封装

```python
# aircraft-core-service/src/infrastructure/object_storage.py — 新增文件

import io
import os
import uuid
import logging
from datetime import timedelta
from typing import Any

try:
    from minio import Minio
    from minio.error import S3Error
    _HAS_MINIO = True
except ImportError:
    _HAS_MINIO = False

logger = logging.getLogger(__name__)


# 允许的文件 MIME 类型
ALLOWED_CONTENT_TYPES: set[str] = {
    "application/pdf",
    "image/dwg",
    "image/vnd.dwg",
    "application/dwg",
    "application/octet-stream",
    "model/step",
    "model/iges",
    "image/png",
    "image/jpeg",
    "image/tiff",
}

# 预定义 Bucket 列表
PREDEFINED_BUCKETS: list[str] = [
    "aeroforge-cert-evidence",
    "aeroforge-dataset-artifacts",
    "aeroforge-mdo-results",
    "aeroforge-phm-models",
    "aeroforge-uq-reports",
    "aeroforge-gdt-annotations",
    "aeroforge-export-packages",
    "aeroforge-backups",
]

MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB


class MinioObjectStorage:
    """MinIO 对象存储客户端 — 降级模式: 不可用时返回 None/503"""

    def __init__(self):
        self._client: Minio | None = None

    async def _ensure_client(self) -> Minio | None:
        if not _HAS_MINIO:
            logger.warning('MinIO library not available, object storage disabled')
            return None
        if self._client is None:
            try:
                self._client = Minio(
                    os.getenv("MINIO_ENDPOINT", "minio:9000"),
                    access_key=os.getenv("MINIO_ACCESS_KEY", "aeroforge"),
                    secret_key=os.getenv("MINIO_SECRET_KEY", "aeroforge123"),
                    secure=False,  # EV-4.5 不启用 TLS
                )
                logger.info(f'MinIO connected to {os.getenv("MINIO_ENDPOINT", "minio:9000")}')
            except Exception as e:
                logger.warning(f'MinIO connection failed: {e}')
                self._client = None
        return self._client

    async def upload_file(
        self,
        bucket: str,
        file_name: str,
        file_data: bytes,
        content_type: str,
    ) -> dict[str, Any] | None:
        """上传文件到 MinIO"""
        client = await self._ensure_client()
        if client is None:
            return None

        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError(f"Unsupported content type: {content_type}")

        if len(file_data) > MAX_FILE_SIZE:
            raise ValueError(f"File size exceeds limit: {len(file_data)} > {MAX_FILE_SIZE}")

        file_id = str(uuid.uuid4())
        client.put_object(
            bucket_name=bucket,
            object_name=file_id,
            data=io.BytesIO(file_data),
            length=len(file_data),
            content_type=content_type,
        )

        return {
            "file_id": file_id,
            "file_name": file_name,
            "bucket": bucket,
            "content_type": content_type,
            "file_size": len(file_data),
            "upload_timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        }

    async def get_presigned_url(
        self,
        bucket: str,
        file_id: str,
        expires_hours: int = 1,
    ) -> str | None:
        """生成预签名下载 URL"""
        client = await self._ensure_client()
        if client is None:
            return None

        url = client.presigned_get_object(
            bucket_name=bucket,
            object_name=file_id,
            expires=timedelta(hours=expires_hours),
        )
        return url


object_storage = MinioObjectStorage()
```

#### Evidence API

```python
# aircraft-core-service/src/api/v6/evidence_controller.py — 新增文件

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from src.infrastructure.object_storage import object_storage, PREDEFINED_BUCKETS

router = APIRouter(prefix="/api/v6/aircraft-core", tags=["Evidence Storage"])


@router.post("/evidence/upload")
async def upload_evidence(
    file: UploadFile = File(...),
    bucket: str = Form("aeroforge-cert-evidence"),
):
    """上传认证证据文件到 MinIO"""
    if bucket not in PREDEFINED_BUCKETS:
        raise HTTPException(status_code=400, detail=f"Invalid bucket: {bucket}")

    content_type = file.content_type or "application/octet-stream"
    file_data = await file.read()

    try:
        result = await object_storage.upload_file(
            bucket=bucket,
            file_name=file.filename or "unnamed",
            file_data=file_data,
            content_type=content_type,
        )
        if result is None:
            raise HTTPException(status_code=503, detail="Object storage unavailable")
        return result
    except ValueError as e:
        error_msg = str(e)
        if "Unsupported content type" in error_msg:
            raise HTTPException(status_code=415, detail=error_msg)
        if "File size exceeds" in error_msg:
            raise HTTPException(status_code=413, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)


@router.get("/evidence/{file_id}/url")
async def get_evidence_url(file_id: str, bucket: str = "aeroforge-cert-evidence"):
    """获取证据文件的预签名下载 URL"""
    url = await object_storage.get_presigned_url(bucket=bucket, file_id=file_id)
    if url is None:
        raise HTTPException(status_code=503, detail="Object storage unavailable")
    return {"file_id": file_id, "url": url}
```

### 1.3.5 Sprint-E: Physics Twin Activation

#### Physics Twin NATS 消费者

```python
# physics-twin-service/src/infrastructure/nats_consumer.py — 新增文件

import json
import logging
from datetime import datetime

from src.infrastructure.event_bus import event_bus

logger = logging.getLogger(__name__)


async def handle_configuration_updated_event(msg):
    """处理 ConfigurationUpdatedEvent — 仅记录日志"""
    try:
        data = json.loads(msg.data.decode())
        event_id = data.get("event_id", "")
        configuration_id = data.get("configuration_id", "")
        change_type = data.get("change_type", "")
        received_at = datetime.utcnow().isoformat()

        logger.info(
            f"ConfigurationUpdatedEvent consumed: event_id={event_id}, "
            f"configuration_id={configuration_id}, "
            f"change_type={change_type}, received_at={received_at}"
        )

        await msg.ack()
    except Exception as e:
        logger.error(f"Error processing ConfigurationUpdatedEvent: {e}")
        await msg.nak()


async def register_config_consumer(bus: EventBus):
    """注册 Physics Twin 的 JetStream 消费者"""
    await bus.subscribe_jetstream(
        subject="aeroforge.config.configuration.updated",
        durable_name="physics-twin-config-consumer",
        callback=handle_configuration_updated_event,
        stream="AEROFORGE_CONFIG",
    )
```

#### Physics Twin main.py 集成

```python
# physics-twin-service/src/main.py — 消费者注册设计

from src.infrastructure.nats_consumer import register_config_consumer

@asynccontextmanager
async def lifespan(app: FastAPI):
    await event_bus.connect()
    await register_config_consumer(event_bus)  # 新增
    yield
    await event_bus.close()
    await close_connections()
```

---

# 2. 接口设计

## 2.1 总体设计

### API 前缀规范

| 服务 | 前缀 | 说明 |
|------|------|------|
| Aircraft Core | `/api/v6/aircraft-core` | 现有 + 新增 |
| Workflow Engine | `/api/v6/workflow-engine` | 现有 |
| Physics Twin | `/api/v6/physics-twin` | 现有 |

### 新增 API 端点

| Sprint | 方法 | 路径 | 说明 |
|--------|------|------|------|
| Sprint-C | GET | `/api/v6/aircraft-core/config-identity-graphs/{aircraft_type}` | 查询 Configuration Identity Graph |
| Sprint-D | POST | `/api/v6/aircraft-core/evidence/upload` | 上传证据文件 |
| Sprint-D | GET | `/api/v6/aircraft-core/evidence/{file_id}/url` | 获取预签名 URL |

### NATS Subject 命名规范

```
aeroforge.{domain}.{entity}.{action}

示例:
  aeroforge.config.block.updated           — Block 配置变更事件
  aeroforge.config.configuration.updated   — Configuration 变更事件
```

**Stream 命名**: `AEROFORGE_CONFIG`  
**Consumer 命名**: `{service-name}-config-consumer`

## 2.2 接口清单

### 2.2.1 GET /api/v6/aircraft-core/config-identity-graphs/{aircraft_type}

**请求**:
- Path Parameter: `aircraft_type` (string, required) — 如 "B737"

**响应 200**:
```json
{
  "aircraft_type": "B737",
  "blocks": [
    {
      "node_id": "B737-WING-001",
      "block_name": "Wing",
      "configuration_type": "Design",
      "version": 1,
      "sns": [
        {
          "node_id": "SN-001",
          "tail_number": "B737-001"
        }
      ]
    },
    {
      "node_id": "B737-FUSE-001",
      "block_name": "Fuselage",
      "configuration_type": "Design",
      "version": 1,
      "sns": []
    }
  ]
}
```

**响应 503**: Neo4j 不可用
```json
{
  "detail": "Graph query failed: Connection refused"
}
```

### 2.2.2 POST /api/v6/aircraft-core/evidence/upload

**请求**: `multipart/form-data`
- `file` (binary, required) — 上传文件
- `bucket` (string, optional, default: "aeroforge-cert-evidence") — 目标 Bucket

**响应 200**:
```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_name": "NDT_Report.pdf",
  "bucket": "aeroforge-cert-evidence",
  "content_type": "application/pdf",
  "file_size": 1048576,
  "upload_timestamp": "2026-06-22T14:30:00Z"
}
```

**响应 413**: 文件过大
```json
{
  "detail": "File size exceeds limit: 53477376 > 52428800"
}
```

**响应 415**: 不支持的文件类型
```json
{
  "detail": "Unsupported content type: application/x-executable"
}
```

**响应 503**: MinIO 不可用
```json
{
  "detail": "Object storage unavailable"
}
```

### 2.2.3 GET /api/v6/aircraft-core/evidence/{file_id}/url

**请求**:
- Path Parameter: `file_id` (string, required) — 文件 UUID
- Query Parameter: `bucket` (string, optional, default: "aeroforge-cert-evidence")

**响应 200**:
```json
{
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "http://minio:9000/aeroforge-cert-evidence/550e8400-...?X-Amz-Algorithm=..."
}
```

**响应 404**: 文件不存在
```json
{
  "detail": "File not found: 550e8400-e29b-41d4-a716-446655440000"
}
```

### 2.2.4 NATS Event Schemas

#### BlockUpdatedEvent

```json
{
  "event_id": "660e8400-e29b-41d4-a716-446655440000",
  "event_type": "BlockUpdated",
  "block_id": "B737-WING-001",
  "aircraft_type": "B737",
  "version": 2,
  "changed_fields": ["block_name"],
  "timestamp": "2026-06-22T14:30:00Z"
}
```

**Subject**: `aeroforge.config.block.updated`  
**Stream**: `AEROFORGE_CONFIG`

#### ConfigurationUpdatedEvent

```json
{
  "event_id": "770e8400-e29b-41d4-a716-446655440000",
  "event_type": "ConfigurationUpdated",
  "configuration_id": "B737-WING-001",
  "block_id": "B737-WING-001",
  "aircraft_type": "B737",
  "change_type": "UPDATED",
  "timestamp": "2026-06-22T14:30:00Z"
}
```

**Subject**: `aeroforge.config.configuration.updated`  
**Stream**: `AEROFORGE_CONFIG`  
**change_type 枚举**: `"CREATED"` | `"UPDATED"` | `"DELETED"`

---

# 4. 数据模型

## 4.1 设计目标

1. **NATS JetStream Stream**: 持久化事件流，支持 durable consumer 和消息重发
2. **Neo4j Schema**: Configuration Identity Graph 的节点约束和关系类型
3. **MinIO Bucket 策略**: 预定义 Bucket 列表，按业务域分类
4. **事件 Pydantic Model**: 类型安全的事件 Schema 定义

## 4.2 模型实现

### 4.2.1 NATS JetStream Stream 配置

| 属性 | 值 | 说明 |
|------|-----|------|
| Stream Name | `AEROFORGE_CONFIG` | 配置域事件流 |
| Subjects | `aeroforge.config.>` | 通配符匹配所有配置事件 |
| Retention | `limits` | 基于限制的保留策略 |
| Max Messages | 100,000 | 最大消息数 |
| Max Age | 168h (7天) | 消息最大保留时间 |
| Storage | `file` | 文件存储（持久化） |

### NATS JetStream Consumer 配置

| Consumer Name | Filter Subject | ACK Policy | Max Deliver | ACK Wait | Durable |
|---------------|---------------|------------|-------------|----------|---------|
| `workflow-engine-config-consumer` | `aeroforge.config.>` | explicit | 3 | 30s | Yes |
| `physics-twin-config-consumer` | `aeroforge.config.configuration.updated` | explicit | 3 | 30s | Yes |

### 4.2.2 Neo4j Schema

#### 节点类型与约束

```cypher
-- Aircraft 节点
CREATE CONSTRAINT aircraft_type_unique IF NOT EXISTS
FOR (a:Aircraft) REQUIRE a.aircraft_type IS UNIQUE;

-- Block 节点
CREATE CONSTRAINT block_node_id_unique IF NOT EXISTS
FOR (b:Block) REQUIRE b.node_id IS UNIQUE;

-- SN 节点
CREATE CONSTRAINT sn_node_id_unique IF NOT EXISTS
FOR (s:SN) REQUIRE s.node_id IS UNIQUE;

-- ConfigurationIdentity 节点
CREATE CONSTRAINT node_id_unique IF NOT EXISTS
FOR (n:ConfigurationIdentity) REQUIRE n.node_id IS UNIQUE;

-- EV-5 预留约束 (仅创建约束，不写入数据)
CREATE CONSTRAINT requirement_id_unique IF NOT EXISTS
FOR (r:Requirement) REQUIRE r.node_id IS UNIQUE;

CREATE CONSTRAINT design_element_id_unique IF NOT EXISTS
FOR (d:DesignElement) REQUIRE d.node_id IS UNIQUE;
```

#### 关系类型

| 关系类型 | 源节点 | 目标节点 | 说明 |
|----------|--------|----------|------|
| `HAS_BLOCK` | Aircraft | Block | 飞行器包含 Block |
| `HAS_SN` | Block | SN | Block 包含 Serial Number |

#### 节点属性

**Aircraft**:
| 属性 | 类型 | 必填 | 说明 |
|------|------|------|------|
| aircraft_type | string | Yes | 飞行器型号，如 "B737" |

**Block**:
| 属性 | 类型 | 必填 | 说明 |
|------|------|------|------|
| node_id | string (UUID) | Yes | 全局唯一标识 |
| block_name | string | Yes | Block 名称，如 "Wing" |
| aircraft_type | string | Yes | 所属飞行器型号 |
| configuration_type | string | Yes | 枚举: "Design"/"Manufacturing"/"Operational" |
| version | integer | No | 版本号，默认 1 |

**SN**:
| 属性 | 类型 | 必填 | 说明 |
|------|------|------|------|
| node_id | string (UUID) | Yes | 全局唯一标识 |
| tail_number | string | Yes | 尾号 |

#### B737 种子数据

```
(Aircraft: B737)
  ├──[:HAS_BLOCK]──→ (Block: B737-WING-001, Wing)
  ├──[:HAS_BLOCK]──→ (Block: B737-FUSE-001, Fuselage)
  └──[:HAS_BLOCK]──→ (Block: B737-ENG-001, Engine)
```

### 4.2.3 MinIO Bucket 策略

| Bucket 名称 | 用途 | 预估文件类型 |
|-------------|------|-------------|
| `aeroforge-cert-evidence` | 认证证据文件 | PDF, DWG, NDT Report |
| `aeroforge-dataset-artifacts` | 数据集产物 | CSV, HDF5, Parquet |
| `aeroforge-mdo-results` | MDO 优化结果 | JSON, CSV |
| `aeroforge-phm-models` | PHM 模型文件 | PKL, ONNX, PT |
| `aeroforge-uq-reports` | 不确定性量化报告 | PDF, JSON |
| `aeroforge-gdt-annotations` | GDT 标注文件 | JSON, XML |
| `aeroforge-export-packages` | 导出包 | ZIP, TAR |
| `aeroforge-backups` | 备份 | 任意 |

**文件大小限制**: 单次上传最大 50MB  
**预签名 URL 有效期**: 1 小时 (3600 秒)  
**允许的 Content-Type**: `application/pdf`, `image/dwg`, `image/vnd.dwg`, `application/dwg`, `application/octet-stream`, `model/step`, `model/iges`, `image/png`, `image/jpeg`, `image/tiff`

### 4.2.4 事件 Pydantic Model

```python
# aircraft-core-service/src/domain/events/block_updated_event.py — 新增文件

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class BlockUpdatedEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "BlockUpdated"
    block_id: str
    aircraft_type: str
    version: int
    changed_fields: list[str]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
```

```python
# aircraft-core-service/src/domain/events/configuration_updated_event.py — 新增文件

import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    DELETED = "DELETED"


class ConfigurationUpdatedEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "ConfigurationUpdated"
    configuration_id: str
    block_id: str
    aircraft_type: str
    change_type: ChangeType
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
```

---

# 5. 实现路径

## 5.1 Sprint-A: Infrastructure Bring-up

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `deploy/docker-compose.ev45.yml` | 7 服务 + 3 init 容器编排 |
| `scripts/init_nats_streams.py` | NATS JetStream Stream + Consumer 初始化 |
| `scripts/init_neo4j_schema.py` | Neo4j Schema 约束 + 种子数据 |
| `scripts/init_minio_buckets.sh` | MinIO Bucket 初始化 |

### 修改文件

| 文件路径 | 修改内容 |
|----------|----------|
| — | 无代码修改，纯基础设施 |

### 验证命令

```bash
docker-compose -f deploy/docker-compose.ev45.yml up -d
docker ps --format "table {{.Names}}\t{{.Status}}" | grep aeroforge
# 预期: 7 个容器全部 healthy + 3 个 init 容器 Exited(0)
```

## 5.2 Sprint-B: NATS JetStream Event Bus

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `services/aircraft-core-service/src/domain/events/__init__.py` | 事件模块初始化 |
| `services/aircraft-core-service/src/domain/events/block_updated_event.py` | BlockUpdatedEvent Pydantic Model |
| `services/aircraft-core-service/src/domain/events/configuration_updated_event.py` | ConfigurationUpdatedEvent Pydantic Model |
| `services/workflow-engine-service/src/infrastructure/nats_consumer.py` | Workflow Engine NATS 消费者 |

### 修改文件

| 文件路径 | 修改内容 |
|----------|----------|
| `services/aircraft-core-service/src/infrastructure/event_bus.py` | 新增 `publish_jetstream()` / `subscribe_jetstream()` 方法，升级 `connect()` 为 JetStream 模式 |
| `services/aircraft-core-service/src/api/v6/configuration_controller.py` | PATCH 端点新增 `BlockUpdatedEvent` 发布逻辑 |
| `services/workflow-engine-service/src/infrastructure/event_bus.py` | 新增 `subscribe_jetstream()` 方法 |
| `services/workflow-engine-service/src/main.py` | lifespan 中注册 NATS 消费者 |

### 验证命令

```bash
# 1. 触发配置变更
curl -X PATCH http://localhost:8001/api/v6/aircraft-core/block-configurations/{block_id} \
  -H "Content-Type: application/json" \
  -d '{"block_name": "Wing-Updated", "expected_version": 1}'

# 2. 检查 Workflow Engine 日志
docker logs aeroforge-workflow-engine 2>&1 | grep "BlockUpdated"
```

## 5.3 Sprint-C: Neo4j Configuration Identity Graph

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `services/aircraft-core-service/src/infrastructure/graph_client.py` | Neo4j 图谱操作客户端 |
| `services/aircraft-core-service/src/api/v6/config_identity_controller.py` | 图谱查询 API |

### 修改文件

| 文件路径 | 修改内容 |
|----------|----------|
| `services/aircraft-core-service/src/infrastructure/database.py` | `get_neo4j_driver()` 增加降级模式（连接失败返回 None + WARNING 日志） |
| `services/aircraft-core-service/src/api/v6/configuration_controller.py` | `create_block_config` 新增 Neo4j 写入逻辑 |
| `services/aircraft-core-service/src/main.py` | 注册 `config_identity_controller` router |

### 验证命令

```bash
# 1. 查询图谱
curl http://localhost:8001/api/v6/aircraft-core/config-identity-graphs/B737

# 2. 直接查询 Neo4j
docker exec aeroforge-neo4j cypher-shell -u neo4j -p aeroforge_neo4j \
  "MATCH (a:Aircraft {aircraft_type: 'B737'})-[:HAS_BLOCK]->(b:Block) RETURN a, b"
```

## 5.4 Sprint-D: MinIO Object Storage

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `services/aircraft-core-service/src/infrastructure/object_storage.py` | MinIO 对象存储客户端 |
| `services/aircraft-core-service/src/api/v6/evidence_controller.py` | 证据文件上传/URL API |

### 修改文件

| 文件路径 | 修改内容 |
|----------|----------|
| `services/aircraft-core-service/src/main.py` | 注册 `evidence_controller` router |
| `services/aircraft-core-service/requirements.txt` | 新增 `minio` 依赖 |

### 验证命令

```bash
# 1. 上传文件
curl -X POST http://localhost:8001/api/v6/aircraft-core/evidence/upload \
  -F "file=@test_ndt_report.pdf" \
  -F "bucket=aeroforge-cert-evidence"

# 2. 获取 URL 并下载
curl -o downloaded.pdf "{presigned_url}"
```

## 5.5 Sprint-E: Physics Twin Activation

### 新增文件

| 文件路径 | 说明 |
|----------|------|
| `services/physics-twin-service/src/infrastructure/nats_consumer.py` | Physics Twin NATS 消费者 |

### 修改文件

| 文件路径 | 修改内容 |
|----------|----------|
| `services/physics-twin-service/src/infrastructure/event_bus.py` | 新增 `subscribe_jetstream()` 方法 |
| `services/physics-twin-service/src/main.py` | lifespan 中注册 NATS 消费者 |

### 验证命令

```bash
# 1. 触发配置变更
curl -X PATCH http://localhost:8001/api/v6/aircraft-core/block-configurations/{block_id} \
  -H "Content-Type: application/json" \
  -d '{"block_name": "Wing-V2", "expected_version": 2}'

# 2. 检查 Physics Twin 日志
docker logs aeroforge-physics-twin 2>&1 | grep "ConfigurationUpdated"
```

---

# 6. 与现有代码的集成点

## 6.1 event_bus.py → NATS JetStream

**现有代码** (`aircraft-core-service/src/infrastructure/event_bus.py`):
- `EventBus` 类已实现 `connect()` / `publish()` / `subscribe()` / `close()`
- 使用 Core NATS 模式
- 有 `_HAS_NATS` 降级检查

**集成方式**:
- 在现有 `EventBus` 类中新增 `publish_jetstream()` 和 `subscribe_jetstream()` 方法
- `connect()` 方法中增加 `self._js = self._nc.jetstream()` 获取 JetStream context
- 保留原有 `publish()` / `subscribe()` 方法不变（向后兼容）
- Workflow Engine 和 Physics Twin 的 `event_bus.py` 同步升级

## 6.2 database.py → Neo4j 连接扩展

**现有代码** (`aircraft-core-service/src/infrastructure/database.py`):
- `get_neo4j_driver()` 已实现 AsyncGraphDatabase.driver 初始化
- 有 `_HAS_NEO4J` 降级检查
- `close_connections()` 已处理 Neo4j driver 关闭

**集成方式**:
- `get_neo4j_driver()` 增加连接验证 (`verify_connectivity()`)
- 连接失败时返回 `None` 并记录 WARNING 日志（降级模式）
- 新增 `graph_client.py` 封装图谱操作，调用 `get_neo4j_driver()` 获取 driver

## 6.3 DomainEventPublisher → NATS 事件发布

**现有代码** (`aircraft-core-service/src/domain/services/domain_event_publisher.py`):
- `DomainEvent` Pydantic Model 已定义 `event_id`, `event_type`, `aggregate_id`, `changed_fields`, `timestamp`
- `DomainEventPublisher.publish_object_change_event()` 仅缓存事件到 `_event_cache`

**集成方式**:
- 不修改 `DomainEventPublisher`（保持现有逻辑）
- 在 `configuration_controller.py` 的 PATCH 端点中，直接调用 `event_bus.publish_jetstream()` 发布新格式的 `BlockUpdatedEvent`
- `BlockUpdatedEvent` 和 `ConfigurationUpdatedEvent` 作为新的 Pydantic Model，独立于 `DomainEvent`

## 6.4 configuration_controller.py → 事件发布 + Neo4j 写入

**现有代码** (`aircraft-core-service/src/api/v6/configuration_controller.py`):
- `update_block_config()` (PATCH) — 已实现乐观锁、缓存失效
- `create_block_config()` (POST) — 已实现 Block 创建

**集成方式**:
- `update_block_config()`: 在现有逻辑末尾（缓存失效后）新增 NATS 事件发布
- `create_block_config()`: 在现有逻辑末尾新增 Neo4j 节点创建
- 新增 `config_identity_controller.py` 和 `evidence_controller.py` 作为独立 router

## 6.5 main.py → Router 注册

**现有代码** (`aircraft-core-service/src/main.py`):
- 已注册 `v6_config_router`, `v6_cert_router`, `v6_supplier_router` 等
- lifespan 中已调用 `event_bus.connect()` 和 `close_connections()`

**集成方式**:
- 新增 `from src.api.v6.config_identity_controller import router as v6_identity_router`
- 新增 `from src.api.v6.evidence_controller import router as v6_evidence_router`
- 新增 `app.include_router(v6_identity_router)` 和 `app.include_router(v6_evidence_router)`

---

# 7. 降级策略

所有新增基础设施连接均采用降级模式，确保单个组件不可用时不影响核心功能：

| 组件 | 不可用时的行为 | 影响范围 |
|------|---------------|----------|
| NATS JetStream | `publish_jetstream` 为 no-op，记录 WARNING | 事件不发布，但 PATCH/POST 请求正常返回 |
| Neo4j | `graph_client` 操作为 no-op，返回 False | 图谱不写入，但 PostgreSQL 正常 |
| MinIO | `object_storage` 操作返回 None | 上传端点返回 503，其他端点正常 |

**健康检查端点** 不受降级影响 — 三个 FastAPI 服务的 `/health` 端点始终返回 `{"status": "healthy"}`。

---

# 8. 风险与缓解

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| NATS Python 库 API 与 JetStream 不兼容 | 中 | 高 | 使用 `nats-py` >= 2.7.0，已验证 JetStream API |
| Neo4j AsyncDriver 连接池泄漏 | 低 | 中 | 使用 singleton driver，lifespan 关闭 |
| MinIO 预签名 URL 在 Docker 网络中不可达 | 中 | 中 | 预签名 URL 使用内部地址，外部访问需通过 nginx 代理 |
| Docker Compose v1 不支持 `condition: service_completed_successfully` | 低 | 高 | 已验证 Docker Compose 1.29+ 支持此条件 |
| init 容器重复执行导致数据冲突 | 低 | 中 | 所有 init 脚本使用 MERGE/IF NOT EXISTS/--ignore-existing 确保幂等 |

---

# 9. 变更日志

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| 1.0 | 2026-06-22 | AeroForge-X Dev Team | 初始设计文档 |