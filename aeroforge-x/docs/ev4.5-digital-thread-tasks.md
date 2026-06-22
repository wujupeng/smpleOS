# AeroForge-X EV-4.5 Digital Thread Foundation — 编码任务清单

**Sprint**: EV-4.5 Digital Thread Foundation  
**目标 TRL**: 6.0 → 6.5  
**日期**: 2026-06-22  
**关联需求**: `docs/specs/ev4.5-digital-thread-spec.md`  
**关联设计**: `docs/specs/ev4.5-digital-thread-design.md`  
**前置基线**: EV-4.5 Architecture Activation（7 容器 healthy，NATS/Neo4j/MinIO 已部署验证）  
**核心原则**: 业务驱动，不是技术驱动

---

## 验收场景

```
B737-000001 → MAIN-WING → AL-2024-001 → Supplier-A → NDT-001 → CAR-001 → Evidence-Package → FAA Compliance
```

**验收级别**:
- **PASS**: Material Thread + Quality Thread + Certification Thread + React Trace 页面
- **A**: PASS + MinIO 接入 + 事件契约 + EventBus 抽象
- **A+**: A + Neo4j 适配层 + Physics Twin 契约

---

## Phase 1 — 业务主线 (串行)

### Sprint-DT01: Material Thread

> 目标：Block → MaterialLot 关联关系，材料批次 CRUD + 事件发布

#### Task-DT01-01: 创建 DDL migration 文件
- **Sprint**: DT01 | **优先级**: P0 | **预估**: 1h
- **依赖**: 无
- **实现步骤**:
  - 创建 `deploy/migrations/v6_4/008_digital_thread_tables.sql`
  - `material_lots` 表: lot_id (PK), material_code, material_name, supplier_id, manufacture_date, received_date, certificate_no, status, created_at, updated_at
  - `block_materials` 关联表: block_id, lot_id (复合 PK), created_at
  - `ndt_records` 表: ndt_record_id (PK UUID), material_lot_id (FK), test_type, result, inspector, test_date, notes, created_at
  - `corrective_actions` 表: car_id (PK UUID), ndt_record_id (FK), description, status, responsible_person, created_at, updated_at, closed_at
  - `compliance_requirements` 表: requirement_id (PK), regulation, description, compliance_status, responsible_person, updated_at
  - `evidences` 表: evidence_id (PK UUID), requirement_id (FK), file_id, file_name, bucket, content_type, file_size, upload_timestamp
  - `compliance_evidences` 关联表: requirement_id, evidence_id (复合 PK)
  - 所有 CREATE TABLE 使用 `IF NOT EXISTS`
  - 添加 CHECK 约束: status 枚举值、result 枚举值、file_size > 0
  - 添加索引: material_lots(material_code), ndt_records(material_lot_id), corrective_actions(ndt_record_id), evidences(requirement_id)
- **验证**: 在远程 PostgreSQL 执行 DDL 无报错，表创建成功

#### Task-DT01-02: 实现 MaterialLot domain model
- **Sprint**: DT01 | **优先级**: P0 | **预估**: 1h
- **依赖**: DT01-01
- **实现步骤**:
  - 创建 `services/aircraft-core-service/src/domain/models/` 目录
  - 创建 `domain/models/__init__.py` (空文件)
  - 创建 `domain/models/material_lot.py`
  - `MaterialLot` dataclass: lot_id, material_code, material_name, supplier_id, manufacture_date, received_date, certificate_no, status, created_at, updated_at
  - `to_dict()` 方法返回 dict
  - `@classmethod from_row(row: Record)` 工厂方法
  - status 默认值 "received"
- **验证**: Python import 无报错，to_dict() 返回正确结构

#### Task-DT01-03: 实现 MaterialLotCreatedEvent
- **Sprint**: DT01 | **优先级**: P0 | **预估**: 0.5h
- **依赖**: 无
- **实现步骤**:
  - 创建 `services/aircraft-core-service/src/domain/events/material_lot_created_event.py`
  - `MaterialLotCreatedEvent(BaseModel)`: event_id (UUID), event_type, lot_id, material_code, supplier_id, block_id, timestamp
  - event_type 固定值 "MaterialLotCreated"
  - event_id 默认 uuid4()
  - timestamp 默认 datetime.utcnow()
- **验证**: Pydantic model 实例化无报错

#### Task-DT01-04: 实现 MaterialLotRepository
- **Sprint**: DT01 | **优先级**: P0 | **预估**: 1.5h
- **依赖**: DT01-01
- **实现步骤**:
  - 创建 `services/aircraft-core-service/src/infrastructure/repositories/material_lot_repository.py`
  - 继承 `AsyncpgRepository` 基类（复用 `_execute`/`_fetchrow`/`_fetch`）
  - `async def create(material_code, material_name, supplier_id, manufacture_date, received_date, certificate_no, block_id=None) -> MaterialLot`
    - 自动生成 lot_id: `{material_code}-{sequence:03d}`，基于 `SELECT COUNT(*) FROM material_lots WHERE material_code = $1`
    - INSERT material_lots
    - 如果 block_id 不为空: INSERT block_materials
    - 返回 MaterialLot
  - `async def find_by_id(lot_id: str) -> Optional[MaterialLot]`
  - `async def find_by_block(block_id: str) -> List[MaterialLot]`
    - JOIN block_materials
  - `async def find_all(limit=100, offset=0) -> List[MaterialLot]`
- **验证**: Repository 方法签名与设计一致

