# AeroForge-X EV-4.5 Digital Thread Foundation — 技术架构设计文档

**项目**: AeroForge-X v6.0 "Project Valkyrie"  
**Sprint**: EV-4.5 Digital Thread Foundation Sprint  
**目标 TRL**: 6.0 → 6.5  
**日期**: 2026-06-22  
**状态**: DRAFT  
**关联需求文档**: `ev4.5-digital-thread-spec.md`  
**关联架构文档**: `ev4.5-architecture-activation-design.md`

---

# 1. 实现模型

## 1.1 上下文视图

EV-4.5 Digital Thread Foundation 在 EV-4.5 Architecture Activation 已部署的 7 容器基础设施之上，构建飞机数字线程的三条业务主线（Material / Quality / Certification Thread）及配套前端追溯页面。所有新代码在 `aircraft-core-service` 内扩展，不新增微服务或数据库。

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    AeroForge-X EV-4.5 Digital Thread                         │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐     │
│  │                    Aircraft Core Service (FastAPI)                   │     │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │     │
│  │  │Config v6 │ │Material  │ │Quality   │ │Certifica-│              │     │
│  │  │Controller│ │Controller│ │Controller│ │tion Ctrl │              │     │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘              │     │
│  │       │            │            │            │                     │     │
│  │  ┌────▼────────────▼────────────▼────────────▼─────┐              │     │
│  │  │     Domain Layer (dataclass + to_dict)           │              │     │
│  │  │  MaterialLot | NDTRecord | CAR | Evidence |      │              │     │
│  │  │  ComplianceRequirement                          │              │     │
│  │  └────────────────────┬────────────────────────────┘              │     │
│  │                       │                                           │     │
│  │  ┌────────────────────▼────────────────────────────┐              │     │
│  │  │     Repository Layer (AsyncpgRepository)         │              │     │
│  │  │  MaterialLotRepo | NDTRepo | CARRepo |           │              │     │
│  │  │  EvidenceRepo | ComplianceRepo                   │              │     │
│  │  └────────────────────┬────────────────────────────┘              │     │
│  │                       │                                           │     │
│  │  ┌────────────────────▼────────────────────────────┐              │     │
│  │  │     Infrastructure Abstraction Layer             │              │     │
│  │  │  EventBus (InMemory/Nats)                        │              │     │
│  │  │  ObjectStorage (Local/MinIO)                     │              │     │
│  │  │  GraphRepository (NoOp/Neo4j)                    │              │     │
│  │  └───┬────────────┬────────────────┬───────────────┘              │     │
│  └──────┼────────────┼────────────────┼──────────────────────────────┘     │
│         │            │                │                                     │
│  ┌──────▼──┐  ┌──────▼──┐  ┌─────────▼──┐  ┌──────────────┐              │
│  │PostgreSQL│  │  NATS   │  │   Neo4j    │  │    MinIO     │              │
│  │  Port    │  │JetStream│  │  Port      │  │  Port        │              │
│  │  5432    │  │4222/8222│  │7474/7687   │  │9000/9001     │              │
│  └─────────┘  └─────────┘  └────────────┘  └──────────────┘              │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                    React Frontend (Port 80)                           │    │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐           │    │
│  │  │Config    │ │Material  │ │Quality   │ │Certification │           │    │
│  │  │Trace Page│ │Trace Page│ │Trace Page│ │Trace Page    │           │    │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────────┘           │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 系统交互关系（新增）

| 发布方 | 消息通道 | 消费方 | 事件类型 | Sprint |
|--------|----------|--------|----------|--------|
| Aircraft Core | NATS `aeroforge.material.lot.created` | (下游服务) | `MaterialLotCreated` | DT01 |
| Aircraft Core | NATS `aeroforge.quality.ndt.completed` | (下游服务) | `NDTCompleted` | DT02 |
| Aircraft Core | NATS `aeroforge.quality.car.created` | (下游服务) | `CARCreated` | DT02 |
| Aircraft Core | NATS `aeroforge.quality.car.closed` | (下游服务) | `CARClosed` | DT02 |
| Aircraft Core | NATS `aeroforge.cert.evidence.uploaded` | (下游服务) | `EvidenceUploaded` | DT03 |
| Aircraft Core | Neo4j (GraphRepository) | — | Block-Material / NDT-CAR 关系 | INF04 |
| Aircraft Core | MinIO (ObjectStorage) | — | Certification Evidence 文件 | INF01 |

## 1.2 服务/组件总体架构

### 1.2.1 新增代码在 aircraft-core-service 中的目录结构

```
services/aircraft-core-service/src/
├── api/v6/
│   ├── configuration_controller.py      # [已有] Block Config CRUD
│   ├── config_identity_controller.py    # [已有] Neo4j graph query
│   ├── evidence_controller.py           # [重构] → 使用 ObjectStorage 抽象
│   ├── material_controller.py           # [新增] MaterialLot CRUD + Block 关联
│   ├── quality_controller.py            # [新增] NDTRecord + CAR CRUD
│   └── certification_controller.py      # [新增] Compliance + Evidence 查询
├── domain/
│   ├── events/
│   │   ├── block_updated_event.py       # [已有]
│   │   ├── configuration_updated_event.py # [已有]
│   │   ├── material_lot_created_event.py  # [新增]
│   │   ├── ndt_completed_event.py         # [新增]
│   │   ├── car_created_event.py           # [新增]
│   │   ├── car_closed_event.py            # [新增]
│   │   └── evidence_uploaded_event.py     # [新增]
│   └── models/                            # [新增目录]
│       ├── material_lot.py
│       ├── ndt_record.py
│       ├── corrective_action_request.py
│       ├── compliance_requirement.py
│       └── evidence.py
├── infrastructure/
│   ├── database.py                        # [已有]
│   ├── event_bus.py                       # [重构] → EventBus 抽象接口
│   ├── graph_client.py                    # [重构] → GraphRepository 抽象接口
│   ├── object_storage.py                  # [重构] → ObjectStorage 抽象接口
│   ├── repositories/
│   │   ├── base_repository.py             # [已有]
│   │   ├── configuration_repository.py    # [已有]
│   │   ├── material_lot_repository.py     # [新增]
│   │   ├── ndt_record_repository.py       # [新增]
│   │   ├── car_repository.py              # [新增]
│   │   ├── evidence_repository.py         # [新增]
│   │   └── compliance_repository.py       # [新增]
│   └── adapters/                          # [新增目录]
│       ├── event_bus_interface.py         # EventBus ABC
│       ├── in_memory_event_bus.py         # InMemory 实现
│       ├── nats_event_bus.py              # NATS JetStream 实现
│       ├── object_storage_interface.py    # ObjectStorage ABC
│       ├── local_object_storage.py        # Local filesystem 实现
│       ├── minio_object_storage.py        # MinIO 实现
│       ├── graph_repository_interface.py  # GraphRepository ABC
│       ├── noop_graph_repository.py       # NoOp 降级实现
│       └── neo4j_graph_repository.py      # Neo4j 实现
└── main.py                                # [更新] 注册新 router

contracts/events/                           # [新增目录]
├── ConfigurationChanged.json
├── MaterialLotCreated.json
├── NDTCompleted.json
├── CARCreated.json
├── CARClosed.json
├── EvidenceUploaded.json
└── DigitalTwinSyncEvent.json

frontend/src/
├── api/
│   ├── v6Api.ts                           # [更新] 新增 material/quality/cert API
│   └── types.ts                           # [更新] 新增 TypeScript 类型
└── modules/v6/
    ├── ConfigurationManagerPage.tsx       # [已有]
    ├── ConfigurationTracePage.tsx         # [新增]
    ├── MaterialTracePage.tsx              # [新增]
    ├── QualityTracePage.tsx               # [新增]
    └── CertificationTracePage.tsx         # [新增]

deploy/migrations/v6_4/                    # [新增目录]
└── 008_digital_thread_tables.sql          # DDL migration
```

