# AeroForge-X EV-4.6 Digital Thread Hardening — 编码任务清单

**Sprint**: EV-4.6 Digital Thread Hardening Sprint  
**目标 TRL**: 6.5 → 7.0  
**日期**: 2026-06-23  
**关联需求**: `docs/specs/ev4.6-digital-thread-hardening-spec.md`  
**关联设计**: `docs/specs/ev4.6-digital-thread-hardening-design.md`  
**前置基线**: EV-4.5 Digital Thread Foundation（PASS 级验收通过）  
**核心原则**: 从"数据贯通阶段"升级为"语义图谱阶段"

---

## 验收场景

```
TraceQuery("B737-MAIN-WING") → 全链路路径:
  Block(B737-MAIN-WING) → MaterialLot(AL-2024-002) → NDTRecord → CAR → Evidence → Compliance

EventContract: 每个事件发布前 schema 验证通过
Identity: Block + MaterialLot + NDT + CAR 共享同一 ConfigurationIdentity
```

**验收级别**:
- **PASS**: Event Contract Layer + Identity Unification + Trace Graph Model (后端)
- **A**: + Schema Registry API + Impact Analysis + Dependency Query + 环路检测
- **A+**: + Trace Analysis UI (交互式依赖图 + 变更传播视图)

---

## Phase 1 — Event Contract Layer (P0)

### Sprint-H01: Event Contract Layer

> 目标：事件契约治理 — JSON Schema + 版本管理 + 验证 + 幂等消费

#### Task-H01-01: 创建 6 个事件 JSON Schema 文件
- **Sprint**: H01 | **优先级**: P0 | **预估**: 1.5h
- **依赖**: 无
- **实现步骤**:
  - 创建 `services/aircraft-core-service/event-contract/schema/` 目录
  - 创建 6 个 JSON Schema Draft 2020-12 格式文件:
    - `MaterialLotCreated.v1.json` — lot_id, material_code, supplier_id, block_id, timestamp
    - `NDTCompleted.v1.json` — ndt_record_id, material_lot_id, test_type, result, timestamp
    - `CARCreated.v1.json` — car_id, ndt_record_id, description, status, timestamp
    - `CARClosed.v1.json` — car_id, closed_by, timestamp
    - `EvidenceUploaded.v1.json` — evidence_id, requirement_id, file_id, file_name, timestamp
    - `ConfigurationChanged.v1.json` — configuration_id, block_id, aircraft_type, change_type, timestamp
  - 每个 schema 包含: `$schema`, `title`, `type: object`, `properties`, `required`, `additionalProperties: false`
  - 每个属性含 `type` + `description`
- **验证**: JSON Schema 语法正确，可被 jsonschema 库解析

#### Task-H01-02: 实现事件版本管理
- **Sprint**: H01 | **优先级**: P0 | **预估**: 1h
- **依赖**: 无
- **实现步骤**:
  - 创建 `services/aircraft-core-service/event-contract/versioning/` 目录
  - 创建 `event-contract/versioning/__init__.py`
  - 创建 `event-contract/versioning/semantic_version.py`
  - `SemanticVersion` dataclass: major, minor, patch
  - `parse_version(version_str: str) -> SemanticVersion`
  - `is_backward_compatible(old: SemanticVersion, new: SemanticVersion) -> bool`
    - major 不同 → 不兼容
    - minor/patch 不同 → 兼容
  - 创建 `event-contract/versioning/event_contract_versions` 表 DDL (在 migration 文件中)
    - contract_id (PK), event_type, schema_version, schema_content (JSONB), is_active, created_at
- **验证**: 版本解析和兼容性判断逻辑正确

#### Task-H01-03: 实现 SchemaRegistry (内存 + 文件系统加载)
- **Sprint**: H01 | **优先级**: P0 | **预估**: 2h
- **依赖**: H01-01
- **实现步骤**:
  - 创建 `services/aircraft-core-service/src/infrastructure/event_contract/` 目录
  - 创建 `infrastructure/event_contract/__init__.py`
  - 创建 `infrastructure/event_contract/schema_registry.py`
  - `SchemaRegistry` 类:
    - `_schemas: dict[str, dict]` — event_type → schema dict
    - `_versions: dict[str, str]` — event_type → current version string
    - `load_from_directory(path: str)` — 扫描 event-contract/schema/ 目录，加载所有 .json 文件
    - `get_schema(event_type: str) -> Optional[dict]`
    - `register_schema(event_type: str, schema: dict, version: str)`
    - `validate_event(event_type: str, payload: dict) -> tuple[bool, str]`
      - 使用 jsonschema.validate() 验证
      - 返回 (True, "") 或 (False, error_message)
    - `list_schemas() -> list[dict]` — 返回所有已注册 schema 的元数据
  - 启动时自动加载 event-contract/schema/ 目录
