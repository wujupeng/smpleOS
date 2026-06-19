import { useState, useEffect } from 'react'
import {
  Card, Table, Tag, Row, Col, Statistic, Typography, Breadcrumb,
  Progress, Tooltip, Badge, Space, Select,
} from 'antd'
import {
  HeartOutlined, ThunderboltOutlined, WarningOutlined,
  CheckCircleOutlined, DashboardOutlined, ToolOutlined,
  ExperimentOutlined,
} from '@ant-design/icons'
import { fleetApi } from '../../../api/v6Api'

const { Title, Text } = Typography

interface FleetAircraft {
  tail_number: string
  aircraft_type: string
  overall_health: number
  rul_min_hours: number
  active_alerts: number
  last_inspection: string
  status: 'Healthy' | 'Watch' | 'Critical'
}

interface PHMPrediction {
  component_id: string
  rul_hours: number
  confidence: number
  is_low_confidence: boolean
}

export default function FleetHealthDashboardPage() {
  const [aircraft, setAircraft] = useState<FleetAircraft[]>([])
  const [predictions, setPredictions] = useState<PHMPrediction[]>([])
  const [filterStatus, setFilterStatus] = useState<string>('all')

  useEffect(() => {
    setAircraft(mockFleet())
    setPredictions(mockPredictions())
  }, [])

  const healthyCount = aircraft.filter(a => a.status === 'Healthy').length
  const watchCount = aircraft.filter(a => a.status === 'Watch').length
  const criticalCount = aircraft.filter(a => a.status === 'Critical').length
  const avgHealth = aircraft.length > 0
    ? Math.round(aircraft.reduce((sum, a) => sum + a.overall_health, 0) / aircraft.length)
    : 0

  const filteredAircraft = filterStatus === 'all'
    ? aircraft
    : aircraft.filter(a => a.status === filterStatus)

  const columns = [
    {
      title: 'Tail Number',
      dataIndex: 'tail_number',
      key: 'tail_number',
      render: (text: string) => <Text strong style={{ fontFamily: 'monospace' }}>{text}</Text>,
    },
    { title: 'Type', dataIndex: 'aircraft_type', key: 'aircraft_type' },
    {
      title: 'Health',
      dataIndex: 'overall_health',
      key: 'health',
      render: (v: number) => (
        <Progress
          percent={v}
          size="small"
          strokeColor={v >= 80 ? '#52c41a' : v >= 60 ? '#faad14' : '#ff4d4f'}
          style={{ width: 100 }}
        />
      ),
    },
    {
      title: 'Min RUL (h)',
      dataIndex: 'rul_min_hours',
      key: 'rul',
      render: (v: number) => (
        <Text style={{ color: v < 500 ? '#ff4d4f' : v < 1000 ? '#faad14' : '#52c41a' }}>
          {v.toLocaleString()}
        </Text>
      ),
    },
    {
      title: 'Alerts',
      dataIndex: 'active_alerts',
      key: 'alerts',
      render: (v: number) => <Badge count={v} style={{ backgroundColor: v > 0 ? '#ff4d4f' : '#52c41a' }} />,
    },
    { title: 'Last Inspection', dataIndex: 'last_inspection', key: 'last_inspection' },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config: Record<string, { color: string; icon: any }> = {
          Healthy: { color: 'success', icon: <CheckCircleOutlined /> },
          Watch: { color: 'warning', icon: <WarningOutlined /> },
          Critical: { color: 'error', icon: <ThunderboltOutlined /> },
        }
        const c = config[status] || config.Healthy
        return <Tag icon={c.icon} color={c.color}>{status}</Tag>
      },
    },
  ]

  const predColumns = [
    {
      title: 'Component',
      dataIndex: 'component_id',
      key: 'component_id',
      render: (text: string) => <Text style={{ fontFamily: 'monospace' }}>{text}</Text>,
    },
    {
      title: 'RUL (hours)',
      dataIndex: 'rul_hours',
      key: 'rul',
      render: (v: number) => (
        <Text style={{ color: v < 500 ? '#ff4d4f' : v < 1000 ? '#faad14' : '#52c41a' }}>
          {v.toLocaleString()}
        </Text>
      ),
    },
    {
      title: 'Confidence',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (v: number) => (
        <Progress
          percent={Math.round(v * 100)}
          size="small"
          strokeColor={v >= 0.8 ? '#52c41a' : v >= 0.6 ? '#faad14' : '#ff4d4f'}
          style={{ width: 80 }}
        />
      ),
    },
    {
      title: 'Quality',
      dataIndex: 'is_low_confidence',
      key: 'quality',
      render: (low: boolean) => low
        ? <Tag icon={<WarningOutlined />} color="warning">Low Confidence</Tag>
        : <Tag icon={<CheckCircleOutlined />} color="success">High Confidence</Tag>,
    },
  ]

  return (
    <div style={{ padding: 0 }}>
      <Breadcrumb items={[
        { title: 'AeroForge-X' },
        { title: 'V6 Programs' },
        { title: 'Fleet Health' },
      ]} style={{ marginBottom: 16 }} />

      <Title level={3} style={{ marginBottom: 24 }}>
        <HeartOutlined style={{ marginRight: 8 }} />
        Fleet Health Dashboard
        <Text type="secondary" style={{ fontSize: 14, marginLeft: 12 }}>
          PHM predictions, RUL tracking, and closed-loop maintenance
        </Text>
      </Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Fleet Size" value={aircraft.length} prefix={<DashboardOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Avg Health" value={avgHealth} suffix="%" prefix={<HeartOutlined />} valueStyle={{ color: avgHealth >= 80 ? '#3f8600' : '#cf1322' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Watch / Critical" value={watchCount + criticalCount} prefix={<WarningOutlined />} valueStyle={{ color: '#faad14' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Closed-Loop Actions" value={3} prefix={<ToolOutlined />} valueStyle={{ color: '#1890ff' }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card title="Fleet Health Distribution" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div><Tag color="success">Healthy</Tag> <Progress percent={aircraft.length > 0 ? Math.round(healthyCount / aircraft.length * 100) : 0} size="small" strokeColor="#52c41a" /></div>
              <div><Tag color="warning">Watch</Tag> <Progress percent={aircraft.length > 0 ? Math.round(watchCount / aircraft.length * 100) : 0} size="small" strokeColor="#faad14" /></div>
              <div><Tag color="error">Critical</Tag> <Progress percent={aircraft.length > 0 ? Math.round(criticalCount / aircraft.length * 100) : 0} size="small" strokeColor="#ff4d4f" /></div>
            </Space>
          </Card>
        </Col>
        <Col span={16}>
          <Card title="PHM Model Confidence" size="small">
            <Row gutter={8}>
              {predictions.slice(0, 5).map(p => (
                <Col span={Math.floor(16 / Math.min(predictions.length, 5))} key={p.component_id}>
                  <Tooltip title={`RUL: ${p.rul_hours}h, Confidence: ${(p.confidence * 100).toFixed(0)}%`}>
                    <Card size="small" hoverable style={{ textAlign: 'center' }}>
                      <Text style={{ fontSize: 11 }}>{p.component_id}</Text>
                      <Progress
                        type="circle"
                        percent={Math.round(p.confidence * 100)}
                        size={48}
                        strokeColor={p.confidence >= 0.8 ? '#52c41a' : p.confidence >= 0.6 ? '#faad14' : '#ff4d4f'}
                      />
                    </Card>
                  </Tooltip>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>
      </Row>

      <Card
        title="Fleet Aircraft Status"
        extra={
          <Select value={filterStatus} onChange={setFilterStatus} style={{ width: 120 }}>
            <Select.Option value="all">All Status</Select.Option>
            <Select.Option value="Healthy">Healthy</Select.Option>
            <Select.Option value="Watch">Watch</Select.Option>
            <Select.Option value="Critical">Critical</Select.Option>
          </Select>
        }
        style={{ marginBottom: 16 }}
      >
        <Table dataSource={filteredAircraft} columns={columns} rowKey="tail_number" size="small" pagination={{ pageSize: 8 }} />
      </Card>

      <Card title="PHM Predictions - Lowest RUL Components">
        <Table dataSource={predictions} columns={predColumns} rowKey="component_id" size="small" pagination={{ pageSize: 8 }} />
      </Card>
    </div>
  )
}

function mockFleet(): FleetAircraft[] {
  return [
    { tail_number: 'B-001A', aircraft_type: 'A320', overall_health: 92, rul_min_hours: 3200, active_alerts: 0, last_inspection: '2026-05-15', status: 'Healthy' },
    { tail_number: 'B-002A', aircraft_type: 'A320', overall_health: 78, rul_min_hours: 1800, active_alerts: 2, last_inspection: '2026-05-10', status: 'Watch' },
    { tail_number: 'B-003A', aircraft_type: 'C919', overall_health: 95, rul_min_hours: 5400, active_alerts: 0, last_inspection: '2026-06-01', status: 'Healthy' },
    { tail_number: 'B-004A', aircraft_type: 'A350', overall_health: 45, rul_min_hours: 320, active_alerts: 5, last_inspection: '2026-04-20', status: 'Critical' },
    { tail_number: 'B-005A', aircraft_type: 'C919', overall_health: 88, rul_min_hours: 2800, active_alerts: 1, last_inspection: '2026-05-28', status: 'Watch' },
    { tail_number: 'B-006A', aircraft_type: 'A320', overall_health: 96, rul_min_hours: 6100, active_alerts: 0, last_inspection: '2026-06-10', status: 'Healthy' },
  ]
}

function mockPredictions(): PHMPrediction[] {
  return [
    { component_id: 'ENG-LF-001', rul_hours: 320, confidence: 0.92, is_low_confidence: false },
    { component_id: 'HYD-ML-003', rul_hours: 580, confidence: 0.75, is_low_confidence: false },
    { component_id: 'APU-001', rul_hours: 1200, confidence: 0.55, is_low_confidence: true },
    { component_id: 'LG-NL-002', rul_hours: 2400, confidence: 0.88, is_low_confidence: false },
    { component_id: 'WNG-SP-001', rul_hours: 4500, confidence: 0.95, is_low_confidence: false },
    { component_id: 'FUS-FR-008', rul_hours: 890, confidence: 0.62, is_low_confidence: true },
  ]
}