### 1.2.2 架构分层与职责

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer (Controllers)                   │
│  FastAPI APIRouter + module-level service instantiation          │
│  职责: HTTP 请求解析、Pydantic 校验、调用 Service、返回响应       │
├─────────────────────────────────────────────────────────────────┤
│                      Domain Layer (Models)                       │
│  dataclass + to_dict() 模式                                      │
│  职责: 业务实体定义、业务规则校验、领域事件构造                    │
├─────────────────────────────────────────────────────────────────┤
│                    Repository Layer (Persistence)                 │
│  AsyncpgRepository 基类 + asyncpg Pool                           │
│  职责: PostgreSQL CRUD、SQL 构建、事务管理                        │
├─────────────────────────────────────────────────────────────────┤
│                Infrastructure Abstraction Layer                   │
│  EventBus / ObjectStorage / GraphRepository 抽象接口              │
│  职责: 基础设施解耦、降级策略、实现切换                           │
├─────────────────────────────────────────────────────────────────┤
│                   Infrastructure Implementations                  │
│  NatsEventBus | InMemoryEventBus | MinioStorage | LocalStorage   │
│  Neo4jGraphRepository | NoOpGraphRepository                      │
│  职责: 具体基础设施客户端封装、连接管理、错误处理                  │
└─────────────────────────────────────────────────────────────────┘
```

## 1.3 实现设计文档

### 1.3.1 关键设计决策

| 决策编号 | 决策描述 | 理由 |
|----------|----------|------|
| DD-01 | 所有新代码在 aircraft-core-service 内扩展，不新增微服务 | 业务驱动原则，避免过度拆分 |
| DD-02 | Domain Model 使用 `dataclass + to_dict()` 模式 | 与现有 `ConfigurationItem`、`MaterialLot` 等保持一致 |
| DD-03 | Event 使用 Pydantic V2 `BaseModel` | 与现有 `BlockUpdatedEvent`、`ConfigurationUpdatedEvent` 保持一致 |
| DD-04 | Repository 继承 `AsyncpgRepository` 基类 | 复用 `_execute`/`_fetchrow`/`_fetch` 等通用方法 |
| DD-05 | Controller 使用 `APIRouter(prefix="/api/v6/aircraft-core")` | 与现有 controller 前缀保持一致 |
| DD-06 | Service 使用 module-level 单例实例化 | 与现有 `_config_service` 等保持一致 |
| DD-07 | 基础设施抽象接口支持降级模式 | 满足 DT-NFR-06 可靠性要求 |
| DD-08 | lot_id 自动生成格式 `{material_code}-{sequence}` | 遵循需求 DT-REQ-05 |
| DD-09 | ndt_record_id / car_id 使用 UUID | 遵循需求规格数据约束 |
| DD-10 | 不提供 MaterialLot / NDTRecord / Evidence 的 DELETE 端点 | 遵循需求禁止项 |

### 1.3.2 降级策略

```
┌──────────────────────────────────────────────────────────┐
│                  Degradation Decision Tree                │
│                                                          │
│  NATS 不可用?                                            │
│  ├── Yes → InMemoryEventBus (进程内回调, 无持久化)        │
│  └── No  → NatsEventBus (JetStream 持久化)               │
│                                                          │
│  MinIO 不可用?                                           │
│  ├── Yes → LocalObjectStorage (本地磁盘存储)             │
│  └── No  → MinioObjectStorage (对象存储)                 │
│                                                          │
│  Neo4j 不可用?                                           │
│  ├── Yes → NoOpGraphRepository (no-op + WARNING 日志)    │
│  └── No  → Neo4jGraphRepository (图谱持久化)             │
│                                                          │
│  原则: 业务 API 始终可用，基础设施降级为 no-op            │
└──────────────────────────────────────────────────────────┘
```

---

# 2. 接口设计

## 2.1 总体设计

所有新增 API 端点统一使用 `/api/v6/aircraft-core` 前缀，遵循 RESTful 风格。请求体使用 Pydantic V2 模型校验，响应体为 JSON。

### API 端点总览

| 方法 | 路径 | 描述 | Sprint |
|------|------|------|--------|
| POST | `/api/v6/aircraft-core/material-lots` | 创建 MaterialLot | DT01 |
| GET | `/api/v6/aircraft-core/material-lots/{lot_id}` | 查询指定 MaterialLot | DT01 |
| GET | `/api/v6/aircraft-core/blocks/{block_id}/materials` | 查询 Block 关联的 MaterialLot | DT01 |
| POST | `/api/v6/aircraft-core/ndt-records` | 创建 NDTRecord | DT02 |
| GET | `/api/v6/aircraft-core/ndt-records/{ndt_record_id}` | 查询指定 NDTRecord | DT02 |
| POST | `/api/v6/aircraft-core/corrective-actions` | 创建 CAR | DT02 |
| PATCH | `/api/v6/aircraft-core/corrective-actions/{car_id}` | 更新 CAR 状态 | DT02 |
| GET | `/api/v6/aircraft-core/corrective-actions/{car_id}` | 查询指定 CAR | DT02 |
| GET | `/api/v6/aircraft-core/material-lots/{lot_id}/quality` | 查询 MaterialLot 质量链路 | DT02 |
| GET | `/api/v6/aircraft-core/compliance/{requirement_id}` | 查询适航合规信息 | DT03 |
| PATCH | `/api/v6/aircraft-core/compliance/{requirement_id}` | 更新合规状态 | DT03 |
| POST | `/api/v6/aircraft-core/evidence/upload` | 上传认证证据文件 | DT03 |
| GET | `/api/v6/aircraft-core/evidence/{evidence_id}` | 查询证据元数据+预签名URL | DT03 |

## 2.2 接口清单

### 2.2.1 Sprint-DT01: Material Thread API

#### POST /api/v6/aircraft-core/material-lots

**请求体** (`CreateMaterialLotRequest`):

```python
class CreateMaterialLotRequest(BaseModel):
    material_code: str = Field(..., min_length=1, description="材料编码，如 AL-2024")
    material_name: str = Field(..., min_length=1, description="材料名称，如 Aluminum 2024-T3")
    supplier_id: str = Field(..., min_length=1, description="供应商标识，如 Supplier-A")
    manufacture_date: str = Field(..., description="ISO 8601 制造日期")
    received_date: str = Field(..., description="ISO 8601 接收日期")
    certificate_no: str = Field(..., min_length=1, description="质量证书编号")
    block_id: str | None = Field(None, description="关联的 Block ID")
```

**响应体** (201 Created):

```python
class MaterialLotResponse(BaseModel):
    lot_id: str                    # 系统自动生成，如 "AL-2024-001"
    material_code: str
    material_name: str
    supplier_id: str
    manufacture_date: str
    received_date: str
    certificate_no: str
    status: str                    # 默认 "received"
    block_id: str | None
    created_at: str
    updated_at: str
```

**业务逻辑**:
1. 校验必填字段（Pydantic 自动校验，缺失返回 422）
2. 自动生成 `lot_id`：查询 `material_lots` 表中相同 `material_code` 的最大 sequence，+1 生成 `{material_code}-{sequence:03d}`
3. INSERT 到 `material_lots` 表
4. 若 `block_id` 不为空，INSERT 到 `block_materials` 关联表
5. 发布 `MaterialLotCreated` 事件到 NATS
6. 通过 `GraphRepository` 写入 `(Block)-[:USES_MATERIAL]->(MaterialLot)` 关系（降级 no-op）

**异常**:
- 422: 缺少必填字段
- 404: block_id 对应的 Block 不存在

---

#### GET /api/v6/aircraft-core/material-lots/{lot_id}

**响应体** (200 OK): `MaterialLotResponse`

**异常**:
- 404: MaterialLot not found

---

#### GET /api/v6/aircraft-core/blocks/{block_id}/materials

**响应体** (200 OK):

```python
class BlockMaterialsResponse(BaseModel):
    block_id: str
    materials: list[MaterialLotResponse]
```

**异常**:
- 200 + 空数组: Block 没有关联材料批次

---

### 2.2.2 Sprint-DT02: Quality Thread API

#### POST /api/v6/aircraft-core/ndt-records

**请求体** (`CreateNDTRecordRequest`):

```python
class CreateNDTRecordRequest(BaseModel):
    material_lot_id: str = Field(..., description="关联的 MaterialLot.lot_id")
    test_type: Literal["ultrasonic", "radiographic", "penetrant", "magnetic_particle", "eddy_current"]
    result: Literal["pass", "fail", "conditional"]
    inspector: str = Field(..., min_length=1, description="检测人员标识")
    test_date: str = Field(..., description="ISO 8601 检测日期")
    notes: str | None = Field(None, description="检测备注")
```

**响应体** (201 Created):

```python
class NDTRecordResponse(BaseModel):
    ndt_record_id: str             # UUID，系统自动生成
    material_lot_id: str
    test_type: str
    result: str
    inspector: str
    test_date: str
    notes: str | None
    created_at: str
```

**业务逻辑**:
1. 校验 `material_lot_id` 存在（不存在返回 404）
2. 自动生成 `ndt_record_id`（UUID4）
3. INSERT 到 `ndt_records` 表
4. 发布 `NDTCompleted` 事件到 NATS
5. 通过 `GraphRepository` 写入 `(MaterialLot)-[:TESTED_BY]->(NDTRecord)` 关系

**异常**:
- 404: MaterialLot not found

---

#### POST /api/v6/aircraft-core/corrective-actions

**请求体** (`CreateCARRequest`):

```python
class CreateCARRequest(BaseModel):
    ndt_record_id: str = Field(..., description="关联的 NDTRecord.ndt_record_id")
    description: str = Field(..., min_length=1, description="问题描述")
    responsible_person: str = Field(..., min_length=1, description="责任人")
