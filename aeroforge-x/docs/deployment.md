# AeroForge-X 部署指南

## 环境要求

- Python 3.12+
- Node.js 18+
- Docker & Docker Compose
- Poetry (Python包管理)

## 1. 快速启动

### 1.1 克隆代码

```bash
git clone https://github.com/aeroforge-x/aeroforge-x.git
cd aeroforge-x
```

### 1.2 启动基础设施

```bash
docker compose -f deploy/docker-compose.yml up -d
```

等待所有服务健康后（约30秒）：

| 服务 | 端口 | 用途 |
|------|------|------|
| PostgreSQL | 5432 | 业务数据 |
| Neo4j | 7687/7474 | BOM关系图 |
| MinIO | 9000/9001 | 模型文件存储 |
| Redis | 6379 | 缓存/任务队列 |
| NATS | 4222/8222 | 事件总线 |
| Keycloak | 8080 | 认证鉴权 |

### 1.3 安装依赖

```bash
poetry install
cd frontend && npm install && cd ..
```

### 1.4 数据库迁移

```bash
bash scripts/db-migrate.sh
```

### 1.5 填充测试数据

```bash
poetry run python scripts/seed-data.py
poetry run python scripts/init-minio.py
```

### 1.6 启动后端服务

```bash
# 设计中心 (端口8001)
poetry run uvicorn services.design_center.src.main:app --host 0.0.0.0 --port 8001 &

# PLM中心 (端口8002)
poetry run uvicorn services.plm_center.src.main:app --host 0.0.0.0 --port 8002 &

# BOM中心 (端口8003)
poetry run uvicorn services.bom_center.src.main:app --host 0.0.0.0 --port 8003 &

# MES中心 (端口8004)
poetry run uvicorn services.mes_center.src.main:app --host 0.0.0.0 --port 8004 &

# QMS服务 (端口8005)
poetry run uvicorn services.qms_service.src.main:app --host 0.0.0.0 --port 8005 &

# 追溯服务 (端口8006)
poetry run uvicorn services.trace_service.src.main:app --host 0.0.0.0 --port 8006 &
```

### 1.7 启动前端

```bash
cd frontend && npm run dev
```

访问 http://localhost:3000

## 2. 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| PG_DATABASE_URL | postgresql+asyncpg://aeroforge:aeroforge_dev@localhost:5432/aeroforge_x | PostgreSQL连接 |
| NEO4J_URI | bolt://localhost:7687 | Neo4j连接 |
| NEO4J_USER | neo4j | Neo4j用户 |
| NEO4J_PASSWORD | aeroforge_dev | Neo4j密码 |
| MINIO_ENDPOINT | localhost:9000 | MinIO端点 |
| MINIO_ACCESS_KEY | aeroforge_minio | MinIO Access Key |
| MINIO_SECRET_KEY | aeroforge_minio_secret | MinIO Secret Key |
| KEYCLOAK_URL | http://localhost:8080 | Keycloak地址 |
| KEYCLOAK_REALM | aeroforge-x | Keycloak Realm |

## 3. Keycloak配置

1. 访问 http://localhost:8080 (admin/admin)
2. 选择 `aeroforge-x` Realm
3. 创建8个角色：chief_designer, structural_engineer, aerodynamic_engineer, process_engineer, quality_engineer, production_manager, airworthiness_engineer, maintenance_engineer
4. 创建客户端 `aeroforge-api`

## 4. 健康检查

```bash
curl http://localhost:8001/health  # 设计中心
curl http://localhost:8002/health  # PLM中心
curl http://localhost:8003/health  # BOM中心
curl http://localhost:8004/health  # MES中心
curl http://localhost:8005/health  # QMS服务
curl http://localhost:8006/health  # 追溯服务
```

## 5. 数据库备份

```bash
# PostgreSQL
docker exec aeroforge-postgres pg_dump -U aeroforge aeroforge_x > backup_$(date +%Y%m%d).sql

# Neo4j
docker exec aeroforge-neo4j neo4j-admin database dump neo4j --to-path=/backup/

# MinIO
mc mirror local/aeroforge-models /backup/minio-models/
```