- **验证**: Schema 加载、查询、验证功能正常

#### Task-H01-04: 创建 event_contract_versions + consumer_idempotency_records DDL
- **Sprint**: H01 | **优先级**: P0 | **预估**: 0.5h
- **依赖**: 无
- **实现步骤**:
  - 创建 `deploy/migrations/v6_4/009_event_contract_tables.sql`
  - `event_contract_versions` 表: contract_id (PK UUID), event_type, schema_version, schema_content (JSONB), is_active (bool), created_at
  - `consumer_idempotency_records` 表: id (PK UUID), consumer_name, event_id, event_type, processed_at
    - UNIQUE (consumer_name, event_id)
  - 索引: event_contract_versions(event_type, is_active), consumer_idempotency_records(consumer_name, event_id)
- **验证**: DDL 在远程 PostgreSQL 执行无报错

#### Task-H01-05: 实现 EventContractService (验证 + 查询)
- **Sprint**: H01 | **优先级**: P0 | **预估**: 3h
- **依赖**: H01-03, H01-02, H01-04
- **实现步骤**:
  - 创建 `infrastructure/event_contract/event_contract_service.py`
  - `EventContractService` 类:
    - `__init__(schema_registry: SchemaRegistry, pool: asyncpg.Pool)`
    - `async def validate_and_publish(event_type: str, payload: dict, subject: str) -> bool`
      - 调用 SchemaRegistry.validate_event()
      - 验证失败: 记录 ERROR 日志，仍发布事件（fire-and-forget 模式）
      - 验证通过: 调用 EventBus.publish_jetstream()
    - `async def check_idempotency(consumer_name: str, event_id: str) -> bool`
      - INSERT INTO consumer_idempotency_records ON CONFLICT DO NOTHING
      - 返回 True (首次消费) / False (重复消费)
    - `async def register_contract(event_type: str, schema: dict, version: str)`
      - 写入 event_contract_versions 表
    - `async def list_contracts() -> list[dict]`
    - `async def get_contract(event_type: str) -> Optional[dict]`
- **验证**: 验证、幂等、注册功能正常

#### Task-H01-06: 实现 event_contract_controller.py (Registry API)
- **Sprint**: H01 | **优先级**: P1 | **预估**: 2h
- **依赖**: H01-05
- **实现步骤**:
  - 创建 `api/v6/event_contract_controller.py`
  - `APIRouter(prefix="/api/v6/aircraft-core/dt", tags=["Event Contract"])`
  - `GET /event-contracts` — 列出所有事件契约
  - `GET /event-contracts/{event_type}` — 查询单个事件契约
  - `POST /event-contracts` — 注册新事件契约版本
- **验证**: API 端点可正常调用

#### Task-H01-07: 修改 3 个 Controller 注入 schema 验证
- **Sprint**: H01 | **优先级**: P0 | **预估**: 2h
- **依赖**: H01-05
- **实现步骤**:
  - 修改 `material_controller.py`: 将 `event_bus.publish_jetstream()` 替换为 `event_contract_service.validate_and_publish()`
  - 修改 `quality_controller.py`: 同上
  - 修改 `dt_certification_controller.py`: 同上
  - 验证失败时记录 ERROR 但不阻断 HTTP 响应
- **验证**: 事件发布前 schema 验证生效

#### Task-H01-08: main.py 启动时加载 Schema Registry
- **Sprint**: H01 | **优先级**: P0 | **预估**: 0.5h
- **依赖**: H01-03
- **实现步骤**:
  - 修改 `main.py` 的 `lifespan` 函数
  - 添加 SchemaRegistry 初始化和 event-contract/schema/ 目录加载
  - 添加 EventContractService 实例化
- **验证**: 启动日志显示 schema 加载成功

