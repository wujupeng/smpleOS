# AeroForge-X EV-4.6 Digital Thread Hardening — 技术架构设计文档

**项目**: AeroForge-X v6.0 "Project Valkyrie"  
**Sprint**: EV-4.6 Digital Thread Hardening Sprint  
**目标 TRL**: 6.5 → 7.0  
**日期**: 2026-06-22  
**状态**: DRAFT  
**关联需求文档**: `ev4.6-digital-thread-hardening-spec.md`  
**关联架构文档**: `ev4.5-digital-thread-design.md`  
**前置基线**: EV-4.5 Digital Thread Foundation（PASS 级验收通过，Material/Quality/Certification Thread 闭环运行）

---

# 1. 实现模型

## 1.1 上下文视图

EV-4.6 Digital Thread Hardening 在 EV-4.5 已建立的 Digital Thread CRUD + Trace UI 基础之上，进行三维度结构化加固——事件契约治理（Event Contract Layer）、身份统一（Identity Unification Layer）、追溯图模型（Trace Graph Model）——将系统从"数据贯通阶段"升级为"语义图谱阶段"。所有新代码在 `aircraft-core-service` 内扩展，不新增微服务或数据库。

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                    AeroForge-X EV-4.6 Digital Thread Hardening                    │
│                                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                    Aircraft Core Service (FastAPI)                          │  │
│  │                                                                             │  │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │  │
│  │  │                 EV-4.6 Hardening Layer (新增)                       │   │  │
│  │  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐   │   │  │
│  │  │  │Event Contract│ │  Identity    │ │  Trace Graph Model       │   │   │  │
│  │  │  │Layer         │ │  Unification │ │  (in-memory + PG)        │   │   │  │
│  │  │  │              │ │  Layer       │ │                          │   │   │  │
│  │  │  │• Schema Reg. │ │• ConfigId    │ │• TraceNode / TraceEdge   │   │   │  │
│  │  │  │• Versioning  │ │• IdMapping   │ │• BFS Traversal          │   │   │  │
│  │  │  │• Validation  │ │• Auto-Map    │ │• Impact Analysis        │   │   │  │
│  │  │  │• Idempotency │ │• Reverse Qry │ │• Dependency Query       │   │   │  │
│  │  │  └──────────────┘ └──────────────┘ │• Rebuild / Cache        │   │   │  │
│  │  │                                    └──────────────────────────┘   │   │  │
│  │  └─────────────────────────────────────────────────────────────────────┘   │  │
│  │                                      │                                      │  │
│  │  ┌───────────────────────────────────▼─────────────────────────────────┐   │  │
│  │  │              EV-4.5 Foundation Layer (已有，不修改)                  │   │  │
│  │  │  Material Controller │ Quality Controller │ Certification Controller│   │  │
│  │  │  MaterialLot │ NDTRecord │ CAR │ Evidence │ ComplianceRequirement  │   │  │
│  │  │  MaterialLotRepo │ NDTRepo │ CARRepo │ EvidenceRepo │ ComplianceRepo│  │
│  │  │  EventBus (NATS JetStream) │ ObjectStorage (MinIO/Local)           │   │  │
│  │  └────────────────────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────────────────┘  │
│         │                          │                                              │
│  ┌──────▼──────────┐  ┌────────────▼─────────────┐  ┌──────────────────────┐    │
│  │  PostgreSQL 16  │  │  NATS JetStream          │  │  React Frontend      │    │
│  │  Port 5432      │  │  Port 4222/8222          │  │  Port 80             │    │
│  │                 │  │                          │  │                      │    │
│  │  + configuration│  │  (复用，不新增 stream)    │  │  + TraceAnalysisPage │    │
│  │    _identities  │  │                          │  │  + DependencyGraph   │    │
│  │  + identity_    │  │                          │  │  + ImpactView        │    │
│  │    mappings     │  │                          │  │  + IdentityPanel     │    │
│  │  + trace_nodes  │  │                          │  │                      │    │
│  │  + trace_edges  │  │                          │  │                      │    │
│  │  + event_       │  │                          │  │                      │    │
│  │    contract_    │  │                          │  │                      │    │
│  │    versions     │  │                          │  │                      │    │
│  │  + consumer_    │  │                          │  │                      │    │
│  │    idempotency_ │  │                          │  │                      │    │
│  │    records      │  │                          │  │                      │    │
│  └─────────────────┘  └──────────────────────────┘  └──────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 系统交互关系（EV-4.6 新增）

| 交互方 | 交互通道 | 交互内容 | Sprint |
|--------|----------|----------|--------|
| Event Producer → Event Contract Layer | 进程内调用 | 发布前 schema 验证 | H01 |
| Event Contract Layer → Schema Registry | 内存 + 文件系统 | schema 查询/注册 | H01 |
| Event Contract Layer → NATS | JetStream | 验证通过后发布事件 | H01 |
| Event Consumer → Event Contract Layer | 进程内调用 | 幂等消费检查 | H01 |
| Domain Controller → Identity Layer | 进程内调用 | resolve_or_create_identity | H02 |
| Identity Layer → PostgreSQL | SQL | identity + mapping CRUD | H02 |
| Domain Controller → Trace Graph | 进程内调用 | create_node / create_edge | H03 |
| Trace Graph → PostgreSQL | SQL | node/edge 持久化 + BFS 查询 | H03 |
| Trace Graph → In-Memory Cache | dict | 邻接表缓存 | H03 |
| React Frontend → Trace Graph API | HTTP | 依赖图/影响分析查询 | H04 |
| React Frontend → Identity API | HTTP | 跨域身份对齐查询 | H04 |

## 1.2 服务/组件总体架构

### 1.2.1 新增代码在 aircraft-core-service 中的目录结构

```
services/aircraft-core-service/src/
├── api/v6/
│   ├── configuration_controller.py          # [已有] 不修改
│   ├── material_controller.py               # [修改] 注入 Event Contract 验证 + Identity + Trace Graph
│   ├── quality_controller.py                # [修改] 注入 Event Contract 验证 + Identity + Trace Graph
│   ├── dt_certification_controller.py       # [修改] 注入 Event Contract 验证 + Identity + Trace Graph
│   ├── event_contract_controller.py         # [新增] Schema Registry API
│   ├── identity_controller.py               # [新增] Identity Query API
│   └── trace_graph_controller.py            # [新增] Trace Graph API
├── domain/
│   ├── events/
│   │   ├── material_lot_created_event.py    # [已有] 不修改
│   │   ├── ndt_completed_event.py           # [已有] 不修改
│   │   ├── car_created_event.py             # [已有] 不修改
│   │   ├── car_closed_event.py              # [已有] 不修改
│   │   └── evidence_uploaded_event.py       # [已有] 不修改
│   └── models/                              # [新增]
│       ├── material_lot.py                  # [已有] 不修改
│       ├── ndt_record.py                    # [已有] 不修改
│       ├── corrective_action_request.py     # [已有] 不修改
│       ├── compliance_requirement.py        # [已有] 不修改
│       ├── evidence.py                      # [已有] 不修改
│       ├── configuration_identity.py        # [新增] ConfigurationIdentity dataclass
│       ├── identity_mapping.py              # [新增] IdentityMapping dataclass
│       ├── trace_node.py                    # [新增] TraceNode dataclass
│       └── trace_edge.py                    # [新增] TraceEdge dataclass
├── infrastructure/
│   ├── database.py                          # [已有] 不修改
│   ├── event_bus.py                         # [已有] 不修改
│   ├── repositories/
│   │   ├── material_lot_repository.py       # [已有] 不修改
│   │   ├── ndt_record_repository.py         # [已有] 不修改
│   │   ├── car_repository.py                # [已有] 不修改
│   │   ├── evidence_repository.py           # [已有] 不修改
│   │   ├── compliance_repository.py         # [已有] 不修改
│   │   ├── configuration_identity_repository.py  # [新增]
│   │   ├── identity_mapping_repository.py        # [新增]
│   │   ├── trace_node_repository.py              # [新增]
│   │   ├── trace_edge_repository.py              # [新增]
│   │   ├── event_contract_repository.py          # [新增]
│   │   └── consumer_idempotency_repository.py    # [新增]
│   └── services/                            # [新增目录]
│       ├── event_contract_service.py        # [新增] Schema Registry + 验证 + 幂等
│       ├── identity_service.py              # [新增] Identity 解析/创建/映射
│       └── trace_graph_service.py           # [新增] Graph CRUD + BFS + Impact + Cache
└── main.py                                  # [修改] 注册新 router + 启动时加载 schema

event-contract/                              # [新增目录]
├── schema/
│   ├── MaterialLotCreated.json
│   ├── NDTCompleted.json
│   ├── CARCreated.json
│   ├── CARClosed.json
│   ├── EvidenceUploaded.json
│   └── ConfigurationChanged.json
└── versioning/
    └── version-manifest.json

frontend/src/
├── api/
│   ├── v6Api.ts                             # [修改] 新增 event-contract / identity / trace-graph API
│   └── types.ts                             # [修改] 新增 TypeScript 类型
└── modules/v6/
    ├── QualityTracePage.tsx                 # [已有] 不修改
    ├── MaterialTracePage.tsx                # [已有] 不修改
    ├── CertificationTracePage.tsx           # [已有] 不修改
    ├── ConfigurationTracePage.tsx           # [已有] 不修改
    └── TraceAnalysisPage.tsx                # [新增] 依赖图 + 影响分析 + 变更传播视图

deploy/migrations/v6_6/                      # [新增目录]
└── 009_digital_thread_hardening_tables.sql  # DDL migration
```

