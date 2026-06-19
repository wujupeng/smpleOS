# AeroForge-X 运维手册

## 服务架构

```
用户 → Kong API Gateway → [设计中心|PLM|BOM|MES|QMS|追溯]
                                ↓
                    [PostgreSQL|Neo4j|MinIO|Redis|NATS]
```

## 常用运维命令

### 查看服务状态

```bash
docker compose -f deploy/docker-compose.yml ps
docker compose -f deploy/docker-compose.yml logs -f [service_name]
```

### 重启服务

```bash
docker compose -f deploy/docker-compose.yml restart [service_name]
```

### 数据库迁移

```bash
# 升级到最新
poetry run alembic -c alembic.ini upgrade head

# 回退一个版本
poetry run alembic -c alembic.ini downgrade -1

# 查看当前版本
poetry run alembic -c alembic.ini current
```

### 日志查看

```bash
# 后端服务日志
docker compose logs -f aeroforge-postgres
docker compose logs -f aeroforge-neo4j

# 应用日志（结构化JSON）
# 日志输出到 stdout，可通过 ELK/Datadog 收集
```

## 常见问题排查

### 1. PostgreSQL连接失败

```bash
# 检查服务状态
docker compose ps aeroforge-postgres

# 检查连接
docker exec aeroforge-postgres pg_isready -U aeroforge

# 查看日志
docker compose logs aeroforge-postgres
```

### 2. Neo4j连接失败

```bash
# 检查服务状态
docker compose ps aeroforge-neo4j

# 测试连接
docker exec aeroforge-neo4j cypher-shell -u neo4j -p aeroforge_dev "RETURN 1"
```

### 3. MinIO无法访问

```bash
# 检查健康
curl http://localhost:9000/minio/health/live

# 查看bucket
docker exec aeroforge-minio mc ls local/
```

### 4. Keycloak认证失败

```bash
# 检查Keycloak状态
curl http://localhost:8080/health

# 重启Keycloak
docker compose restart aeroforge-keycloak
```

## 监控指标

- PostgreSQL: 连接数、查询延迟、锁等待
- Neo4j: 查询延迟、页面缓存命中率
- Redis: 内存使用、连接数
- NATS: 消息吞吐量、消费者延迟
- 应用: API响应时间P95、错误率