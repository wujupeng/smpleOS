import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu } from 'antd'
import {
  ProjectOutlined,
  RobotOutlined,
  AimOutlined,
  ShopOutlined,
  RocketOutlined,
  ExperimentOutlined,
  CloudSyncOutlined,
  DashboardOutlined,
  ApartmentOutlined,
  ToolOutlined,
  ScheduleOutlined,
  SafetyCertificateOutlined,
  LineChartOutlined,
  BarChartOutlined,
  AuditOutlined,
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'

const { Footer } = Layout

const PRIMARY_ITEMS = [
  { key: '/design', icon: <RocketOutlined /> },
  { key: '/mes', icon: <ToolOutlined /> },
  { key: '/qms', icon: <SafetyCertificateOutlined /> },
  { key: '/analytics', icon: <BarChartOutlined /> },
  { key: '/more', icon: <AuditOutlined /> },
]

const MORE_ITEMS = [
  { key: '/projects', icon: <ProjectOutlined /> },
  { key: '/ai', icon: <RobotOutlined /> },
  { key: '/optimization', icon: <AimOutlined /> },
  { key: '/supply', icon: <ShopOutlined /> },
  { key: '/cae', icon: <ExperimentOutlined /> },
  { key: '/twin', icon: <CloudSyncOutlined /> },
  { key: '/predictive-twin', icon: <DashboardOutlined /> },
  { key: '/plm', icon: <AuditOutlined /> },
  { key: '/bom', icon: <ApartmentOutlined /> },
  { key: '/scheduling', icon: <ScheduleOutlined /> },
  { key: '/spc', icon: <LineChartOutlined /> },
  { key: '/trace', icon: <AuditOutlined /> },
]

export default function MobileTabNav() {
  const navigate = useNavigate()
  const location = useLocation()
  const { t } = useTranslation()

  const activeKey = PRIMARY_ITEMS.find(item => location.pathname.startsWith(item.key))?.key
    || (MORE_ITEMS.find(item => location.pathname.startsWith(item.key)) ? '/more' : '/design')

  const [showMore, setShowMore] = useState(false)

  const handlePrimaryClick = (key: string) => {
    if (key === '/more') {
      setShowMore(prev => !prev)
    } else {
      setShowMore(false)
      navigate(key)
    }
  }

  return (
    <Footer style={{ position: 'fixed', bottom: 0, left: 0, right: 0, padding: 0, zIndex: 1000, background: '#001529' }}>
      <Menu
        mode="horizontal"
        selectedKeys={[activeKey]}
        onClick={({ key }) => handlePrimaryClick(key)}
        items={PRIMARY_ITEMS.map(item => ({
          key: item.key,
          icon: item.icon,
          label: item.key === '/more' ? t('menu.more') : t(`menu.${item.key.slice(1)}`),
        }))}
        style={{ display: 'flex', justifyContent: 'space-around', background: '#001529', borderBottom: 'none' }}
        theme="dark"
      />
      {showMore && (
        <div style={{
          position: 'fixed', bottom: 46, left: 0, right: 0,
          background: '#001529', padding: '8px 16px',
          maxHeight: '50vh', overflowY: 'auto',
          borderTop: '1px solid rgba(255,255,255,0.1)',
        }}>
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            onClick={({ key }) => { navigate(key); setShowMore(false) }}
            items={MORE_ITEMS.map(item => ({
              key: item.key,
              icon: item.icon,
              label: t(`menu.${item.key.slice(1)}`),
            }))}
            style={{ background: 'transparent' }}
            theme="dark"
          />
        </div>
      )}
    </Footer>
  )
}