### 1.2.2 架构分层与职责

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         API Layer (Controllers)                              │
│  FastAPI APIRouter(prefix="/api/v6/aircraft-core/dt")                       │
│  职责: HTTP 请求解析、Pydantic 校验、调用 Service、返回响应                  │
│  新增: event_contract_controller / identity_controller / trace_graph_controller │
├─────────────────────────────────────────────────────────────────────────────┤
│                       Service Layer (业务编排)                               │
│  module-level 单例实例化                                                     │
│  职责: 编排 Domain Model + Repository + Infrastructure                      │
│  新增: EventContractService / IdentityService / TraceGraphService            │
│  修改: material_controller / quality_controller / dt_certification_controller │
│        在业务流程中注入 Event Contract 验证 + Identity 解析 + Trace Graph 写入 │
├─────────────────────────────────────────────────────────────────────────────┤
│                     Domain Layer (Models)                                    │
│  dataclass + to_dict() 模式                                                  │
│  职责: 业务实体定义、业务规则校验                                             │
│  新增: ConfigurationIdentity / IdentityMapping / TraceNode / TraceEdge       │
├─────────────────────────────────────────────────────────────────────────────┤
│                   Repository Layer (Persistence)                             │
│  AsyncpgRepository 基类 + asyncpg Pool                                       │
│  职责: PostgreSQL CRUD、SQL 构建、事务管理                                   │
│  新增: ConfigIdentityRepo / IdMappingRepo / TraceNodeRepo / TraceEdgeRepo    │
│        EventContractRepo / ConsumerIdempotencyRepo                           │
├─────────────────────────────────────────────────────────────────────────────┤
│               Infrastructure Layer (已有，不修改)                             │
│  EventBus (NATS JetStream) │ ObjectStorage (MinIO/Local)                     │
│  职责: 基础设施客户端封装、连接管理、错误处理                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2.3 关键设计决策

| 决策编号 | 决策描述 | 理由 |
|----------|----------|------|
| HD-01 | 所有新代码在 aircraft-core-service 内扩展，不新增微服务 | 遵循 EV-4.5 架构原则，避免过度拆分 |
| HD-02 | 新增 Service Layer 编排 Event Contract / Identity / Trace Graph | Controller 仅做 HTTP 解析，业务编排逻辑下沉到 Service |
| HD-03 | Domain Model 使用 `dataclass + to_dict()` 模式 | 与 EV-4.5 MaterialLot / NDTRecord 等保持一致 |
| HD-04 | Event Contract schema 存储为文件系统 JSON + 内存 registry | 文件系统保证可审计，内存 registry 保证查询性能 |
| HD-05 | Event Contract 版本信息持久化到 PostgreSQL | 版本变更是关键业务事件，需要持久化和审计 |
| HD-06 | Consumer Idempotency 使用 PostgreSQL UPSERT | 利用数据库唯一约束保证幂等，不引入 Redis |
| HD-07 | ConfigurationIdentity 使用 UUID 作为 identity_id | 全局唯一、无业务含义、适合跨域映射 |
| HD-08 | Identity Mapping 使用 UPSERT 策略 | 防止并发创建重复映射（DH-NFR-09） |
| HD-09 | Trace Graph 使用 PostgreSQL relational + in-memory cache | 禁止引入 Neo4j，relational 保证持久化，cache 保证遍历性能 |
| HD-10 | Trace Graph in-memory cache 使用邻接表 `dict[str, list[TraceEdge]]` | BFS 遍历 O(V+E) 时间复杂度，满足 DH-NFR-01 |
| HD-11 | Trace Graph Rebuild 为管理级 API，不暴露到前端 | DH-NFR-13 安全约束 |
| HD-12 | 事件发布前 schema 验证失败不阻断业务请求 | fire-and-forget 模式，记录 ERROR 日志但不影响 HTTP 响应 |
| HD-13 | Trace Graph traversal 使用 visited set 防止环路 | DH-REQ-25 环路检测 |
| HD-14 | Trace Graph 遍历结果截断而非异常 | DH-NFR-10 可靠性约束，返回部分结果 + truncated_at_depth |
| HD-15 | ConfigurationIdentity 只增不删 | DH-REQ-17 不可变记录约束 |
| HD-16 | Trace Node properties 仅存储摘要信息 | DH-REQ-28 禁止项，完整数据通过域 API 查询 |
| HD-17 | 新增 API 端点使用 `/api/v6/aircraft-core/dt/` 前缀 | 与 EV-4.5 已有端点保持一致（material_controller 已使用此前缀） |
| HD-18 | React Trace Analysis UI 使用 Canvas/SVG 自定义渲染 | 不引入重型图形库，保持轻量可控 |
| HD-19 | Event Contract v1.0.0 schema 与 EV-4.5 已有事件 payload 完全兼容 | DH-NFR-21 向后兼容约束 |

---

# 2. 接口设计

## 2.1 总体设计

所有新增 API 端点统一使用 `/api/v6/aircraft-core/dt` 前缀（与 EV-4.5 material_controller/quality_controller 保持一致），遵循 RESTful 风格。请求体使用 Pydantic V2 模型校验，响应体为 JSON。

### API 端点总览

| 方法 | 路径 | 描述 | Sprint |
|------|------|------|--------|
| GET | `/api/v6/aircraft-core/dt/event-contracts` | 查询所有事件契约 | H01 |
| GET | `/api/v6/aircraft-core/dt/event-contracts/{event_type}` | 查询单个事件契约 | H01 |
| GET | `/api/v6/aircraft-core/dt/identities` | 查询 ConfigurationIdentity 列表 | H02 |
| GET | `/api/v6/aircraft-core/dt/identities/{identity_id}` | 查询指定 Identity 及映射 | H02 |
| GET | `/api/v6/aircraft-core/dt/identities/by-domain` | 通过域记录反查 Identity | H02 |
| GET | `/api/v6/aircraft-core/dt/trace-graph/query` | TraceQuery 全链路遍历 | H03 |
| GET | `/api/v6/aircraft-core/dt/trace-graph/impact` | Impact Analysis 影响分析 | H03 |
| GET | `/api/v6/aircraft-core/dt/trace-graph/dependencies` | Dependency Query 依赖查询 | H03 |
| GET | `/api/v6/aircraft-core/dt/trace-graph/nodes/{node_id}` | 查询 Trace Node 详情 | H03 |
| GET | `/api/v6/aircraft-core/dt/trace-graph/stats` | Trace Graph 统计 | H03 |
| POST | `/api/v6/aircraft-core/dt/trace-graph/rebuild` | 从 PostgreSQL 重建图模型 | H03 |

## 2.2 接口清单

### 2.2.1 Sprint-H01: Event Contract Layer API

#### GET /api/v6/aircraft-core/dt/event-contracts

**查询参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| 无 | — | — | — |

**响应体** (200 OK):

```python
class EventContractSummary(BaseModel):
    event_type: str          # 如 "MaterialLotCreated"
    version: str             # 如 "1.0.0"
    breaking_change: bool    # 是否为 breaking change
    schema_url: str          # 如 "/api/v6/aircraft-core/dt/event-contracts/MaterialLotCreated"

class EventContractListResponse(BaseModel):
    contracts: list[EventContractSummary]
    total: int
```

**业务逻辑**:
1. 从内存 Schema Registry 查询所有已注册事件契约
2. 从 event_contract_versions 表查询每个事件类型的当前版本
3. 组装返回列表

---

#### GET /api/v6/aircraft-core/dt/event-contracts/{event_type}

**路径参数**:

| 参数 | 类型 | 描述 |
|------|------|------|
| event_type | str | 事件类型名称，如 "MaterialLotCreated" |

**响应体** (200 OK):

```python
class EventContractDetailResponse(BaseModel):
    event_type: str
    version: str
    breaking_change: bool
    schema: dict              # 完整 JSON Schema 对象
```

**异常**:
- 404: Event contract not found

---

### 2.2.2 Sprint-H02: Identity Unification Layer API

#### GET /api/v6/aircraft-core/dt/identities

**查询参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| domain | str | 否 | 按域类型过滤，如 "material_lot" |
| limit | int | 否 | 默认 100 |
| offset | int | 否 | 默认 0 |

**响应体** (200 OK):

```python
class IdentitySummaryResponse(BaseModel):
    identity_id: str
    created_at: str
    mapping_count: int
    domains: list[str]        # 如 ["block", "material_lot"]

class IdentityListResponse(BaseModel):
    identities: list[IdentitySummaryResponse]
    total: int
```

**业务逻辑**:
1. 若指定 domain 参数，查询 identity_mappings 表中包含该 domain 的 identity_id
2. 否则查询所有 configuration_identities
3. 对每个 identity 统计 mapping_count 和 domains

---

#### GET /api/v6/aircraft-core/dt/identities/{identity_id}

**路径参数**:

| 参数 | 类型 | 描述 |
|------|------|------|
| identity_id | str | ConfigurationIdentity UUID |

**响应体** (200 OK):

```python
class DomainMappingEntry(BaseModel):
    domain: str               # "block" / "material_lot" / "ndt_record" / "car" / "evidence" / "compliance_requirement"
    domain_id: str            # 域记录主键值
    mapped_at: str

class ConfigurationIdentityResponse(BaseModel):
    identity_id: str
    created_at: str
    updated_at: str
    mappings: list[DomainMappingEntry]
```

**异常**:
- 404: ConfigurationIdentity not found

---

#### GET /api/v6/aircraft-core/dt/identities/by-domain

**查询参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| domain | str | 是 | 域类型，如 "material_lot" |
| domain_id | str | 是 | 域记录主键值，如 "AL-2024-001" |

