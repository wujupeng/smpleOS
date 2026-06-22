# AeroForge-X EV-4.5 Architecture Activation — 编码任务清单

**Sprint**: EV-4.5 Architecture Activation  
**目标 TRL**: 5.5 → 6.0  
**日期**: 2026-06-22  
**关联需求**: `docs/specs/ev4.5-architecture-activation-spec.md`  
**关联设计**: `docs/specs/ev4.5-architecture-activation-design.md`  
**前置基线**: EV-4 (React → FastAPI → PostgreSQL 单服务闭环已验证)  

---

## Sprint-A: Infrastructure Bring-up

> 目标：7 容器全部 healthy 启动，3 个 init 容器幂等执行成功

### Task-EV45-01: 编写 docker-compose.ev45.yml 编排文件
- **Sprint**: A | **优先级**: P0 | **预估**: 2h
- **依赖**: 无
- **实现步骤**:
  - 基于 `deploy/docker-compose.v61.yml` 模板创建 `deploy/docker-compose.ev45.yml`
  - 移除 `timescaledb` 服务及 `ts_data` volume
  - 移除 physics-twin 的 `TIMESCALEDB_URL` 环境变量及对 timescaledb 的依赖
  - 新增 `nats` 服务 (image: nats:alpine, command: --jetstream --store_dir /data, ports: 4222/8222, healthcheck: curl http://localhost:8222/healthz)
  - 新增 `neo4j` 服务 (image: neo4j:5, ports: 7474/7687, NEO4J_AUTH, NEO4J_PLUGINS: apoc, healthcheck: curl http://localhost:7474)
  - 新增 `minio` 服务 (image: minio/minio:latest, command: server /data --console-address ":9001", ports: 9000/9001, healthcheck: curl http://localhost:9000/minio/health/live)
  - 新增 `init-nats` init 容器 (image: python:3.12-slim, depends_on nats:service_healthy, volume mount init_nats_streams.py, restart: "no")
  - 新增 `init-neo4j` init 容器 (image: neo4j:5, depends_on neo4j:service_healthy, volume mount init_neo4j_schema.py, restart: "no")
  - 新增 `init-minio` init 容器 (image: minio/mc:latest, depends_on minio:service_healthy, volume mount init_minio_buckets.sh, restart: "no")
  - 修改 `aircraft-core` depends_on: 增加 neo4j:service_healthy, nats:service_healthy, init-nats/init-neo4j:service_completed_successfully
  - 修改 `aircraft-core` environment: 增加 NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NATS_SERVERS, MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
  - 修改 `workflow-engine` depends_on: 增加 nats:service_healthy, init-nats:service_completed_successfully
  - 修改 `workflow-engine` environment: 增加 NATS_SERVERS
  - 修改 `physics-twin` depends_on: 增加 nats:service_healthy, minio:service_healthy, init-nats:service_completed_successfully
  - 修改 `physics-twin` environment: 增加 NATS_SERVERS, MINIO_ENDPOINT, MINIO_ACCESS_KEY, MINIO_SECRET_KEY
  - 新增 volumes: neo4j_data, nats_data, minio_data
  - 新增 network: aeroforge-net (bridge)
  - 所有凭证使用 `${ENV_VAR:-default}` 格式，不硬编码
- **文件**: `deploy/docker-compose.ev45.yml` (新增)
- **验收标准**: `docker-compose -f deploy/docker-compose.ev45.yml config` 无语法错误；文件中不包含 timescaledb 服务定义

### Task-EV45-02: 编写 NATS JetStream 初始化脚本
- **Sprint**: A | **优先级**: P0 | **预估**: 1.5h
- **依赖**: 无
- **实现步骤**:
  - 创建 `scripts/init_nats_streams.py`
  - 使用 `nats-py` 库连接 NATS_SERVERS 环境变量指定的服务器
  - 创建 `AEROFORGE_CONFIG` stream: subjects=["aeroforge.config.>"], retention="limits", max_msgs=100000, max_age=168h
  - 创建 durable consumer `workflow-engine-config-consumer`: filter_subject="aeroforge.config.>", ack_policy="explicit", max_deliver=3, ack_wait=30s
  - 创建 durable consumer `physics-twin-config-consumer`: filter_subject="aeroforge.config.configuration.updated", ack_policy="explicit", max_deliver=3, ack_wait=30s
  - 所有操作使用 try/except 捕获 StreamAlreadyExistsError / ConsumerAlreadyExistsError，确保幂等
  - 脚本末尾 `await nc.close()`
  - 使用 `asyncio.run(main())` 入口
- **文件**: `scripts/init_nats_streams.py` (新增)
- **验收标准**: 重复执行脚本无报错；NATS JetStream 中存在 AEROFORGE_CONFIG stream 和 2 个 durable consumer

### Task-EV45-03: 编写 Neo4j Schema 初始化脚本
- **Sprint**: A | **优先级**: P0 | **预估**: 1.5h
- **依赖**: 无
- **实现步骤**:
  - 创建 `scripts/init_neo4j_schema.py`
  - 使用 `neo4j` Python driver 连接 NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD
  - 创建 UNIQUE 约束 (IF NOT EXISTS): ConfigurationIdentity.node_id, Aircraft.aircraft_type, Block.node_id, SN.node_id
  - 创建 EV-5 预留约束 (IF NOT EXISTS): Requirement.node_id, DesignElement.node_id
  - 使用 MERGE 语句插入 B737 种子数据: Aircraft(B737) → Block(Wing), Block(Fuselage), Block(Engine)，node_id 分别为 B737-WING-001, B737-FUSE-001, B737-ENG-001
  - 建立 HAS_BLOCK 关系
  - 脚本末尾 `driver.close()`
- **文件**: `scripts/init_neo4j_schema.py` (新增)
- **验收标准**: 重复执行脚本无报错；Cypher `MATCH (a:Aircraft {aircraft_type: 'B737'})-[:HAS_BLOCK]->(b:Block) RETURN count(b)` 返回 ≥ 3

### Task-EV45-04: 编写 MinIO Bucket 初始化脚本
- **Sprint**: A | **优先级**: P0 | **预估**: 0.5h
- **依赖**: 无
- **实现步骤**:
  - 创建 `scripts/init_minio_buckets.sh`
  - 使用 `mc alias set` 配置 MinIO 连接
  - 循环创建 8 个 bucket: aeroforge-cert-evidence, aeroforge-dataset-artifacts, aeroforge-mdo-results, aeroforge-phm-models, aeroforge-uq-reports, aeroforge-gdt-annotations, aeroforge-export-packages, aeroforge-backups
  - 使用 `mc mb --ignore-existing` 确保幂等
- **文件**: `scripts/init_minio_buckets.sh` (新增)
- **验收标准**: 重复执行脚本无报错；`mc ls aeroforge/` 列出全部 8 个 bucket

### Task-EV45-05: 补充服务 Dockerfile 及依赖文件
- **Sprint**: A | **优先级**: P1 | **预估**: 1h
- **依赖**: Task-EV45-01
- **实现步骤**:
  - 确认 `services/aircraft-core-service/Dockerfile` 存在且可用，如不存在则创建 (基于 python:3.12-slim, 安装 requirements.txt, COPY src, CMD uvicorn)
  - 确认 `services/workflow-engine-service/Dockerfile` 存在且可用
  - 确认 `services/physics-twin-service/Dockerfile` 存在且可用
  - 在 `services/aircraft-core-service/requirements.txt` 中新增依赖: `nats-py>=2.7.0`, `neo4j>=5.0.0`, `minio>=7.0.0`
  - 在 `services/workflow-engine-service/requirements.txt` 中新增依赖: `nats-py>=2.7.0`
  - 在 `services/physics-twin-service/requirements.txt` 中新增依赖: `nats-py>=2.7.0`
  - 确认 3 个服务的 `/health` 端点已实现 (返回 `{"status": "healthy", "version": "6.0"}`)
- **文件**: 3 个 Dockerfile, 3 个 requirements.txt
- **验收标准**: `docker build` 三个服务镜像成功；`/health` 端点返回正确 JSON

### Task-EV45-06: 本地 Docker Compose 全栈启动验证
- **Sprint**: A | **优先级**: P0 | **预估**: 1.5h
- **依赖**: Task-EV45-01, Task-EV45-02, Task-EV45-03, Task-EV45-04, Task-EV45-05
- **实现步骤**:
  - 执行 `docker-compose -f deploy/docker-compose.ev45.yml up -d --build`
  - 等待所有容器启动 (约 60-90s)
  - 执行 `docker ps --format "table {{.Names}}\t{{.Status}}" | grep aeroforge`，确认 7 个应用容器 healthy + 3 个 init 容器 Exited(0)
  - 验证 NATS: `curl http://localhost:8222/healthz`
  - 验证 Neo4j: `curl http://localhost:7474`
  - 验证 MinIO: `curl http://localhost:9000/minio/health/live`
  - 验证 Aircraft Core: `curl http://localhost:8001/api/v6/aircraft-core/health`
  - 验证 Workflow Engine: `curl http://localhost:8002/api/v6/workflow-engine/health`
  - 验证 Physics Twin: `curl http://localhost:8003/api/v6/physics-twin/health`
  - 验证 EV-4 回归: `curl http://localhost:8001/api/v6/aircraft-core/config-hierarchies/B737` 正常返回
  - 记录启动耗时，确认 < 120s (NFR-01)
- **验收标准**: 7/7 容器 healthy；3 个 init 容器 Exited(0)；EV-4 API 无回归

### Task-EV45-07: 远程服务器部署验证
- **Sprint**: A | **优先级**: P0 | **预估**: 1.5h
- **依赖**: Task-EV45-06
- **实现步骤**:
  - 将项目文件传输到远程服务器 8.210.239.214 (通过 scp/rsync)
  - 在远程服务器执行 `docker-compose -f deploy/docker-compose.ev45.yml up -d --build`
  - 确认 7 容器全部 healthy
  - 通过 SSH tunnel 或直接访问验证各服务 health 端点
  - 确认端口不暴露到公网 (NFR-08): 从外部无法直接访问 5432/7687/9000
  - 执行 1 小时稳定性观察 (NFR-05): 记录容器状态
- **验收标准**: 远程服务器 7/7 容器 healthy；EV-4 前端页面正常访问；1 小时后容器仍 healthy

---

## Sprint-B: NATS JetStream Event Bus

> 目标：Aircraft Core → NATS → Workflow Engine 事件链路端到端验证

### Task-EV45-08: 升级 Aircraft Core EventBus 为 JetStream 模式
- **Sprint**: B | **优先级**: P0 | **预估**: 1.5h
- **依赖**: Task-EV45-06
- **实现步骤**:
  - 修改 `services/aircraft-core-service/src/infrastructure/event_bus.py`
  - 在 `connect()` 方法中新增 `self._js = self._nc.jetstream()` 获取 JetStream context
  - 新增 `publish_jetstream(subject, data)` 方法: 使用 `self._js.publish()` 发布，记录 seq 日志
  - 新增 `subscribe_jetstream(subject, durable_name, callback, stream)` 方法: 使用 `self._js.subscribe()` 订阅，manual_ack=True
  - 保留原有 `publish()` / `subscribe()` 方法不变 (向后兼容)
  - 连接失败时 `self._js = None`，降级为 no-op + WARNING 日志
- **文件**: `services/aircraft-core-service/src/infrastructure/event_bus.py` (修改)
- **验收标准**: EventBus 实例调用 `publish_jetstream()` 后 NATS stream 收到消息；NATS 不可用时无报错仅 WARNING

### Task-EV45-09: 创建事件 Pydantic Model
- **Sprint**: B | **优先级**: P0 | **预估**: 1h
- **依赖**: Task-EV45-08
- **实现步骤**:
  - 创建 `services/aircraft-core-service/src/domain/events/__init__.py`
  - 创建 `services/aircraft-core-service/src/domain/events/block_updated_event.py`:
    - `BlockUpdatedEvent(BaseModel)`: event_id (UUID default), event_type="BlockUpdated", block_id, aircraft_type, version (int), changed_fields (list[str]), timestamp (ISO 8601 default)
    - `to_dict()` 方法返回 dict
  - 创建 `services/aircraft-core-service/src/domain/events/configuration_updated_event.py`:
    - `ChangeType(str, Enum)`: CREATED / UPDATED / DELETED
    - `ConfigurationUpdatedEvent(BaseModel)`: event_id (UUID default), event_type="ConfigurationUpdated", configuration_id, block_id, aircraft_type, change_type (ChangeType), timestamp (ISO 8601 default)
    - `to_dict()` 方法返回 dict
- **文件**: `services/aircraft-core-service/src/domain/events/__init__.py` (新增), `block_updated_event.py` (新增), `configuration_updated_event.py` (新增)
- **验收标准**: BlockUpdatedEvent 和 ConfigurationUpdatedEvent 可实例化并序列化为 JSON；字段类型与 spec 6.1/6.2 一致

### Task-EV45-10: Aircraft Core PATCH 端点集成事件发布
- **Sprint**: B | **优先级**: P0 | **预估**: 1.5h
- **依赖**: Task-EV45-09
- **实现步骤**:
  - 修改 `services/aircraft-core-service/src/api/v6/configuration_controller.py` 的 `update_block_config()` 函数
  - 在现有 PATCH 逻辑末尾（缓存失效后、return 前）新增:
    - 构造 `BlockUpdatedEvent`，填充 block_id, aircraft_type, version, changed_fields
    - 调用 `event_bus.publish_jetstream("aeroforge.config.block.updated", event.to_dict())`
    - 构造 `ConfigurationUpdatedEvent`，change_type="UPDATED"
    - 调用 `event_bus.publish_jetstream("aeroforge.config.configuration.updated", config_event.to_dict())`
  - 事件发布为 fire-and-forget，不阻塞 HTTP 响应 (NFR: PATCH 响应不受消费方影响)
  - NATS 不可用时 publish_jetstream 为 no-op，PATCH 请求仍正常返回 200
- **文件**: `services/aircraft-core-service/src/api/v6/configuration_controller.py` (修改)
- **验收标准**: PATCH /block-configurations/{id} 成功后，NATS subject `aeroforge.config.block.updated` 收到事件；响应时间不受消费方影响

### Task-EV45-11: Workflow Engine NATS 消费者实现
- **Sprint**: B | **优先级**: P0 | **预估**: 1.5h
- **依赖**: Task-EV45-08
- **实现步骤**:
  - 升级 `services/workflow-engine-service/src/infrastructure/event_bus.py`，新增 `publish_jetstream()` / `subscribe_jetstream()` 方法 (与 Aircraft Core 同步)
  - 创建 `services/workflow-engine-service/src/infrastructure/nats_consumer.py`:
    - `handle_block_updated_event(msg)`: 解析 JSON payload，记录 INFO 日志 (event_id, block_id, received_at)，调用 `msg.ack()`；异常时 `msg.nak()`
    - `register_config_consumer(bus)`: 调用 `bus.subscribe_jetstream(subject="aeroforge.config.>", durable_name="workflow-engine-config-consumer", callback=handle_block_updated_event, stream="AEROFORGE_CONFIG")`
  - 修改 `services/workflow-engine-service/src/main.py` lifespan:
    - 在 `event_bus.connect()` 后调用 `register_config_consumer(event_bus)`
- **文件**: `services/workflow-engine-service/src/infrastructure/nats_consumer.py` (新增), `event_bus.py` (修改), `main.py` (修改)
- **验收标准**: Workflow Engine 启动后注册 durable consumer；收到 BlockUpdatedEvent 后日志包含 block_id 和 received_at

### Task-EV45-12: Sprint-B 端到端事件链路验证
- **Sprint**: B | **优先级**: P0 | **预估**: 1h
- **依赖**: Task-EV45-10, Task-EV45-11
- **实现步骤**:
  - 重建 Aircraft Core 和 Workflow Engine Docker 镜像
  - 重启全栈: `docker-compose -f deploy/docker-compose.ev45.yml up -d --build`
  - 触发配置变更: `curl -X PATCH http://localhost:8001/api/v6/aircraft-core/block-configurations/{block_id} -H "Content-Type: application/json" -d '{"block_name": "Wing-Updated", "expected_version": 1}'`
  - 检查 Workflow Engine 日志: `docker logs aeroforge-workflow-engine 2>&1 | grep "BlockUpdated"`
  - 验证事件延迟 < 2s (NFR-02): 比较发布时间戳与消费时间戳
  - 验证 NATS stream 信息: `curl http://localhost:8222/jsz` 确认 AEROFORGE_CONFIG stream 存在
  - 验证 consumer 信息: `curl http://localhost:8222/connz` 确认 durable consumer 存在
  - 在远程服务器 8.210.239.214 重复上述验证
- **验收标准**: PATCH → NATS → Workflow Engine 日志完整链路验证通过；端到端延迟 < 2s

---

## Sprint-C: Neo4j Configuration Identity Graph

> 目标：Neo4j 图谱写入 + 查询 API + 种子数据验证

### Task-EV45-13: 扩展 database.py 支持 Neo4j 连接降级模式
- **Sprint**: C | **优先级**: P0 | **预估**: 1h
- **依赖**: Task-EV45-06
- **实现步骤**:
  - 修改 `services/aircraft-core-service/src/infrastructure/database.py`
  - 在 `DatabaseConfig` 中新增 `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` 配置项 (从环境变量读取)
  - 新增全局变量 `_neo4j_driver`
  - 新增 `get_neo4j_driver()` 函数:
    - 检查 `_HAS_NEO4J` (neo4j 库是否安装)
    - 创建 `AsyncGraphDatabase.driver()` 实例
    - 调用 `verify_connectivity()` 验证连接
    - 连接失败时返回 `None` + WARNING 日志 (降级模式)
  - 修改 `close_connections()`: 增加 `_neo4j_driver.close()` 逻辑
- **文件**: `services/aircraft-core-service/src/infrastructure/database.py` (修改)
- **验收标准**: Neo4j 可用时返回 driver 实例；不可用时返回 None 且服务仍正常启动

### Task-EV45-14: 创建 Neo4j Graph Client 封装
- **Sprint**: C | **优先级**: P0 | **预估**: 1.5h
- **依赖**: Task-EV45-13
- **实现步骤**:
  - 创建 `services/aircraft-core-service/src/infrastructure/graph_client.py`
  - 实现 `Neo4jGraphClient` 类:
    - `create_configuration_identity(node_id, block_name, aircraft_type, configuration_type, version)`: MERGE Block 节点 + MERGE Aircraft 节点 + MERGE HAS_BLOCK 关系 + MERGE ConfigurationIdentity 节点
    - `create_sn_node(sn_node_id, tail_number, block_node_id)`: MERGE SN 节点 + MATCH Block + MERGE HAS_SN 关系
    - `query_identity_graph(aircraft_type)`: MATCH Aircraft → Block → SN 层级结构，返回聚合 JSON
  - 所有方法内部调用 `get_neo4j_driver()`，driver 为 None 时返回 False/[] (降级模式)
  - 创建模块级单例 `graph_client = Neo4jGraphClient()`
- **文件**: `services/aircraft-core-service/src/infrastructure/graph_client.py` (新增)
- **验收标准**: 调用 `create_configuration_identity()` 后 Neo4j 中存在对应节点和关系；Neo4j 不可用时方法返回 False

### Task-EV45-15: 创建图谱查询 API (config_identity_controller)
- **Sprint**: C | **优先级**: P0 | **预估**: 1h
- **依赖**: Task-EV45-14
- **实现步骤**:
  - 创建 `services/aircraft-core-service/src/api/v6/config_identity_controller.py`
  - 定义 router: `APIRouter(prefix="/api/v6/aircraft-core", tags=["Configuration Identity Graph"])`
  - 实现 `GET /config-identity-graphs/{aircraft_type}`:
    - 调用 `graph_client.query_identity_graph(aircraft_type)`
    - 返回 `{"aircraft_type": ..., "blocks": [...]}` JSON
    - 查询结果为空时返回空 blocks 数组 (HTTP 200)
    - Neo4j 不可用时返回 503 Service Unavailable
  - 修改 `services/aircraft-core-service/src/main.py`: 注册 `config_identity_controller` router
- **文件**: `services/aircraft-core-service/src/api/v6/config_identity_controller.py` (新增), `main.py` (修改)
- **验收标准**: `GET /api/v6/aircraft-core/config-identity-graphs/B737` 返回包含 Wing/Fuselage/Engine 的层级结构 JSON

### Task-EV45-16: Block 创建端点集成 Neo4j 写入
- **Sprint**: C | **优先级**: P1 | **预估**: 1h
- **依赖**: Task-EV45-14
- **实现步骤**:
  - 修改 `services/aircraft-core-service/src/api/v6/configuration_controller.py` 的 `create_block_config()` 函数
  - 在现有 Block 创建逻辑末尾（return 前）新增:
    - 调用 `graph_client.create_configuration_identity(node_id=block.block_id, block_name=block_name, aircraft_type=aircraft_type)`
  - Neo4j 写入失败不影响 HTTP 响应 (降级为 no-op)
- **文件**: `services/aircraft-core-service/src/api/v6/configuration_controller.py` (修改)
- **验收标准**: POST /block-configurations 创建 Block 后，Neo4j 中存在对应节点；Cypher 查询确认 HAS_BLOCK 关系

### Task-EV45-17: Sprint-C 端到端图谱链路验证
- **Sprint**: C | **优先级**: P0 | **预估**: 1h
- **依赖**: Task-EV45-15, Task-EV45-16
- **实现步骤**:
  - 重建 Aircraft Core Docker 镜像
  - 重启全栈
  - 验证种子数据: `curl http://localhost:8001/api/v6/aircraft-core/config-identity-graphs/B737` 返回 ≥ 3 个 Block
  - 验证直接查询: `docker exec aeroforge-neo4j cypher-shell -u neo4j -p aeroforge_neo4j "MATCH (a:Aircraft {aircraft_type: 'B737'})-[:HAS_BLOCK]->(b:Block) RETURN a, b"`
  - 验证新创建: `curl -X POST http://localhost:8001/api/v6/aircraft-core/block-configurations -H "Content-Type: application/json" -d '{"aircraft_type": "B737", "block_name": "Tail"}'` → 查询确认新节点
  - 验证唯一性约束: 尝试插入相同 node_id → Neo4j 返回 ConstraintViolation
  - 验证查询空结果: `GET /config-identity-graphs/A380` → 返回空 blocks 数组 (HTTP 200)
  - 验证 Cypher 查询性能 < 5s (NFR-03)
  - 在远程服务器重复验证
- **验收标准**: 种子数据查询成功；新创建 Block 写入图谱；唯一性约束生效；查询性能达标

---

## Sprint-D: MinIO Object Storage

> 目标：文件上传 → 预签名 URL → 下载 完整链路验证

### Task-EV45-18: 创建 MinIO Object Storage 客户端封装
- **Sprint**: D | **优先级**: P0 | **预估**: 1.5h
- **依赖**: Task-EV45-06
- **实现步骤**:
  - 创建 `services/aircraft-core-service/src/infrastructure/object_storage.py`
  - 实现 `MinioObjectStorage` 类:
    - `_ensure_client()`: 懒初始化 Minio 客户端，连接失败返回 None + WARNING
    - `upload_file(bucket, file_name, file_data, content_type)`: 校验 content_type (ALLOWED_CONTENT_TYPES)、文件大小 (MAX_FILE_SIZE=50MB)，生成 UUID file_id，调用 `put_object()`，返回 file_id/file_name/bucket/content_type/file_size/upload_timestamp
    - `get_presigned_url(bucket, file_id, expires_hours=1)`: 调用 `presigned_get_object()`，返回 URL 字符串
  - 定义常量: `ALLOWED_CONTENT_TYPES`, `PREDEFINED_BUCKETS`, `MAX_FILE_SIZE`
  - 创建模块级单例 `object_storage = MinioObjectStorage()`
- **文件**: `services/aircraft-core-service/src/infrastructure/object_storage.py` (新增)
- **验收标准**: 调用 `upload_file()` 后 MinIO bucket 中存在文件；不支持的 content_type 抛出 ValueError；超过 50MB 抛出 ValueError

### Task-EV45-19: 创建 Evidence 上传和预签名 URL API
- **Sprint**: D | **优先级**: P0 | **预估**: 1.5h
- **依赖**: Task-EV45-18
- **实现步骤**:
  - 创建 `services/aircraft-core-service/src/api/v6/evidence_controller.py`
  - 定义 router: `APIRouter(prefix="/api/v6/aircraft-core", tags=["Evidence Storage"])`
  - 实现 `POST /evidence/upload`:
    - 接收 `file: UploadFile` 和 `bucket: str = Form("aeroforge-cert-evidence")`
    - 校验 bucket 在 PREDEFINED_BUCKETS 中
    - 调用 `object_storage.upload_file()`，返回 file_id/file_name/bucket/content_type/file_size/upload_timestamp
    - 错误处理: 415 (Unsupported Media Type), 413 (Payload Too Large), 503 (MinIO unavailable)
  - 实现 `GET /evidence/{file_id}/url`:
    - 接收 `file_id` path param 和 `bucket` query param (default: aeroforge-cert-evidence)
    - 调用 `object_storage.get_presigned_url()`，返回 `{"file_id": ..., "url": ...}`
    - MinIO 不可用时返回 503
  - 修改 `services/aircraft-core-service/src/main.py`: 注册 `evidence_controller` router
- **文件**: `services/aircraft-core-service/src/api/v6/evidence_controller.py` (新增), `main.py` (修改)
- **验收标准**: POST 上传 PDF 文件成功返回 file_id；GET 获取预签名 URL 成功；通过 URL 可下载文件

### Task-EV45-20: Sprint-D 端到端对象存储链路验证
- **Sprint**: D | **优先级**: P0 | **预估**: 1h
- **依赖**: Task-EV45-19
- **实现步骤**:
  - 重建 Aircraft Core Docker 镜像
  - 重启全栈
  - 上传测试文件: `curl -X POST http://localhost:8001/api/v6/aircraft-core/evidence/upload -F "file=@test.pdf" -F "bucket=aeroforge-cert-evidence"` → 记录 file_id
  - 获取预签名 URL: `curl http://localhost:8001/api/v6/aircraft-core/evidence/{file_id}/url` → 获取 URL
  - 下载验证: `curl -o downloaded.pdf "{presigned_url}"` → 比较文件大小一致
  - 验证文件大小限制: 上传 51MB 文件 → 返回 413
  - 验证不支持的文件类型: 上传 .exe 文件 → 返回 415
  - 验证不存在的 file_id: GET URL → 返回 404
  - 验证上传性能 < 10s (NFR-04, 10MB 以内文件)
  - 在远程服务器重复验证
- **验收标准**: 上传→URL→下载完整链路通过；413/415/404 错误码正确；性能达标

---

## Sprint-E: Physics Twin Activation

> 目标：Configuration Change → NATS → Physics Twin 同步链路验证

### Task-EV45-21: Physics Twin NATS 消费者实现
- **Sprint**: E | **优先级**: P0 | **预估**: 1.5h
- **依赖**: Task-EV45-12
- **实现步骤**:
  - 升级 `services/physics-twin-service/src/infrastructure/event_bus.py`，新增 `publish_jetstream()` / `subscribe_jetstream()` 方法 (与 Aircraft Core 同步)
  - 创建 `services/physics-twin-service/src/infrastructure/nats_consumer.py`:
    - `handle_configuration_updated_event(msg)`: 解析 JSON payload，记录 INFO 日志 (event_id, configuration_id, change_type, received_at)，调用 `msg.ack()`；异常时 `msg.nak()`
    - `register_config_consumer(bus)`: 调用 `bus.subscribe_jetstream(subject="aeroforge.config.configuration.updated", durable_name="physics-twin-config-consumer", callback=handle_configuration_updated_event, stream="AEROFORGE_CONFIG")`
  - 修改 `services/physics-twin-service/src/main.py` lifespan:
    - 在 `event_bus.connect()` 后调用 `register_config_consumer(event_bus)`
- **文件**: `services/physics-twin-service/src/infrastructure/nats_consumer.py` (新增), `event_bus.py` (修改), `main.py` (修改)
- **验收标准**: Physics Twin 启动后注册 durable consumer；收到 ConfigurationUpdatedEvent 后日志包含 configuration_id 和 received_at

### Task-EV45-22: Sprint-E 端到端同步链路验证
- **Sprint**: E | **优先级**: P0 | **预估**: 1h
- **依赖**: Task-EV45-21
- **实现步骤**:
  - 重建 Physics Twin Docker 镜像
  - 重启全栈
  - 触发配置变更: `curl -X PATCH http://localhost:8001/api/v6/aircraft-core/block-configurations/{block_id} -H "Content-Type: application/json" -d '{"block_name": "Wing-V2", "expected_version": 2}'`
  - 检查 Physics Twin 日志: `docker logs aeroforge-physics-twin 2>&1 | grep "ConfigurationUpdated"`
  - 验证端到端延迟 < 5s: 比较 Aircraft Core 发布时间戳与 Physics Twin 接收时间戳
  - 验证事件 payload: 确认包含 event_id, event_type="ConfigurationUpdated", configuration_id, block_id, aircraft_type, change_type="UPDATED", timestamp 字段
  - 验证 NATS consumer: `curl http://localhost:8222/jsz` 确认 physics-twin-config-consumer 存在
  - 在远程服务器 8.210.239.214 重复上述验证
- **验收标准**: PATCH → NATS → Physics Twin 日志完整链路验证通过；端到端延迟 < 5s；事件字段完整

### Task-EV45-23: EV-4.5 全栈集成验证 + TRL 6.0 评估
- **Sprint**: E | **优先级**: P0 | **预估**: 2h
- **依赖**: Task-EV45-12, Task-EV45-17, Task-EV45-20, Task-EV45-22
- **实现步骤**:
  - 执行 A 级验收矩阵 (spec 7.1):
    - EV4.5-REQ-01~05: 7 容器全部 healthy
    - EV4.5-REQ-06: Aircraft Core 发布 BlockUpdatedEvent
    - EV4.5-REQ-07: Workflow Engine 消费 BlockUpdatedEvent
    - EV4.5-REQ-08: Neo4j 写入 Configuration Identity 节点
    - EV4.5-REQ-09: Cypher MATCH 查询返回 B737 图谱数据
    - EV4.5-REQ-10: MinIO 上传证据文件成功
    - EV4.5-REQ-11: MinIO 获取预签名 URL 并下载成功
  - 执行 A+ 级验收矩阵 (spec 7.2):
    - EV4.5-REQ-12: Configuration Change → NATS → Workflow Engine 完整链路
    - EV4.5-REQ-13: Configuration Change → NATS → Physics Twin 完整链路
    - EV4.5-REQ-14: Evidence Upload → MinIO 完整链路
    - EV4.5-REQ-15: Identity Link → Neo4j 完整链路
    - EV4.5-REQ-16: 7 容器连续运行 1 小时无故障
  - 验证 EV-4 回归: React 前端 → FastAPI → PostgreSQL 闭环仍正常 (NFR-14)
  - 验证降级策略: 停止 NATS/Neo4j/MinIO 容器，确认 Aircraft Core HTTP 请求仍正常
  - 收集验证证据: docker ps 截图、API 响应 JSON、日志输出
  - 在远程服务器执行全量验证
  - 评估 TRL 5.5 → 6.0 达标情况
- **验收标准**: A 级 11 项验收全部通过；A+ 级 5 项验收至少 4 项通过；EV-4 无回归；TRL 6.0 达标

---

## 依赖关系图

```
Sprint-A (Infrastructure Bring-up)
  Task-EV45-01 (docker-compose.ev45.yml)
  Task-EV45-02 (init_nats_streams.py)
  Task-EV45-03 (init_neo4j_schema.py)
  Task-EV45-04 (init_minio_buckets.sh)
  Task-EV45-05 (Dockerfile + deps) ──→ Task-EV45-01
  Task-EV45-06 (本地全栈验证) ──→ 01, 02, 03, 04, 05
  Task-EV45-07 (远程部署验证) ──→ 06

Sprint-B (NATS JetStream Event Bus)
  Task-EV45-08 (EventBus JetStream 升级) ──→ 06
  Task-EV45-09 (事件 Pydantic Model) ──→ 08
  Task-EV45-10 (PATCH 端点事件发布) ──→ 09
  Task-EV45-11 (Workflow Engine 消费者) ──→ 08
  Task-EV45-12 (Sprint-B E2E 验证) ──→ 10, 11

Sprint-C (Neo4j Identity Graph)
  Task-EV45-13 (database.py Neo4j 扩展) ──→ 06
  Task-EV45-14 (Graph Client 封装) ──→ 13
  Task-EV45-15 (图谱查询 API) ──→ 14
  Task-EV45-16 (Block 创建 Neo4j 写入) ──→ 14
  Task-EV45-17 (Sprint-C E2E 验证) ──→ 15, 16

Sprint-D (MinIO Object Storage)
  Task-EV45-18 (MinIO Client 封装) ──→ 06
  Task-EV45-19 (Evidence API) ──→ 18
  Task-EV45-20 (Sprint-D E2E 验证) ──→ 19

Sprint-E (Physics Twin Activation)
  Task-EV45-21 (Physics Twin 消费者) ──→ 12
  Task-EV45-22 (Sprint-E E2E 验证) ──→ 21
  Task-EV45-23 (全栈集成验证) ──→ 12, 17, 20, 22
```

---

## 文件变更汇总

### 新增文件 (13)

| 文件路径 | 任务 | 说明 |
|----------|------|------|
| `deploy/docker-compose.ev45.yml` | 01 | 7 服务 + 3 init 容器编排 |
| `scripts/init_nats_streams.py` | 02 | NATS JetStream Stream + Consumer 初始化 |
| `scripts/init_neo4j_schema.py` | 03 | Neo4j Schema 约束 + B737 种子数据 |
| `scripts/init_minio_buckets.sh` | 04 | MinIO 8 个 Bucket 初始化 |
| `services/aircraft-core-service/src/domain/events/__init__.py` | 09 | 事件模块初始化 |
| `services/aircraft-core-service/src/domain/events/block_updated_event.py` | 09 | BlockUpdatedEvent Pydantic Model |
| `services/aircraft-core-service/src/domain/events/configuration_updated_event.py` | 09 | ConfigurationUpdatedEvent Pydantic Model |
| `services/workflow-engine-service/src/infrastructure/nats_consumer.py` | 11 | Workflow Engine NATS 消费者 |
| `services/aircraft-core-service/src/infrastructure/graph_client.py` | 14 | Neo4j 图谱操作客户端 |
| `services/aircraft-core-service/src/api/v6/config_identity_controller.py` | 15 | 图谱查询 API |
| `services/aircraft-core-service/src/infrastructure/object_storage.py` | 18 | MinIO 对象存储客户端 |
| `services/aircraft-core-service/src/api/v6/evidence_controller.py` | 19 | 证据文件上传/URL API |
| `services/physics-twin-service/src/infrastructure/nats_consumer.py` | 21 | Physics Twin NATS 消费者 |

### 修改文件 (10)

| 文件路径 | 任务 | 修改内容 |
|----------|------|----------|
| `services/aircraft-core-service/src/infrastructure/event_bus.py` | 08 | 新增 publish_jetstream / subscribe_jetstream，connect() 增加 JetStream context |
| `services/aircraft-core-service/src/api/v6/configuration_controller.py` | 10, 16 | PATCH 端点新增事件发布；POST 端点新增 Neo4j 写入 |
| `services/aircraft-core-service/src/infrastructure/database.py` | 13 | 新增 get_neo4j_driver() 降级模式 + close_connections 扩展 |
| `services/aircraft-core-service/src/main.py` | 15, 19 | 注册 config_identity_controller + evidence_controller router |
| `services/aircraft-core-service/requirements.txt` | 05 | 新增 nats-py, neo4j, minio 依赖 |
| `services/workflow-engine-service/src/infrastructure/event_bus.py` | 11 | 新增 publish_jetstream / subscribe_jetstream |
| `services/workflow-engine-service/src/main.py` | 11 | lifespan 中注册 NATS 消费者 |
| `services/workflow-engine-service/requirements.txt` | 05 | 新增 nats-py 依赖 |
| `services/physics-twin-service/src/infrastructure/event_bus.py` | 21 | 新增 publish_jetstream / subscribe_jetstream |
| `services/physics-twin-service/src/main.py` | 21 | lifespan 中注册 NATS 消费者 |

---

## 验收矩阵追踪

| 验收编号 | 验收项 | 覆盖任务 |
|----------|--------|----------|
| EV4.5-REQ-01 | NATS 启动且 healthy | 06, 07 |
| EV4.5-REQ-02 | Neo4j 启动且 healthy | 06, 07 |
| EV4.5-REQ-03 | MinIO 启动且 healthy | 06, 07 |
| EV4.5-REQ-04 | Workflow Engine 启动且 healthy | 06, 07 |
| EV4.5-REQ-05 | Physics Twin 启动且 healthy | 06, 07 |
| EV4.5-REQ-06 | Aircraft Core 发布 BlockUpdatedEvent | 10, 12 |
| EV4.5-REQ-07 | Workflow Engine 消费 BlockUpdatedEvent | 11, 12 |
| EV4.5-REQ-08 | Neo4j 写入 Configuration Identity 节点 | 16, 17 |
| EV4.5-REQ-09 | Cypher MATCH 查询返回 B737 图谱数据 | 15, 17 |
| EV4.5-REQ-10 | MinIO 上传证据文件成功 | 19, 20 |
| EV4.5-REQ-11 | MinIO 获取预签名 URL 并下载成功 | 19, 20 |
| EV4.5-REQ-12 | Config → NATS → WE 完整链路 | 12 |
| EV4.5-REQ-13 | Config → NATS → PT 完整链路 | 22 |
| EV4.5-REQ-14 | Evidence Upload → MinIO 完整链路 | 20 |
| EV4.5-REQ-15 | Identity Link → Neo4j 完整链路 | 17 |
| EV4.5-REQ-16 | 7 容器连续运行 1 小时无故障 | 07, 23 |