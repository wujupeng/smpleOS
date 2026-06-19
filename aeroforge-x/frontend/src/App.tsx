import React, { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Spin } from 'antd'
import './locales'
import MainLayout from './layouts/MainLayout'
import LoginPage from './pages/LoginPage'
import DesignCenter from './modules/design/DesignCenter'
import BomCenter from './modules/bom/BomCenter'
import MesCenter from './modules/mes/MesCenter'
import QmsCenter from './modules/qms/QmsCenter'
import TraceCenter from './modules/trace/TraceCenter'
import CAECenter from './modules/cae/CAECenter'
import TwinCenter from './modules/twin/TwinCenter'
import PLMCenter from './modules/plm/PLMCenter'
import PLMPage from './modules/plm/PLMPage'
import ProjectListPage from './modules/project/ProjectListPage'
import ProjectDetailPage from './modules/project/ProjectDetailPage'
import AIEnginePage from './modules/ai/AIEnginePage'
import OptimizationPage from './modules/ai/OptimizationPage'
import SupplyChainPage from './modules/supply/SupplyChainPage'
import SPCPage from './modules/qms/spc/SPCPage'
import SchedulingPage from './modules/mes/scheduling/SchedulingPage'
import PredictiveTwinPage from './modules/twin/predictive/PredictiveTwinPage'
import AnalyticsPage from './modules/analytics/AnalyticsPage'
import AdvancedCAEPage from './modules/cae/AdvancedCAEPage'
import FlightTestPage from './modules/delivery/FlightTestPage'
import DeliveryPackagePage from './modules/delivery/DeliveryPackagePage'
import ERPIntegrationPage from './modules/integrations/ERPIntegrationPage'
import UnifiedTwinFusionPage from './modules/twin/fusion/UnifiedTwinFusionPage'
import AdaptiveSchedulingPage from './modules/mes/adaptive-scheduling/AdaptiveSchedulingPage'
import QualityPredictionPage from './modules/mes/quality-prediction/QualityPredictionPage'
import ProcessOptimizationPage from './modules/mes/process-optimization/ProcessOptimizationPage'
import CertificationCenterPage from './modules/certification/CertificationCenterPage'
import SupplyCollaborationPage from './modules/supply/collaboration/SupplyCollaborationPage'
import KnowledgeCenterPage from './modules/knowledge/KnowledgeCenterPage'
import KnowledgeGraphPage from './modules/knowledge/graph/KnowledgeGraphPage'
import KnowledgeAnalysisPage from './modules/knowledge/analysis/KnowledgeAnalysisPage'
import ConfigurationPage from './modules/configuration/ConfigurationPage'
import EcosystemPage from './modules/ecosystem/EcosystemPage'
import EnterprisePage from './modules/enterprise/EnterprisePage'
import FullPipelinePage from './modules/delivery/pipeline/FullPipelinePage'
import SpecPage from './modules/requirement/spec/SpecPage'
import DesignModelPage from './modules/design/model/DesignModelPage'
import StabilityPage from './modules/verification/stability/StabilityPage'
import FlightDynamicsPage from './modules/verification/flight-dynamics/FlightDynamicsPage'
import ControlSynthesisPage from './modules/verification/control-synthesis/ControlSynthesisPage'
import FlightEnvelopePage from './modules/verification/flight-envelope/FlightEnvelopePage'
import TravelerPage from './modules/mes/traveler/TravelerPage'
import FMEAPage from './modules/quality/fmea/FMEAPage'
import FleetTwinPage from './modules/twin/fleet/FleetTwinPage'
import FleetManagementPage from './modules/operations/fleet/FleetManagementPage'
import OperationAnalyticsPage from './modules/operations/analytics/OperationAnalyticsPage'
import AeroGPTDesignerPage from './modules/ai/designer/AeroGPTDesignerPage'
import AeroGPTEngineerPage from './modules/ai/engineer/AeroGPTEngineerPage'
import AeroGPTManufacturingPage from './modules/ai/manufacturing/AeroGPTManufacturingPage'
import AeroGPTCertificationPage from './modules/ai/certification/AeroGPTCertificationPage'
import AeroGPTTestPilotPage from './modules/ai/testpilot/AeroGPTTestPilotPage'
import OptimizationV1Page from './modules/ai/optimization/OptimizationPage'
import CertificationPlansPage from './modules/certification/plans/CertificationPlansPage'
import ComplianceVerificationPage from './modules/certification/verification/ComplianceVerificationPage'
import AirworthinessApprovalPage from './modules/certification/approval/AirworthinessApprovalPage'
import ContinuousAirworthinessPage from './modules/certification/continuous/ContinuousAirworthinessPage'
import AircraftObjectExplorer from './modules/aircraft-core/AircraftObjectExplorer'
import AircraftObjectDetail from './modules/aircraft-core/AircraftObjectDetail'
import WorkflowEditor from './modules/workflow/WorkflowEditor'
import WorkflowTemplateGallery from './modules/workflow/WorkflowTemplateGallery'
import TwinRuntimeDashboard from './modules/physics-twin/TwinRuntimeDashboard'
import ConfigurationManagerPage from './modules/v6/ConfigurationManagerPage'
import RequirementsTraceabilityPage from './modules/v6/RequirementsTraceabilityPage'
import CertificationDashboardPage from './modules/v6/CertificationDashboardPage'
import FleetHealthDashboardPage from './modules/v6/FleetHealthDashboardPage'
import ProductionDashboardPage from './modules/v6/ProductionDashboardPage'