**响应体** (200 OK): `ConfigurationIdentityResponse`

**异常**:
- 404: No identity mapping found for domain record

---

### 2.2.3 Sprint-H03: Trace Graph Model API

#### GET /api/v6/aircraft-core/dt/trace-graph/query

**查询参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| root | str | 是 | 起点节点 ID，如 "B737-MAIN-WING" |
| direction | str | 否 | 遍历方向 "outgoing"(默认) / "incoming" / "both" |
| max_depth | int | 否 | 最大遍历深度，默认 10 |
| edge_types | str | 否 | 过滤边类型，逗号分隔，如 "USES_MATERIAL,TESTED_BY" |

**响应体** (200 OK):

```python
class TraceNodeResponse(BaseModel):
    node_id: str
    node_type: str
    label: str
    properties: dict | None
    identity_id: str | None

class TraceEdgeResponse(BaseModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: str
    properties: dict | None

class TraceQueryResponse(BaseModel):
    root_node_id: str
    nodes: list[TraceNodeResponse]
    edges: list[TraceEdgeResponse]
    truncated_at_depth: int | None     # 若截断，标注截断深度
    total_nodes: int
    total_edges: int
```

**业务逻辑**:
1. 查询 root 节点是否存在（不存在返回 404）
2. 从 in-memory cache 执行 BFS 遍历（cache miss 时从 PostgreSQL 加载）
3. 遍历过程中维护 visited set 防止环路
4. 超过 max_depth 时截断，设置 truncated_at_depth
5. 组装 nodes + edges 返回

**异常**:
- 404: Trace node not found

---

#### GET /api/v6/aircraft-core/dt/trace-graph/impact

**查询参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| node_id | str | 是 | 分析起点节点 ID |
| max_depth | int | 否 | 最大遍历深度，默认 5 |

**响应体** (200 OK):

```python
class ImpactedNodeEntry(BaseModel):
    node_id: str
    node_type: str
    label: str
    impact_level: str          # "direct" / "indirect"
    depth: int                 # 距离起点节点的跳数
    properties: dict | None

class ImpactAnalysisResponse(BaseModel):
    source_node_id: str
    impacted_nodes: list[ImpactedNodeEntry]
    total_impacted: int
    truncated_at_depth: int | None
```

**业务逻辑**:
1. 从指定节点出发，沿 outgoing 方向 BFS 遍历
2. depth=1 的节点标记为 "direct"，depth>1 标记为 "indirect"
3. 维护 visited set 防止环路
4. 超过 max_depth 截断

---

#### GET /api/v6/aircraft-core/dt/trace-graph/dependencies

**查询参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| node_id | str | 是 | 查询起点节点 ID |
| max_depth | int | 否 | 最大遍历深度，默认 10 |

**响应体** (200 OK):

```python
class DependencyNodeEntry(BaseModel):
    node_id: str
    node_type: str
    label: str
    depth: int
    properties: dict | None

class DependencyQueryResponse(BaseModel):
    target_node_id: str
    dependencies: list[DependencyNodeEntry]
    total_dependencies: int
    truncated_at_depth: int | None
```

**业务逻辑**:
1. 从指定节点出发，沿 incoming 方向 BFS 遍历
2. 维护 visited set 防止环路
3. 超过 max_depth 截断

---

#### GET /api/v6/aircraft-core/dt/trace-graph/nodes/{node_id}

**路径参数**:

| 参数 | 类型 | 描述 |
|------|------|------|
| node_id | str | Trace Node ID |

**响应体** (200 OK):

```python
class TraceNodeDetailResponse(BaseModel):
    node_id: str
    node_type: str
    label: str
    properties: dict | None
    identity_id: str | None
    created_at: str
    updated_at: str
    incoming_edges: list[TraceEdgeResponse]
    outgoing_edges: list[TraceEdgeResponse]
```

**异常**:
- 404: Trace node not found

---

#### GET /api/v6/aircraft-core/dt/trace-graph/stats

**响应体** (200 OK):

```python
class TraceGraphStatsResponse(BaseModel):
    node_count: int
    edge_count: int
    node_types: dict[str, int]    # 如 {"block": 3, "material_lot": 5, ...}
```

---

#### POST /api/v6/aircraft-core/dt/trace-graph/rebuild

**请求体**: 无

**响应体** (200 OK):

```python
class TraceGraphRebuildResponse(BaseModel):
    node_count: int
    edge_count: int
    rebuild_duration_ms: int
```

**业务逻辑**:
1. 在事务中 TRUNCATE trace_nodes + trace_edges
2. 从 dt_material_lots / dt_ndt_records / dt_corrective_actions / dt_evidences / dt_compliance_requirements / block_configurations 扫描所有域记录
3. 为每条域记录 INSERT trace_nodes
4. 根据 block_materials / ndt_records.material_lot_id / corrective_actions.ndt_record_id / compliance_evidences 关联关系 INSERT trace_edges
5. 重建 in-memory cache
6. 返回 node_count + edge_count

---

# 3. Event Contract Layer 设计

## 3.1 Schema 存储格式

### 3.1.1 文件系统存储

Schema 文件以 JSON Schema Draft 2020-12 格式存储在 `event-contract/schema/` 目录，每个事件类型一个文件：

```
event-contract/schema/
├── MaterialLotCreated.json
├── NDTCompleted.json
├── CARCreated.json
├── CARClosed.json
├── EvidenceUploaded.json
└── ConfigurationChanged.json
```

每个 schema 文件遵循以下模板（以 MaterialLotCreated 为例）：

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "aeroforge://events/MaterialLotCreated",
  "title": "MaterialLotCreated",
  "description": "Event emitted when a new material lot is created",
  "type": "object",
  "properties": {
    "event_id": { "type": "string", "format": "uuid" },
    "event_type": { "type": "string", "const": "MaterialLotCreated" },
    "lot_id": { "type": "string" },
    "material_code": { "type": "string" },
    "supplier_id": { "type": "string" },
    "block_id": { "type": "string" },
    "timestamp": { "type": "string", "format": "date-time" }
  },
  "required": ["event_id", "event_type", "lot_id", "material_code", "supplier_id", "timestamp"],
  "additionalProperties": false,
  "x-version": "1.0.0"
}
```

**关键约束**:
- v1.0.0 schema 与 EV-4.5 已有 Pydantic 事件类字段完全兼容（DH-NFR-21）
- `additionalProperties: false` 确保事件 payload 严格匹配 schema
- `x-version` 自定义扩展字段记录语义化版本号

### 3.1.2 内存 Registry

系统启动时将所有 schema 文件加载到内存 `dict[str, dict]`，key 为 event_type，value 为完整 JSON Schema dict。

```python
class SchemaRegistry:
    """内存 Schema Registry，启动时从文件系统加载"""
    
    def __init__(self):
        self._schemas: dict[str, dict] = {}     # event_type → JSON Schema dict
        self._validators: dict[str, ...] = {}    # event_type → jsonschema validator
    
    def load_from_directory(self, schema_dir: str) -> int:
        """从目录加载所有 schema 文件，返回加载数量"""
        
    def get_schema(self, event_type: str) -> dict | None:
        """查询指定事件类型的 schema"""
        
    def validate(self, event_type: str, payload: dict) -> tuple[bool, str]:
        """验证 payload 是否符合 schema，返回 (is_valid, error_message)"""
        
    def list_contracts(self) -> list[str]:
        """列出所有已注册事件类型"""
