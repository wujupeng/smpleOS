# EV-4: Frontend Integration & Architecture Foundation — Task List

**Sprint**: EV-4  
**Target TRL**: 4.5 → 5.5  
**Date**: 2026-06-22  

---

## Phase 1: API Alignment & Backend Hardening (EV4-P1)

### Task-01: v6Api 端点对齐
- **Priority**: HIGH | **Est**: 1h
- **Problem**: 前端 `v6Api.ts` 的端点路径与后端 `configuration_controller.py` 不匹配
  - 前端: `/aircraft-core/config/blocks` → 后端: `/aircraft-core/block-configurations`
  - 前端: `/aircraft-core/config/blocks/{id}/sns` → 后端: `/aircraft-core/sn-configurations` (body传参)
  - 前端: `/aircraft-core/config/conflicts?block_id=&sn_id=` → 后端: `/aircraft-core/config-conflicts/detect` (POST)
  - 前端: `/aircraft-core/config/baselines` → 后端: `/aircraft-core/baselines/fbl|fcl|fsdl` (POST)
  - 前端缺少: GET hierarchy, PATCH block, GET block by id
- **Action**: 重写 `v6Api.ts` 的 `configApi`，对齐后端实际端点
- **Files**: `frontend/src/api/v6Api.ts`
- **Acceptance**: 每个前端 API 函数的 URL + HTTP method + 参数与后端 controller 完全一致

### Task-02: TypeScript 类型定义
- **Priority**: HIGH | **Est**: 1h
- **Problem**: 无独立类型文件，`BlockConfig` 接口缺少 `version`, `created_at`, `updated_at` 字段
- **Action**: 创建 `frontend/src/api/types.ts`，定义所有 v6 API 的请求/响应类型
- **Files**: `frontend/src/api/types.ts` (new)
- **Acceptance**: 所有 v6Api 函数的参数和返回值有明确类型，`BlockConfig` 包含 version/created_at/updated_at

### Task-03: 后端 CORS 配置
- **Priority**: HIGH | **Est**: 0.5h
- **Problem**: FastAPI 未配置 CORS，前端 dev server (port 3000) 无法调用后端 (port 8000)
- **Action**: 在 FastAPI app 中添加 `CORSMiddleware`，允许 localhost:3000
- **Files**: `services/aircraft-core-service/src/main.py`
- **Acceptance**: 前端 `fetch('/api/v6/...')` 不被浏览器 CORS 拦截

---

## Phase 2: Configuration Manager Page Rewrite (EV4-P2)

### Task-04: ConfigurationManagerPage 重写 — Tree View (EV4-101)
- **Priority**: HIGH | **Est**: 3h
- **Problem**: 当前页面使用 Table 展示 blocks，不是 Tree View；使用 mock 数据降级
- **Action**: 重写为左侧 Tree + 右侧 Detail 布局
  - 左侧: `GET /config-hierarchies/{aircraft_type}` → Ant Design Tree 组件
  - 树节点: Aircraft Type → Block → SN 三级结构
  - 顶部: Aircraft Type 选择器 (Select 或手动输入)
  - 移除 mock 数据降级逻辑
- **Files**: `frontend/src/modules/v6/ConfigurationManagerPage.tsx`
- **Acceptance**: 选择 B737 → 展示配置树 → 无报错 (EV4-101)

### Task-05: Block Detail Panel (EV4-102)
- **Priority**: HIGH | **Est**: 2h
- **Problem**: 当前 detail panel 缺少 version, created_at, updated_at 字段
- **Action**: 点击 Block 节点 → `GET /block-configurations/{block_id}` → 右侧展示详情
  - 展示字段: block_id, block_name, aircraft_type, version, locked, created_at, updated_at
  - 展示 design_config / manufacturing_config / operational_config 状态
- **Files**: `frontend/src/modules/v6/ConfigurationManagerPage.tsx`
- **Acceptance**: 点击 Block → 右侧显示完整详情含 version 和时间戳 (EV4-102)

### Task-06: Block Edit — PATCH 联调 (EV4-103)
- **Priority**: HIGH | **Est**: 2h
- **Problem**: 当前无编辑功能
- **Action**: 
  - 右侧 Detail Panel 添加 "Edit" 按钮
  - 点击后弹出 Modal，可编辑 block_name
  - 提交: `PATCH /block-configurations/{block_id}` with `expected_version` 乐观锁
  - 成功后: 刷新 Detail Panel + 失效 Hierarchy 缓存 (重新 GET hierarchy)
- **Files**: `frontend/src/modules/v6/ConfigurationManagerPage.tsx`
- **Acceptance**: 前端修改 block_name → 数据库真实变化 → GET 确认 (EV4-103)

### Task-07: 乐观锁 UI 验证 (EV4-104)
- **Priority**: HIGH | **Est**: 2h
- **Problem**: 当前无 409 Conflict 处理
- **Action**:
  - PATCH 失败时检查 `err.response.status === 409`
  - 显示 Ant Design Modal: "配置已被其它用户修改，请刷新后重试"
  - 提供 "刷新" 按钮，重新 GET block detail
  - Detail Panel 展示当前 version 号，帮助用户理解冲突