const SchemaEditor = lazy(() => import('./modules/aircraft-core/schemas/SchemaEditor'))
const SchemaVersionManager = lazy(() => import('./modules/aircraft-core/schemas/SchemaVersionManager'))
const SchemaMigrationDashboard = lazy(() => import('./modules/aircraft-core/schemas/SchemaMigrationDashboard'))
const UnitConverter = lazy(() => import('./modules/aircraft-core/schemas/UnitConverter'))
const AttributeNameResolver = lazy(() => import('./modules/aircraft-core/schemas/AttributeNameResolver'))
const SchemaInstanceViewer = lazy(() => import('./modules/aircraft-core/schemas/SchemaInstanceViewer'))
const ModelPluginManager = lazy(() => import('./modules/physics-twin/plugins/ModelPluginManager'))
const ModelParameterConfig = lazy(() => import('./modules/physics-twin/plugins/ModelParameterConfig'))
const DOF6TrajectoryViewer = lazy(() => import('./modules/physics-twin/simulations/DOF6TrajectoryViewer'))
const BatterySOCCurve = lazy(() => import('./modules/physics-twin/simulations/BatterySOCCurve'))
const ControlResponseCurve = lazy(() => import('./modules/physics-twin/simulations/ControlResponseCurve'))
const CoupledSimulationDashboard = lazy(() => import('./modules/physics-twin/runtimes/CoupledSimulationDashboard'))
const ModelRegistryDashboard = lazy(() => import('./modules/physics-twin/plugins/ModelRegistryDashboard'))
const PropagationChainConfig = lazy(() => import('./modules/workflow/propagation/PropagationChainConfig'))
const PropagationChainMonitor = lazy(() => import('./modules/workflow/propagation/PropagationChainMonitor'))
const HandlerRegistryManager = lazy(() => import('./modules/workflow/propagation/HandlerRegistryManager'))
const ChainAuditLog = lazy(() => import('./modules/workflow/propagation/ChainAuditLog'))
const PropagationDashboard = lazy(() => import('./modules/workflow/propagation/PropagationDashboard'))