```

## 3.2 版本管理策略

### 3.2.1 语义化版本号

版本号格式: `major.minor.patch`

| 变更类型 | 版本变更 | 规则 |
|----------|----------|------|
| Breaking change | major+1, minor=0, patch=0 | 删除必填字段、修改字段类型、重命名字段 |
| Backward-compatible 新增 | minor+1, patch=0 | 新增可选字段（必须有默认值）、新增 additionalProperties |
| 文档修正 | patch+1 | 修改 description、examples，不改变 schema 结构 |

### 3.2.2 Version Manifest 文件

`event-contract/versioning/version-manifest.json` 记录所有事件契约的当前版本：

```json
{
  "version_manifest": {
    "MaterialLotCreated": { "version": "1.0.0", "breaking_change": false },
    "NDTCompleted": { "version": "1.0.0", "breaking_change": false },
    "CARCreated": { "version": "1.0.0", "breaking_change": false },
    "CARClosed": { "version": "1.0.0", "breaking_change": false },
    "EvidenceUploaded": { "version": "1.0.0", "breaking_change": false },
    "ConfigurationChanged": { "version": "1.0.0", "breaking_change": false }
  },
  "last_updated": "2026-06-22T00:00:00Z"
}
```

### 3.2.3 版本持久化

版本信息同时持久化到 PostgreSQL `event_contract_versions` 表，确保版本变更有审计记录。文件系统 manifest 为启动时加载的初始值，运行时版本变更通过 API 写入数据库。

## 3.3 Schema Registry API

见 2.2.1 节接口清单。API 端点：
- `GET /dt/event-contracts` — 列表查询
- `GET /dt/event-contracts/{event_type}` — 单事件查询

## 3.4 事件发布前 Schema 验证流程

```
┌─────────────────────────────────────────────────────────────────┐
│                  Event Publish Validation Flow                    │
│                                                                  │
│  Controller 调用 event_bus.publish_jetstream()                   │
│       │                                                          │
│       ▼                                                          │
│  EventContractService.validate_before_publish(event_type, data)  │
│       │                                                          │
│       ├── SchemaRegistry.get_schema(event_type)                  │
│       │       │                                                  │
│       │       ├── Schema 存在?                                   │
│       │       │   ├── Yes → jsonschema.validate(data, schema)    │
│       │       │   │       ├── Valid → 继续发布                   │
│       │       │   │       └── Invalid → 记录 ERROR 日志         │
│       │       │   │               + 继续发布（fire-and-forget）   │
│       │       │   └── No → 记录 WARNING 日志 + 继续发布          │
│       │       │                                                  │
│       ▼                                                          │
│  event_bus.publish_jetstream(subject, data)                      │
│       │                                                          │
│       └── 发布成功/失败（降级为 no-op）                           │
└─────────────────────────────────────────────────────────────────┘
```

**关键设计**:
- 验证失败不阻断业务请求（fire-and-forget 模式）
- Schema 缺失时跳过验证，仅记录 WARNING
- 验证结果记录结构化 JSON 日志（DH-NFR-14）

## 3.5 Consumer Idempotency Key 设计

### 3.5.1 幂等键生成规则

```
idempotency_key = SHA256(event_id + ":" + consumer_id)
```

- `event_id`: 事件 payload 中的 event_id 字段（UUID）
- `consumer_id`: 消费方标识字符串（如 "quality-service" / "cert-service"）

### 3.5.2 幂等消费流程

```
┌──────────────────────────────────────────────────────────────┐
│              Consumer Idempotency Check Flow                  │
│                                                              │
│  Consumer 收到事件                                            │
│       │                                                      │
│       ▼                                                      │
│  EventContractService.check_idempotency(event_id, consumer_id)│
│       │                                                      │
│       ├── INSERT INTO consumer_idempotency_records            │
│       │   (event_id, consumer_id, consumed_at)                │
│       │   ON CONFLICT (event_id, consumer_id) DO NOTHING      │
│       │                                                      │
│       ├── INSERT 成功（首次消费）                              │
│       │   └── 执行业务回调                                    │
│       │                                                      │
│       └── INSERT 冲突（重复消费）                              │
│           └── 记录 WARNING "Idempotent consumption detected"  │
│               + 跳过业务回调                                   │
└──────────────────────────────────────────────────────────────┘
```

### 3.5.3 EventContractService 接口

```python
class EventContractService:
    """事件契约治理服务"""
    
    def __init__(self, registry: SchemaRegistry, contract_repo: EventContractRepository, 
                 idempotency_repo: ConsumerIdempotencyRepository):
        self._registry = registry
        self._contract_repo = contract_repo
        self._idempotency_repo = idempotency_repo
    
    async def validate_before_publish(self, event_type: str, payload: dict) -> None:
        """发布前 schema 验证，验证失败记录 ERROR 但不抛异常"""
    
    async def check_idempotency(self, event_id: str, consumer_id: str) -> bool:
        """检查消费幂等性，返回 True=首次消费 / False=重复消费"""
    
    async def get_all_contracts(self) -> list[EventContractSummary]:
        """查询所有事件契约"""
    
    async def get_contract(self, event_type: str) -> EventContractDetailResponse | None:
        """查询单个事件契约"""
```

---

# 4. Identity Unification Layer 设计

## 4.1 ConfigurationIdentity Dataclass

```python
@dataclass
class ConfigurationIdentity:
    identity_id: str = ""          # UUID，系统自动生成
    created_at: str = ""           # ISO 8601
    updated_at: str = ""           # ISO 8601

    def to_dict(self) -> dict:
        return {
            "identity_id": self.identity_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_row(cls, row) -> ConfigurationIdentity:
        return cls(
            identity_id=str(row["identity_id"]),
            created_at=row["created_at"].isoformat() if row.get("created_at") else "",
            updated_at=row["updated_at"].isoformat() if row.get("updated_at") else "",
        )


@dataclass
class IdentityMapping:
    mapping_id: str = ""           # UUID，系统自动生成
    identity_id: str = ""          # FK → configuration_identities.identity_id
    domain: str = ""               # "block" / "material_lot" / "ndt_record" / "car" / "evidence" / "compliance_requirement"
    domain_id: str = ""            # 域记录主键值
    mapped_at: str = ""            # ISO 8601

    def to_dict(self) -> dict:
        return {
            "mapping_id": self.mapping_id,
            "identity_id": self.identity_id,
            "domain": self.domain,
            "domain_id": self.domain_id,
            "mapped_at": self.mapped_at,
        }

    @classmethod
    def from_row(cls, row) -> IdentityMapping:
        return cls(
            mapping_id=str(row["mapping_id"]),
            identity_id=str(row["identity_id"]),
            domain=row["domain"],
            domain_id=row["domain_id"],
            mapped_at=row["mapped_at"].isoformat() if row.get("mapped_at") else "",
        )
```

## 4.2 IdentityMapping 表设计

见第 7 节数据库 Schema 设计。

## 4.3 自动关联流程

### 4.3.1 域记录创建时的 Identity 解析逻辑

```
┌────────────────────────────────────────────────────────────────────┐
│              Identity Resolution on Domain Record Creation          │
│                                                                    │
│  Controller 收到创建请求 (如 POST /material-lots, block_id=X)      │
│       │                                                            │
│       ▼                                                            │
│  IdentityService.resolve_or_create_identity(context)               │
│       │                                                            │
│       ├── context 包含关联信息?                                     │
│       │   (如 block_id / material_lot_id / ndt_record_id)          │
│       │                                                            │
│       │   ├── Yes → 查询关联域记录的 Identity                       │
│       │   │       │                                                │
│       │   │       ├── 关联域已有 Identity?                          │
│       │   │       │   ├── Yes → 复用该 identity_id                 │
│       │   │       │   └── No  → 创建新 ConfigurationIdentity       │
│       │   │       │           + 映射关联域记录到新 Identity          │
│       │   │       │           + 映射当前域记录到新 Identity          │
│       │   │                                                        │
│       │   └── No  → 创建独立 ConfigurationIdentity                 │
│       │           + 映射当前域记录到新 Identity                      │
│       │                                                            │
│       ▼                                                            │
│  返回 identity_id → Controller 继续业务流程                         │
└────────────────────────────────────────────────────────────────────┘
```

### 4.3.2 各域记录的 Identity 解析规则

| 域记录 | 关联字段 | Identity 解析规则 |
|--------|----------|-------------------|
| MaterialLot | block_id | 若 block_id 存在，查找 Block 的 Identity；若 Block 无 Identity 则创建新 Identity 并同时映射 Block 和 MaterialLot |
| NDTRecord | material_lot_id | 查找 MaterialLot 的 Identity，将 NDTRecord 映射到同一 Identity |
| CAR | ndt_record_id | 查找 NDTRecord 的 Identity，将 CAR 映射到同一 Identity |
| Evidence | requirement_id | 查找 ComplianceRequirement 的 Identity，将 Evidence 映射到同一 Identity |
| ComplianceRequirement | — | 创建独立 Identity |
| Block | — | 创建独立 Identity |

### 4.3.3 IdentityService 接口

```python
class IdentityService:
    """身份统一服务"""
    
    def __init__(self, identity_repo: ConfigurationIdentityRepository, 
                 mapping_repo: IdentityMappingRepository):
        self._identity_repo = identity_repo
        self._mapping_repo = mapping_repo
    
    async def resolve_or_create_identity(
        self, 
        domain: str, 
        domain_id: str, 
        related_domain: str | None = None, 
        related_domain_id: str | None = None,
    ) -> str:
        """解析或创建 Identity，返回 identity_id"""
    
    async def get_identity(self, identity_id: str) -> ConfigurationIdentityResponse | None:
        """查询 Identity 及所有映射"""
    
    async def get_identity_by_domain(self, domain: str, domain_id: str) -> ConfigurationIdentityResponse | None:
        """通过域记录反查 Identity"""
    
    async def list_identities(self, domain: str | None = None, 
                              limit: int = 100, offset: int = 0) -> IdentityListResponse:
        """查询 Identity 列表"""
```

## 4.4 反查 API

见 2.2.2 节接口清单。API 端点：
- `GET /dt/identities/by-domain?domain=material_lot&domain_id=AL-2024-001` — 通过域记录反查 Identity

反查逻辑：查询 `identity_mappings` 表中 `(domain, domain_id)` 匹配的记录，获取 `identity_id`，然后查询该 Identity 的所有映射。

---

# 5. Trace Graph Model 设计

## 5.1 TraceNode / TraceEdge Dataclass

```python
@dataclass
class TraceNode:
    node_id: str = ""              # 域记录主键值（如 "B737-MAIN-WING"）
    node_type: str = ""            # "block" / "material_lot" / "ndt_record" / "car" / "evidence" / "compliance_requirement"
    label: str = ""                # 显示标签
    properties: dict | None = None # 摘要属性（如 {"status": "inspected"}）
    identity_id: str | None = None # FK → configuration_identities.identity_id
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "label": self.label,
            "properties": self.properties,
            "identity_id": self.identity_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_row(cls, row) -> TraceNode:
        return cls(
            node_id=row["node_id"],
            node_type=row["node_type"],
            label=row["label"],
            properties=json.loads(row["properties"]) if isinstance(row.get("properties"), str) else row.get("properties"),
            identity_id=str(row["identity_id"]) if row.get("identity_id") else None,
            created_at=row["created_at"].isoformat() if row.get("created_at") else "",
            updated_at=row["updated_at"].isoformat() if row.get("updated_at") else "",
        )


@dataclass
class TraceEdge:
    edge_id: str = ""              # UUID
    source_node_id: str = ""       # FK → trace_nodes.node_id
    target_node_id: str = ""       # FK → trace_nodes.node_id
    edge_type: str = ""            # "USES_MATERIAL" / "TESTED_BY" / "HAS_CAR" / "EVIDENCE_FOR" / "COMPLIANCE_FOR" / "CONTAINS_BLOCK"
    properties: dict | None = None
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "edge_type": self.edge_type,
            "properties": self.properties,
            "created_at": self.created_at,
        }

    @classmethod
    def from_row(cls, row) -> TraceEdge:
        return cls(
            edge_id=str(row["edge_id"]),
            source_node_id=row["source_node_id"],
            target_node_id=row["target_node_id"],
            edge_type=row["edge_type"],
            properties=json.loads(row["properties"]) if isinstance(row.get("properties"), str) else row.get("properties"),
            created_at=row["created_at"].isoformat() if row.get("created_at") else "",
        )