#### Task-DT01-05: 实现 material_controller.py
- **Sprint**: DT01 | **优先级**: P0 | **预估**: 1.5h
- **依赖**: DT01-02, DT01-03, DT01-04
- **实现步骤**:
  - 创建 `services/aircraft-core-service/src/api/v6/material_controller.py`
  - `APIRouter(prefix="/api/v6/aircraft-core", tags=["Material Thread"])`
  - `POST /material-lots` — 创建 MaterialLot + Block 关联 + 发布 MaterialLotCreated 事件
    - Pydantic 请求模型: CreateMaterialLotRequest (material_code, material_name, supplier_id, manufacture_date, received_date, certificate_no, block_id?)
    - 调用 MaterialLotRepository.create()
    - 调用 EventBus.publish("aeroforge.material.lot.created", event.model_dump_json())
    - 返回 201 + MaterialLot JSON
  - `GET /material-lots/{lot_id}` — 查询指定 MaterialLot
    - 返回 200 + MaterialLot JSON
    - 不存在返回 404
  - `GET /blocks/{block_id}/materials` — 查询 Block 关联的 MaterialLot 列表
    - 返回 200 + MaterialLot 数组
    - 无关联返回空数组 []
  - `GET /material-lots` — 查询所有 MaterialLot（分页）
    - 返回 200 + MaterialLot 数组
  - module-level 实例化: `_material_repo = MaterialLotRepository()`
  - EventBus 降级: publish 失败记录 WARNING 日志，不影响 HTTP 响应
- **验证**: API 端点签名与需求 DT-REQ-01~06 一致，无 DELETE 端点

#### Task-DT01-06: 在 main.py 注册 material_router
- **Sprint**: DT01 | **优先级**: P0 | **预估**: 0.5h
- **依赖**: DT01-05
- **实现步骤**:
  - 编辑 `services/aircraft-core-service/src/main.py`
  - 添加 `from api.v6.material_controller import router as material_router`
  - 添加 `app.include_router(material_router)`
- **验证**: 服务启动无报错，/docs 显示新端点

#### Task-DT01-07: 远程部署 + 集成测试 Material Thread
- **Sprint**: DT01 | **优先级**: P0 | **预估**: 2h
- **依赖**: DT01-06
- **实现步骤**:
  - 执行 DDL migration 在远程 PostgreSQL
  - 重新构建 aircraft-core Docker 镜像
  - 重启 aircraft-core 容器
  - curl 测试:
    - `POST /material-lots` (material_code=AL-2024, block_id=B737-MAIN-WING) → 201, lot_id=AL-2024-001
    - `GET /material-lots/AL-2024-001` → 200, 完整 MaterialLot JSON
    - `GET /blocks/B737-MAIN-WING/materials` → 200, 包含 AL-2024-001
    - `POST /material-lots` 缺少必填字段 → 422
    - `GET /material-lots/NONEXISTENT` → 404
  - 验证 NATS 事件发布 (aeroforge.material.lot.created)
- **验证**: 所有 curl 测试通过，NATS 收到事件

---

### Sprint-DT02: Quality Thread

> 目标：MaterialLot → NDTRecord → CAR 质量追溯链路

#### Task-DT02-01: 实现 NDTRecord domain model
- **Sprint**: DT02 | **优先级**: P0 | **预估**: 1h
- **依赖**: DT01-02
- **实现步骤**:
  - 创建 `domain/models/ndt_record.py`
  - `NDTRecord` dataclass: ndt_record_id, material_lot_id, test_type, result, inspector, test_date, notes, created_at
  - `to_dict()` + `from_row()` 方法
  - test_type 枚举: ultrasonic/radiographic/penetrant/magnetic_particle/eddy_current
  - result 枚举: pass/fail/conditional
- **验证**: Python import 无报错

#### Task-DT02-02: 实现 CorrectiveActionRequest domain model
- **Sprint**: DT02 | **优先级**: P0 | **预估**: 1h
- **依赖**: DT02-01
- **实现步骤**:
  - 创建 `domain/models/corrective_action_request.py`
  - `CorrectiveActionRequest` dataclass: car_id, ndt_record_id, description, status, responsible_person, created_at, updated_at, closed_at
  - `to_dict()` + `from_row()` 方法
  - status 枚举: open/in_progress/closed
  - closed_at 仅 status="closed" 时有值
- **验证**: Python import 无报错

#### Task-DT02-03: 实现 Quality Thread 事件模型
- **Sprint**: DT02 | **优先级**: P0 | **预估**: 1h
- **依赖**: 无
- **实现步骤**:
  - 创建 `domain/events/ndt_completed_event.py`
    - `NDTCompletedEvent(BaseModel)`: event_id, event_type, ndt_record_id, material_lot_id, test_type, result, timestamp
  - 创建 `domain/events/car_created_event.py`
    - `CARCreatedEvent(BaseModel)`: event_id, event_type, car_id, ndt_record_id, description, status, timestamp
  - 创建 `domain/events/car_closed_event.py`
    - `CARClosedEvent(BaseModel)`: event_id, event_type, car_id, closed_by, timestamp
- **验证**: Pydantic model 实例化无报错

#### Task-DT02-04: 实现 NDTRecordRepository
- **Sprint**: DT02 | **优先级**: P0 | **预估**: 1h
- **依赖**: DT01-01
- **实现步骤**:
  - 创建 `infrastructure/repositories/ndt_record_repository.py`
  - `async def create(material_lot_id, test_type, result, inspector, test_date, notes=None) -> NDTRecord`
    - ndt_record_id 自动生成 uuid4()
    - 校验 material_lot_id 存在（不存在抛异常）
  - `async def find_by_id(ndt_record_id: str) -> Optional[NDTRecord]`
  - `async def find_by_material_lot(material_lot_id: str) -> List[NDTRecord]`