- **Files**: `frontend/src/modules/v6/ConfigurationManagerPage.tsx`
- **Acceptance**: 浏览器A修改成功 → 浏览器B提交 → 409 提示 → 刷新后重试 (EV4-104)

### Task-08: Cache Invalidation 前端验证 (EV4-105)
- **Priority**: HIGH | **Est**: 1h
- **Problem**: PATCH 后 Hierarchy 可能返回旧缓存
- **Action**:
  - PATCH 成功后，强制重新 `GET /config-hierarchies/{aircraft_type}`
  - Tree View 自动刷新展示最新值
  - 在 Detail Panel 显示 "数据已更新" 提示
- **Files**: `frontend/src/modules/v6/ConfigurationManagerPage.tsx`
- **Acceptance**: 修改 Block → Tree 自动刷新 → 显示最新值 (EV4-105)

---

## Phase 3: Deployment & Integration Testing (EV4-P3)

### Task-09: Docker Compose 添加前端服务
- **Priority**: HIGH | **Est**: 1h
- **Problem**: 当前 docker-compose.ev3.yml 仅有 postgres + aircraft-core
- **Action**: 
  - 添加 frontend service (nginx 静态托管 + API proxy)
  - 创建 `frontend/Dockerfile` (multi-stage: node build → nginx serve)
  - 创建 `frontend/nginx.conf` (API proxy to aircraft-core:8000)
  - 更新 docker-compose 添加 frontend service
- **Files**: `frontend/Dockerfile`, `frontend/nginx.conf`, `deploy/docker-compose.ev4.yml`
- **Acceptance**: `docker-compose up` 后浏览器访问 80 端口可见前端页面

### Task-10: 远程服务器部署 + 端到端验证
- **Priority**: HIGH | **Est**: 2h
- **Problem**: 需要在远程服务器上验证完整 React → FastAPI → PostgreSQL 闭环
- **Action**:
  - 传输新文件到远程服务器
  - 重建 aircraft-core Docker 镜像
  - 构建前端 Docker 镜像
  - docker-compose up
  - 执行 EV4-101~105 验收测试
- **Acceptance**: 5项验收全部通过

---

## Phase 4: Engineering Tasks (EV4-P4)

### Task-11: Git 基线 + GitHub 同步
- **Priority**: MEDIUM | **Est**: 1h
- **Action**: 
  - 本地 git add + commit "EV-4 baseline"
  - 推送到 GitHub `wujupeng/smpleOS`
  - 建立 main/develop 分支
- **Acceptance**: GitHub 上可见最新代码

### Task-12: B5-105 Version Domain Model 文档 (已完成 ✅)
- **Status**: COMPLETED — `docs/B5-105_Version_Domain_Model_Specification.md`

### Task-13: B5-106 读取路径统一代码修复 (已完成 ✅)
- **Status**: COMPLETED — P1~P4 代码修复已实施

---

## Phase 5: EV-5 Preparation (A+ 目标)

### Task-14: EventBus Interface 抽象
- **Priority**: LOW | **Est**: 1h
- **Action**: 定义 `EventBus` protocol (publish/subscribe)，实现 `FakeEventBus`
- **Files**: `services/aircraft-core-service/src/infrastructure/event_bus.py` (已部分实现)

### Task-15: ObjectStorage Interface 抽象
- **Priority**: LOW | **Est**: 1h
- **Action**: 定义 `ObjectStorage` protocol (put/get/delete)，实现 `LocalStorage`

### Task-16: GraphRepository Interface 抽象
- **Priority**: LOW | **Est**: 1h
- **Action**: 定义 `GraphRepository` protocol (create_relation/query_relation)，实现 `NoOpGraphRepo`

### Task-17: DigitalTwinSyncEvent 事件契约
- **Priority**: LOW | **Est**: 0.5h
- **Action**: 定义 `DigitalTwinSyncEvent` dataclass (aircraft_id, block_id, timestamp, change_type)

---

## Dependency Graph

```
Task-01 (API对齐) ──→ Task-04 (Tree View) ──→ Task-05 (Detail) ──→ Task-06 (Edit) ──→ Task-07 (乐观锁) ──→ Task-08 (Cache)
Task-02 (Types)   ──→ Task-04
Task-03 (CORS)    ──→ Task-04
Task-04~08        ──→ Task-09 (Docker) ──→ Task-10 (部署验证)
Task-11 (Git)     — 独立
Task-14~17        — 独立 (EV-5 铺路)
```

## Verification Checklist (EV-4 Pass Criteria)

- [ ] EV4-101: 浏览器打开 → 读取 B737 → 展示配置树 → 无报错
- [ ] EV4-102: 点击 Block → GET Block → 右侧详情面板含 version/created_at/updated_at
- [ ] EV4-103: 修改名称 → PATCH → 数据库更新 → 界面刷新
- [ ] EV4-104: 浏览器A修改成功 → 浏览器B提交 → 409 Conflict 提示
- [ ] EV4-105: Hierarchy 打开 → 修改 Block → 自动刷新 → 最新值
- [ ] B5-105: Version Domain Model 文档 ✅
- [ ] B5-106: 读取路径统一 ✅
- [ ] Git 基线