```

## 5.2 TraceNode / TraceEdge 表设计

见第 7 节数据库 Schema 设计。

## 5.3 BFS 遍历算法

### 5.3.1 算法描述

```
算法: BFS Traversal
输入: root_node_id, direction, max_depth, edge_types_filter
输出: TraceQueryResponse (nodes, edges, truncated_at_depth)

1. 初始化:
   - queue = [(root_node_id, depth=0)]
   - visited = {root_node_id}
   - result_nodes = [root_node]
   - result_edges = []

2. BFS 循环:
   WHILE queue 不为空:
     (current_id, depth) = queue.popleft()
     
     IF depth >= max_depth:
       truncated_at_depth = max_depth
       CONTINUE
     
     # 根据 direction 获取邻接边
     IF direction == "outgoing":
       edges = cache.get_outgoing_edges(current_id)
     ELIF direction == "incoming":
       edges = cache.get_incoming_edges(current_id)
     ELSE:  # "both"
       edges = cache.get_outgoing_edges(current_id) + cache.get_incoming_edges(current_id)
     
     # 按 edge_types 过滤
     IF edge_types_filter:
       edges = [e for e in edges if e.edge_type in edge_types_filter]
     
     FOR edge IN edges:
       neighbor_id = edge.target_node_id if direction != "incoming" else edge.source_node_id
       
       IF neighbor_id NOT IN visited:
         visited.add(neighbor_id)
         result_nodes.append(neighbor_node)
         result_edges.append(edge)
         queue.append((neighbor_id, depth + 1))

3. 返回 TraceQueryResponse
```

**时间复杂度**: O(V + E)，V 为节点数，E 为边数  
**空间复杂度**: O(V + E)，visited set + result

### 5.3.2 In-Memory Cache 邻接表结构

```python
class TraceGraphCache:
    """Trace Graph 内存缓存，邻接表实现"""
    
    def __init__(self):
        self._outgoing: dict[str, list[TraceEdge]] = {}  # node_id → [outgoing edges]
        self._incoming: dict[str, list[TraceEdge]] = {}   # node_id → [incoming edges]
        self._nodes: dict[str, TraceNode] = {}            # node_id → TraceNode
    
    def get_outgoing_edges(self, node_id: str) -> list[TraceEdge]:
        return self._outgoing.get(node_id, [])
    
    def get_incoming_edges(self, node_id: str) -> list[TraceEdge]:
        return self._incoming.get(node_id, [])
    
    def get_node(self, node_id: str) -> TraceNode | None:
        return self._nodes.get(node_id)
    
    def add_node(self, node: TraceNode) -> None:
        self._nodes[node.node_id] = node
        if node.node_id not in self._outgoing:
            self._outgoing[node.node_id] = []
        if node.node_id not in self._incoming:
            self._incoming[node.node_id] = []
    
    def add_edge(self, edge: TraceEdge) -> None:
        self._outgoing.setdefault(edge.source_node_id, []).append(edge)
        self._incoming.setdefault(edge.target_node_id, []).append(edge)
    
    def clear(self) -> None:
        self._outgoing.clear()
        self._incoming.clear()
        self._nodes.clear()
    
    @property
    def node_count(self) -> int:
        return len(self._nodes)
    
    @property
    def edge_count(self) -> int:
        return sum(len(edges) for edges in self._outgoing.values())
```

## 5.4 Impact Analysis 算法

### 5.4.1 算法描述

```
算法: Impact Analysis
输入: source_node_id, max_depth
输出: ImpactAnalysisResponse

1. 初始化:
   - queue = [(source_node_id, depth=0)]
   - visited = {source_node_id}
   - impacted_nodes = []

2. BFS 循环 (仅沿 outgoing 方向):
   WHILE queue 不为空:
     (current_id, depth) = queue.popleft()
     
     IF depth >= max_depth:
       truncated_at_depth = max_depth
       CONTINUE
     
     FOR edge IN cache.get_outgoing_edges(current_id):
       IF edge.target_node_id NOT IN visited:
         visited.add(edge.target_node_id)
         impact_level = "direct" if depth == 0 else "indirect"
         impacted_nodes.append(ImpactedNodeEntry(
           node_id=edge.target_node_id,
           impact_level=impact_level,
           depth=depth + 1,
         ))
         queue.append((edge.target_node_id, depth + 1))

3. 返回 ImpactAnalysisResponse
```

**说明**: Impact Analysis 本质上是 outgoing-only 的 BFS，额外标注 impact_level。

## 5.5 In-Memory Cache 策略

### 5.5.1 Cache 生命周期

```
┌──────────────────────────────────────────────────────────────┐
│                  Trace Graph Cache Lifecycle                  │
│                                                              │
│  系统启动                                                    │
│    │                                                         │
│    ├── 从 PostgreSQL 全量加载 trace_nodes + trace_edges      │
│    │   → 构建 in-memory 邻接表                               │
│    │                                                         │
│  运行时                                                      │
│    │                                                         │
│    ├── create_node() → PostgreSQL INSERT + cache.add_node()  │
│    ├── create_edge() → PostgreSQL INSERT + cache.add_edge()  │
│    ├── update_node() → PostgreSQL UPDATE + cache 更新        │
│    │                                                         │
│    ├── Cache Miss (节点不在 cache 中)                         │
│    │   → 从 PostgreSQL 加载该节点及其邻接边到 cache           │
│    │                                                         │
│    └── Rebuild (管理级操作)                                   │
│        → TRUNCATE PostgreSQL + 重建 + cache.clear() + 重建   │
│                                                              │
│  Cache 与 PostgreSQL 不一致时                                 │
│    → 不自动修复，用户手动触发 POST /trace-graph/rebuild       │
│    → 日志记录 WARNING "Cache inconsistency detected"         │
└──────────────────────────────────────────────────────────────┘
```

### 5.5.2 Cache 一致性保证

- **写路径**: 每次 create_node / create_edge / update_node 同时写 PostgreSQL 和 cache
- **读路径**: 优先从 cache 读取，cache miss 时从 PostgreSQL 加载
- **不一致检测**: 定期（可选）或 Rebuild 时比对 cache.node_count 与 PostgreSQL COUNT(*)
- **修复策略**: 仅通过 POST /trace-graph/rebuild 显式修复，不自动静默修复（DH-NFR-07）

## 5.6 Graph Rebuild 流程

```
┌──────────────────────────────────────────────────────────────────┐
│                    Trace Graph Rebuild Flow                       │
│                                                                  │
│  POST /trace-graph/rebuild                                       │
│       │                                                          │
│       ▼                                                          │
│  TraceGraphService.rebuild_from_postgresql()                     │
│       │                                                          │
│       ├── 1. cache.clear() — 清空内存缓存                        │
│       │                                                          │
│       ├── 2. BEGIN TRANSACTION                                   │
│       │       │                                                  │
│       │       ├── TRUNCATE trace_nodes, trace_edges              │
│       │       │                                                  │
│       │       ├── 扫描 block_configurations → INSERT trace_nodes │
│       │       │   (node_type="block", properties={"version": N}) │
│       │       │                                                  │
│       │       ├── 扫描 dt_material_lots → INSERT trace_nodes     │
│       │       │   (node_type="material_lot", properties={"status": S})│
│       │       │                                                  │
│       │       ├── 扫描 dt_ndt_records → INSERT trace_nodes       │
│       │       │   (node_type="ndt_record", properties={"result": R})│
│       │       │                                                  │
│       │       ├── 扫描 dt_corrective_actions → INSERT trace_nodes│
│       │       │   (node_type="car", properties={"status": S})    │
│       │       │                                                  │
│       │       ├── 扫描 dt_evidences → INSERT trace_nodes         │
│       │       │   (node_type="evidence", properties={})           │
│       │       │                                                  │
│       │       ├── 扫描 dt_compliance_requirements → INSERT trace_nodes│
│       │       │   (node_type="compliance_requirement",            │
│       │       │    properties={"compliance_status": S})           │
│       │       │                                                  │
│       │       ├── 扫描 dt_block_materials → INSERT trace_edges   │
│       │       │   (edge_type="USES_MATERIAL")                    │
│       │       │                                                  │
│       │       ├── 扫描 dt_ndt_records.material_lot_id →          │
│       │       │   INSERT trace_edges (edge_type="TESTED_BY")     │
│       │       │                                                  │
│       │       ├── 扫描 dt_corrective_actions.ndt_record_id →     │
│       │       │   INSERT trace_edges (edge_type="HAS_CAR")       │
│       │       │                                                  │
│       │       └── 扫描 dt_compliance_evidences →                  │
│       │           INSERT trace_edges (edge_type="EVIDENCE_FOR")  │
│       │                                                          │
│       ├── 3. COMMIT TRANSACTION                                  │
│       │                                                          │
│       ├── 4. 从 PostgreSQL 全量加载到 cache                      │
│       │                                                          │
│       └── 5. 返回 {node_count, edge_count, rebuild_duration_ms}  │
└──────────────────────────────────────────────────────────────────┘
```

### 5.6.1 TraceGraphService 接口

```python
class TraceGraphService:
    """追溯图模型服务"""
    
    def __init__(self, node_repo: TraceNodeRepository, edge_repo: TraceEdgeRepository,
                 cache: TraceGraphCache):
        self._node_repo = node_repo
        self._edge_repo = edge_repo
        self._cache = cache
    
    async def create_node(self, node_type: str, node_id: str, label: str, 
                          properties: dict | None = None, identity_id: str | None = None) -> TraceNode:
        """创建 Trace Node（PostgreSQL + cache）"""
    
    async def create_edge(self, source_node_id: str, target_node_id: str, 
                          edge_type: str, properties: dict | None = None) -> TraceEdge:
        """创建 Trace Edge（PostgreSQL + cache）"""
    
    async def update_node_properties(self, node_id: str, properties: dict) -> None:
        """更新 Trace Node properties（PostgreSQL + cache）"""
    
    async def traverse(self, root_node_id: str, direction: str = "outgoing", 
                       max_depth: int = 10, edge_types: list[str] | None = None) -> TraceQueryResponse:
        """BFS 遍历"""
    
    async def impact_analysis(self, node_id: str, max_depth: int = 5) -> ImpactAnalysisResponse:
        """影响分析"""
    
    async def dependency_query(self, node_id: str, max_depth: int = 10) -> DependencyQueryResponse:
        """依赖查询"""
    
    async def get_node_detail(self, node_id: str) -> TraceNodeDetailResponse | None:
        """查询节点详情"""
    
    async def get_stats(self) -> TraceGraphStatsResponse:
        """图统计"""
    
    async def rebuild(self) -> TraceGraphRebuildResponse:
        """从 PostgreSQL 重建图模型"""