```

**响应体** (201 Created):

```python
class CARResponse(BaseModel):
    car_id: str                    # UUID，系统自动生成
    ndt_record_id: str
    description: str
    status: str                    # 默认 "open"
    responsible_person: str
    created_at: str
    updated_at: str
    closed_at: str | None
```

**业务逻辑**:
1. 校验 `ndt_record_id` 存在（不存在返回 404）
2. 校验对应 NDT result 为 `fail` 或 `conditional`（`pass` 返回 400）
3. 自动生成 `car_id`（UUID4）
4. INSERT 到 `corrective_actions` 表
5. 发布 `CARCreated` 事件到 NATS
6. 通过 `GraphRepository` 写入 `(NDTRecord)-[:HAS_CAR]->(CAR)` 关系

**异常**:
- 404: NDT Record not found
- 400: "CAR can only be created for failed or conditional NDT results"

---

#### PATCH /api/v6/aircraft-core/corrective-actions/{car_id}

**请求体** (`UpdateCARRequest`):

```python
class UpdateCARRequest(BaseModel):
    status: Literal["in_progress", "closed"]
    closed_by: str | None = Field(None, description="关闭操作人，status=closed 时必填")
```

**响应体** (200 OK): `CARResponse`

**业务逻辑**:
1. 查询 CAR，不存在返回 404
2. 校验当前 status 不为 `closed`（已关闭返回 400）
3. 更新 status，若为 `closed` 则设置 `closed_at = NOW()`
4. 发布 `CARClosed` 事件到 NATS

**异常**:
- 404: CAR not found
- 400: "CAR is already closed"

---

#### GET /api/v6/aircraft-core/material-lots/{lot_id}/quality

**响应体** (200 OK):

```python
class QualityThreadResponse(BaseModel):
    material_lot: MaterialLotResponse
    ndt_records: list[NDTRecordWithCARs]

class NDTRecordWithCARs(BaseModel):
    ndt_record_id: str
    material_lot_id: str
    test_type: str
    result: str
    inspector: str
    test_date: str
    notes: str | None
    created_at: str
    corrective_actions: list[CARResponse]
```

**业务逻辑**:
1. 查询 MaterialLot（不存在返回 404）
2. 查询关联的所有 NDTRecord
3. 对每个 NDTRecord 查询关联的 CAR 列表
4. 组装为 MaterialLot → NDT → CAR 完整链路

---

### 2.2.3 Sprint-DT03: Certification Thread API

#### POST /api/v6/aircraft-core/evidence/upload

**请求体**: `multipart/form-data`

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| file | UploadFile | 是 | 证据文件 |
| requirement_id | str (Form) | 是 | 关联的适航条款编号 |

**响应体** (201 Created):

```python
class EvidenceUploadResponse(BaseModel):
    evidence_id: str               # UUID
    requirement_id: str
    file_id: str                   # MinIO/Local 中的对象 key
    file_name: str
    bucket: str                    # "aeroforge-cert-evidence"
    content_type: str
    file_size: int
    upload_timestamp: str
    presigned_url: str | None      # 下载预签名 URL
```

**业务逻辑**:
1. 校验 `content_type` 在允许列表中（不符合返回 415）
2. 校验文件大小 ≤ 50MB（超过返回 413）
3. 通过 `ObjectStorage.upload_file()` 存储文件（MinIO 优先，降级 Local）
4. 若存储失败返回 503
5. 自动生成 `evidence_id`（UUID4）
6. INSERT 到 `evidences` 表
7. INSERT 到 `compliance_evidences` 关联表
8. 确保 `compliance_requirements` 表中存在该 `requirement_id`（不存在则自动创建，status="pending"）
9. 发布 `EvidenceUploaded` 事件到 NATS

**异常**:
- 415: Unsupported content type
- 413: File size exceeds limit
- 503: Object storage unavailable

---

#### GET /api/v6/aircraft-core/evidence/{evidence_id}

**响应体** (200 OK):

```python
class EvidenceDetailResponse(BaseModel):
    evidence_id: str
    requirement_id: str
    file_id: str
    file_name: str
    bucket: str
    content_type: str
    file_size: int
    upload_timestamp: str
    presigned_url: str | None
```

**业务逻辑**:
1. 查询 `evidences` 表获取元数据
2. 通过 `ObjectStorage.get_presigned_url()` 获取下载 URL
3. 组装返回

**异常**:
- 404: Evidence not found

---

#### GET /api/v6/aircraft-core/compliance/{requirement_id}

**响应体** (200 OK):

```python
class ComplianceDetailResponse(BaseModel):
    requirement_id: str
    regulation: str | None
    description: str | None
    compliance_status: str         # compliant/non_compliant/partial/pending
    responsible_person: str | None
    updated_at: str
    evidence_items: list[EvidenceDetailResponse]
```

**业务逻辑**:
1. 查询 `compliance_requirements` 表
2. 若不存在，自动创建（compliance_status="pending"），返回空证据列表
3. 查询 `compliance_evidences` 关联表获取 evidence_id 列表
4. 查询 `evidences` 表获取每个证据的元数据
5. 通过 `ObjectStorage` 获取预签名 URL
6. 组装返回

---

#### PATCH /api/v6/aircraft-core/compliance/{requirement_id}

**请求体** (`UpdateComplianceRequest`):

```python
class UpdateComplianceRequest(BaseModel):
    compliance_status: Literal["compliant", "non_compliant", "partial"]
    responsible_person: str | None = None
```

**响应体** (200 OK): `ComplianceDetailResponse`

---

# 3. 领域事件设计

## 3.1 事件模型

所有事件继承 Pydantic V2 `BaseModel`，与现有 `BlockUpdatedEvent` 模式保持一致。

### 3.1.1 MaterialLotCreatedEvent

```python
class MaterialLotCreatedEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "MaterialLotCreated"
    lot_id: str = ""
    material_code: str = ""
    supplier_id: str = ""
    block_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
```

**NATS Subject**: `aeroforge.material.lot.created`  
**JetStream Stream**: `AEROFORGE_MATERIAL`

### 3.1.2 NDTCompletedEvent

```python
class NDTCompletedEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "NDTCompleted"
    ndt_record_id: str = ""
    material_lot_id: str = ""
    test_type: str = ""
    result: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
```

**NATS Subject**: `aeroforge.quality.ndt.completed`  
**JetStream Stream**: `AEROFORGE_QUALITY`

### 3.1.3 CARCreatedEvent

```python
class CARCreatedEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "CARCreated"
    car_id: str = ""
    ndt_record_id: str = ""
    description: str = ""
    status: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
```

**NATS Subject**: `aeroforge.quality.car.created`  
**JetStream Stream**: `AEROFORGE_QUALITY`

### 3.1.4 CARClosedEvent

```python
class CARClosedEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "CARClosed"
    car_id: str = ""
    closed_by: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
```

**NATS Subject**: `aeroforge.quality.car.closed`  
**JetStream Stream**: `AEROFORGE_QUALITY`

### 3.1.5 EvidenceUploadedEvent

```python
class EvidenceUploadedEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "EvidenceUploaded"
    evidence_id: str = ""
    requirement_id: str = ""
    file_id: str = ""
    file_name: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
```

**NATS Subject**: `aeroforge.cert.evidence.uploaded`  
**JetStream Stream**: `AEROFORGE_CERT`

### 3.1.6 DigitalTwinSyncEvent

```python
class DigitalTwinSyncEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = "DigitalTwinSync"
    aircraft_id: str = ""
    block_id: str = ""
    version: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    change_type: str = ""          # CREATED / UPDATED / DELETED
```

**说明**: 仅定义契约，不实现同步逻辑。`ConfigurationUpdatedEvent` → `DigitalTwinSyncEvent` 的映射关系在契约文件中定义。

## 3.2 事件契约文件

所有事件契约以 JSON Schema 格式输出到 `contracts/events/` 目录，版本号 `1.0.0`。

示例 — `contracts/events/MaterialLotCreated.json`:

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

---

# 4. 数据模型

## 4.1 设计目标

- 所有新表在现有 `aeroforge` 数据库中创建
- 使用 `search_path: aircraft_core,public`（已在 database.py 中配置）
- 遵循现有 `block_configurations` 表的命名和约束风格
- 外键约束确保引用完整性
- 索引优化高频查询路径

## 4.2 模型实现

### 4.2.1 Domain Model (Python dataclass)

#### MaterialLot

```python
@dataclass
class MaterialLot:
    lot_id: str                        # 格式: {material_code}-{sequence:03d}
    material_code: str                 # 如 "AL-2024"
    material_name: str                 # 如 "Aluminum 2024-T3"
    supplier_id: str                   # 如 "Supplier-A"
    manufacture_date: str              # ISO 8601
    received_date: str                 # ISO 8601
    certificate_no: str                # 质量证书编号
    status: str = "received"           # received/inspected/accepted/rejected/quarantined
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "lot_id": self.lot_id,
            "material_code": self.material_code,
            "material_name": self.material_name,
            "supplier_id": self.supplier_id,
            "manufacture_date": self.manufacture_date,
            "received_date": self.received_date,
            "certificate_no": self.certificate_no,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
