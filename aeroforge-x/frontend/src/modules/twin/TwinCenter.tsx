import { useState, useEffect } from 'react'
import {
  Tabs, Card, Typography, Space, Tag, Table, Button, Input, Form,
  message, Descriptions, Timeline, Alert, Badge, Statistic, Row, Col,
  Progress, List, Tooltip, Empty,
} from 'antd'
import {
  CloudSyncOutlined, ExperimentOutlined, ToolOutlined,
  WarningOutlined, CheckCircleOutlined, SyncOutlined,
  SwapOutlined, RocketOutlined, AlertOutlined,
} from '@ant-design/icons'
import apiClient from '../../services/apiClient'
import DesignTwinPage from './DesignTwinPage'
import ManufacturingTwinPage from './ManufacturingTwinPage'
import FlightTwinPage from './FlightTwinPage'
import MaintenanceTwinPage from './MaintenanceTwinPage'

const { Title, Text } = Typography

interface TwinInfo {
  twin_id: string
  sync_status: string
  data_version: number
  last_sync_time: string | null
}

interface AircraftOverview {
  aircraft_sn: string
  twin_count: number
  twins: Record<string, TwinInfo>
}

interface FeedbackRecord {
  feedback_id: string
  feedback_type: string
  aircraft_sn: string
  source_twin_id: string
  target_twin_id: string
  trigger_reason: string
  details: Record<string, unknown>
  status: string
  created_at: string
  resolved_at: string | null
}

interface ConflictRecord {
  conflict_id: string
  aircraft_sn: string
  dimension_name: string
  manufacturing_value: number
  flight_inferred_value: number
  deviation: number
  resolution: string
  resolved_value: number | null
  reason: string
  detected_at: string
  resolved_at: string | null
}

const syncStatusConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  realtime: { color: 'green', icon: <CheckCircleOutlined />, label: '实时同步' },
  lagged: { color: 'orange', icon: <WarningOutlined />, label: '数据滞后' },
  offline: { color: 'red', icon: <AlertOutlined />, label: '离线' },
}

const twinTypeLabels: Record<string, { label: string; icon: React.ReactNode }> = {
  design: { label: '设计孪生', icon: <RocketOutlined /> },
  manufacturing: { label: '制造孪生', icon: <ToolOutlined /> },
  flight: { label: '飞行孪生', icon: <ExperimentOutlined /> },
  maintenance: { label: '维护孪生', icon: <SyncOutlined /> },
}

function TwinOverviewPage() {
  const [searchSn, setSearchSn] = useState('')
  const [overview, setOverview] = useState<AircraftOverview | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchOverview = async (sn: string) => {
    if (!sn) return
    setLoading(true)
    try {
      const resp = await apiClient.get(`/twin/aircraft/${sn}/overview`)
      setOverview(resp.data?.data ?? null)
    } catch {
      message.error('获取孪生概览失败')
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      title: '孪生类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const cfg = twinTypeLabels[type] || { label: type, icon: null }
        return (
          <Space>
            {cfg.icon}
            <span>{cfg.label}</span>
          </Space>
        )
      },
    },
    {
      title: '同步状态',
      dataIndex: 'sync_status',
      key: 'sync_status',
      render: (status: string) => {
        const cfg = syncStatusConfig[status] || syncStatusConfig.offline
        return (
          <Tag color={cfg.color} icon={cfg.icon}>
            {cfg.label}
          </Tag>
        )
      },
    },
    {
      title: '数据版本',
      dataIndex: 'data_version',
      key: 'data_version',
      render: (v: number) => `v${v}`,
    },
    {
      title: '最后同步时间',
      dataIndex: 'last_sync_time',
      key: 'last_sync_time',
      render: (t: string | null) => t ? new Date(t).toLocaleString() : '-',
    },
    {
      title: '数据滞后警告',
      key: 'lag_warning',
      render: (_: unknown, record: TwinInfo) => {
        if (record.sync_status === 'lagged') {
          return <Alert type="warning" message="数据滞后超过5分钟" showIcon banner={false} style={{ padding: '2px 8px' }} />
        }
        if (record.sync_status === 'offline') {
          return <Alert type="error" message="孪生体离线" showIcon banner={false} style={{ padding: '2px 8px' }} />
        }
        return <Tag color="green">正常</Tag>
      },
    },
  ]

  const twinTableData = overview
    ? Object.entries(overview.twins).map(([type, info]) => ({ ...info, type, key: type }))
    : []

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Input.Search
            placeholder="输入飞行器序列号"
            value={searchSn}
            onChange={(e) => setSearchSn(e.target.value)}
            onSearch={fetchOverview}
            enterButton="查询"
            style={{ width: 400 }}
          />
        </Space>
      </Card>

      {overview && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card>
                <Statistic title="飞行器序列号" value={overview.aircraft_sn} />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic title="孪生体数量" value={overview.twin_count} suffix="/ 4" />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="实时同步"
                  value={twinTableData.filter(t => t.sync_status === 'realtime').length}
                  valueStyle={{ color: '#3f8600' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="数据滞后/离线"
                  value={twinTableData.filter(t => t.sync_status !== 'realtime').length}
                  valueStyle={{ color: '#cf1322' }}
                />
              </Card>
            </Col>
          </Row>

          <Card title="孪生体状态">
            <Table
              columns={columns}
              dataSource={twinTableData}
              pagination={false}
              loading={loading}
              size="small"
            />
          </Card>
        </>
      )}

      {!overview && (
        <Card>
          <Empty description="请输入飞行器序列号查询孪生体概览" />
        </Card>
      )}
    </div>
  )
}