#### Task-H01-09: 远程部署 + 集成测试 Event Contract Layer
- **Sprint**: H01 | **优先级**: P0 | **预估**: 2h
- **依赖**: H01-04, H01-05, H01-07, H01-08
- **实现步骤**:
  - 执行 DDL migration
  - 上传所有新文件到远程服务器
  - 重建 aircraft-core Docker 镜像
  - 重启容器
  - curl 测试:
    - `POST /dt/material-lots` → 事件发布 + schema 验证通过
    - `GET /dt/event-contracts` → 返回 6 个 schema
    - `GET /dt/event-contracts/MaterialLotCreated` → 返回 schema 详情
    - 故意发送 schema 不匹配的事件 → 日志显示 ERROR 但 HTTP 仍成功
- **验证**: PASS 级 Event Contract 验收通过

---

## Phase 2 — Identity Unification Layer (P0)

### Sprint-H02: Identity Unification Layer

> 目标：ConfigurationIdentity 统一身份 — 1 Identity → N Domain Records

#### Task-H02-01: 创建 configuration_identities + identity_mappings DDL
- **Sprint**: H02 | **优先级**: P0 | **预估**: 1h
- **依赖**: 无
- **实现步骤**:
  - 创建 `deploy/migrations/v6_4/010_identity_tables.sql`
  - `configuration_identities` 表: identity_id (PK UUID), label, node_type, created_at
  - `identity_mappings` 表: mapping_id (PK UUID), identity_id (FK), domain, domain_id, created_at
    - UNIQUE (domain, domain_id)
    - INDEX (identity_id)
- **验证**: DDL 执行无报错

#### Task-H02-02: 实现 ConfigurationIdentity + IdentityMapping dataclass
- **Sprint**: H02 | **优先级**: P0 | **预估**: 1h
- **依赖**: 无
- **实现步骤**:
  - 创建 `domain/models/configuration_identity.py`
  - `ConfigurationIdentity` dataclass: identity_id, label, node_type, created_at
  - `to_dict()` + `from_row()`
  - 创建 `domain/models/identity_mapping.py`
  - `IdentityMapping` dataclass: mapping_id, identity_id, domain, domain_id, created_at
  - `to_dict()` + `from_row()`
- **验证**: Python import 无报错

#### Task-H02-03: 实现 ConfigurationIdentityRepository
- **Sprint**: H02 | **优先级**: P0 | **预估**: 2h
- **依赖**: H02-01
- **实现步骤**:
  - 创建 `infrastructure/repositories/configuration_identity_repository.py`
  - `async def create(label: str, node_type: str) -> ConfigurationIdentity`
  - `async def find_by_id(identity_id: str) -> Optional[ConfigurationIdentity]`
  - `async def find_by_domain(domain: str, domain_id: str) -> Optional[ConfigurationIdentity]`
    - JOIN identity_mappings
  - `async def find_all(limit, offset) -> list[ConfigurationIdentity]`
- **验证**: Repository 方法签名与设计一致

#### Task-H02-04: 实现 IdentityMappingRepository (含 UPSERT)
- **Sprint**: H02 | **优先级**: P0 | **预估**: 2h
- **依赖**: H02-01
- **实现步骤**:
  - 创建 `infrastructure/repositories/identity_mapping_repository.py`
  - `async def upsert(identity_id: str, domain: str, domain_id: str) -> IdentityMapping`
    - INSERT ON CONFLICT (domain, domain_id) DO UPDATE SET identity_id = EXCLUDED.identity_id
  - `async def find_by_identity(identity_id: str) -> list[IdentityMapping]`
  - `async def find_by_domain(domain: str, domain_id: str) -> Optional[IdentityMapping]`
- **验证**: UPSERT 逻辑正确

#### Task-H02-05: 实现 IdentityService (resolve_or_create + 查询)
- **Sprint**: H02 | **优先级**: P0 | **预估**: 3h
- **依赖**: H02-03, H02-04
- **实现步骤**:
  - 创建 `domain/services/identity_service.py`
  - `IdentityService` 类:
    - `async def resolve_or_create_identity(domain: str, domain_id: str, label: str, node_type: str, related_domain: str = None, related_domain_id: str = None) -> ConfigurationIdentity`
      - 如果 (domain, domain_id) 已有映射 → 返回已有 Identity
      - 如果 related_domain/related_domain_id 不为空且已有映射 → 复用该 Identity，创建新映射
      - 否则 → 创建新 Identity + 新映射
    - `async def get_identity(identity_id: str) -> Optional[dict]`
      - 返回 Identity + 所有映射
    - `async def get_identity_by_domain(domain: str, domain_id: str) -> Optional[dict]`
    - `async def list_identities(limit, offset) -> list[dict]`