```

---

# 6. Trace Analysis UI 设计

## 6.1 React 组件结构

```
frontend/src/modules/v6/
└── TraceAnalysisPage.tsx                # 主页面
    ├── TraceGraphCanvas                 # 依赖图渲染组件（Canvas/SVG）
    │   ├── TraceGraphNode               # 节点渲染
    │   └── TraceGraphEdge               # 边渲染
    ├── TraceNodeDetailPanel             # 节点详情侧面板
    │   ├── NodePropertyList             # 节点属性列表
    │   └── IdentityAlignmentView        # ConfigurationIdentity 跨域对齐视图
    ├── ImpactAnalysisView               # 变更传播视图（颜色编码）
    ├── TraceSearchBar                   # 搜索过滤栏
    └── TraceGraphToolbar                # 工具栏（Impact Analysis / Rebuild / Zoom）
```

## 6.2 依赖图渲染方案

### 6.2.1 渲染技术选择

| 方案 | 优势 | 劣势 | 选择 |
|------|------|------|------|
| SVG | DOM 事件绑定简单、可缩放 | 大量节点性能差 | ❌ |
| Canvas | 渲染性能好 | 事件处理复杂 | ✅ 主渲染 |
| SVG overlay | 交互层 + Canvas 渲染层 | 实现复杂 | ✅ 辅助 |

**最终方案**: Canvas 渲染 + SVG overlay 交互层。Canvas 负责节点/边绘制（高性能），SVG overlay 负责节点点击事件绑定（易交互）。

### 6.2.2 布局算法

使用分层布局（Hierarchical Layout），按 node_type 分层：

```
Layer 0: block
Layer 1: material_lot
Layer 2: ndt_record
Layer 3: car
Layer 4: evidence
Layer 5: compliance_requirement
```

节点在每层内水平均匀分布，层间垂直间距固定。

### 6.2.3 节点样式

| node_type | 形状 | 颜色 | 图标 |
|-----------|------|------|------|
| block | 圆角矩形 | #1890FF (蓝色) | 📦 |
| material_lot | 圆角矩形 | #52C41A (绿色) | 🔩 |
| ndt_record | 菱形 | #FAAD14 (橙色) | 🔍 |
| car | 菱形 | #FF4D4F (红色) | ⚠️ |
| evidence | 圆形 | #722ED1 (紫色) | 📄 |
| compliance_requirement | 圆形 | #13C2C2 (青色) | ✅ |

### 6.2.4 边样式

| edge_type | 线型 | 箭头 | 颜色 |
|-----------|------|------|------|
| USES_MATERIAL | 实线 | → | #52C41A |
| TESTED_BY | 实线 | → | #FAAD14 |
| HAS_CAR | 实线 | → | #FF4D4F |
| EVIDENCE_FOR | 虚线 | → | #722ED1 |
| COMPLIANCE_FOR | 虚线 | → | #13C2C2 |

## 6.3 交互设计

### 6.3.1 节点点击高亮上下游路径

```
用户点击节点 N:
  1. 获取 N 的所有 upstream 节点（沿 incoming 方向遍历）
  2. 获取 N 的所有 downstream 节点（沿 outgoing 方向遍历）
  3. 高亮路径上的所有节点和边
  4. 淡化非路径节点和边（opacity: 0.2）
  5. 侧面板展示节点详情 + Identity 信息
