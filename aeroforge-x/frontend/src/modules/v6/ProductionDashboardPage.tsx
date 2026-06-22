import { useState, useEffect } from 'react'
import {
  Card, Table, Tag, Row, Col, Statistic, Typography, Breadcrumb,
  Progress, Tooltip, Badge, Space, Select, Timeline,
} from 'antd'
import {
  DashboardOutlined, ToolOutlined, ThunderboltOutlined,
  CheckCircleOutlined, WarningOutlined, RobotOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import { factoryApi } from '../../api/v6Api'

const { Title, Text } = Typography

interface EquipmentOEE {
  equipment_id: string
  equipment_name: string
  equipment_type: string
  availability: number
  performance: number
  quality: number
  oee: number
  status: 'Running' | 'Idle' | 'Down'
}

interface AGVStatus {
  agv_id: string
  location: string
  battery: number
  task: string
  status: 'Active' | 'Charging' | 'Idle'
}

export default function ProductionDashboardPage() {
  const [equipment, setEquipment] = useState<EquipmentOEE[]>([])
  const [agvs, setAGVs] = useState<AGVStatus[]>([])
  const [filterType, setFilterType] = useState<string>('all')

  useEffect(() => {
    setEquipment(mockEquipment())
    setAGVs(mockAGVs())
  }, [])

  const avgOEE = equipment.length > 0
    ? Math.round(equipment.reduce((s, e) => s + e.oee, 0) / equipment.length)
    : 0

  const runningCount = equipment.filter(e => e.status === 'Running').length
  const downCount = equipment.filter(e => e.status === 'Down').length
  const activeAGVs = agvs.filter(a => a.status === 'Active').length

  const filteredEquipment = filterType === 'all'
    ? equipment
    : equipment.filter(e => e.equipment_type === filterType)

  const eqColumns = [
    { title: 'Equipment', dataIndex: 'equipment_name', key: 'name' },
    {
      title: 'Type',
      dataIndex: 'equipment_type',
      key: 'type',
      render: (t: string) => <Tag>{t}</Tag>,
    },
    {
      title: 'Availability',
      dataIndex: 'availability',
      key: 'avail',
      render: (v: number) => <Progress percent={v} size="small" strokeColor={v >= 90 ? '#52c41a' : v >= 70 ? '#faad14' : '#ff4d4f'} style={{ width: 80 }} />,
    },
    {
      title: 'Performance',
      dataIndex: 'performance',
      key: 'perf',
      render: (v: number) => <Progress percent={v} size="small" strokeColor={v >= 90 ? '#52c41a' : v >= 70 ? '#faad14' : '#ff4d4f'} style={{ width: 80 }} />,
    },
    {
      title: 'Quality',
      dataIndex: 'quality',
      key: 'qual',
      render: (v: number) => <Progress percent={v} size="small" strokeColor={v >= 95 ? '#52c41a' : v >= 85 ? '#faad14' : '#ff4d4f'} style={{ width: 80 }} />,
    },
    {
      title: 'OEE',
      dataIndex: 'oee',
      key: 'oee',
      render: (v: number) => (
        <Text strong style={{ color: v >= 85 ? '#52c41a' : v >= 65 ? '#faad14' : '#ff4d4f' }}>
          {v.toFixed(1)}%
        </Text>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config: Record<string, { color: string; icon: any }> = {
          Running: { color: 'success', icon: <CheckCircleOutlined /> },
          Idle: { color: 'warning', icon: <ClockCircleOutlined /> },
          Down: { color: 'error', icon: <WarningOutlined /> },
        }
        const c = config[status] || config.Idle
        return <Tag icon={c.icon} color={c.color}>{status}</Tag>
      },
    },
  ]

  const agvColumns = [
    { title: 'AGV ID', dataIndex: 'agv_id', key: 'agv_id' },
    { title: 'Location', dataIndex: 'location', key: 'location' },
    {
      title: 'Battery',
      dataIndex: 'battery',
      key: 'battery',
      render: (v: number) => <Progress percent={v} size="small" strokeColor={v >= 50 ? '#52c41a' : '#ff4d4f'} style={{ width: 60 }} />,
    },
    { title: 'Task', dataIndex: 'task', key: 'task' },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => {
        const colors: Record<string, string> = { Active: 'success', Charging: 'processing', Idle: 'default' }
        return <Tag color={colors[s] || 'default'}>{s}</Tag>
      },
    },
  ]

  return (
    <div style={{ padding: 0 }}>
      <Breadcrumb items={[
        { title: 'AeroForge-X' },
        { title: 'V6 Programs' },
        { title: 'Production Dashboard' },
      ]} style={{ marginBottom: 16 }} />

      <Title level={3} style={{ marginBottom: 24 }}>
        <DashboardOutlined style={{ marginRight: 8 }} />
        Production Dashboard
        <Text type="secondary" style={{ fontSize: 14, marginLeft: 12 }}>
          Real-time OEE monitoring, AGV fleet status, and bottleneck detection
        </Text>
      </Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Avg OEE" value={avgOEE} suffix="%" prefix={<DashboardOutlined />} valueStyle={{ color: avgOEE >= 85 ? '#3f8600' : '#cf1322' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Running" value={runningCount} suffix={`/ ${equipment.length}`} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Down" value={downCount} prefix={<WarningOutlined />} valueStyle={{ color: '#cf1322' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Active AGVs" value={activeAGVs} suffix={`/ ${agvs.length}`} prefix={<RobotOutlined />} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={16}>
          <Card
            title="Equipment OEE"
            extra={
              <Select value={filterType} onChange={setFilterType} style={{ width: 120 }}>
                <Select.Option value="all">All Types</Select.Option>
                <Select.Option value="CNC">CNC</Select.Option>
                <Select.Option value="Robot">Robot</Select.Option>
                <Select.Option value="PLC">PLC</Select.Option>
              </Select>
            }
          >
            <Table dataSource={filteredEquipment} columns={eqColumns} rowKey="equipment_id" size="small" pagination={{ pageSize: 8 }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="Production Events" size="small" style={{ marginBottom: 16 }}>
            <Timeline
              items={[
                { color: 'green', children: 'CNC-003: Operation #47 completed' },
                { color: 'red', children: 'Robot-002: Quality alert - surface defect' },
                { color: 'blue', children: 'AGV-03: Delivered parts to Bay-4' },
                { color: 'orange', children: 'CNC-001: Deviation detected - tolerance' },
                { color: 'green', children: 'PLC-005: Process step completed' },
              ]}
            />
          </Card>
          <Card title="AGV Fleet" size="small">
            <Table dataSource={agvs} columns={agvColumns} rowKey="agv_id" size="small" pagination={false} />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

function mockEquipment(): EquipmentOEE[] {
  return [
    { equipment_id: 'CNC-001', equipment_name: 'CNC Milling Bay-1', equipment_type: 'CNC', availability: 92, performance: 88, quality: 97, oee: 78.7, status: 'Running' },
    { equipment_id: 'CNC-002', equipment_name: 'CNC Turning Bay-2', equipment_type: 'CNC', availability: 88, performance: 91, quality: 99, oee: 79.3, status: 'Running' },
    { equipment_id: 'CNC-003', equipment_name: 'CNC 5-Axis Bay-3', equipment_type: 'CNC', availability: 75, performance: 82, quality: 95, oee: 58.4, status: 'Idle' },
    { equipment_id: 'Robot-001', equipment_name: 'Assembly Robot A', equipment_type: 'Robot', availability: 96, performance: 94, quality: 99, oee: 89.5, status: 'Running' },
    { equipment_id: 'Robot-002', equipment_name: 'Welding Robot B', equipment_type: 'Robot', availability: 45, performance: 60, quality: 88, oee: 23.8, status: 'Down' },
    { equipment_id: 'PLC-001', equipment_name: 'Heat Treatment PLC', equipment_type: 'PLC', availability: 98, performance: 95, quality: 99, oee: 92.2, status: 'Running' },
  ]
}

function mockAGVs(): AGVStatus[] {
  return [
    { agv_id: 'AGV-01', location: 'Bay-1 → Bay-3', battery: 82, task: 'Transporting wing spar', status: 'Active' },
    { agv_id: 'AGV-02', location: 'Charging Station', battery: 15, task: '-', status: 'Charging' },
    { agv_id: 'AGV-03', location: 'Bay-4', battery: 65, task: 'Delivering fasteners', status: 'Active' },
    { agv_id: 'AGV-04', location: 'Staging Area', battery: 90, task: '-', status: 'Idle' },
  ]
}