- **验证**: Repository 方法签名与设计一致

#### Task-DT02-05: 实现 CARRepository
- **Sprint**: DT02 | **优先级**: P0 | **预估**: 1h
- **依赖**: DT01-01
- **实现步骤**:
  - 创建 `infrastructure/repositories/car_repository.py`
  - `async def create(ndt_record_id, description, responsible_person) -> CorrectiveActionRequest`
    - car_id 自动生成 uuid4()
    - 校验 ndt_record_id 存在
    - 校验对应 NDT result != "pass"（pass 时拒绝创建 CAR）
  - `async def find_by_id(car_id: str) -> Optional[CorrectiveActionRequest]`
  - `async def find_by_ndt_record(ndt_record_id: str) -> List[CorrectiveActionRequest]`
  - `async def update_status(car_id: str, status: str, closed_by: str = None) -> CorrectiveActionRequest`
    - 校验当前 status != "closed"（已关闭不能再次关闭）
    - 如果 status="closed": 设置 closed_at = NOW()
- **验证**: Repository 方法签名与设计一致

#### Task-DT02-06: 实现 quality_controller.py
- **Sprint**: DT02 | **优先级**: P0 | **预估**: 2h
- **依赖**: DT02-01~05
- **实现步骤**:
  - 创建 `api/v6/quality_controller.py`
  - `APIRouter(prefix="/api/v6/aircraft-core", tags=["Quality Thread"])`
  - `POST /ndt-records` — 创建 NDT 记录 + 发布 NDTCompleted 事件
    - Pydantic 请求: CreateNDTRecordRequest (material_lot_id, test_type, result, inspector, test_date, notes?)
    - material_lot_id 不存在 → 404
    - 返回 201 + NDTRecord JSON
  - `POST /corrective-actions` — 创建 CAR + 发布 CARCreated 事件
    - Pydantic 请求: CreateCARRequest (ndt_record_id, description, responsible_person)
    - ndt_record_id 不存在 → 404
    - NDT result 为 pass → 400 "CAR can only be created for failed or conditional NDT results"
    - 返回 201 + CAR JSON
  - `PATCH /corrective-actions/{car_id}` — 更新 CAR 状态 + 发布 CARClosed 事件
    - Pydantic 请求: UpdateCARRequest (status, closed_by?)
    - car_id 不存在 → 404
    - 已关闭 → 400 "CAR is already closed"
    - 返回 200 + CAR JSON
  - `GET /material-lots/{lot_id}/quality` — 查询质量链路
    - 返回 200 + { lot_id, ndt_records: [{..., cars: [...]}] }
    - 无 NDT 记录 → ndt_records 为空数组
  - `GET /ndt-records/{ndt_record_id}` — 查询 NDT 记录
    - 返回 200 + NDTRecord JSON
  - module-level 实例化
- **验证**: API 端点与需求 DT-REQ-07~12 一致，无 DELETE 端点

#### Task-DT02-07: 在 main.py 注册 quality_router
- **Sprint**: DT02 | **优先级**: P0 | **预估**: 0.5h
- **依赖**: DT02-06
- **实现步骤**:
  - 编辑 main.py
  - 添加 `from api.v6.quality_controller import router as quality_router`
  - 添加 `app.include_router(quality_router)`
- **验证**: 服务启动无报错

#### Task-DT02-08: 远程部署 + 集成测试 Quality Thread
- **Sprint**: DT02 | **优先级**: P0 | **预估**: 2h
- **依赖**: DT02-07
- **实现步骤**:
  - 重新构建 aircraft-core Docker 镜像
  - 重启 aircraft-core 容器
  - curl 测试:
    - `POST /ndt-records` (material_lot_id=AL-2024-001, result=conditional) → 201
    - `POST /corrective-actions` (ndt_record_id=..., description="Minor porosity") → 201
    - `PATCH /corrective-actions/{car_id}` (status=closed) → 200
    - `GET /material-lots/AL-2024-001/quality` → 200, 完整链路
    - `POST /corrective-actions` (NDT result=pass) → 400
    - `PATCH /corrective-actions/{car_id}` (已关闭) → 400
  - 验证 NATS 事件: aeroforge.quality.ndt.completed, aeroforge.quality.car.created, aeroforge.quality.car.closed
- **验证**: 所有 curl 测试通过

---

### Sprint-DT03: Certification Thread

> 目标：Requirement → Evidence → Compliance 适航追溯链路

#### Task-DT03-01: 实现 ComplianceRequirement domain model
- **Sprint**: DT03 | **优先级**: P0 | **预估**: 1h
- **依赖**: 无
- **实现步骤**:
  - 创建 `domain/models/compliance_requirement.py`
  - `ComplianceRequirement` dataclass: requirement_id, regulation, description, compliance_status, responsible_person, updated_at
  - `to_dict()` + `from_row()` 方法
  - compliance_status 枚举: compliant/non_compliant/partial/pending
- **验证**: Python import 无报错

#### Task-DT03-02: 实现 Evidence domain model
- **Sprint**: DT03 | **优先级**: P0 | **预估**: 1h
- **依赖**: 无
- **实现步骤**:
  - 创建 `domain/models/evidence.py`
  - `Evidence` dataclass: evidence_id, requirement_id, file_id, file_name, bucket, content_type, file_size, upload_timestamp
  - `to_dict()` + `from_row()` 方法