const LazyLoad = ({ children }: { children: React.ReactNode }) => (
  <Suspense fallback={<div style={{ padding: 48, textAlign: 'center' }}><Spin size="large" /></div>}>{children}</Suspense>
)

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Navigate to="/design" replace />} />
        <Route path="projects" element={<ProjectListPage />} />
        <Route path="projects/:projectId" element={<ProjectDetailPage />} />
        <Route path="ai" element={<AIEnginePage />} />
        <Route path="optimization" element={<OptimizationPage />} />
        <Route path="supply" element={<SupplyChainPage />} />
        <Route path="design" element={<DesignCenter />} />
        <Route path="cae" element={<CAECenter />} />
        <Route path="advanced-cae" element={<AdvancedCAEPage />} />
        <Route path="twin" element={<TwinCenter />} />
        <Route path="predictive-twin" element={<PredictiveTwinPage />} />
        <Route path="plm" element={<PLMCenter />} />
        <Route path="plm-v1" element={<PLMPage />} />
        <Route path="bom" element={<BomCenter />} />
        <Route path="mes" element={<MesCenter />} />
        <Route path="scheduling" element={<SchedulingPage />} />
        <Route path="qms" element={<QmsCenter />} />
        <Route path="spc" element={<SPCPage />} />
        <Route path="analytics" element={<AnalyticsPage />} />
        <Route path="trace" element={<TraceCenter />} />
        <Route path="flight-test" element={<FlightTestPage />} />
        <Route path="delivery" element={<DeliveryPackagePage />} />
        <Route path="erp-integration" element={<ERPIntegrationPage />} />
        <Route path="twin-fusion" element={<UnifiedTwinFusionPage />} />
        <Route path="adaptive-scheduling" element={<AdaptiveSchedulingPage />} />
        <Route path="quality-prediction" element={<QualityPredictionPage />} />
        <Route path="process-optimization" element={<ProcessOptimizationPage />} />
        <Route path="certification" element={<CertificationCenterPage />} />
        <Route path="supply-collaboration" element={<SupplyCollaborationPage />} />
        <Route path="knowledge" element={<KnowledgeCenterPage />} />
        <Route path="knowledge-graph" element={<KnowledgeGraphPage />} />
        <Route path="knowledge-analysis" element={<KnowledgeAnalysisPage />} />
        <Route path="configuration" element={<ConfigurationPage />} />
        <Route path="ecosystem" element={<EcosystemPage />} />
        <Route path="enterprise" element={<EnterprisePage />} />
        <Route path="full-pipeline" element={<FullPipelinePage />} />
        <Route path="requirement-spec" element={<SpecPage />} />
        <Route path="design-model" element={<DesignModelPage />} />
        <Route path="stability" element={<StabilityPage />} />
        <Route path="flight-dynamics" element={<FlightDynamicsPage />} />
        <Route path="control-synthesis" element={<ControlSynthesisPage />} />
        <Route path="flight-envelope" element={<FlightEnvelopePage />} />
        <Route path="traveler" element={<TravelerPage />} />
        <Route path="fmea" element={<FMEAPage />} />
        <Route path="fleet-twin" element={<FleetTwinPage />} />
        <Route path="fleet-management" element={<FleetManagementPage />} />
        <Route path="operation-analytics" element={<OperationAnalyticsPage />} />
        <Route path="aerogpt-designer" element={<AeroGPTDesignerPage />} />
        <Route path="aerogpt-engineer" element={<AeroGPTEngineerPage />} />
        <Route path="aerogpt-manufacturing" element={<AeroGPTManufacturingPage />} />
        <Route path="aerogpt-certification" element={<AeroGPTCertificationPage />} />
        <Route path="aerogpt-testpilot" element={<AeroGPTTestPilotPage />} />
        <Route path="optimization-v1" element={<OptimizationV1Page />} />
        <Route path="cert-plans" element={<CertificationPlansPage />} />
        <Route path="compliance-verification" element={<ComplianceVerificationPage />} />
        <Route path="airworthiness-approval" element={<AirworthinessApprovalPage />} />
        <Route path="continuous-airworthiness" element={<ContinuousAirworthinessPage />} />
        <Route path="aircraft-core/objects" element={<AircraftObjectExplorer />} />
        <Route path="aircraft-core/objects/:id" element={<AircraftObjectDetail />} />
        <Route path="aircraft-core/properties" element={<div>Property Definition Manager</div>} />
        <Route path="aircraft-core/baselines" element={<div>Baseline Manager</div>} />
        <Route path="aircraft-core/schemas" element={<LazyLoad><SchemaEditor /></LazyLoad>} />
        <Route path="aircraft-core/schemas/versions" element={<LazyLoad><SchemaVersionManager /></LazyLoad>} />
        <Route path="aircraft-core/schemas/migration" element={<LazyLoad><SchemaMigrationDashboard /></LazyLoad>} />
        <Route path="aircraft-core/schemas/unit-converter" element={<LazyLoad><UnitConverter /></LazyLoad>} />
        <Route path="aircraft-core/schemas/attribute-resolver" element={<LazyLoad><AttributeNameResolver /></LazyLoad>} />
        <Route path="aircraft-core/schemas/instances/:id" element={<LazyLoad><SchemaInstanceViewer /></LazyLoad>} />
        <Route path="workflow/definitions/:id/edit" element={<WorkflowEditor />} />
        <Route path="workflow/templates" element={<WorkflowTemplateGallery />} />
        <Route path="workflow/instances/:id" element={<div>Workflow Instance Monitor</div>} />
        <Route path="workflow/tasks" element={<div>Human Task Inbox</div>} />
        <Route path="workflow/triggers" element={<div>Event Trigger Config</div>} />
        <Route path="workflow/audit" element={<div>Workflow Audit Log</div>} />
        <Route path="workflow/propagation/config" element={<LazyLoad><PropagationChainConfig /></LazyLoad>} />
        <Route path="workflow/propagation/monitor" element={<LazyLoad><PropagationChainMonitor /></LazyLoad>} />
        <Route path="workflow/propagation/handlers" element={<LazyLoad><HandlerRegistryManager /></LazyLoad>} />
        <Route path="workflow/propagation/audit" element={<LazyLoad><ChainAuditLog /></LazyLoad>} />
        <Route path="workflow/propagation/dashboard" element={<LazyLoad><PropagationDashboard /></LazyLoad>} />
        <Route path="physics-twin/models" element={<div>Physics Model Manager</div>} />
        <Route path="physics-twin/simulations" element={<div>Simulation Dashboard</div>} />
        <Route path="physics-twin/simulations/:id/results" element={<div>Simulation Result Viewer</div>} />
        <Route path="physics-twin/reduced-models" element={<div>ROM Manager</div>} />
        <Route path="physics-twin/runtimes" element={<TwinRuntimeDashboard />} />
        <Route path="physics-twin/calibrations" element={<div>Calibration Manager</div>} />
        <Route path="physics-twin/plugins" element={<LazyLoad><ModelPluginManager /></LazyLoad>} />
        <Route path="physics-twin/plugins/parameters" element={<LazyLoad><ModelParameterConfig /></LazyLoad>} />
        <Route path="physics-twin/plugins/registry" element={<LazyLoad><ModelRegistryDashboard /></LazyLoad>} />
        <Route path="physics-twin/simulations/dof6" element={<LazyLoad><DOF6TrajectoryViewer /></LazyLoad>} />
        <Route path="physics-twin/simulations/battery" element={<LazyLoad><BatterySOCCurve /></LazyLoad>} />
        <Route path="physics-twin/simulations/control" element={<LazyLoad><ControlResponseCurve /></LazyLoad>} />
        <Route path="physics-twin/runtimes/coupled" element={<LazyLoad><CoupledSimulationDashboard /></LazyLoad>} />
        <Route path="v6/config" element={<ConfigurationManagerPage />} />
        <Route path="v6/traceability" element={<RequirementsTraceabilityPage />} />
        <Route path="v6/certification" element={<CertificationDashboardPage />} />
        <Route path="v6/fleet-health" element={<FleetHealthDashboardPage />} />
        <Route path="v6/production" element={<ProductionDashboardPage />} />
      </Route>
    </Routes>
  )
}

export default App