- **验证**: resolve_or_create 逻辑正确，Block + MaterialLot 共享同一 Identity

#### Task-H02-06: 实现 identity_controller.py (Identity Query API)
- **Sprint**: H02 | **优先级**: P1 | **预估**: 2h
- **依赖**: H02-05
- **实现步骤**:
  - 创建 `api/v6/identity_controller.py`
  - `APIRouter(prefix="/api/v6/aircraft-core/dt", tags=["Identity"])`
  - `GET /identities` — 列出所有 Identity
  - `GET /identities/{identity_id}` — 查询 Identity + 所有映射
  - `GET /identities/by-domain/{domain}/{domain_id}` — 域 ID 反查 Identity
- **验证**: API 端点可正常调用

#### Task-H02-07: 修改 material_controller 注入 Identity 解析
- **Sprint**: H02 | **优先级**: P0 | **预估**: 1.5h
- **依赖**: H02-05
- **实现步骤**:
  - 修改 `material_controller.py`
  - 在 `create_material_lot` 中:
    - 调用 `identity_service.resolve_or_create_identity(domain="material_lot", domain_id=lot.lot_id, label=lot.material_name, node_type="material_lot", related_domain="block", related_domain_id=body.block_id)`
    - 如果 block_id 不为空，Block + MaterialLot 共享同一 Identity
- **验证**: 创建 MaterialLot 后，Block 和 MaterialLot 映射到同一 Identity

#### Task-H02-08: 修改 quality_controller 注入 Identity 解析
- **Sprint**: H02 | **优先级**: P0 | **预估**: 1.5h
- **依赖**: H02-05
- **实现步骤**:
  - 修改 `quality_controller.py`
  - 在 `create_ndt_record` 中: NDTRecord 复用 MaterialLot 的 Identity
  - 在 `create_car` 中: CAR 复用 NDTRecord 的 Identity
- **验证**: NDT + CAR 与 MaterialLot 共享同一 Identity

#### Task-H02-09: 修改 dt_certification_controller 注入 Identity 解析
- **Sprint**: H02 | **优先级**: P0 | **预估**: 1.5h
- **依赖**: H02-05
- **实现步骤**:
  - 修改 `dt_certification_controller.py`
  - 在 `upload_certification_evidence` 中: Evidence 复用 Compliance 的 Identity
- **验证**: Evidence 与 Compliance 共享同一 Identity

#### Task-H02-10: 远程部署 + 集成测试 Identity Unification Layer
- **Sprint**: H02 | **优先级**: P0 | **预估**: 2h
- **依赖**: H02-06~09
- **实现步骤**:
  - 执行 DDL migration
  - 重建 Docker 镜像 + 重启
  - curl 测试:
    - `POST /dt/material-lots` (block_id=BLK-B737-MAIN-WING)
    - `GET /dt/identities` → 返回 Identity 列表
    - `GET /dt/identities/by-domain/material_lot/AL-2024-002` → 返回 Identity + Block 映射
    - `POST /dt/ndt-records` → NDT 复用 MaterialLot Identity
    - `GET /dt/identities/{id}` → 返回 Identity + 4 个域映射 (block, material, ndt, car)
- **验证**: PASS 级 Identity Unification 验收通过

---

## Phase 3 — Trace Graph Model (P0)

### Sprint-H03: Trace Graph Model

> 目标：in-memory / relational 图模型 — TraceQuery + Impact Analysis + Dependency Query

#### Task-H03-01: 创建 trace_nodes + trace_edges DDL
- **Sprint**: H03 | **优先级**: P0 | **预估**: 1h
- **依赖**: 无
- **实现步骤**:
  - 创建 `deploy/migrations/v6_4/011_trace_graph_tables.sql`
  - `trace_nodes` 表: node_id (PK UUID), identity_id (FK), node_type, label, properties (JSONB), created_at
  - `trace_edges` 表: edge_id (PK UUID), source_node_id (FK), target_node_id (FK), edge_type, properties (JSONB), created_at
    - INDEX (source_node_id), INDEX (target_node_id), INDEX (edge_type)