- **验证**: Python import 无报错

#### Task-DT03-03: 实现 EvidenceUploadedEvent
- **Sprint**: DT03 | **优先级**: P0 | **预估**: 0.5h
- **依赖**: 无
- **实现步骤**:
  - 创建 `domain/events/evidence_uploaded_event.py`
  - `EvidenceUploadedEvent(BaseModel)`: event_id, event_type, evidence_id, requirement_id, file_id, file_name, timestamp
- **验证**: Pydantic model 实例化无报错

#### Task-DT03-04: 实现 EvidenceRepository
- **Sprint**: DT03 | **优先级**: P0 | **预估**: 1h
- **依赖**: DT01-01
- **实现步骤**:
  - 创建 `infrastructure/repositories/evidence_repository.py`
  - `async def create(evidence_id, requirement_id, file_id, file_name, bucket, content_type, file_size) -> Evidence`
  - `async def find_by_id(evidence_id: str) -> Optional[Evidence]`
  - `async def find_by_requirement(requirement_id: str) -> List[Evidence]`
- **验证**: Repository 方法签名与设计一致

#### Task-DT03-05: 实现 ComplianceRepository
- **Sprint**: DT03 | **优先级**: P0 | **预估**: 1h
- **依赖**: DT01-01
- **实现步骤**:
  - 创建 `infrastructure/repositories/compliance_repository.py`
  - `async def find_or_create(requirement_id: str, regulation: str, description: str) -> ComplianceRequirement`
    - 先查询，不存在则创建（compliance_status="pending"）
  - `async def find_by_id(requirement_id: str) -> Optional[ComplianceRequirement]`
  - `async def update_compliance_status(requirement_id: str, compliance_status: str, responsible_person: str = None) -> ComplianceRequirement`
  - `async def find_evidences(requirement_id: str) -> List[Evidence]`
- **验证**: Repository 方法签名与设计一致