```

#### NDTRecord

```python
@dataclass
class NDTRecord:
    ndt_record_id: str                 # UUID
    material_lot_id: str               # FK → material_lots.lot_id
    test_type: str                     # ultrasonic/radiographic/penetrant/magnetic_particle/eddy_current
    result: str                        # pass/fail/conditional
    inspector: str
    test_date: str                     # ISO 8601
    notes: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "ndt_record_id": self.ndt_record_id,
            "material_lot_id": self.material_lot_id,
            "test_type": self.test_type,
            "result": self.result,
            "inspector": self.inspector,
            "test_date": self.test_date,
            "notes": self.notes,
            "created_at": self.created_at,
        }
```

#### CorrectiveActionRequest

```python
@dataclass
class CorrectiveActionRequest:
    car_id: str                        # UUID
    ndt_record_id: str                 # FK → ndt_records.ndt_record_id
    description: str
    status: str = "open"               # open/in_progress/closed
    responsible_person: str = ""
    created_at: str = ""
    updated_at: str = ""
    closed_at: str = ""

    def to_dict(self) -> dict:
        return {
            "car_id": self.car_id,
            "ndt_record_id": self.ndt_record_id,
            "description": self.description,
            "status": self.status,
            "responsible_person": self.responsible_person,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "closed_at": self.closed_at or None,
        }
```

#### ComplianceRequirement

```python
@dataclass
class ComplianceRequirement:
    requirement_id: str                # 如 "FAA-25.853"
    regulation: str                    # 如 "FAR-25"
    description: str
    compliance_status: str = "pending" # compliant/non_compliant/partial/pending
    responsible_person: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "requirement_id": self.requirement_id,
            "regulation": self.regulation,
            "description": self.description,
            "compliance_status": self.compliance_status,
            "responsible_person": self.responsible_person,
            "updated_at": self.updated_at,
        }
```

#### Evidence

```python
@dataclass
class Evidence:
    evidence_id: str                   # UUID
    requirement_id: str                # FK → compliance_requirements.requirement_id
    file_id: str                       # MinIO/Local 对象 key
    file_name: str
    bucket: str = "aeroforge-cert-evidence"
    content_type: str = ""
    file_size: int = 0
    upload_timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "requirement_id": self.requirement_id,
            "file_id": self.file_id,
            "file_name": self.file_name,
            "bucket": self.bucket,
            "content_type": self.content_type,
            "file_size": self.file_size,
            "upload_timestamp": self.upload_timestamp,
        }
```

### 4.2.2 PostgreSQL DDL

```sql
-- ============================================================
-- AeroForge-X EV-4.5 Digital Thread Tables
-- Migration: 008_digital_thread_tables.sql
-- ============================================================