- **验证**: DDL 执行无报错

#### Task-H03-02: 实现 TraceNode + TraceEdge dataclass
- **Sprint**: H03 | **优先级**: P0 | **预估**: 1h
- **依赖**: 无
- **实现步骤**:
  - 创建 `domain/models/trace_node.py`
  - `TraceNode` dataclass: node_id, identity_id, node_type, label, properties, created_at
  - `to_dict()` + `from_row()`
  - 创建 `domain/models/trace_edge.py`
  - `TraceEdge` dataclass: edge_id, source_node_id, target_node_id, edge_type, properties, created_at
  - `to_dict()` + `from_row()`
- **验证**: Python import 无报错

#### Task-H03-03: 实现 TraceNodeRepository
- **Sprint**: H03 | **优先级**: P0 | **预估**: 2h
- **依赖**: H03-01
- **实现步骤**:
  - 创建 `infrastructure/repositories/trace_node_repository.py`
  - `async def create(identity_id, node_type, label, properties=None) -> TraceNode`
  - `async def find_by_id(node_id) -> Optional[TraceNode]`
  - `async def find_by_identity(identity_id) -> Optional[TraceNode]`
  - `async def find_by_type(node_type, limit, offset) -> list[TraceNode]`
  - `async def update_properties(node_id, properties) -> Optional[TraceNode]`
  - `async def delete_all() -> int`
- **验证**: Repository 方法签名与设计一致

#### Task-H03-04: 实现 TraceEdgeRepository
- **Sprint**: H03 | **优先级**: P0 | **预估**: 2h
- **依赖**: H03-01
- **实现步骤**:
  - 创建 `infrastructure/repositories/trace_edge_repository.py`
  - `async def create(source_node_id, target_node_id, edge_type, properties=None) -> TraceEdge`
  - `async def find_outgoing(node_id) -> list[TraceEdge]`
  - `async def find_incoming(node_id) -> list[TraceEdge]`
  - `async def find_by_type(edge_type, limit, offset) -> list[TraceEdge]`
  - `async def delete_all() -> int`
- **验证**: Repository 方法签名与设计一致

#### Task-H03-05: 实现 TraceGraphCache (邻接表 + CRUD)
- **Sprint**: H03 | **优先级**: P0 | **预估**: 3h
- **依赖**: 无
- **实现步骤**:
  - 创建 `infrastructure/trace_graph_cache.py`
  - `TraceGraphCache` 类:
    - `_adjacency: dict[str, list[TraceEdge]]` — node_id → outgoing edges
    - `_reverse_adjacency: dict[str, list[TraceEdge]]` — node_id → incoming edges
    - `_nodes: dict[str, TraceNode]` — node_id → node
    - `add_node(node: TraceNode)`
    - `add_edge(edge: TraceEdge)`
    - `get_node(node_id) -> Optional[TraceNode]`
    - `get_outgoing(node_id) -> list[TraceEdge]`
    - `get_incoming(node_id) -> list[TraceEdge]`
    - `clear()`
    - `node_count() -> int`
    - `edge_count() -> int`
  - 线程安全: 使用 asyncio.Lock
- **验证**: 缓存 CRUD 功能正常