```

### 6.3.2 Change Propagation View

```
用户选择节点 N 并点击 "Impact Analysis":
  1. 调用 GET /trace-graph/impact?node_id=N
  2. 根据返回的 impacted_nodes 列表更新节点颜色:
     - direct impact → 红色 (#FF4D4F)
     - indirect impact → 橙色 (#FAAD14)
     - 未受影响 → 灰色 (#D9D9D9)
  3. 高亮影响路径上的边
  4. 侧面板展示影响分析结果
```

### 6.3.3 ConfigurationIdentity 跨域对齐视图

```
用户在节点详情面板点击 Identity:
  1. 调用 GET /identities/{identity_id}
  2. 展示该 Identity 关联的所有域记录:
     - Block 域: block_id
     - Material 域: lot_id
     - Quality 域: ndt_record_id, car_id
     - Certification 域: evidence_id, requirement_id
  3. 每个域记录可点击跳转到对应详情
```

### 6.3.4 截断结果 Load More

```
TraceQuery 返回 truncated_at_depth=3:
  1. 依赖图在深度 3 处显示 "..." 标识
  2. 提供 "Load More" 按钮
  3. 点击后以 max_depth=当前深度+5 重新发起 TraceQuery
  4. 合并新结果到现有图数据
```

## 6.4 API 集成

### 6.4.1 新增 TypeScript 类型

```typescript
// === Event Contract ===
export interface EventContractSummary {
  event_type: string
  version: string
  breaking_change: boolean
  schema_url: string
}

export interface EventContractDetail {
  event_type: string
  version: string
  breaking_change: boolean
  schema: Record<string, unknown>
}

// === Identity ===
export interface DomainMappingEntry {
  domain: string
  domain_id: string
  mapped_at: string
}

export interface ConfigurationIdentity {
  identity_id: string
  created_at: string
  updated_at: string
  mappings: DomainMappingEntry[]
}

export interface IdentitySummary {
  identity_id: string
  created_at: string
  mapping_count: number
  domains: string[]
}

// === Trace Graph ===
export interface TraceNodeResponse {
  node_id: string
  node_type: string
  label: string
  properties: Record<string, unknown> | null
  identity_id: string | null
}

export interface TraceEdgeResponse {
  edge_id: string
  source_node_id: string
  target_node_id: string
  edge_type: string
  properties: Record<string, unknown> | null
}

export interface TraceQueryResponse {
  root_node_id: string
  nodes: TraceNodeResponse[]
  edges: TraceEdgeResponse[]
  truncated_at_depth: number | null
  total_nodes: number
  total_edges: number
}

export interface ImpactedNodeEntry {
  node_id: string
  node_type: string
  label: string
  impact_level: 'direct' | 'indirect'
  depth: number
  properties: Record<string, unknown> | null
}

export interface ImpactAnalysisResponse {
  source_node_id: string
  impacted_nodes: ImpactedNodeEntry[]
  total_impacted: number
  truncated_at_depth: number | null
}

export interface DependencyNodeEntry {
  node_id: string
  node_type: string
  label: string
  depth: number
  properties: Record<string, unknown> | null
}

export interface DependencyQueryResponse {
  target_node_id: string
  dependencies: DependencyNodeEntry[]
  total_dependencies: number
  truncated_at_depth: number | null
}

export interface TraceNodeDetailResponse {
  node_id: string
  node_type: string
  label: string
  properties: Record<string, unknown> | null
  identity_id: string | null
  created_at: string
  updated_at: string
  incoming_edges: TraceEdgeResponse[]
  outgoing_edges: TraceEdgeResponse[]
}

export interface TraceGraphStatsResponse {
  node_count: number
  edge_count: number
  node_types: Record<string, number>
}

export interface TraceGraphRebuildResponse {
  node_count: number
  edge_count: number
  rebuild_duration_ms: number
}
```

### 6.4.2 新增 API 函数

```typescript
// v6Api.ts 新增

export const dtHardeningApi = {
  // Event Contract
  listEventContracts: () =>
    v6Client.get('/aircraft-core/dt/event-contracts'),
  
  getEventContract: (eventType: string) =>
    v6Client.get(`/aircraft-core/dt/event-contracts/${eventType}`),
  
  // Identity
  listIdentities: (domain?: string, limit = 100, offset = 0) =>
    v6Client.get('/aircraft-core/dt/identities', { params: { domain, limit, offset } }),
  
  getIdentity: (identityId: string) =>
    v6Client.get(`/aircraft-core/dt/identities/${identityId}`),
  
  getIdentityByDomain: (domain: string, domainId: string) =>
    v6Client.get('/aircraft-core/dt/identities/by-domain', { params: { domain, domain_id: domainId } }),
  
  // Trace Graph
  traceQuery: (root: string, direction = 'outgoing', maxDepth = 10, edgeTypes?: string) =>
    v6Client.get('/aircraft-core/dt/trace-graph/query', { params: { root, direction, max_depth: maxDepth, edge_types: edgeTypes } }),
  
  impactAnalysis: (nodeId: string, maxDepth = 5) =>
    v6Client.get('/aircraft-core/dt/trace-graph/impact', { params: { node_id: nodeId, max_depth: maxDepth } }),
  
  dependencyQuery: (nodeId: string, maxDepth = 10) =>
    v6Client.get('/aircraft-core/dt/trace-graph/dependencies', { params: { node_id: nodeId, max_depth: maxDepth } }),
  
  getTraceNode: (nodeId: string) =>
    v6Client.get(`/aircraft-core/dt/trace-graph/nodes/${nodeId}`),
  
  getTraceGraphStats: () =>
    v6Client.get('/aircraft-core/dt/trace-graph/stats'),
  
  rebuildTraceGraph: () =>
    v6Client.post('/aircraft-core/dt/trace-graph/rebuild'),
}
```

---

# 7. 数据库 Schema 设计

## 7.1 DDL for 新增表

```sql
-- ============================================================
-- AeroForge-X EV-4.6 Digital Thread Hardening Tables
-- Migration: 009_digital_thread_hardening_tables.sql
-- ============================================================

-- Configuration Identities (配置统一身份)
CREATE TABLE IF NOT EXISTS configuration_identities (
    identity_id        UUID           NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at         TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_configuration_identities_created_at ON configuration_identities (created_at);

-- Identity Mappings (身份映射: 1 Identity → N Domain Records)
CREATE TABLE IF NOT EXISTS identity_mappings (
    mapping_id         UUID           NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    identity_id        UUID           NOT NULL REFERENCES configuration_identities(identity_id) ON DELETE RESTRICT,
    domain             VARCHAR(32)    NOT NULL CHECK (domain IN ('block', 'material_lot', 'ndt_record', 'car', 'evidence', 'compliance_requirement')),
    domain_id          VARCHAR(128)   NOT NULL,
    mapped_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    
    -- 同一域记录只能映射到一个 ConfigurationIdentity
    CONSTRAINT uq_identity_mappings_domain UNIQUE (domain, domain_id)
);

CREATE INDEX idx_identity_mappings_identity_id ON identity_mappings (identity_id);
CREATE INDEX idx_identity_mappings_domain ON identity_mappings (domain);
CREATE INDEX idx_identity_mappings_domain_id ON identity_mappings (domain, domain_id);

-- Trace Nodes (追溯节点)
CREATE TABLE IF NOT EXISTS trace_nodes (
    node_id            VARCHAR(128)   NOT NULL PRIMARY KEY,
    node_type          VARCHAR(32)    NOT NULL CHECK (node_type IN ('block', 'material_lot', 'ndt_record', 'car', 'evidence', 'compliance_requirement')),
    label              VARCHAR(256)   NOT NULL,
    properties         JSONB          DEFAULT '{}',
    identity_id        UUID           REFERENCES configuration_identities(identity_id) ON DELETE SET NULL,
    created_at         TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_trace_nodes_node_type ON trace_nodes (node_type);
CREATE INDEX idx_trace_nodes_identity_id ON trace_nodes (identity_id);

-- Trace Edges (追溯边)
CREATE TABLE IF NOT EXISTS trace_edges (
    edge_id            UUID           NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node_id     VARCHAR(128)   NOT NULL REFERENCES trace_nodes(node_id) ON DELETE CASCADE,
    target_node_id     VARCHAR(128)   NOT NULL REFERENCES trace_nodes(node_id) ON DELETE CASCADE,
    edge_type          VARCHAR(32)    NOT NULL CHECK (edge_type IN ('USES_MATERIAL', 'TESTED_BY', 'HAS_CAR', 'EVIDENCE_FOR', 'COMPLIANCE_FOR', 'CONTAINS_BLOCK')),
    properties         JSONB          DEFAULT '{}',
    created_at         TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    
    -- 同一对节点之间同类型边只允许一条
    CONSTRAINT uq_trace_edges_source_target_type UNIQUE (source_node_id, target_node_id, edge_type)
);

CREATE INDEX idx_trace_edges_source_node_id ON trace_edges (source_node_id);
CREATE INDEX idx_trace_edges_target_node_id ON trace_edges (target_node_id);
CREATE INDEX idx_trace_edges_edge_type ON trace_edges (edge_type);

-- Event Contract Versions (事件契约版本)
CREATE TABLE IF NOT EXISTS event_contract_versions (
    event_type         VARCHAR(64)    NOT NULL PRIMARY KEY,
    version            VARCHAR(16)    NOT NULL DEFAULT '1.0.0',
    breaking_change    BOOLEAN        NOT NULL DEFAULT FALSE,
    schema_path        VARCHAR(256)   NOT NULL,
    registered_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

-- Consumer Idempotency Records (消费幂等记录)
CREATE TABLE IF NOT EXISTS consumer_idempotency_records (
    event_id           UUID           NOT NULL,
    consumer_id        VARCHAR(128)   NOT NULL,
    consumed_at        TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    
    -- 同一事件同一消费方只记录一次
    CONSTRAINT uq_consumer_idempotency UNIQUE (event_id, consumer_id)
);

CREATE INDEX idx_consumer_idempotency_event_id ON consumer_idempotency_records (event_id);
CREATE INDEX idx_consumer_idempotency_consumer_id ON consumer_idempotency_records (consumer_id);
```

## 7.2 ER 关系图（EV-4.6 新增表）

```
┌──────────────────────┐       ┌──────────────────────┐
│ configuration_       │       │  identity_mappings   │
│     identities       │       │                      │
│ identity_id (PK)  ◄─┼───────┤ identity_id (FK)     │
│ created_at           │       │ domain               │
│ updated_at           │       │ domain_id            │
│                      │       │ mapped_at            │
└──────────┬───────────┘       └──────────────────────┘
           │
           │ (可选关联)
           │
┌──────────▼───────────┐       ┌──────────────────────┐
│    trace_nodes       │       │    trace_edges        │
│                      │       │                      │
│ node_id (PK)     ◄──┼───────┤ source_node_id (FK)  │
│ node_type            │       │ target_node_id (FK) ──┼──► trace_nodes.node_id
│ label                │       │ edge_type            │
│ properties (JSONB)   │       │ properties (JSONB)   │
│ identity_id (FK)     │       │ created_at           │
│ created_at           │       └──────────────────────┘
│ updated_at           │
└──────────────────────┘

┌──────────────────────┐       ┌──────────────────────────────┐
│ event_contract_      │       │  consumer_idempotency_       │
│     versions         │       │     records                  │
│                      │       │                              │
│ event_type (PK)      │       │ event_id                     │
│ version              │       │ consumer_id                  │
│ breaking_change      │       │ consumed_at                  │
│ schema_path          │       │                              │
│ registered_at        │       │ UNIQUE (event_id,consumer_id)│
└──────────────────────┘       └──────────────────────────────┘
```

## 7.3 与 EV-4.5 已有表的关系

EV-4.6 新增表不修改 EV-4.5 已有表结构，通过 domain_id 字段关联：

| EV-4.6 表 | EV-4.5 表 | 关联方式 |
|-----------|-----------|----------|
| identity_mappings | block_configurations | domain="block", domain_id=block_id |
| identity_mappings | dt_material_lots | domain="material_lot", domain_id=lot_id |
| identity_mappings | dt_ndt_records | domain="ndt_record", domain_id=ndt_record_id |
| identity_mappings | dt_corrective_actions | domain="car", domain_id=car_id |
| identity_mappings | dt_evidences | domain="evidence", domain_id=evidence_id |
| identity_mappings | dt_compliance_requirements | domain="compliance_requirement", domain_id=requirement_id |
| trace_nodes | (同上) | node_id = 域记录主键值 |
| trace_edges | dt_block_materials | source=block_id, target=lot_id, type=USES_MATERIAL |
| trace_edges | dt_ndt_records | source=lot_id, target=ndt_record_id, type=TESTED_BY |
| trace_edges | dt_corrective_actions | source=ndt_record_id, target=car_id, type=HAS_CAR |
| trace_edges | dt_compliance_evidences | source=evidence_id, target=requirement_id, type=EVIDENCE_FOR |

---

# 8. Sprint 执行计划

## 8.1 任务分解与依赖

### Sprint-H01: Event Contract Layer

| 任务编号 | 任务描述 | 依赖 | 预估 | 验收标准 |
|----------|----------|------|------|----------|
| H01-T01 | 创建 event-contract/schema/ 目录，编写 6 个 JSON Schema 文件 | 无 | 2h | DH-REQ-01 |
| H01-T02 | 创建 event-contract/versioning/version-manifest.json | 无 | 0.5h | DH-REQ-03 |
| H01-T03 | 实现 SchemaRegistry 内存加载 + 验证逻辑 | H01-T01 | 3h | DH-REQ-09 |
| H01-T04 | 创建 event_contract_versions + consumer_idempotency_records 表 | 无 | 1h | — |
| H01-T05 | 实现 EventContractRepository | H01-T04 | 2h | — |
| H01-T06 | 实现 ConsumerIdempotencyRepository | H01-T04 | 1.5h | — |
| H01-T07 | 实现 EventContractService（验证 + 幂等 + 查询） | H01-T03, H01-T05, H01-T06 | 3h | DH-REQ-02, DH-REQ-08 |
| H01-T08 | 实现 event_contract_controller（Registry API） | H01-T07 | 2h | DH-REQ-06, DH-REQ-07 |
| H01-T09 | 修改 material_controller / quality_controller / dt_certification_controller 注入 schema 验证 | H01-T07 | 2h | DH-REQ-02 |
| H01-T10 | main.py 启动时加载 Schema Registry | H01-T03 | 0.5h | DH-REQ-09 |

### Sprint-H02: Identity Unification Layer

| 任务编号 | 任务描述 | 依赖 | 预估 | 验收标准 |
|----------|----------|------|------|----------|
| H02-T01 | 创建 configuration_identities + identity_mappings 表 | 无 | 1h | — |
| H02-T02 | 实现 ConfigurationIdentity / IdentityMapping dataclass | 无 | 1h | — |
| H02-T03 | 实现 ConfigurationIdentityRepository | H02-T01 | 2h | — |
| H02-T04 | 实现 IdentityMappingRepository（含 UPSERT） | H02-T01 | 2h | DH-NFR-09 |
| H02-T05 | 实现 IdentityService（resolve_or_create + 查询） | H02-T03, H02-T04 | 3h | DH-REQ-10, DH-REQ-14, DH-REQ-15 |
| H02-T06 | 实现 identity_controller（Identity Query API） | H02-T05 | 2h | DH-REQ-11, DH-REQ-12, DH-REQ-16, DH-REQ-17 |
| H02-T07 | 修改 material_controller 注入 Identity 解析 | H02-T05 | 1.5h | DH-REQ-10, DH-REQ-14 |
| H02-T08 | 修改 quality_controller 注入 Identity 解析 | H02-T05 | 1.5h | DH-REQ-15 |
| H02-T09 | 修改 dt_certification_controller 注入 Identity 解析 | H02-T05 | 1.5h | DH-REQ-10 |

### Sprint-H03: Trace Graph Model

| 任务编号 | 任务描述 | 依赖 | 预估 | 验收标准 |
|----------|----------|------|------|----------|
| H03-T01 | 创建 trace_nodes + trace_edges 表 | 无 | 1h | — |
| H03-T02 | 实现 TraceNode / TraceEdge dataclass | 无 | 1h | — |
| H03-T03 | 实现 TraceNodeRepository | H03-T01 | 2h | — |
| H03-T04 | 实现 TraceEdgeRepository | H03-T01 | 2h | — |
| H03-T05 | 实现 TraceGraphCache（邻接表 + CRUD） | 无 | 3h | — |
| H03-T06 | 实现 TraceGraphService（BFS + Impact + Dependency + Rebuild） | H03-T03, H03-T04, H03-T05 | 5h | DH-REQ-20, DH-REQ-21, DH-REQ-22, DH-REQ-23, DH-REQ-25 |
| H03-T07 | 实现 trace_graph_controller | H03-T06 | 2h | DH-REQ-20, DH-REQ-26, DH-REQ-27 |
| H03-T08 | 修改 material_controller 注入 Trace Graph create_node/create_edge | H03-T06, H02-T07 | 1.5h | DH-REQ-18, DH-REQ-19 |
| H03-T09 | 修改 quality_controller 注入 Trace Graph create_node/create_edge | H03-T06, H02-T08 | 1.5h | DH-REQ-18, DH-REQ-19 |
| H03-T10 | 修改 dt_certification_controller 注入 Trace Graph create_node/create_edge | H03-T06, H02-T09 | 1.5h | DH-REQ-18, DH-REQ-19 |
| H03-T11 | 实现 Trace Node properties 同步（域记录更新时） | H03-T06 | 1h | DH-REQ-28 |
| H03-T12 | 系统启动时从 PostgreSQL 加载 Trace Graph cache | H03-T05, H03-T06 | 1h | — |

### Sprint-H04: Trace Analysis UI

| 任务编号 | 任务描述 | 依赖 | 预估 | 验收标准 |
|----------|----------|------|------|----------|
| H04-T01 | 新增 TypeScript 类型定义 | 无 | 1h | — |
| H04-T02 | 新增 v6Api.ts dtHardeningApi 函数 | H04-T01 | 1h | — |
| H04-T03 | 实现 TraceGraphCanvas 组件（Canvas 渲染 + 分层布局） | H04-T02 | 5h | DH-REQ-29 |
| H04-T04 | 实现节点点击高亮上下游路径 | H04-T03 | 3h | DH-REQ-30 |
| H04-T05 | 实现 TraceNodeDetailPanel + IdentityAlignmentView | H04-T04 | 3h | DH-REQ-30, DH-REQ-34 |
| H04-T06 | 实现 ImpactAnalysisView（变更传播视图 + 颜色编码） | H04-T03 | 3h | DH-REQ-31 |
| H04-T07 | 实现 TraceSearchBar（node_type + label 搜索过滤） | H04-T03 | 1.5h | DH-REQ-32 |
| H04-T08 | 实现截断结果 Load More | H04-T03 | 1.5h | DH-REQ-33 |
| H04-T09 | 组装 TraceAnalysisPage 主页面 | H04-T03~T08 | 2h | DH-REQ-29~35 |

## 8.2 执行顺序

```
Phase 1 (H01): Event Contract Layer ──────────────────── P0
    │
    ├── H01-T01, H01-T02, H01-T04 (并行，无依赖)
    │
    ├── H01-T03 (依赖 T01)
    │
    ├── H01-T05, H01-T06 (依赖 T04，并行)
    │
    ├── H01-T07 (依赖 T03, T05, T06)
    │
    ├── H01-T08, H01-T09, H01-T10 (依赖 T07，并行)
    │
Phase 2 (H02): Identity Unification Layer ───────────── P0
    │
    ├── H02-T01, H02-T02 (并行，无依赖)
    │
    ├── H02-T03, H02-T04 (依赖 T01，并行)
    │
    ├── H02-T05 (依赖 T03, T04)
    │
    ├── H02-T06, H02-T07, H02-T08, H02-T09 (依赖 T05，并行)
    │
Phase 3 (H03): Trace Graph Model ────────────────────── P0
    │
    ├── H03-T01, H03-T02 (并行，无依赖)
    │
    ├── H03-T03, H03-T04, H03-T05 (依赖 T01/T02，并行)
    │
    ├── H03-T06 (依赖 T03, T04, T05)
    │
    ├── H03-T07, H03-T08, H03-T09, H03-T10, H03-T11, H03-T12 (依赖 T06，并行)
    │
Phase 4 (H04): Trace Analysis UI ────────────────────── P1
    │
    ├── H04-T01, H04-T02 (并行，无依赖)
    │
    ├── H04-T03 (依赖 T02)
    │
    ├── H04-T04, H04-T06, H04-T07 (依赖 T03，并行)
    │
    ├── H04-T05 (依赖 T04)
    │
    ├── H04-T08 (依赖 T03)
    │
    └── H04-T09 (依赖 T03~T08)
```

## 8.3 验收标准映射

| 验收级别 | 需求编号 | 关键验收项 | 对应任务 |
|----------|----------|------------|----------|
| PASS | DH-REQ-01 | 6 个 schema 文件 | H01-T01 |
| PASS | DH-REQ-02 | 发布前 schema 验证 | H01-T07, H01-T09 |
| PASS | DH-REQ-03 | 语义化版本管理 | H01-T02 |
| PASS | DH-REQ-08 | 消费幂等 | H01-T06, H01-T07 |
| PASS | DH-REQ-10 | 域记录自动关联 Identity | H02-T05, H02-T07~T09 |
| PASS | DH-REQ-11 | 查询 Identity 返回所有映射 | H02-T06 |
| PASS | DH-REQ-14 | Block + MaterialLot 同一 Identity | H02-T05, H02-T07 |
| PASS | DH-REQ-18 | 域记录创建自动创建 Trace Node | H03-T08~T10 |
| PASS | DH-REQ-19 | 域记录关联自动创建 Trace Edge | H03-T08~T10 |
| PASS | DH-REQ-20 | TraceQuery 全链路遍历 | H03-T06, H03-T07 |
| PASS | DH-REQ-23 | Trace Graph Rebuild | H03-T06, H03-T07 |
| A | DH-REQ-04 | Major 版本 breaking change | H01-T07 |
| A | DH-REQ-05 | Minor 版本向后兼容 | H01-T07 |
| A | DH-REQ-06 | Schema Registry API | H01-T08 |
| A | DH-REQ-07 | 单事件契约查询 | H01-T08 |
| A | DH-REQ-12 | 域 ID 反查 Identity | H02-T06 |
| A | DH-REQ-15 | MaterialLot + NDTRecord 同一 Identity | H02-T05, H02-T08 |
| A | DH-REQ-21 | Impact Analysis | H03-T06, H03-T07 |
| A | DH-REQ-22 | Dependency Query | H03-T06, H03-T07 |
| A | DH-REQ-25 | 环路检测 | H03-T06 |
| A | DH-REQ-26 | Trace Node 详情查询 | H03-T07 |
| A | DH-REQ-27 | Trace Graph 统计 | H03-T07 |
| A | DH-REQ-28 | Node properties 同步 | H03-T11 |
| A+ | DH-REQ-29 | 交互式依赖图 | H04-T03 |
| A+ | DH-REQ-30 | 节点点击高亮 + Identity 面板 | H04-T04, H04-T05 |
| A+ | DH-REQ-31 | Change Propagation View | H04-T06 |
| A+ | DH-REQ-32 | 节点搜索过滤 | H04-T07 |
| A+ | DH-REQ-33 | 截断 Load More | H04-T08 |
| A+ | DH-REQ-34 | Identity 跨域对齐视图 | H04-T05 |