-- Material Lots (材料批次)
CREATE TABLE IF NOT EXISTS material_lots (
    lot_id              VARCHAR(64)    NOT NULL PRIMARY KEY,
    material_code       VARCHAR(64)    NOT NULL,
    material_name       VARCHAR(256)   NOT NULL,
    supplier_id         VARCHAR(64)    NOT NULL,
    manufacture_date    DATE           NOT NULL,
    received_date       DATE           NOT NULL,
    certificate_no      VARCHAR(128)   NOT NULL,
    status              VARCHAR(32)    NOT NULL DEFAULT 'received'
                                        CHECK (status IN ('received','inspected','accepted','rejected','quarantined')),
    created_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_material_lots_material_code ON material_lots (material_code);
CREATE INDEX idx_material_lots_supplier_id ON material_lots (supplier_id);
CREATE INDEX idx_material_lots_status ON material_lots (status);

-- Block-Material Association (Block → MaterialLot 关联)
CREATE TABLE IF NOT EXISTS block_materials (
    block_id            VARCHAR(128)   NOT NULL,
    lot_id              VARCHAR(64)    NOT NULL REFERENCES material_lots(lot_id) ON DELETE RESTRICT,
    associated_at       TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    PRIMARY KEY (block_id, lot_id)
);

CREATE INDEX idx_block_materials_block_id ON block_materials (block_id);
CREATE INDEX idx_block_materials_lot_id ON block_materials (lot_id);

-- NDT Records (无损检测记录)
CREATE TABLE IF NOT EXISTS ndt_records (
    ndt_record_id       UUID           NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    material_lot_id     VARCHAR(64)    NOT NULL REFERENCES material_lots(lot_id) ON DELETE RESTRICT,
    test_type           VARCHAR(32)    NOT NULL CHECK (test_type IN ('ultrasonic','radiographic','penetrant','magnetic_particle','eddy_current')),
    result              VARCHAR(16)    NOT NULL CHECK (result IN ('pass','fail','conditional')),
    inspector           VARCHAR(128)   NOT NULL,
    test_date           DATE           NOT NULL,
    notes               TEXT           DEFAULT '',
    created_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ndt_records_material_lot_id ON ndt_records (material_lot_id);
CREATE INDEX idx_ndt_records_result ON ndt_records (result);
CREATE INDEX idx_ndt_records_test_type ON ndt_records (test_type);

-- Corrective Action Requests (纠正措施请求)
CREATE TABLE IF NOT EXISTS corrective_actions (
    car_id              UUID           NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    ndt_record_id       UUID           NOT NULL REFERENCES ndt_records(ndt_record_id) ON DELETE RESTRICT,
    description         TEXT           NOT NULL,
    status              VARCHAR(16)    NOT NULL DEFAULT 'open'
                                        CHECK (status IN ('open','in_progress','closed')),
    responsible_person  VARCHAR(128)   NOT NULL,
    created_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    closed_at           TIMESTAMPTZ
);

CREATE INDEX idx_corrective_actions_ndt_record_id ON corrective_actions (ndt_record_id);
CREATE INDEX idx_corrective_actions_status ON corrective_actions (status);

-- Compliance Requirements (适航合规条款)
CREATE TABLE IF NOT EXISTS compliance_requirements (
    requirement_id      VARCHAR(128)   NOT NULL PRIMARY KEY,
    regulation          VARCHAR(64)    NOT NULL DEFAULT '',
    description         TEXT           NOT NULL DEFAULT '',
    compliance_status   VARCHAR(32)    NOT NULL DEFAULT 'pending'
                                        CHECK (compliance_status IN ('compliant','non_compliant','partial','pending')),
    responsible_person  VARCHAR(128)   DEFAULT '',
    updated_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

-- Evidence (认证证据)
CREATE TABLE IF NOT EXISTS evidences (
    evidence_id         UUID           NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    requirement_id      VARCHAR(128)   NOT NULL REFERENCES compliance_requirements(requirement_id) ON DELETE RESTRICT,
    file_id             UUID           NOT NULL DEFAULT gen_random_uuid(),
    file_name           VARCHAR(512)   NOT NULL,
    bucket              VARCHAR(128)   NOT NULL DEFAULT 'aeroforge-cert-evidence',
    content_type        VARCHAR(128)   NOT NULL,
    file_size           BIGINT         NOT NULL DEFAULT 0,
    upload_timestamp    TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_evidences_requirement_id ON evidences (requirement_id);
CREATE INDEX idx_evidences_file_id ON evidences (file_id);

-- Compliance-Evidence Association (合规条款-证据关联)
CREATE TABLE IF NOT EXISTS compliance_evidences (
    requirement_id      VARCHAR(128)   NOT NULL REFERENCES compliance_requirements(requirement_id),
    evidence_id         UUID           NOT NULL REFERENCES evidences(evidence_id) ON DELETE RESTRICT,
    associated_at       TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    PRIMARY KEY (requirement_id, evidence_id)
);

CREATE INDEX idx_compliance_evidences_evidence_id ON compliance_evidences (evidence_id);
```

### 4.2.3 ER 关系图

```
┌──────────────────┐       ┌──────────────────┐
│ block_configura- │       │  material_lots   │
│     tions        │       │                  │
│ block_id (PK)    │──┐    │ lot_id (PK)      │
│ aircraft_type    │  │    │ material_code    │
│ block_name       │  │    │ material_name    │
│ version          │  │    │ supplier_id      │
└──────────────────┘  │    │ manufacture_date │
                      │    │ received_date    │
                      │    │ certificate_no   │
                      │    │ status           │
                      │    └────────┬─────────┘
                      │             │
               ┌──────┴──────┐      │
               │block_materials│    │
               │ block_id (PK)│    │
               │ lot_id (PK)  │────┘
               └─────────────┘
                                   │
                      ┌────────────▼─────────┐
                      │    ndt_records        │
                      │ ndt_record_id (PK)   │
                      │ material_lot_id (FK) │
                      │ test_type            │
                      │ result               │
                      │ inspector            │
                      │ test_date            │
                      │ notes                │
                      └──────────┬───────────┘
                                 │
                      ┌──────────▼───────────┐
                      │ corrective_actions    │
                      │ car_id (PK)          │
                      │ ndt_record_id (FK)   │
                      │ description          │
                      │ status               │
                      │ responsible_person   │
                      │ closed_at            │
                      └──────────────────────┘

┌──────────────────────┐       ┌──────────────────┐
│compliance_requirements│       │    evidences      │
│ requirement_id (PK)  │──┐    │ evidence_id (PK)  │
│ regulation           │  │    │ requirement_id(FK)│
│ description          │  │    │ file_id           │
│ compliance_status    │  │    │ file_name         │
│ responsible_person   │  │    │ bucket            │
│ updated_at           │  │    │ content_type      │
└──────────────────────┘  │    │ file_size         │
                          │    │ upload_timestamp  │
               ┌──────────┴──┐ └────────┬─────────┘
               │compliance_   │          │
               │evidences     │──────────┘
               │requirement_id│
               │evidence_id   │
               └──────────────┘
```

---

# 5. Repository 设计

## 5.1 MaterialLotRepository

```python
class MaterialLotRepository(AsyncpgRepository):
    
    async def save(self, lot: dict) -> None:
        """INSERT material_lots 记录"""
        
    async def get_by_lot_id(self, lot_id: str) -> Optional[dict]:
        """SELECT * FROM material_lots WHERE lot_id = $1"""
        
    async def list_by_block_id(self, block_id: str) -> list[dict]:
        """SELECT ml.* FROM material_lots ml 
           JOIN block_materials bm ON ml.lot_id = bm.lot_id 
           WHERE bm.block_id = $1"""
        
    async def get_next_sequence(self, material_code: str) -> int:
        """SELECT COUNT(*) + 1 FROM material_lots 
           WHERE material_code = $1"""
        
    async def associate_block(self, block_id: str, lot_id: str) -> None:
        """INSERT INTO block_materials (block_id, lot_id) VALUES ($1, $2) 
           ON CONFLICT DO NOTHING"""
```

## 5.2 NDTRecordRepository

```python
class NDTRecordRepository(AsyncpgRepository):
    
    async def save(self, record: dict) -> None:
        """INSERT ndt_records 记录"""
        
    async def get_by_id(self, ndt_record_id: str) -> Optional[dict]:
        """SELECT * FROM ndt_records WHERE ndt_record_id = $1"""
        
    async def list_by_material_lot_id(self, material_lot_id: str) -> list[dict]:
        """SELECT * FROM ndt_records WHERE material_lot_id = $1 
           ORDER BY created_at DESC"""
        
    async def get_result(self, ndt_record_id: str) -> Optional[str]:
        """SELECT result FROM ndt_records WHERE ndt_record_id = $1"""
```

## 5.3 CARRepository

```python
class CARRepository(AsyncpgRepository):
    
    async def save(self, car: dict) -> None:
        """INSERT corrective_actions 记录"""
        
    async def get_by_id(self, car_id: str) -> Optional[dict]:
        """SELECT * FROM corrective_actions WHERE car_id = $1"""
        
    async def list_by_ndt_record_id(self, ndt_record_id: str) -> list[dict]:
        """SELECT * FROM corrective_actions WHERE ndt_record_id = $1 
           ORDER BY created_at DESC"""
        
    async def update_status(self, car_id: str, status: str, closed_at: Optional[str] = None) -> bool:
        """UPDATE corrective_actions SET status = $2, updated_at = NOW(), closed_at = $3 
           WHERE car_id = $1 AND status != 'closed'"""
```

## 5.4 EvidenceRepository

```python
class EvidenceRepository(AsyncpgRepository):
    
    async def save(self, evidence: dict) -> None:
        """INSERT evidences 记录"""
        
    async def get_by_id(self, evidence_id: str) -> Optional[dict]:
        """SELECT * FROM evidences WHERE evidence_id = $1"""
        
    async def list_by_requirement_id(self, requirement_id: str) -> list[dict]:
        """SELECT e.* FROM evidences e 
           JOIN compliance_evidences ce ON e.evidence_id = ce.evidence_id 
           WHERE ce.requirement_id = $1 
           ORDER BY e.upload_timestamp DESC"""
        
    async def associate_requirement(self, requirement_id: str, evidence_id: str) -> None:
        """INSERT INTO compliance_evidences (requirement_id, evidence_id) 
           VALUES ($1, $2) ON CONFLICT DO NOTHING"""
```

## 5.5 ComplianceRepository

```python
class ComplianceRepository(AsyncpgRepository):
    
    async def get_by_requirement_id(self, requirement_id: str) -> Optional[dict]:
        """SELECT * FROM compliance_requirements WHERE requirement_id = $1"""
        
    async def save(self, requirement: dict) -> None:
        """INSERT INTO compliance_requirements ... ON CONFLICT (requirement_id) DO NOTHING"""
        
    async def update_status(self, requirement_id: str, compliance_status: str, 
                           responsible_person: Optional[str] = None) -> bool:
        """UPDATE compliance_requirements SET compliance_status = $2, 
           responsible_person = COALESCE($3, responsible_person), 
           updated_at = NOW() WHERE requirement_id = $1"""
```

---

# 6. 基础设施抽象层设计

## 6.1 EventBus 抽象接口

### 6.1.1 接口定义

```python
from abc import ABC, abstractmethod
from typing import Any, Callable

class EventBusInterface(ABC):
    """EventBus 抽象接口，支持 InMemory 和 NATS 双实现"""
    
    @abstractmethod
    async def publish(self, subject: str, data: dict[str, Any]) -> None:
        """发布事件到指定 subject"""
        
    @abstractmethod
    async def subscribe(self, subject: str, callback: Callable) -> None:
        """订阅指定 subject 的事件"""
        
    @abstractmethod
    async def close(self) -> None:
        """关闭连接"""
```

### 6.1.2 InMemoryEventBus

```python
class InMemoryEventBus(EventBusInterface):
    """进程内事件总线，NATS 不可用时的降级实现"""
    
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}
    
    async def publish(self, subject: str, data: dict[str, Any]) -> None:
        callbacks = self._subscribers.get(subject, [])
        for cb in callbacks:
            try:
                await cb(data)
            except Exception as e:
                logger.warning(f"InMemoryEventBus callback error: {e}")
    
    async def subscribe(self, subject: str, callback: Callable) -> None:
        if subject not in self._subscribers:
            self._subscribers[subject] = []
        self._subscribers[subject].append(callback)
    
    async def close(self) -> None:
        self._subscribers.clear()
```

### 6.1.3 NatsEventBus

```python
class NatsEventBus(EventBusInterface):
    """NATS JetStream 事件总线，生产级持久化实现"""
    
    def __init__(self, servers: str = "nats://localhost:4222"):
        self._servers = servers
        self._nc = None
        self._js = None
    
    async def connect(self) -> None:
        """连接 NATS 并启用 JetStream"""
        import nats as nats_lib
        self._nc = await nats_lib.connect(self._servers)
        self._js = self._nc.jetstream()
        logger.info(f"NatsEventBus connected to {self._servers}")
    
    async def publish(self, subject: str, data: dict[str, Any]) -> None:
        if self._js is None:
            logger.debug(f'JetStream not available, skipping publish to {subject}')
            return
        try:
            payload = json.dumps(data, default=str).encode()
            ack = await self._js.publish(subject, payload)
            logger.info(f'JetStream publish to {subject}, seq={ack.seq}')
        except Exception as e:
            logger.warning(f'JetStream publish failed for {subject}: {e}')
    
    async def subscribe(self, subject: str, callback: Callable) -> None:
        # ... 与现有 event_bus.py 的 subscribe_jetstream 逻辑一致
        pass
    
    async def close(self) -> None:
        if self._nc:
            await self._nc.close()
```

### 6.1.4 EventBus 工厂

```python
# 替换现有 event_bus.py 中的 module-level 实例化
_event_bus: EventBusInterface | None = None

async def get_event_bus() -> EventBusInterface:
    global _event_bus
    if _event_bus is not None:
        return _event_bus
    try:
        nats_bus = NatsEventBus()
        await nats_bus.connect()
        _event_bus = nats_bus
        logger.info("Using NatsEventBus")
    except Exception:
        _event_bus = InMemoryEventBus()
        logger.warning("Using InMemoryEventBus (NATS unavailable)")
    return _event_bus

# 兼容现有代码的 module-level 引用
event_bus = InMemoryEventBus()  # 默认降级实例，lifespan 中替换
```

## 6.2 ObjectStorage 抽象接口

### 6.2.1 接口定义

```python
class ObjectStorageInterface(ABC):
    """ObjectStorage 抽象接口，支持 Local 和 MinIO 双实现"""
    
    @abstractmethod
    async def upload_file(self, bucket: str, file_name: str, 
                         file_data: bytes, content_type: str) -> dict | None:
        """上传文件，返回 {file_id, file_name, bucket, content_type, file_size, upload_timestamp}"""
        
    @abstractmethod
    async def get_presigned_url(self, bucket: str, file_id: str, 
                                expires_hours: int = 1) -> str | None:
        """获取预签名下载 URL"""
```

### 6.2.2 LocalObjectStorage

```python
class LocalObjectStorage(ObjectStorageInterface):
    """本地文件系统存储，MinIO 不可用时的降级实现"""
    
    def __init__(self, base_path: str = "/tmp/aeroforge-evidence"):
        self._base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    async def upload_file(self, bucket: str, file_name: str, 
                         file_data: bytes, content_type: str) -> dict | None:
        file_id = str(uuid.uuid4())
        dir_path = os.path.join(self._base_path, bucket, file_id)
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, file_name)
        with open(file_path, "wb") as f:
            f.write(file_data)
        logger.warning(f"LocalStorage: saved {file_name} to {file_path} (degraded mode)")
        return {
            "file_id": file_id,
            "file_name": file_name,
            "bucket": bucket,
            "content_type": content_type,
            "file_size": len(file_data),
            "upload_timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    async def get_presigned_url(self, bucket: str, file_id: str, 
                                expires_hours: int = 1) -> str | None:
        # 本地存储无预签名 URL，返回 API 端点路径
        return f"/api/v6/aircraft-core/evidence/{file_id}/download"
```

### 6.2.3 MinioObjectStorage

复用现有 `object_storage.py` 中的 `MinioObjectStorage` 类，实现 `ObjectStorageInterface` 接口。

### 6.2.4 ObjectStorage 工厂

```python
_object_storage: ObjectStorageInterface | None = None

def get_object_storage() -> ObjectStorageInterface:
    global _object_storage
    if _object_storage is not None:
        return _object_storage
    try:
        storage = MinioObjectStorage()
        storage._ensure_client()
        if storage._client is not None:
            _object_storage = storage
            logger.info("Using MinioObjectStorage")
            return _object_storage
    except Exception:
        pass
    _object_storage = LocalObjectStorage()
    logger.warning("Using LocalObjectStorage (MinIO unavailable)")
    return _object_storage
```

## 6.3 GraphRepository 抽象接口

### 6.3.1 接口定义

```python
class GraphRepositoryInterface(ABC):
    """GraphRepository 抽象接口，支持 NoOp 和 Neo4j 双实现"""
    
    @abstractmethod
    async def create_relation(self, from_id: str, to_id: str, 
                              relation_type: str, 
                              from_label: str = "Node", 
                              to_label: str = "Node") -> bool:
        """创建两个节点之间的关系 (MERGE 幂等)"""
        
    @abstractmethod
    async def find_relations(self, node_id: str, 
                            relation_type: str | None = None,
                            direction: str = "outgoing") -> list[dict]:
        """查询节点的关联关系"""
```

### 6.3.2 NoOpGraphRepository

```python
class NoOpGraphRepository(GraphRepositoryInterface):
    """NoOp 降级实现，Neo4j 不可用时使用"""
    
    async def create_relation(self, from_id: str, to_id: str, 
                              relation_type: str, **kwargs) -> bool:
        logger.warning(f"NoOpGraphRepository: skipping create_relation({from_id}-{relation_type}->{to_id})")
        return False
    
    async def find_relations(self, node_id: str, **kwargs) -> list[dict]:
        logger.warning(f"NoOpGraphRepository: skipping find_relations({node_id})")
        return []
```

### 6.3.3 Neo4jGraphRepository

```python
class Neo4jGraphRepository(GraphRepositoryInterface):
    """Neo4j 持久化图谱实现"""
    
    async def create_relation(self, from_id: str, to_id: str, 
                              relation_type: str,
                              from_label: str = "Node",
                              to_label: str = "Node") -> bool:
        driver = await get_neo4j_driver()
        if driver is None:
            return False
        try:
            async with driver.session() as session:
                await session.run(
                    f"MERGE (a:{from_label} {{node_id: $from_id}}) "
                    f"MERGE (b:{to_label} {{node_id: $to_id}}) "
                    f"MERGE (a)-[:{relation_type}]->(b)",
                    from_id=from_id,
                    to_id=to_id,
                )
                logger.info(f"Neo4j: created {from_label}-{relation_type}->{to_label}: {from_id}->{to_id}")
                return True
        except Exception as e:
            logger.warning(f"Neo4j create_relation failed: {e}")
            return False
    
    async def find_relations(self, node_id: str, 
                            relation_type: str | None = None,
                            direction: str = "outgoing") -> list[dict]:
        driver = await get_neo4j_driver()
        if driver is None:
            return []
        try:
            rel_pattern = f"-[:{relation_type}]->" if relation_type else "-[r]->"
            if direction == "incoming":
                query = f"MATCH (n)<-{rel_pattern}-(m) WHERE n.node_id = $node_id RETURN m.node_id AS related_id, labels(m) AS labels"
            else:
                query = f"MATCH (n)-{rel_pattern}->(m) WHERE n.node_id = $node_id RETURN m.node_id AS related_id, labels(m) AS labels"
            async with driver.session() as session:
                result = await session.run(query, node_id=node_id)
                relations = []
                async for record in result:
                    relations.append({
                        "related_id": record["related_id"],
                        "labels": record["labels"],
                    })
                return relations
        except Exception as e:
            logger.warning(f"Neo4j find_relations failed: {e}")
            return []
```

### 6.3.4 GraphRepository 工厂

```python
_graph_repo: GraphRepositoryInterface | None = None

async def get_graph_repository() -> GraphRepositoryInterface:
    global _graph_repo
    if _graph_repo is not None:
        return _graph_repo
    driver = await get_neo4j_driver()
    if driver is not None:
        _graph_repo = Neo4jGraphRepository()
        logger.info("Using Neo4jGraphRepository")
    else:
        _graph_repo = NoOpGraphRepository()
        logger.warning("Using NoOpGraphRepository (Neo4j unavailable)")
    return _graph_repo
```

### 6.3.5 Digital Thread 中的 Neo4j 关系类型

| 关系类型 | 源节点 | 目标节点 | 描述 | 创建时机 |
|----------|--------|----------|------|----------|
| `USES_MATERIAL` | Block | MaterialLot | Block 使用的材料批次 | MaterialLot 创建并关联 Block 时 |
| `TESTED_BY` | MaterialLot | NDTRecord | 材料批次的检测记录 | NDTRecord 创建时 |
| `HAS_CAR` | NDTRecord | CAR | 检测记录的纠正措施 | CAR 创建时 |
| `EVIDENCED_BY` | ComplianceRequirement | Evidence | 条款的证据 | Evidence 上传时 |

---

# 7. 前端设计

## 7.1 路由规划

```typescript
// 新增路由
/configuration-trace    → ConfigurationTracePage
/material-trace        → MaterialTracePage
/quality-trace         → QualityTracePage
/certification-trace   → CertificationTracePage
```

## 7.2 API 客户端扩展

### v6Api.ts 新增

```typescript
export const materialApi = {
  createMaterialLot: (data: CreateMaterialLotRequest) =>
    v6Client.post('/aircraft-core/material-lots', data),

  getMaterialLot: (lotId: string) =>
    v6Client.get(`/aircraft-core/material-lots/${lotId}`),

  getBlockMaterials: (blockId: string) =>
    v6Client.get(`/aircraft-core/blocks/${blockId}/materials`),
}

export const qualityApi = {
  createNDTRecord: (data: CreateNDTRecordRequest) =>
    v6Client.post('/aircraft-core/ndt-records', data),

  getNDTRecord: (ndtRecordId: string) =>
    v6Client.get(`/aircraft-core/ndt-records/${ndtRecordId}`),

  createCAR: (data: CreateCARRequest) =>
    v6Client.post('/aircraft-core/corrective-actions', data),

  updateCAR: (carId: string, data: UpdateCARRequest) =>
    v6Client.patch(`/aircraft-core/corrective-actions/${carId}`, data),

  getQualityThread: (lotId: string) =>
    v6Client.get(`/aircraft-core/material-lots/${lotId}/quality`),
}

export const certificationApi = {
  getCompliance: (requirementId: string) =>
    v6Client.get(`/aircraft-core/compliance/${requirementId}`),

  updateCompliance: (requirementId: string, data: UpdateComplianceRequest) =>
    v6Client.patch(`/aircraft-core/compliance/${requirementId}`, data),

  uploadEvidence: (file: File, requirementId: string) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('requirement_id', requirementId)
    return v6Client.post('/aircraft-core/evidence/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  getEvidence: (evidenceId: string) =>
    v6Client.get(`/aircraft-core/evidence/${evidenceId}`),
}
```

### types.ts 新增

```typescript
// Material Thread
export interface MaterialLot {
  lot_id: string
  material_code: string
  material_name: string
  supplier_id: string
  manufacture_date: string
  received_date: string
  certificate_no: string
  status: 'received' | 'inspected' | 'accepted' | 'rejected' | 'quarantined'
  block_id?: string
  created_at: string
  updated_at: string
}

export interface CreateMaterialLotRequest {
  material_code: string
  material_name: string
  supplier_id: string
  manufacture_date: string
  received_date: string
  certificate_no: string
  block_id?: string
}

// Quality Thread
export interface NDTRecord {
  ndt_record_id: string
  material_lot_id: string
  test_type: 'ultrasonic' | 'radiographic' | 'penetrant' | 'magnetic_particle' | 'eddy_current'
  result: 'pass' | 'fail' | 'conditional'
  inspector: string
  test_date: string
  notes?: string
  created_at: string
}

export interface CorrectiveActionRequest {
  car_id: string
  ndt_record_id: string
  description: string
  status: 'open' | 'in_progress' | 'closed'
  responsible_person: string
  created_at: string
  updated_at: string
  closed_at?: string
}

export interface QualityThreadResponse {
  material_lot: MaterialLot
  ndt_records: (NDTRecord & { corrective_actions: CorrectiveActionRequest[] })[]
}

// Certification Thread
export interface ComplianceRequirement {
  requirement_id: string
  regulation: string
  description: string
  compliance_status: 'compliant' | 'non_compliant' | 'partial' | 'pending'
  responsible_person?: string
  updated_at: string
  evidence_items: Evidence[]
}

export interface Evidence {
  evidence_id: string
  requirement_id: string
  file_id: string
  file_name: string
  bucket: string
  content_type: string
  file_size: number
  upload_timestamp: string
  presigned_url?: string
}
```

## 7.3 Trace 页面组件设计

### 7.3.1 通用布局模式

4 个 Trace 页面共享统一布局：左侧追溯树 + 右侧详情面板。

```
┌──────────────────────────────────────────────────────────────┐
│ Breadcrumb: AeroForge-X > V6 Programs > [Trace Page Name]   │
├──────────────────────────────────────────────────────────────┤
│ Title + Description                                          │
├──────────────────────┬───────────────────────────────────────┤
│                      │                                       │
│   Trace Tree/Graph   │       Detail Panel                    │
│   (Ant Design Tree   │   (Ant Design Descriptions)           │
│    or Steps)         │                                       │
│                      │   [Node Details]                      │
│   - Node A           │   - Field 1: Value 1                 │
│     - Node B         │   - Field 2: Value 2                 │
│       - Node C       │   - ...                               │
│                      │                                       │
├──────────────────────┴───────────────────────────────────────┤
│ Statistics Row (Cards)                                        │
└──────────────────────────────────────────────────────────────┘
```

### 7.3.2 ConfigurationTracePage

- **数据源**: `configApi.getHierarchy(aircraftType)`
- **追溯树**: Aircraft → Block → Version (复用现有 Tree 组件)
- **详情面板**: Block 配置信息 (复用现有 Descriptions 组件)

### 7.3.3 MaterialTracePage

- **数据源**: `materialApi.getBlockMaterials(blockId)` → `materialApi.getMaterialLot(lotId)`
- **追溯树**: Block → MaterialLot 列表
- **详情面板**: MaterialLot 完整信息 (lot_id, material_code, supplier_id, certificate_no, status)
- **交互**: 点击 MaterialLot 节点 → 跳转 Quality Trace 页面

### 7.3.4 QualityTracePage

- **数据源**: `qualityApi.getQualityThread(lotId)`
- **追溯树**: MaterialLot → NDT → CAR (使用 Ant Design Steps 组件)
- **详情面板**: 
  - NDT 详情: test_type, result, inspector, test_date
  - CAR 详情: description, status, responsible_person, closed_at
- **状态标识**: 
  - NDT pass → 绿色
  - NDT fail/conditional → 红色/黄色
  - CAR open → 红色
  - CAR closed → 绿色
- **空状态**: MaterialLot 无 NDT 记录时显示 "未检测" 灰色/虚线

### 7.3.5 CertificationTracePage

- **数据源**: `certificationApi.getCompliance(requirementId)`
- **追溯树**: Requirement → Evidence 列表
- **详情面板**:
  - Compliance 信息: compliance_status, responsible_person, updated_at
  - Evidence 列表: file_name, content_type, file_size, presigned_url
- **状态标识**:
  - compliant → 绿色
  - non_compliant → 红色
  - partial → 黄色
  - pending → 灰色
- **操作**: 上传新证据按钮 → Modal 表单

---

# 8. Sprint 执行计划

## 8.1 任务分解与依赖

### Sprint-DT01: Material Thread (P1)

| 任务ID | 任务描述 | 依赖 | 交付物 |
|--------|----------|------|--------|
| DT01-01 | 创建 DDL migration `008_digital_thread_tables.sql` | 无 | SQL 文件 |
| DT01-02 | 实现 `MaterialLot` dataclass + `to_dict()` | DT01-01 | domain/models/material_lot.py |
| DT01-03 | 实现 `MaterialLotCreatedEvent` Pydantic model | 无 | domain/events/material_lot_created_event.py |
| DT01-04 | 实现 `MaterialLotRepository` (AsyncpgRepository) | DT01-01 | infrastructure/repositories/material_lot_repository.py |
| DT01-05 | 实现 `material_controller.py` (POST/GET endpoints) | DT01-02, DT01-03, DT01-04 | api/v6/material_controller.py |
| DT01-06 | 在 `main.py` 注册 material_router | DT01-05 | main.py 更新 |
| DT01-07 | 集成测试: MaterialLot CRUD + Block 关联 + Event 发布 | DT01-06 | 测试脚本 |

### Sprint-DT02: Quality Thread (P1)

| 任务ID | 任务描述 | 依赖 | 交付物 |
|--------|----------|------|--------|
| DT02-01 | 实现 `NDTRecord` dataclass + `to_dict()` | DT01-02 | domain/models/ndt_record.py |
| DT02-02 | 实现 `CorrectiveActionRequest` dataclass + `to_dict()` | DT02-01 | domain/models/corrective_action_request.py |
| DT02-03 | 实现 `NDTCompletedEvent` / `CARCreatedEvent` / `CARClosedEvent` | 无 | domain/events/*.py |
| DT02-04 | 实现 `NDTRecordRepository` | DT01-01 | infrastructure/repositories/ndt_record_repository.py |
| DT02-05 | 实现 `CARRepository` | DT01-01 | infrastructure/repositories/car_repository.py |
| DT02-06 | 实现 `quality_controller.py` | DT02-01~05 | api/v6/quality_controller.py |
| DT02-07 | 在 `main.py` 注册 quality_router | DT02-06 | main.py 更新 |
| DT02-08 | 集成测试: NDT + CAR CRUD + Quality Thread 查询 + Event | DT02-07 | 测试脚本 |

### Sprint-DT03: Certification Thread (P1)

| 任务ID | 任务描述 | 依赖 | 交付物 |
|--------|----------|------|--------|
| DT03-01 | 实现 `ComplianceRequirement` dataclass + `to_dict()` | 无 | domain/models/compliance_requirement.py |
| DT03-02 | 实现 `Evidence` dataclass + `to_dict()` | 无 | domain/models/evidence.py |
| DT03-03 | 实现 `EvidenceUploadedEvent` | 无 | domain/events/evidence_uploaded_event.py |
| DT03-04 | 实现 `EvidenceRepository` | DT01-01 | infrastructure/repositories/evidence_repository.py |
| DT03-05 | 实现 `ComplianceRepository` | DT01-01 | infrastructure/repositories/compliance_repository.py |
| DT03-06 | 重构 `evidence_controller.py` 使用 ObjectStorage 抽象 | INF01-01 | api/v6/evidence_controller.py |
| DT03-07 | 实现 `certification_controller.py` | DT03-01~06 | api/v6/certification_controller.py |
| DT03-08 | 在 `main.py` 注册 certification_router | DT03-07 | main.py 更新 |
| DT03-09 | 集成测试: Evidence upload + Compliance query + Event | DT03-08 | 测试脚本 |

### Sprint-DT04: React Trace Pages (P1)

| 任务ID | 任务描述 | 依赖 | 交付物 |
|--------|----------|------|--------|
| DT04-01 | 扩展 `v6Api.ts` 新增 material/quality/certification API | DT01-07, DT02-08 | api/v6Api.ts |
| DT04-02 | 扩展 `types.ts` 新增 TypeScript 类型定义 | DT04-01 | api/types.ts |
| DT04-03 | 实现 `ConfigurationTracePage.tsx` | DT04-01 | Trace 页面 |
| DT04-04 | 实现 `MaterialTracePage.tsx` | DT04-01 | Trace 页面 |
| DT04-05 | 实现 `QualityTracePage.tsx` | DT04-01 | Trace 页面 |
| DT04-06 | 实现 `CertificationTracePage.tsx` | DT04-01 | Trace 页面 |
| DT04-07 | 配置路由 (4 个 Trace 页面) | DT04-03~06 | 路由配置 |
| DT04-08 | E2E 验证: 4 个 Trace 页面完整追溯链展示 | DT04-07 | 验证截图 |

### Sprint-INF01: MinIO Integration (P2)

| 任务ID | 任务描述 | 依赖 | 交付物 |
|--------|----------|------|--------|
| INF01-01 | 定义 `ObjectStorageInterface` ABC | 无 | infrastructure/adapters/object_storage_interface.py |
| INF01-02 | 实现 `LocalObjectStorage` | INF01-01 | infrastructure/adapters/local_object_storage.py |
| INF01-03 | 重构 `MinioObjectStorage` 实现 `ObjectStorageInterface` | INF01-01 | infrastructure/adapters/minio_object_storage.py |
| INF01-04 | 实现 ObjectStorage 工厂方法 | INF01-02, INF01-03 | infrastructure/adapters/ |
| INF01-05 | 降级测试: MinIO 不可用时 LocalStorage 正常工作 | INF01-04 | 测试脚本 |

### Sprint-INF02: Event Contracts (P2)

| 任务ID | 任务描述 | 依赖 | 交付物 |
|--------|----------|------|--------|
| INF02-01 | 创建 `contracts/events/` 目录 | 无 | 目录结构 |
| INF02-02 | 编写 6 个事件契约 JSON Schema 文件 | DT01-03, DT02-03, DT03-03 | contracts/events/*.json |
| INF02-03 | 编写 `DigitalTwinSyncEvent.json` 契约 | 无 | contracts/events/DigitalTwinSyncEvent.json |
| INF02-04 | Schema 验证测试: 事件 payload 符合契约 | INF02-02 | 测试脚本 |

### Sprint-INF03: NATS Adapter (P2)

| 任务ID | 任务描述 | 依赖 | 交付物 |
|--------|----------|------|--------|
| INF03-01 | 定义 `EventBusInterface` ABC | 无 | infrastructure/adapters/event_bus_interface.py |
| INF03-02 | 实现 `InMemoryEventBus` | INF03-01 | infrastructure/adapters/in_memory_event_bus.py |
| INF03-03 | 实现 `NatsEventBus` (重构现有 event_bus.py) | INF03-01 | infrastructure/adapters/nats_event_bus.py |
| INF03-04 | 实现 EventBus 工厂方法 | INF03-02, INF03-03 | infrastructure/adapters/ |
| INF03-05 | 更新所有 Controller 使用 EventBusInterface | INF03-04 | controllers 更新 |
| INF03-06 | 降级测试: NATS 不可用时 InMemoryEventBus 正常工作 | INF03-05 | 测试脚本 |

### Sprint-INF04: Neo4j Adapter (P3)

| 任务ID | 任务描述 | 依赖 | 交付物 |
|--------|----------|------|--------|
| INF04-01 | 定义 `GraphRepositoryInterface` ABC | 无 | infrastructure/adapters/graph_repository_interface.py |
| INF04-02 | 实现 `NoOpGraphRepository` | INF04-01 | infrastructure/adapters/noop_graph_repository.py |
| INF04-03 | 实现 `Neo4jGraphRepository` (重构现有 graph_client.py) | INF04-01 | infrastructure/adapters/neo4j_graph_repository.py |
| INF04-04 | 实现 GraphRepository 工厂方法 | INF04-02, INF04-03 | infrastructure/adapters/ |
| INF04-05 | 更新所有 Controller 使用 GraphRepositoryInterface | INF04-04 | controllers 更新 |
| INF04-06 | 降级测试: Neo4j 不可用时 NoOpGraphRepository 正常工作 | INF04-05 | 测试脚本 |

### Sprint-INF05: Physics Twin Contract (P3)

| 任务ID | 任务描述 | 依赖 | 交付物 |
|--------|----------|------|--------|
| INF05-01 | 编写 `DigitalTwinSyncEvent.json` 契约 (如 INF02-03 未完成) | 无 | contracts/events/ |
| INF05-02 | 编写 ConfigurationUpdatedEvent → DigitalTwinSyncEvent 映射文档 | INF05-01 | contracts/events/mapping.md |

## 8.2 执行顺序

```
Phase 1 — 业务主线 (串行):
  DT01 → DT02 → DT03

Phase 2 — 前端 + 基础设施 (并行):
  DT04 (依赖 DT01/DT02/DT03 API)
  INF01 (依赖 DT03 evidence upload)
  INF02 (依赖 DT01/DT02 event 定义)

Phase 3 — 高级适配层 (并行):
  INF03 (依赖 INF02 契约)
  INF04 (独立)
  INF05 (独立)

最终验证:
  端到端验证场景:
  B737-000001 → MAIN-WING → AL-2024-001 → Supplier-A 
  → NDT-001 → CAR-001 → Evidence-Package → FAA Compliance
```

## 8.3 验收标准映射

| 验收级别 | 必须通过的 Sprint | 验证方式 |
|----------|-------------------|----------|
| PASS | DT01 + DT02 + DT03 + DT04 | curl 命令验证 + React 页面可视化 |
| A | PASS + INF01 + INF02 + INF03 | MinIO/EventBus 降级测试 + Schema 验证 |
| A+ | A + INF04 + INF05 | Neo4j 降级测试 + DigitalTwinSyncEvent 契约 |

---

# 9. 与现有代码的兼容性

## 9.1 不变更的现有代码

| 文件 | 说明 |
|------|------|
| `api/v2/*` | EV-4 API 端点完全保留 |
| `domain/services/configuration_management/*` | 配置管理服务不变更 |
| `domain/services/supplier/material_lot_tracker_service.py` | 现有 MaterialLot domain service 保留，DT01 新建独立的 domain model |
| `domain/services/supplier/ndt_integration_service.py` | 现有 NDT domain service 保留，DT02 新建独立的 domain model |
| `infrastructure/database.py` | PostgreSQL/Neo4j 连接池不变更 |
| `infrastructure/repositories/base_repository.py` | 基类不变更，新 Repository 继承 AsyncpgRepository |
| `deploy/docker-compose.ev45.yml` | 不新增容器，不新增服务 |

## 9.2 重构的现有代码

| 文件 | 重构内容 | Sprint |
|------|----------|--------|
| `infrastructure/event_bus.py` | 提取 `EventBusInterface` ABC，现有逻辑迁移到 `NatsEventBus`，新增 `InMemoryEventBus` | INF03 |
| `infrastructure/graph_client.py` | 提取 `GraphRepositoryInterface` ABC，现有逻辑迁移到 `Neo4jGraphRepository`，新增 `NoOpGraphRepository` | INF04 |
| `infrastructure/object_storage.py` | 提取 `ObjectStorageInterface` ABC，现有逻辑迁移到 `MinioObjectStorage`，新增 `LocalObjectStorage` | INF01 |
| `api/v6/evidence_controller.py` | 使用 `ObjectStorageInterface` 替代直接 `MinioObjectStorage` 引用 | INF01 |
| `api/v6/config_identity_controller.py` | 使用 `GraphRepositoryInterface` 替代直接 `graph_client` 引用 | INF04 |
| `main.py` | 注册新 router (material/quality/certification) | DT01/DT02/DT03 |

## 9.3 NATS JetStream Stream 扩展

现有 Stream（由 `init_nats_streams.py` 创建）:

| Stream | Subjects | 状态 |
|--------|----------|------|
| `AEROFORGE_CONFIG` | `aeroforge.config.>` | 已有 |
| `AEROFORGE_MATERIAL` | `aeroforge.material.>` | 需新增 |
| `AEROFORGE_QUALITY` | `aeroforge.quality.>` | 需新增 |
| `AEROFORGE_CERT` | `aeroforge.cert.>` | 需新增 |

需更新 `scripts/init_nats_streams.py` 添加 3 个新 Stream 定义。

---

# 10. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| NATS JetStream 新 Stream 创建失败 | 事件无法持久化 | 降级到 InMemoryEventBus，业务 API 不受影响 |
| Neo4j 写入超时 | 图谱关系缺失 | NoOpGraphRepository 降级，业务数据在 PostgreSQL 中完整 |
| MinIO 不可用 | 证据文件无法上传 | LocalObjectStorage 降级，文件存本地磁盘 |
| lot_id 序列号并发冲突 | 重复 lot_id | 使用 PostgreSQL `SELECT COUNT(*) + 1` + `INSERT ... ON CONFLICT DO NOTHING` + 重试 |
| DDL migration 与现有表冲突 | 数据库初始化失败 | 使用 `IF NOT EXISTS` 防护，独立 migration 文件 |