#### Task-H03-06: 实现 TraceGraphService (BFS + Impact + Dependency + Rebuild)
- **Sprint**: H03 | **优先级**: P0 | **预估**: 5h
- **依赖**: H03-03, H03-04, H03-05
- **实现步骤**:
  - 创建 `domain/services/trace_graph_service.py`
  - `TraceGraphService` 类:
    - `__init__(node_repo, edge_repo, cache: TraceGraphCache)`
    - `async def create_trace_node(identity_id, node_type, label, properties=None) -> TraceNode`
      - 写入 PostgreSQL + 更新 cache
    - `async def create_trace_edge(source_node_id, target_node_id, edge_type, properties=None) -> TraceEdge`
      - 写入 PostgreSQL + 更新 cache
    - `async def trace_query(start_node_id, direction="both", max_depth=5, max_nodes=100) -> dict`
      - BFS 遍历，返回 { nodes: [], edges: [], truncated: bool }
      - direction: "outgoing" / "incoming" / "both"
    - `async def impact_analysis(start_node_id, max_depth=5) -> dict`
      - outgoing-only BFS
      - 返回 { direct: [], indirect: [] }
      - direct = depth=1 的受影响节点
      - indirect = depth>1 的受影响节点
    - `async def dependency_query(start_node_id, max_depth=5) -> dict`
      - incoming-only BFS
      - 返回 { dependencies: [] }
    - `async def rebuild_graph() -> dict`
      - 事务内: TRUNCATE trace_nodes + trace_edges
      - 从 dt_material_lots, dt_ndt_records, dt_corrective_actions, dt_compliance_requirements 重建
      - 刷新 cache
      - 返回 { nodes: count, edges: count }
    - `async def detect_cycles() -> list[list[str]]`
      - DFS 环路检测
    - `async def get_statistics() -> dict`
      - 返回 { node_count, edge_count, node_types: {type: count}, edge_types: {type: count} }
    - `async def load_cache_from_db()`
      - 启动时从 PostgreSQL 加载所有 nodes + edges 到 cache
- **验证**: BFS、Impact Analysis、Dependency Query 功能正常

#### Task-H03-07: 实现 trace_graph_controller.py
- **Sprint**: H03 | **优先级**: P0 | **预估**: 2h
- **依赖**: H03-06
- **实现步骤**:
  - 创建 `api/v6/trace_graph_controller.py`
  - `APIRouter(prefix="/api/v6/aircraft-core/dt", tags=["Trace Graph"])`
  - `GET /trace/query?start_node_id={id}&direction=both&max_depth=5` — TraceQuery
  - `GET /trace/impact/{node_id}` — Impact Analysis
  - `GET /trace/dependencies/{node_id}` — Dependency Query
  - `POST /trace/rebuild` — Graph Rebuild (管理级)
  - `GET /trace/statistics` — Trace Graph 统计
  - `GET /trace/nodes/{node_id}` — Trace Node 详情
- **验证**: API 端点可正常调用

#### Task-H03-08: 修改 material_controller 注入 Trace Graph
- **Sprint**: H03 | **优先级**: P0 | **预估**: 1.5h
- **依赖**: H03-06, H02-07
- **实现步骤**:
  - 修改 `material_controller.py`
  - 在 `create_material_lot` 中:
    - 调用 `trace_graph_service.create_trace_node(identity_id, "material_lot", lot.material_name)`
    - 如果 block_id 不为空: `trace_graph_service.create_trace_edge(block_node_id, material_node_id, "contains_material")`
- **验证**: 创建 MaterialLot 后 Trace Graph 中有对应 node + edge

#### Task-H03-09: 修改 quality_controller 注入 Trace Graph
- **Sprint**: H03 | **优先级**: P0 | **预估**: 1.5h
- **依赖**: H03-06, H02-08
- **实现步骤**:
  - 修改 `quality_controller.py`
  - 在 `create_ndt_record` 中: create_trace_node + create_trace_edge(material→ndt, "tested_by")
  - 在 `create_car` 中: create_trace_node + create_trace_edge(ndt→car, "corrected_by")
  - 在 `update_car` 中: update node properties
- **验证**: NDT + CAR 在 Trace Graph 中有对应 node + edge

#### Task-H03-10: 修改 dt_certification_controller 注入 Trace Graph
- **Sprint**: H03 | **优先级**: P0 | **预估**: 1.5h
- **依赖**: H03-06, H02-09
- **实现步骤**:
  - 修改 `dt_certification_controller.py`
  - 在 `upload_certification_evidence` 中: create_trace_node + create_trace_edge(compliance→evidence, "supported_by")
- **验证**: Evidence 在 Trace Graph 中有对应 node + edge

#### Task-H03-11: main.py 启动时加载 Trace Graph cache
- **Sprint**: H03 | **优先级**: P0 | **预估**: 1h
- **依赖**: H03-06
- **实现步骤**:
  - 修改 `main.py` 的 lifespan 函数
  - 添加 TraceGraphService 初始化
  - 添加 `await trace_graph_service.load_cache_from_db()`
  - 注册 trace_graph_router
- **验证**: 启动日志显示 cache 加载成功

