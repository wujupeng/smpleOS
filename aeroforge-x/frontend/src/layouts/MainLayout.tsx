import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Layout, Menu, Select, Space, Drawer } from 'antd'
import {
  RocketOutlined,
  ApartmentOutlined,
  ToolOutlined,
  SafetyCertificateOutlined,
  AuditOutlined,
  ExperimentOutlined,
  CloudSyncOutlined,
  ProjectOutlined,
  RobotOutlined,
  AimOutlined,
  ShopOutlined,
  LineChartOutlined,
  ScheduleOutlined,
  DashboardOutlined,
  BarChartOutlined,
  GlobalOutlined,
  MenuOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
  BranchesOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { useProjectStore } from '../stores/projectStore'
import { useTranslation } from 'react-i18next'
import { changeLocale, getCurrentLocale } from '../locales'
import { useIsMobile } from '../hooks/useBreakpoint'
import MobileTabNav from '../components/MobileTabNav'
import { OfflineBanner } from '../components/OfflineBanner'
import { isDemoMode } from '../config/appMode'

const { Header, Sider, Content } = Layout

const ALL_MENU_ITEMS = [
  { key: '/projects', icon: <ProjectOutlined />, labelKey: 'menu.projects' },
  { key: '/ai', icon: <RobotOutlined />, labelKey: 'menu.aerogpt' },
  { key: '/optimization', icon: <AimOutlined />, labelKey: 'menu.optimization' },
  { key: '/supply', icon: <ShopOutlined />, labelKey: 'menu.supply' },
  { key: '/design', icon: <RocketOutlined />, labelKey: 'menu.design' },
  { key: '/cae', icon: <ExperimentOutlined />, labelKey: 'menu.cae' },
  { key: '/twin', icon: <CloudSyncOutlined />, labelKey: 'menu.twin' },
  { key: '/predictive-twin', icon: <DashboardOutlined />, labelKey: 'menu.predictiveTwin' },
  { key: '/plm', icon: <AuditOutlined />, labelKey: 'menu.plm' },
  { key: '/bom', icon: <ApartmentOutlined />, labelKey: 'menu.bom' },
  { key: '/mes', icon: <ToolOutlined />, labelKey: 'menu.mes' },
  { key: '/scheduling', icon: <ScheduleOutlined />, labelKey: 'menu.scheduling' },
  { key: '/qms', icon: <SafetyCertificateOutlined />, labelKey: 'menu.qms' },
  { key: '/spc', icon: <LineChartOutlined />, labelKey: 'menu.spc' },
  { key: '/analytics', icon: <BarChartOutlined />, labelKey: 'menu.analytics' },
  { key: '/trace', icon: <AuditOutlined />, labelKey: 'menu.trace' },
  {
    key: 'v3-schema',
    icon: <DatabaseOutlined />,
    label: 'Schema System',
    children: [
      { key: '/aircraft-core/schemas', label: 'Schema Editor' },
      { key: '/aircraft-core/schemas/versions', label: 'Version Manager' },
      { key: '/aircraft-core/schemas/migration', label: 'Migration Dashboard' },
      { key: '/aircraft-core/schemas/unit-converter', label: 'Unit Converter' },
      { key: '/aircraft-core/schemas/attribute-resolver', label: 'Attribute Resolver' },
    ],
  },
  {
    key: 'v3-physics',
    icon: <ThunderboltOutlined />,
    label: 'Physics Plugins',
    children: [
      { key: '/physics-twin/plugins', label: 'Plugin Manager' },
      { key: '/physics-twin/plugins/parameters', label: 'Parameter Config' },
      { key: '/physics-twin/plugins/registry', label: 'Registry Dashboard' },
      { key: '/physics-twin/simulations/dof6', label: '6DOF Trajectory' },
      { key: '/physics-twin/simulations/battery', label: 'Battery SOC' },
      { key: '/physics-twin/simulations/control', label: 'Control Response' },
      { key: '/physics-twin/runtimes/coupled', label: 'Coupled Simulation' },
    ],
  },
  {
    key: 'v3-propagation',
    icon: <BranchesOutlined />,
    label: 'Propagation',
    children: [
      { key: '/workflow/propagation/dashboard', label: 'Dashboard' },
      { key: '/workflow/propagation/config', label: 'Chain Config' },
      { key: '/workflow/propagation/monitor', label: 'Chain Monitor' },
      { key: '/workflow/propagation/handlers', label: 'Handler Registry' },
      { key: '/workflow/propagation/audit', label: 'Audit Log' },
    ],
  },
  {
    key: 'v6-programs',
    icon: <RocketOutlined />,
    label: 'V6 Programs',
    children: [
      { key: '/v6/config', label: 'Configuration Manager' },
      { key: '/v6/traceability', label: 'Requirements Traceability' },
      { key: '/v6/certification', label: 'Certification Dashboard' },
      { key: '/v6/fleet-health', label: 'Fleet Health' },
      { key: '/v6/production', label: 'Production Dashboard' },
    ],
  },
]

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { projects, currentProjectId, setCurrentProject } = useProjectStore()
  const { t } = useTranslation()
  const isMobile = useIsMobile()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const menuItems = ALL_MENU_ITEMS.map(item => {
    if ('children' in item && item.children) {
      return {
        key: item.key,
        icon: item.icon,
        label: item.label,
        children: item.children.map(child => ({
          key: child.key,
          label: child.label,
        })),
      }
    }
    return {
      key: item.key,
      icon: item.icon,
      label: t((item as any).labelKey),
    }
  })

  if (isMobile) {
    return (
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#001529', padding: '0 12px' }}>
          <div style={{ color: '#fff', fontSize: 16, fontWeight: 'bold' }}>
            AeroForge-X
          </div>
          <Space size={8}>
            <Select
              value={currentProjectId || undefined}
              onChange={(val) => setCurrentProject(val)}
              placeholder={t('project.selectProject')}
              style={{ width: 120 }}
              options={projects.map(p => ({ value: p.id, label: p.name }))}
              allowClear
              size="small"
            />
            <Select
              value={getCurrentLocale()}
              onChange={(val) => changeLocale(val)}
              style={{ width: 80 }}
              size="small"
              options={[
                { value: 'zh-CN', label: '中文' },
                { value: 'en-US', label: 'EN' },
              ]}
              suffixIcon={<GlobalOutlined />}
            />
          </Space>
        </Header>
        <Layout style={{ padding: '8px', paddingBottom: 56 }}>
          <OfflineBanner />
          <Content style={{ background: '#fff', padding: 12, borderRadius: 8, minHeight: 280 }}>
            <Outlet />
          </Content>
        </Layout>
        <MobileTabNav />
      </Layout>
    )
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ display: 'flex', alignItems: 'center', background: '#001529' }}>
        <div style={{ color: '#fff', fontSize: 18, fontWeight: 'bold', marginRight: 40 }}>
          AeroForge-X
          {isDemoMode() && (
            <span style={{ marginLeft: 8, fontSize: 11, background: '#faad14', color: '#000', padding: '2px 8px', borderRadius: 4, fontWeight: 'bold' }}>
              DEMO MODE
            </span>
          )}
        </div>
        <Space>
          <Select
            value={currentProjectId || undefined}
            onChange={(val) => setCurrentProject(val)}
            placeholder={t('project.selectProject')}
            style={{ width: 200 }}
            options={projects.map(p => ({ value: p.id, label: p.name }))}
            allowClear
          />
          <Select
            value={getCurrentLocale()}
            onChange={(val) => changeLocale(val)}
            style={{ width: 100 }}
            options={[
              { value: 'zh-CN', label: '中文' },
              { value: 'en-US', label: 'English' },
            ]}
            suffixIcon={<GlobalOutlined />}
          />
        </Space>
      </Header>
      <Layout>
        <Sider width={200} theme="dark">
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{ height: '100%', borderRight: 0 }}
          />
        </Sider>
        <Layout style={{ padding: '16px' }}>
          <OfflineBanner />
          <Content style={{ background: '#fff', padding: 24, borderRadius: 8, minHeight: 280 }}>
            <Outlet />
          </Content>
        </Layout>
      </Layout>
    </Layout>
  )
}