function TwinLoopPage() {
  const [feedbackRecords, setFeedbackRecords] = useState<FeedbackRecord[]>([])
  const [conflictRecords, setConflictRecords] = useState<ConflictRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [feedbackForm] = Form.useForm()
  const [conflictForm] = Form.useForm()

  const fetchRecords = async () => {
    setLoading(true)
    try {
      const [fbResp, cfResp] = await Promise.all([
        apiClient.get('/twin/loop/feedback-records'),
        apiClient.get('/twin/loop/conflict-records'),
      ])
      setFeedbackRecords(fbResp.data?.data?.records ?? [])
      setConflictRecords(cfResp.data?.data?.records ?? [])
    } catch {
      message.error('获取闭环记录失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRecords()
  }, [])

  const handleFeedbackToDesign = async (values: { aircraft_sn: string; source_type: string }) => {
    try {
      await apiClient.post('/twin/loop/feedback-to-design', values)
      message.success('设计反馈已触发')
      fetchRecords()
    } catch {
      message.error('反馈触发失败')
    }
  }

  const handleFeedbackToMaintenance = async (values: { aircraft_sn: string }) => {
    try {
      await apiClient.post('/twin/loop/feedback-to-maintenance', values)
      message.success('维护反馈已触发')
      fetchRecords()
    } catch {
      message.error('反馈触发失败')
    }
  }

  const handleDetectConflict = async (values: { aircraft_sn: string }) => {
    try {
      const resp = await apiClient.post('/twin/loop/detect-conflict', values)
      const data = resp.data?.data
      if (data?.conflict_count > 0) {
        message.warning(`检测到 ${data.conflict_count} 个数据冲突，以制造孪生实测数据为准`)
      } else {
        message.success('未检测到数据冲突')
      }
      fetchRecords()
    } catch {
      message.error('冲突检测失败')
    }
  }

  const feedbackTypeLabels: Record<string, string> = {
    manufacturing_to_design: '制造→设计',
    flight_to_design: '飞行→设计',
    design_to_maintenance: '设计→维护',
  }

  const feedbackColumns = [
    { title: '反馈ID', dataIndex: 'feedback_id', key: 'feedback_id' },
    { title: '类型', dataIndex: 'feedback_type', key: 'feedback_type', render: (t: string) => feedbackTypeLabels[t] || t },
    { title: '飞行器SN', dataIndex: 'aircraft_sn', key: 'aircraft_sn' },
    { title: '触发原因', dataIndex: 'trigger_reason', key: 'trigger_reason' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => {
        const colorMap: Record<string, string> = { pending: 'orange', applied: 'green', approved: 'blue', rejected: 'red' }
        return <Tag color={colorMap[s] || 'default'}>{s}</Tag>
      },
    },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (t: string) => t ? new Date(t).toLocaleString() : '-' },
  ]

  const conflictColumns = [
    { title: '冲突ID', dataIndex: 'conflict_id', key: 'conflict_id' },
    { title: '飞行器SN', dataIndex: 'aircraft_sn', key: 'aircraft_sn' },
    { title: '维度', dataIndex: 'dimension_name', key: 'dimension_name' },
    { title: '制造值', dataIndex: 'manufacturing_value', key: 'manufacturing_value' },
    { title: '飞行推断值', dataIndex: 'flight_inferred_value', key: 'flight_inferred_value' },
    { title: '偏差', dataIndex: 'deviation', key: 'deviation' },
    {
      title: '解决策略',
      dataIndex: 'resolution',
      key: 'resolution',
      render: (r: string) => r === 'manufacturing_wins'
        ? <Tag color="blue">制造孪生优先</Tag>
        : <Tag>{r}</Tag>,
    },
    { title: '解决值', dataIndex: 'resolved_value', key: 'resolved_value' },
  ]

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card title="制造/飞行 → 设计反馈" size="small">
            <Form form={feedbackForm} onFinish={handleFeedbackToDesign} layout="vertical">
              <Form.Item name="aircraft_sn" label="飞行器SN" rules={[{ required: true }]}>
                <Input placeholder="SN-001" />
              </Form.Item>
              <Form.Item name="source_type" label="反馈来源" initialValue="manufacturing">
                <Input />
              </Form.Item>
              <Button type="primary" htmlType="submit" icon={<SwapOutlined />}>
                触发反馈
              </Button>
            </Form>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="设计 → 维护反馈" size="small">
            <Form onFinish={handleFeedbackToMaintenance} layout="vertical">
              <Form.Item name="aircraft_sn" label="飞行器SN" rules={[{ required: true }]}>
                <Input placeholder="SN-001" />
              </Form.Item>
              <Button type="primary" htmlType="submit" icon={<ToolOutlined />}>
                触发反馈
              </Button>
            </Form>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="数据冲突检测" size="small">
            <Form form={conflictForm} onFinish={handleDetectConflict} layout="vertical">
              <Form.Item name="aircraft_sn" label="飞行器SN" rules={[{ required: true }]}>
                <Input placeholder="SN-001" />
              </Form.Item>
              <Button type="primary" htmlType="submit" icon={<WarningOutlined />}>
                检测冲突
              </Button>
            </Form>
          </Card>
        </Col>
      </Row>

      <Card title="闭环反馈链路可视化" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16, padding: '16px 0' }}>
          <div style={{ textAlign: 'center', padding: 16, background: '#e6f7ff', borderRadius: 8, minWidth: 120 }}>
            <ToolOutlined style={{ fontSize: 24, color: '#1890ff' }} />
            <div style={{ marginTop: 4, fontWeight: 'bold' }}>制造孪生</div>
            <div style={{ fontSize: 12, color: '#666' }}>实测数据</div>
          </div>
          <SwapOutlined style={{ fontSize: 20, color: '#999' }} />
          <div style={{ textAlign: 'center', padding: 16, background: '#f6ffed', borderRadius: 8, minWidth: 120 }}>
            <RocketOutlined style={{ fontSize: 24, color: '#52c41a' }} />
            <div style={{ marginTop: 4, fontWeight: 'bold' }}>设计中心</div>
            <div style={{ fontSize: 12, color: '#666' }}>参数调整</div>
          </div>
          <SwapOutlined style={{ fontSize: 20, color: '#999' }} />
          <div style={{ textAlign: 'center', padding: 16, background: '#fff7e6', borderRadius: 8, minWidth: 120 }}>
            <SyncOutlined style={{ fontSize: 24, color: '#fa8c16' }} />
            <div style={{ marginTop: 4, fontWeight: 'bold' }}>维护计划</div>
            <div style={{ fontSize: 12, color: '#666' }}>策略更新</div>
          </div>
        </div>
        <div style={{ textAlign: 'center', color: '#999', fontSize: 12 }}>
          制造偏差超差 → 设计参数调整 → 维护策略更新 | 数据冲突时以制造孪生实测数据为准
        </div>
      </Card>

      <Card title="反馈记录" style={{ marginBottom: 16 }}>
        <Table
          columns={feedbackColumns}
          dataSource={feedbackRecords}
          rowKey="feedback_id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Card title="冲突记录">
        <Table
          columns={conflictColumns}
          dataSource={conflictRecords}
          rowKey="conflict_id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  )
}

export default function TwinCenter() {
  return (
    <div>
      <Title level={3} style={{ marginBottom: 16 }}>
        <CloudSyncOutlined style={{ marginRight: 8 }} />
        数字孪生中心
      </Title>
      <Tabs
        defaultActiveKey="overview"
        items={[
          { key: 'overview', label: '孪生体总览', children: <TwinOverviewPage /> },
          { key: 'design', label: '设计孪生', children: <DesignTwinPage /> },
          { key: 'manufacturing', label: '制造孪生', children: <ManufacturingTwinPage /> },
          { key: 'flight', label: '飞行孪生', children: <FlightTwinPage /> },
          { key: 'maintenance', label: '维护孪生', children: <MaintenanceTwinPage /> },
          { key: 'loop', label: '孪生闭环', children: <TwinLoopPage /> },
        ]}
      />
    </div>
  )
}