#### Task-H03-12: 远程部署 + 集成测试 Trace Graph Model
- **Sprint**: H03 | **优先级**: P0 | **预估**: 2h
- **依赖**: H03-07~11
- **实现步骤**:
  - 执行 DDL migration
  - 重建 Docker 镜像 + 重启
  - curl 测试:
    - `POST /dt/material-lots` → Trace Graph 自动创建 node + edge
    - `POST /dt/ndt-records` → Trace Graph 自动创建 node + edge
    - `GET /dt/trace/query?start_node_id={block_node_id}&direction=outgoing` → 全链路遍历
    - `GET /dt/trace/impact/{node_id}` → 影响分析
    - `GET /dt/trace/dependencies/{node_id}` → 依赖查询
    - `POST /dt/trace/rebuild` → 重建成功
    - `GET /dt/trace/statistics` → 统计数据
  - 验证 TraceQuery("B737-MAIN-WING") 返回全链路路径
- **验证**: PASS 级 Trace Graph 验收通过

---

## Phase 4 — Trace Analysis UI (P1)

### Sprint-H04: Trace Analysis UI

> 目标：交互式依赖图 + 变更传播视图 + Identity 跨域对齐

#### Task-H04-01: 新增 TypeScript 类型定义
- **Sprint**: H04 | **优先级**: P1 | **预估**: 1h
- **依赖**: 无
- **实现步骤**:
  - 编辑 `frontend/src/api/types.ts`
  - 新增: TraceNode, TraceEdge, TraceQueryResult, ImpactAnalysisResult, DependencyQueryResult, ConfigurationIdentity, IdentityMapping, TraceStatistics
- **验证**: TypeScript 编译无报错

#### Task-H04-02: 新增 v6Api.ts dtHardeningApi 函数
- **Sprint**: H04 | **优先级**: P1 | **预估**: 1h
- **依赖**: H04-01
- **实现步骤**:
  - 编辑 `frontend/src/api/v6Api.ts`
  - 新增 dtHardeningApi:
    - `traceQuery(startNodeId, direction, maxDepth)`
    - `impactAnalysis(nodeId)`
    - `dependencyQuery(nodeId)`
    - `rebuildGraph()`
    - `getTraceStatistics()`
    - `getTraceNode(nodeId)`
    - `getIdentities()`
    - `getIdentity(identityId)`
    - `getIdentityByDomain(domain, domainId)`
    - `getEventContracts()`
    - `getEventContract(eventType)`
- **验证**: TypeScript 编译无报错

#### Task-H04-03: 实现 TraceGraphCanvas 组件
- **Sprint**: H04 | **优先级**: P1 | **预估**: 5h
- **依赖**: H04-02
- **实现步骤**:
  - 创建 `frontend/src/modules/v6/trace/TraceGraphCanvas.tsx`
  - Canvas 渲染 + SVG overlay 交互层
  - 分层布局: 按 node_type 分 6 层 (block → material → ndt → car → evidence → compliance)
  - 节点: 圆角矩形 + label + node_type 颜色编码
  - 边: 带箭头有向线 + edge_type 标签
  - 缩放 + 拖拽
  - 数据源: dtHardeningApi.traceQuery()
- **验证**: Canvas 渲染正确，节点和边可见

#### Task-H04-04: 实现节点点击高亮上下游路径
- **Sprint**: H04 | **优先级**: P1 | **预估**: 3h
- **依赖**: H04-03
- **实现步骤**:
  - 节点点击事件 → 调用 impactAnalysis + dependencyQuery
  - 高亮: 上游节点蓝色边框，下游节点橙色边框
  - 非相关节点灰色半透明
  - 高亮边加粗
- **验证**: 点击节点后上下游路径高亮

#### Task-H04-05: 实现 TraceNodeDetailPanel + IdentityAlignmentView
- **Sprint**: H04 | **优先级**: P1 | **预估**: 3h
- **依赖**: H04-04
- **实现步骤**:
  - 创建 `TraceNodeDetailPanel.tsx` — 右侧面板展示节点详情
  - 创建 `IdentityAlignmentView.tsx` — 展示 Identity 跨域映射
    - 4 列: Block | Material | Quality | Certification
    - 每列显示该域的 domain_id
    - 空域显示 "—"
- **验证**: 节点详情和 Identity 对齐视图正确

