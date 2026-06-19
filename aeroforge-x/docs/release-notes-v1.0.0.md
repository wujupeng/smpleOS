# AeroForge-X v1.0.0 Release Notes

## 概述

AeroForge-X 是一个航空器设计-制造全流程数字化操作系统（Aircraft Design-to-Manufacturing Operating System），实现从飞行器需求输入到可制造飞行器完整交付包的自动生成。

## 功能清单

### 设计中心 (Design Center)
- ✅ AircraftSpec 需求规格书 CRUD（创建/查询/更新/确认/冻结）
- ✅ 参数校验引擎（完整性/范围/一致性三级校验）
- ✅ 飞行器类型自动推荐（固定翼/eVTOL/滑翔机/无人机）
- ✅ 参数化3D模型生成（机身/机翼/尾翼自动生成+装配）
- ✅ 设计规则引擎（气动规则集+结构规则集+增量校验）

### PLM中心 (Product Lifecycle Management)
- ✅ 产品结构树管理（多层级展开/折叠）
- ✅ 版本管理（主/次版本号自动计算+版本对比diff）
- ✅ 使用处查询（where-used）

### BOM中心
- ✅ eBOM自动生成引擎（从设计模型自动提取零部件+物料编码）
- ✅ eBOM Neo4j图存储（BOMItem节点+CONTAINS关系）
- ✅ eBOM发布与事件通知

### MES中心 (Manufacturing Execution System)
- ✅ 工单全生命周期管理（创建→派发→执行→完工→关闭）
- ✅ 工单派发逻辑（IQC门控+工位冲突检测）
- ✅ 工位管理（状态/排程/冲突解决）
- ✅ 生产进度跟踪（进度计算+完工预估）
- ✅ 序列号管理（唯一序列号+工单关联+安装记录）

### QMS质量系统
- ✅ IQC来料检验（计划生成+结果录入+门控拦截）
- ✅ FQC终检（计划生成+结果录入）
- ✅ CAPA纠正预防措施（4状态流转+超期升级告警）

### 追溯系统
- ✅ 物料追溯记录（Neo4j: Supplier→Batch→Part→Inspection→WorkOrder→Aircraft）
- ✅ 序列号追溯链查询
- ✅ 批次正向/反向追溯
- ✅ 追溯链完整性校验

### 基础设施
- ✅ Docker Compose本地开发环境（6服务）
- ✅ Keycloak认证集成（8角色RBAC权限矩阵）
- ✅ Kong API Gateway（JWT鉴权+限流）
- ✅ NATS JetStream事件总线（10个核心事件）
- ✅ 统一响应格式与全局异常处理
- ✅ 审计日志中间件
- ✅ CI/CD流水线（GitHub Actions）

### 前端
- ✅ React+TypeScript+Vite+Ant Design+Three.js
- ✅ 设计中心5步向导UI
- ✅ BOM树可视化
- ✅ MES工位看板+工单管理
- ✅ QMS检验执行+CAPA管理
- ✅ 追溯链可视化+完整性校验

## 技术栈

| 层次 | 技术 |
|------|------|
| 后端 | Python 3.12 + FastAPI |
| 前端 | React 18 + TypeScript + Vite + Ant Design + Three.js |
| 数据库 | PostgreSQL 16 + Neo4j 5 + MinIO + TimescaleDB(预留) |
| 缓存/队列 | Redis 7 + Celery |
| 事件总线 | NATS JetStream |
| 认证 | Keycloak 24 |
| API网关 | Kong |
| CI/CD | GitHub Actions |

## 已知限制

1. 参数化3D模型输出为JSON格式，STEP格式导出需Phase 2实现
2. CFD/FEA分析功能为Phase 2范围
3. mBOM/sBOM转换引擎为Phase 2范围
4. 数字孪生中心为Phase 2范围
5. AI设计引擎(AeroGPT)为Phase 3范围
6. 桌面客户端(Electron)为Phase 2范围

## 升级指南

首次部署请参考 `docs/deployment.md`