#### Task-DT03-06: 实现 certification_controller.py
- **Sprint**: DT03 | **优先级**: P0 | **预估**: 2h
- **依赖**: DT03-01~05
- **实现步骤**:
  - 创建 `api/v6/certification_controller.py`
  - `APIRouter(prefix="/api/v6/aircraft-core", tags=["Certification Thread"])`
  - `POST /evidence/upload` — 上传证据文件 + 创建 Evidence 记录 + 发布 EvidenceUploaded 事件
    - 接收 multipart/form-data: file + requirement_id
    - 文件类型校验: 仅允许 application/pdf, image/*, model/step, application/octet-stream
    - 调用 ObjectStorage (当前直接用 MinIO client) 上传文件
    - 创建 Evidence 记录
    - 返回 201 + { evidence_id, file_id, file_name, presigned_url }
  - `GET /evidence/{evidence_id}` — 查询证据文件元数据 + 预签名 URL
    - 不存在 → 404
    - 返回 200 + Evidence JSON + presigned_url
  - `GET /compliance/{requirement_id}` — 查询适航条款合规信息
    - 不存在 → 自动创建 (compliance_status="pending")
    - 返回 200 + { requirement_id, compliance_status, responsible_person, updated_at, evidences: [...] }
  - `PATCH /compliance/{requirement_id}` — 更新合规状态
    - Pydantic 请求: UpdateComplianceRequest (compliance_status, responsible_person?)
    - 返回 200 + ComplianceRequirement JSON
  - `GET /compliance-requirements` — 查询所有适航条款
    - 返回 200 + ComplianceRequirement 数组
  - module-level 实例化
- **验证**: API 端点与需求 DT-REQ-13~17 一致，无 DELETE 端点

#### Task-DT03-07: 在 main.py 注册 certification_router + 更新 evidence_controller
- **Sprint**: DT03 | **优先级**: P0 | **预估**: 1h
- **依赖**: DT03-06
- **实现步骤**:
  - 编辑 main.py
  - 添加 `from api.v6.certification_controller import router as certification_router`
  - 添加 `app.include_router(certification_router)`
  - 评估是否需要移除/合并旧 evidence_controller.py 的端点到 certification_controller
  - 确保无端点冲突
- **验证**: 服务启动无报错，/docs 显示所有新端点

#### Task-DT03-08: 远程部署 + 集成测试 Certification Thread
- **Sprint**: DT03 | **优先级**: P0 | **预估**: 2h
- **依赖**: DT03-07
- **实现步骤**:
  - 重新构建 aircraft-core Docker 镜像
  - 重启 aircraft-core 容器
  - curl 测试:
    - `POST /evidence/upload` (file=test.pdf, requirement_id=FAA-25.853) → 201
    - `GET /evidence/{evidence_id}` → 200 + presigned_url
    - `GET /compliance/FAA-25.853` → 200 + evidence 列表 + compliance_status
    - `PATCH /compliance/FAA-25.853` (compliance_status=compliant) → 200
    - `GET /compliance/NONEXISTENT` → 200 (自动创建 pending)
    - 上传 .exe 文件 → 415
  - 验证 NATS 事件: aeroforge.cert.evidence.uploaded
- **验证**: 所有 curl 测试通过

---

## Phase 2 — 前端 + 基础设施 (并行)

### Sprint-DT04: React 数字线程追溯页面

> 目标：4 个 Trace 页面可视化展示完整追溯链

#### Task-DT04-01: 扩展 v6Api.ts 新增 API 调用
- **Sprint**: DT04 | **优先级**: P1 | **预估**: 1.5h
- **依赖**: DT01-07, DT02-08, DT03-08
- **实现步骤**:
  - 编辑 `frontend/src/api/v6Api.ts`
  - 新增 Material Thread API:
    - `createMaterialLot(data)`, `getMaterialLot(lotId)`, `getBlockMaterials(blockId)`, `getMaterialLots()`
  - 新增 Quality Thread API:
    - `createNDTRecord(data)`, `createCAR(data)`, `updateCAR(carId, data)`, `getQualityThread(lotId)`, `getNDTRecord(ndtId)`
  - 新增 Certification Thread API:
    - `uploadEvidence(file, requirementId)`, `getEvidence(evidenceId)`, `getCompliance(requirementId)`, `updateCompliance(requirementId, data)`, `getComplianceRequirements()`
- **验证**: TypeScript 编译无报错

#### Task-DT04-02: 扩展 types.ts 新增 TypeScript 类型
- **Sprint**: DT04 | **优先级**: P1 | **预估**: 1h
- **依赖**: DT04-01
- **实现步骤**:
  - 编辑 `frontend/src/api/types.ts`
  - 新增类型: MaterialLot, NDTRecord, CorrectiveActionRequest, ComplianceRequirement, Evidence
  - 新增请求类型: CreateMaterialLotRequest, CreateNDTRecordRequest, CreateCARRequest, UpdateCARRequest, UpdateComplianceRequest
  - 新增响应类型: QualityThreadResponse, ComplianceResponse
  - 枚举类型: MaterialStatus, TestType, NDTResult, CARStatus, ComplianceStatus
- **验证**: TypeScript 编译无报错

#### Task-DT04-03: 实现 ConfigurationTracePage.tsx
- **Sprint**: DT04 | **优先级**: P1 | **预估**: 2h
- **依赖**: DT04-01
- **实现步骤**:
  - 创建 `frontend/src/modules/v6/ConfigurationTracePage.tsx`
  - 布局: 左侧 Aircraft → Block 层级树 (Ant Design Tree)，右侧 Block 详情面板
  - 数据源: GET /config-hierarchies/{aircraft_type}
  - 点击 Block 节点 → 右侧展示 block_id, version, configuration 数据
  - 空状态提示
- **验证**: 页面渲染无报错

#### Task-DT04-04: 实现 MaterialTracePage.tsx
- **Sprint**: DT04 | **优先级**: P1 | **预估**: 2h
- **依赖**: DT04-01
- **实现步骤**:
  - 创建 `frontend/src/modules/v6/MaterialTracePage.tsx`
  - 布局: 左侧 Block → MaterialLot 追溯树，右侧 MaterialLot 详情面板
  - 数据源: GET /blocks/{id}/materials
  - 点击 MaterialLot 节点 → 右侧展示 lot_id, material_code, supplier_id, certificate_no, status
  - 空状态: "暂无材料数据"
- **验证**: 页面渲染无报错

#### Task-DT04-05: 实现 QualityTracePage.tsx
- **Sprint**: DT04 | **优先级**: P1 | **预估**: 2h
- **依赖**: DT04-01
- **实现步骤**:
  - 创建 `frontend/src/modules/v6/QualityTracePage.tsx`
  - 布局: 左侧 MaterialLot → NDT → CAR 追溯链 (Steps/Timeline)，右侧详情面板
  - 数据源: GET /material-lots/{id}/quality
  - NDT 节点: test_type, result (pass=绿色, fail=红色, conditional=黄色)
  - CAR 节点: description, status, responsible_person
  - 无 NDT 记录: 灰色虚线 + "未检测" 标识
- **验证**: 页面渲染无报错

#### Task-DT04-06: 实现 CertificationTracePage.tsx
- **Sprint**: DT04 | **优先级**: P1 | **预估**: 2h
- **依赖**: DT04-01
- **实现步骤**:
  - 创建 `frontend/src/modules/v6/CertificationTracePage.tsx`
  - 布局: 左侧 Requirement → Evidence 追溯树，右侧 Compliance 详情面板
  - 数据源: GET /compliance/{requirement_id}
  - Requirement 节点: requirement_id, compliance_status (颜色编码)
  - Evidence 节点: file_name, upload_timestamp, 下载链接 (presigned_url)
  - 空状态: "暂无认证数据"
- **验证**: 页面渲染无报错

#### Task-DT04-07: 配置路由 + 导航菜单
- **Sprint**: DT04 | **优先级**: P1 | **预估**: 1h
- **依赖**: DT04-03~06
- **实现步骤**:
  - 编辑路由配置文件，添加 4 个 Trace 页面路由:
    - `/configuration-trace` → ConfigurationTracePage
    - `/material-trace` → MaterialTracePage
    - `/quality-trace` → QualityTracePage
    - `/certification-trace` → CertificationTracePage
  - 添加导航菜单项 "Digital Thread" (子菜单: Configuration / Material / Quality / Certification)
- **验证**: 浏览器访问 4 个路由均能正确渲染

#### Task-DT04-08: 前端 Docker 构建 + 远程部署 + E2E 验证
- **Sprint**: DT04 | **优先级**: P1 | **预估**: 2h
- **依赖**: DT04-07
- **实现步骤**:
  - 重新构建前端 Docker 镜像
  - 重启 frontend 容器
  - 浏览器验证:
    - http://8.210.239.214:6000/configuration-trace → B737 配置层级
    - http://8.210.239.214:6000/material-trace → MAIN-WING → AL-2024-001
    - http://8.210.239.214:6000/quality-trace → AL-2024-001 → NDT-001 → CAR-001
    - http://8.210.239.214:6000/certification-trace → FAA-25.853 → Evidence → Compliance
  - 验证端到端追溯链: B737-000001 → MAIN-WING → AL-2024-001 → NDT-001 → CAR-001 → FAA Compliance
- **验证**: PASS 级验收通过

---

### Sprint-INF01: MinIO 接入 (ObjectStorage 抽象)

> 目标：ObjectStorage 接口抽象 + MinIO/Local 双实现 + 降级

#### Task-INF01-01: 定义 ObjectStorageInterface ABC
- **Sprint**: INF01 | **优先级**: P2 | **预估**: 1h
- **依赖**: 无
- **实现步骤**:
  - 创建 `infrastructure/adapters/` 目录
  - 创建 `infrastructure/adapters/__init__.py`
  - 创建 `infrastructure/adapters/object_storage_interface.py`
  - `ObjectStorageInterface(ABC)`:
    - `async def upload_file(bucket: str, file_id: str, file_data: bytes, content_type: str) -> str` → 返回 etag
    - `async def get_presigned_url(bucket: str, file_id: str, expires: int = 3600) -> str` → 返回预签名 URL
    - `async def is_available() -> bool`
- **验证**: ABC 定义完整

#### Task-INF01-02: 实现 LocalObjectStorage
- **Sprint**: INF01 | **优先级**: P2 | **预估**: 1h
- **依赖**: INF01-01
- **实现步骤**:
  - 创建 `infrastructure/adapters/local_object_storage.py`
  - `LocalObjectStorage(ObjectStorageInterface)`:
    - 文件存储到 `/tmp/aeroforge-evidence/{bucket}/{file_id}`
    - presigned_url 返回 `/api/v6/aircraft-core/evidence/local/{bucket}/{file_id}`
    - `is_available()` → True (本地存储始终可用)
- **验证**: 文件上传到本地磁盘，可获取 URL

#### Task-INF01-03: 重构 MinioObjectStorage 实现 ObjectStorageInterface
- **Sprint**: INF01 | **优先级**: P2 | **预估**: 1h
- **依赖**: INF01-01
- **实现步骤**:
  - 创建 `infrastructure/adapters/minio_object_storage.py`
  - 将现有 `object_storage.py` 的 MinIO 逻辑迁移到 `MinioObjectStorage(ObjectStorageInterface)`
  - `is_available()` → 尝试 MinIO health check，失败返回 False
- **验证**: MinIO 上传/下载功能不变

#### Task-INF01-04: 实现 ObjectStorage 工厂方法 + 更新 evidence_controller
- **Sprint**: INF01 | **优先级**: P2 | **预估**: 1h
- **依赖**: INF01-02, INF01-03
- **实现步骤**:
  - 在 `infrastructure/adapters/` 中实现工厂方法 `create_object_storage()`
    - MinIO 可用 → MinioObjectStorage
    - MinIO 不可用 → LocalObjectStorage + WARNING 日志
  - 更新 `evidence_controller.py` 和 `certification_controller.py` 使用 ObjectStorageInterface
  - 移除对 `object_storage.py` 的直接引用
- **验证**: 证据上传通过 ObjectStorageInterface 完成

#### Task-INF01-05: 降级测试: MinIO 不可用时 LocalStorage 正常工作
- **Sprint**: INF01 | **优先级**: P2 | **预估**: 1h
- **依赖**: INF01-04
- **实现步骤**:
  - 停止 MinIO 容器
  - curl 测试: POST /evidence/upload → 文件存储到本地磁盘，API 返回成功
  - 检查日志: WARNING "Using LocalObjectStorage (MinIO unavailable)"
  - 重启 MinIO 容器
  - curl 测试: POST /evidence/upload → 文件存储到 MinIO
- **验证**: 降级和恢复均正常

---

### Sprint-INF02: Event Contract (事件契约)

> 目标：6+1 个 JSON Schema 事件契约文件

#### Task-INF02-01: 创建 contracts/events/ 目录 + 6 个事件契约
- **Sprint**: INF02 | **优先级**: P2 | **预估**: 1.5h
- **依赖**: DT01-03, DT02-03, DT03-03
- **实现步骤**:
  - 创建 `contracts/events/` 目录
  - 编写 6 个 JSON Schema 契约文件:
    - `ConfigurationChanged.json` — event_id, event_type, configuration_id, block_id, aircraft_type, change_type, timestamp
    - `MaterialLotCreated.json` — event_id, event_type, lot_id, material_code, supplier_id, block_id, timestamp
    - `NDTCompleted.json` — event_id, event_type, ndt_record_id, material_lot_id, test_type, result, timestamp
    - `CARCreated.json` — event_id, event_type, car_id, ndt_record_id, description, status, timestamp
    - `CARClosed.json` — event_id, event_type, car_id, closed_by, timestamp
    - `EvidenceUploaded.json` — event_id, event_type, evidence_id, requirement_id, file_id, file_name, timestamp
  - 每个契约包含 version: "1.0.0"
- **验证**: JSON Schema 语法正确，可被验证器解析

#### Task-INF02-02: 编写 DigitalTwinSyncEvent.json 契约
- **Sprint**: INF02 | **优先级**: P2 | **预估**: 0.5h
- **依赖**: 无
- **实现步骤**:
  - 创建 `contracts/events/DigitalTwinSyncEvent.json`
  - 字段: aircraft_id, block_id, version, timestamp, change_type
  - version: "1.0.0"
- **验证**: JSON Schema 语法正确

#### Task-INF02-03: Schema 验证测试
- **Sprint**: INF02 | **优先级**: P2 | **预估**: 1h
- **依赖**: INF02-01
- **实现步骤**:
  - 编写 Python 测试脚本
  - 使用 jsonschema 库验证每个事件 Pydantic model 的 model_dump() 输出符合对应 JSON Schema
  - 验证 6 个事件均通过
- **验证**: 所有事件 payload 通过 Schema 验证

---

### Sprint-INF03: NATS 适配层 (EventBus 抽象)

> 目标：EventBus 接口抽象 + InMemory/Nats 双实现 + 降级

#### Task-INF03-01: 定义 EventBusInterface ABC
- **Sprint**: INF03 | **优先级**: P2 | **预估**: 1h
- **依赖**: 无
- **实现步骤**:
  - 创建 `infrastructure/adapters/event_bus_interface.py`
  - `EventBusInterface(ABC)`:
    - `async def publish(subject: str, data: str) -> bool`
    - `async def subscribe(subject: str, durable_name: str, callback: Callable) -> Optional[Any]`
    - `async def close()`
    - `def is_available() -> bool`
- **验证**: ABC 定义完整

#### Task-INF03-02: 实现 InMemoryEventBus
- **Sprint**: INF03 | **优先级**: P2 | **预估**: 1h
- **依赖**: INF03-01
- **实现步骤**:
  - 创建 `infrastructure/adapters/in_memory_event_bus.py`
  - `InMemoryEventBus(EventBusInterface)`:
    - 进程内回调列表
    - publish → 遍历回调并调用
    - subscribe → 注册回调
    - is_available() → True
- **验证**: 事件在进程内传递

#### Task-INF03-03: 实现 NatsEventBus (重构现有 event_bus.py)
- **Sprint**: INF03 | **优先级**: P2 | **预估**: 1.5h
- **依赖**: INF03-01
- **实现步骤**:
  - 创建 `infrastructure/adapters/nats_event_bus.py`
  - 将现有 `event_bus.py` 的 NATS JetStream 逻辑迁移到 `NatsEventBus(EventBusInterface)`
  - publish → JetStream publish
  - subscribe → pull_subscribe + fetch 循环
  - is_available() → 检查 NATS 连接状态
  - 降级: publish 失败 → WARNING 日志 + 返回 False
- **验证**: NATS 事件发布/消费功能不变

#### Task-INF03-04: 实现 EventBus 工厂方法 + 更新所有 Controller
- **Sprint**: INF03 | **优先级**: P2 | **预估**: 1.5h
- **依赖**: INF03-02, INF03-03
- **实现步骤**:
  - 在 `infrastructure/adapters/` 中实现工厂方法 `create_event_bus()`
    - NATS 可用 → NatsEventBus
    - NATS 不可用 → InMemoryEventBus + WARNING 日志
  - 更新所有 Controller 使用 EventBusInterface
  - 更新 main.py 中的 EventBus 初始化逻辑
- **验证**: 所有事件通过 EventBusInterface 发布

#### Task-INF03-05: 降级测试: NATS 不可用时 InMemoryEventBus 正常工作
- **Sprint**: INF03 | **优先级**: P2 | **预估**: 1h
- **依赖**: INF03-04
- **实现步骤**:
  - 停止 NATS 容器
  - 重启 aircraft-core 容器
  - curl 测试: POST /material-lots → 创建成功
  - 检查日志: WARNING "Using InMemoryEventBus (NATS unavailable)"
  - 重启 NATS 容器
  - 重启 aircraft-core → 日志显示 "Using NatsEventBus"
- **验证**: 降级和恢复均正常

---

## Phase 3 — 高级适配层 (并行)

### Sprint-INF04: Neo4j 适配层 (GraphRepository 抽象)

> 目标：GraphRepository 接口抽象 + NoOp/Neo4j 双实现 + 降级

#### Task-INF04-01: 定义 GraphRepositoryInterface ABC
- **Sprint**: INF04 | **优先级**: P3 | **预估**: 1h
- **依赖**: 无
- **实现步骤**:
  - 创建 `infrastructure/adapters/graph_repository_interface.py`
  - `GraphRepositoryInterface(ABC)`:
    - `async def create_relation(from_id: str, to_id: str, relation_type: str, from_label: str, to_label: str) -> bool`
    - `async def find_relations(node_id: str, relation_type: str = None, direction: str = "outgoing") -> List[dict]`
    - `async def find_path(from_id: str, to_id: str, max_depth: int = 5) -> Optional[dict]`
    - `def is_available() -> bool`
  - 禁止暴露 execute_cypher 方法
- **验证**: ABC 定义完整

#### Task-INF04-02: 实现 NoOpGraphRepository
- **Sprint**: INF04 | **优先级**: P3 | **预估**: 0.5h
- **依赖**: INF04-01
- **实现步骤**:
  - 创建 `infrastructure/adapters/noop_graph_repository.py`
  - `NoOpGraphRepository(GraphRepositoryInterface)`:
    - create_relation → WARNING 日志 + 返回 True
    - find_relations → 返回空列表
    - find_path → 返回 None
    - is_available() → False
- **验证**: 所有方法为 no-op

#### Task-INF04-03: 实现 Neo4jGraphRepository (重构现有 graph_client.py)
- **Sprint**: INF04 | **优先级**: P3 | **预估**: 1.5h
- **依赖**: INF04-01
- **实现步骤**:
  - 创建 `infrastructure/adapters/neo4j_graph_repository.py`
  - 将现有 `graph_client.py` 逻辑迁移到 `Neo4jGraphRepository(GraphRepositoryInterface)`
  - create_relation → MERGE 语句
  - find_relations → MATCH 语句
  - find_path → shortestPath 查询
  - is_available() → 检查 Neo4j 连接
  - 超时处理: 5 秒超时 → WARNING + 返回 False/空
- **验证**: Neo4j 图谱操作功能不变

#### Task-INF04-04: 实现 GraphRepository 工厂方法 + 更新所有 Controller
- **Sprint**: INF04 | **优先级**: P3 | **预估**: 1h
- **依赖**: INF04-02, INF04-03
- **实现步骤**:
  - 在 `infrastructure/adapters/` 中实现工厂方法 `create_graph_repository()`
    - Neo4j 可用 → Neo4jGraphRepository
    - Neo4j 不可用 → NoOpGraphRepository + WARNING 日志
  - 更新 config_identity_controller.py 使用 GraphRepositoryInterface
  - 更新 material_controller.py 在创建 MaterialLot 时写入 Block-MaterialLot 关系
- **验证**: 图谱操作通过 GraphRepositoryInterface 完成

#### Task-INF04-05: 降级测试: Neo4j 不可用时 NoOpGraphRepository 正常工作
- **Sprint**: INF04 | **优先级**: P3 | **预估**: 1h
- **依赖**: INF04-04
- **实现步骤**:
  - 停止 Neo4j 容器
  - curl 测试: POST /material-lots → 创建成功，GraphRepository no-op
  - 检查日志: WARNING "Using NoOpGraphRepository (Neo4j unavailable)"
  - 重启 Neo4j 容器
  - curl 测试: POST /material-lots → Neo4j 关系写入成功
- **验证**: 降级和恢复均正常

---

### Sprint-INF05: Physics Twin 契约

> 目标：DigitalTwinSyncEvent 契约定义（仅契约，禁止仿真）

#### Task-INF05-01: 编写 DigitalTwinSyncEvent 映射文档
- **Sprint**: INF05 | **优先级**: P3 | **预估**: 0.5h
- **依赖**: INF02-02
- **实现步骤**:
  - 创建 `contracts/events/mapping.md`
  - 文档说明 ConfigurationUpdatedEvent → DigitalTwinSyncEvent 的字段映射关系
  - 明确标注 "EV-4.5 阶段仅定义契约，不实现同步逻辑"
- **验证**: 映射文档清晰完整

---

## 最终验证: 端到端验收场景

> B737-000001 → MAIN-WING → AL-2024-001 → Supplier-A → NDT-001 → CAR-001 → Evidence-Package → FAA Compliance

| 步骤 | 操作 | 预期结果 | 验收级别 |
|------|------|----------|----------|
| 1 | GET /config-hierarchies/B737 | B737-000001 → MAIN-WING 层级 | PASS |
| 2 | POST /material-lots (AL-2024, B737-MAIN-WING) | 201, lot_id=AL-2024-001 | PASS |
| 3 | GET /blocks/B737-MAIN-WING/materials | 200, 包含 AL-2024-001 | PASS |
| 4 | POST /ndt-records (AL-2024-001, conditional) | 201, ndt_record_id | PASS |
| 5 | POST /corrective-actions (ndt_record_id) | 201, car_id | PASS |
| 6 | GET /material-lots/AL-2024-001/quality | 200, NDT+CAR 完整链路 | PASS |
| 7 | POST /evidence/upload (file, FAA-25.853) | 201, evidence_id | PASS |
| 8 | GET /compliance/FAA-25.853 | 200, evidence+status+responsible+updated_at | PASS |
| 9 | React /configuration-trace | B737 配置层级可视化 | PASS |
| 10 | React /material-trace | MAIN-WING → AL-2024-001 | PASS |
| 11 | React /quality-trace | AL-2024-001 → NDT → CAR | PASS |
| 12 | React /certification-trace | FAA-25.853 → Evidence → Compliance | PASS |
| 13 | MinIO 降级测试 | LocalStorage 降级正常 | A |
| 14 | 事件契约验证 | 6 个事件通过 Schema 验证 | A |
| 15 | EventBus 降级测试 | InMemoryEventBus 降级正常 | A |
| 16 | Neo4j 降级测试 | NoOpGraphRepository 降级正常 | A+ |
| 17 | DigitalTwinSyncEvent 契约 | 契约文件存在 | A+ |

---

## 任务统计

| Sprint | 任务数 | 优先级 | 预估总工时 |
|--------|--------|--------|-----------|
| DT01 (Material Thread) | 7 | P0 | 8h |
| DT02 (Quality Thread) | 8 | P0 | 9h |
| DT03 (Certification Thread) | 8 | P0 | 9.5h |
| DT04 (React Trace Pages) | 8 | P1 | 13.5h |
| INF01 (MinIO 接入) | 5 | P2 | 5h |
| INF02 (Event Contract) | 3 | P2 | 3h |
| INF03 (NATS 适配层) | 5 | P2 | 6h |
| INF04 (Neo4j 适配层) | 5 | P3 | 5h |
| INF05 (Physics Twin 契约) | 1 | P3 | 0.5h |
| **总计** | **50** | — | **59.5h** |