#### Task-H04-06: 实现 ImpactAnalysisView (变更传播视图)
- **Sprint**: H04 | **优先级**: P1 | **预估**: 3h
- **依赖**: H04-03
- **实现步骤**:
  - 创建 `ImpactAnalysisView.tsx`
  - 选择起始节点 → 调用 impactAnalysis API
  - 颜色编码: direct=红色, indirect=橙色, 未受影响=灰色
  - 列表展示: 直接影响 / 间接影响 分组
- **验证**: 变更传播视图正确

#### Task-H04-07: 实现 TraceSearchBar
- **Sprint**: H04 | **优先级**: P1 | **预估**: 1.5h
- **依赖**: H04-03
- **实现步骤**:
  - 创建 `TraceSearchBar.tsx`
  - node_type 下拉选择 (block/material_lot/ndt_record/car/evidence/compliance)
  - label 搜索输入
  - 搜索结果列表 → 点击跳转到对应节点
- **验证**: 搜索过滤功能正常

#### Task-H04-08: 组装 TraceAnalysisPage 主页面
- **Sprint**: H04 | **优先级**: P1 | **预估**: 2h
- **依赖**: H04-03~07
- **实现步骤**:
  - 创建 `frontend/src/modules/v6/TraceAnalysisPage.tsx`
  - 布局: 顶部 TraceSearchBar, 左侧 TraceGraphCanvas, 右侧 TraceNodeDetailPanel + IdentityAlignmentView
  - 底部 ImpactAnalysisView (可折叠)
  - 添加路由: `/v6/trace-analysis`
  - 编辑 App.tsx 添加路由
- **验证**: 页面渲染无报错

#### Task-H04-09: 前端 Docker 构建 + 远程部署 + E2E 验证
- **Sprint**: H04 | **优先级**: P1 | **预估**: 2h
- **依赖**: H04-08
- **实现步骤**:
  - 重建前端 Docker 镜像
  - 重启 frontend 容器
  - 浏览器验证:
    - http://8.210.239.214/v6/trace-analysis → Trace Graph Canvas 渲染
    - 点击 B737-MAIN-WING 节点 → 上下游高亮
    - Identity 面板显示跨域映射
    - Impact Analysis 视图正确
  - 端到端验证: TraceQuery("B737-MAIN-WING") → 全链路路径可视化
- **验证**: A+ 级验收通过

---

## 最终验证: 端到端验收场景

| 步骤 | 操作 | 预期结果 | 验收级别 |
|------|------|----------|----------|
| 1 | `GET /dt/event-contracts` | 返回 6 个事件契约 | PASS |
| 2 | `POST /dt/material-lots` | schema 验证通过 + 事件发布 | PASS |
| 3 | `GET /dt/identities` | Identity 列表 | PASS |
| 4 | `GET /dt/identities/by-domain/material_lot/AL-2024-002` | Block + Material 共享 Identity | PASS |
| 5 | `GET /dt/trace/query?start_node_id={id}` | 全链路遍历结果 | PASS |
| 6 | `POST /dt/trace/rebuild` | 重建成功 | PASS |
| 7 | `GET /dt/trace/impact/{id}` | 影响分析 direct + indirect | A |
| 8 | `GET /dt/trace/dependencies/{id}` | 依赖查询 | A |
| 9 | `GET /dt/trace/statistics` | 统计数据 | A |
| 10 | `GET /dt/event-contracts/MaterialLotCreated` | 单个契约详情 | A |
| 11 | React /v6/trace-analysis | 交互式依赖图 | A+ |
| 12 | 点击节点高亮上下游 | 蓝色/橙色边框 | A+ |
| 13 | Identity 跨域对齐视图 | 4 域映射 | A+ |
| 14 | Impact Analysis View | 红/橙/灰颜色编码 | A+ |

---

## 任务统计

| Sprint | 任务数 | 优先级 | 预估总工时 |
|--------|--------|--------|-----------|
| H01 (Event Contract Layer) | 9 | P0 | 14.5h |
| H02 (Identity Unification) | 10 | P0 | 17.5h |
| H03 (Trace Graph Model) | 12 | P0 | 22.5h |
| H04 (Trace Analysis UI) | 9 | P1 | 21.5h |
| **总计** | **40** | — | **76h** |