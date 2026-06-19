import { useState } from 'react'
import {
  Card, Typography, Space, Tag, Table, Button, Input, Form,
  message, Descriptions, Row, Col, Statistic, Empty, Divider,
  Alert, Progress, Select, Timeline,
} from 'antd'
import {
  ToolOutlined, SafetyCertificateOutlined, ScheduleOutlined,
  CheckCircleOutlined, WarningOutlined, AlertOutlined,
  HistoryOutlined, ReloadOutlined,
} from '@ant-design/icons'
import apiClient from '../../services/apiClient'

const { Title, Text } = Typography

interface MaintenanceRecord {
  record_id: string
  aircraft_sn: string
  maintenance_type: string
  content: string
  result: string
  component_id: string
  component_name: string
  description: string
  performed_by: string
  performed_at: string
  flight_hours_at_maintenance: number
  parts_replaced: string[]
}

interface RemainingLifeEstimate {
  component_id: string
  component_name: string
  total_design_life_fh: number
  flight_hours_elapsed: number
  fatigue_damage: number
  maintenance_benefit: number
  estimated_remaining_fh: number
  confidence: string
}

interface MaintenancePlanItem {
  plan_item_id: string
  aircraft_sn: string
  maintenance_type: string
  component_id: string
  component_name: string
  description: string
  scheduled_at: string
  priority: string
  trigger_reason: string
}

const maintenanceTypeLabels: Record<string, { label: string; color: string }> = {
  preventive: { label: '预防性维护', color: 'blue' },
  corrective: { label: '纠正性维护', color: 'orange' },
  improvement: { label: '改进性维护', color: 'green' },
}

const contentLabels: Record<string, string> = {
  part_replacement: '部件更换',
  defect_repair: '缺陷修复',
  system_upgrade: '系统升级',
  inspection: '检查',
  lubrication: '润滑',
}

const resultLabels: Record<string, { label: string; color: string }> = {
  completed: { label: '已完成', color: 'green' },
  partially_completed: { label: '部分完成', color: 'orange' },
  follow_up_required: { label: '需跟进', color: 'red' },
}

const priorityLabels: Record<string, { label: string; color: string }> = {
  urgent: { label: '紧急', color: 'red' },
  high: { label: '高', color: 'orange' },
  normal: { label: '普通', color: 'blue' },
  low: { label: '低', color: 'default' },
}

const confidenceLabels: Record<string, { label: string; color: string }> = {
  high: { label: '高', color: 'green' },
  medium: { label: '中', color: 'orange' },
  low: { label: '低', color: 'red' },
}

export default function MaintenanceTwinPage() {
  const [searchSn, setSearchSn] = useState('')
  const [records, setRecords] = useState<MaintenanceRecord[]>([])
  const [lifeEstimates, setLifeEstimates] = useState<RemainingLifeEstimate[]>([])
  const [planItems, setPlanItems] = useState<MaintenancePlanItem[]>([])
  const [loading, setLoading] = useState(false)

  const fetchData = async (sn: string) => {
    if (!sn) return
    setLoading(true)
    try {
      const [recordsResp, lifeResp] = await Promise.all([
        apiClient.get(`/twin/maintenance/${sn}/records`),
        apiClient.post('/twin/maintenance/estimate-life', {
          aircraft_serial_number: sn,
          flight_hours: 0,
        }),
      ])
      setRecords(recordsResp.data?.data?.records ?? [])
      setLifeEstimates(lifeResp.data?.data?.estimates ?? [])
    } catch {
      message.error('获取维护孪生数据失败')
    } finally {
      setLoading(false)
    }
  }

  const handleRecordMaintenance = async (values: {
    aircraft_serial_number: string
    maintenance_type: string
    content: string
    result: string
    component_id: string
    component_name: string
    description: string
    performed_by: string
    flight_hours: number
    parts_replaced: string
  }) => {
    try {
      const partsReplaced = values.parts_replaced
        ? values.parts_replaced.split(',').map(s => s.trim()).filter(Boolean)
        : []
      await apiClient.post('/twin/maintenance/record', {
        aircraft_serial_number: values.aircraft_serial_number,
        maintenance_type: values.maintenance_type,
        content: values.content,
        result: values.result,
        component_id: values.component_id,
        component_name: values.component_name,
        description: values.description,
        performed_by: values.performed_by,
        flight_hours: values.flight_hours,
        parts_replaced: partsReplaced,
      })
      message.success('维护记录已保存')
      fetchData(values.aircraft_serial_number)
    } catch {
      message.error('保存维护记录失败')
    }
  }

  const handleGeneratePlan = async (values: { aircraft_serial_number: string; flight_hours: number }) => {
    try {
      const resp = await apiClient.post('/twin/maintenance/generate-plan', {
        aircraft_serial_number: values.aircraft_serial_number,
        flight_hours: values.flight_hours,
      })
      setPlanItems(resp.data?.data?.plan_items ?? [])
      message.success('维护计划已生成')
    } catch {
      message.error('生成维护计划失败')
    }
  }

  const criticalComponents = lifeEstimates.filter(e => e.fatigue_damage > 0.8)
  const warningComponents = lifeEstimates.filter(e => e.fatigue_damage > 0.6 && e.fatigue_damage <= 0.8)
  const urgentPlanItems = planItems.filter(p => p.priority === 'urgent')

  const recordColumns = [
    { title: '记录ID', dataIndex: 'record_id', key: 'record_id', width: 120 },
    {
      title: '维护类型',
      dataIndex: 'maintenance_type',
      key: 'maintenance_type',
      width: 110,
      render: (t: string) => {
        const cfg = maintenanceTypeLabels[t] || { label: t, color: 'default' }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: '内容',
      dataIndex: 'content',
      key: 'content',
      width: 100,
      render: (t: string) => contentLabels[t] || t,
    },
    {
      title: '结果',
      dataIndex: 'result',
      key: 'result',
      width: 100,
      render: (t: string) => {
        const cfg = resultLabels[t] || { label: t, color: 'default' }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    { title: '部件', dataIndex: 'component_name', key: 'component_name', width: 120 },
    { title: '执行人', dataIndex: 'performed_by', key: 'performed_by', width: 100 },
    {
      title: '飞行小时',
      dataIndex: 'flight_hours_at_maintenance',
      key: 'flight_hours_at_maintenance',
      width: 100,
      render: (v: number) => v?.toLocaleString(),
    },
    {
      title: '执行时间',
      dataIndex: 'performed_at',
      key: 'performed_at',
      width: 160,
      render: (t: string) => t ? new Date(t).toLocaleString() : '-',
    },
  ]

  const lifeColumns = [
    { title: '部件ID', dataIndex: 'component_id', key: 'component_id', width: 130 },
    { title: '部件名称', dataIndex: 'component_name', key: 'component_name', width: 120 },
    {
      title: '设计寿命(FH)',
      dataIndex: 'total_design_life_fh',
      key: 'total_design_life_fh',
      width: 110,
      render: (v: number) => v?.toLocaleString(),
    },
    {
      title: '已飞行(FH)',
      dataIndex: 'flight_hours_elapsed',
      key: 'flight_hours_elapsed',
      width: 100,
      render: (v: number) => v?.toLocaleString(),
    },
    {
      title: '疲劳损伤',
      dataIndex: 'fatigue_damage',
      key: 'fatigue_damage',
      width: 120,
      render: (v: number) => (
        <Progress
          percent={Math.min(v * 100, 100)}
          size="small"
          strokeColor={v > 0.8 ? '#cf1322' : v > 0.6 ? '#fa8c16' : '#52c41a'}
          format={() => `${(v * 100).toFixed(2)}%`}
        />
      ),
    },
    {
      title: '维护收益',
      dataIndex: 'maintenance_benefit',
      key: 'maintenance_benefit',
      width: 100,
      render: (v: number) => `${(v * 100).toFixed(1)}%`,
    },
    {
      title: '剩余寿命(FH)',
      dataIndex: 'estimated_remaining_fh',
      key: 'estimated_remaining_fh',
      width: 120,
      render: (v: number) => v?.toLocaleString(),
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 80,
      render: (c: string) => {
        const cfg = confidenceLabels[c] || { label: c, color: 'default' }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
  ]

  const planColumns = [
    { title: '计划ID', dataIndex: 'plan_item_id', key: 'plan_item_id', width: 120 },
    {
      title: '类型',
      dataIndex: 'maintenance_type',
      key: 'maintenance_type',
      width: 110,
      render: (t: string) => {
        const cfg = maintenanceTypeLabels[t] || { label: t, color: 'default' }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    { title: '部件', dataIndex: 'component_name', key: 'component_name', width: 120 },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      render: (p: string) => {
        const cfg = priorityLabels[p] || { label: p, color: 'default' }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: '触发原因',
      dataIndex: 'trigger_reason',
      key: 'trigger_reason',
      width: 140,
      render: (r: string) => {
        const reasonLabels: Record<string, string> = {
          replacement_interval: '更换间隔到期',
          health_assessment: '健康评估触发',
          anomaly_detected: '异常检测触发',
        }
        return reasonLabels[r] || r
      },
    },
    {
      title: '计划时间',
      dataIndex: 'scheduled_at',
      key: 'scheduled_at',
      width: 160,
      render: (t: string) => t ? new Date(t).toLocaleString() : '-',
    },
  ]

  return (
    <div>
      <Card title="记录维护" style={{ marginBottom: 16 }}>
        <Form onFinish={handleRecordMaintenance} layout="inline" style={{ marginBottom: 16 }}>
          <Form.Item name="aircraft_serial_number" rules={[{ required: true }]}>
            <Input placeholder="飞行器SN" style={{ width: 140 }} />
          </Form.Item>
          <Form.Item name="maintenance_type" initialValue="preventive">
            <Select style={{ width: 130 }} options={[
              { value: 'preventive', label: '预防性维护' },
              { value: 'corrective', label: '纠正性维护' },
              { value: 'improvement', label: '改进性维护' },
            ]} />
          </Form.Item>
          <Form.Item name="content" initialValue="inspection">
            <Select style={{ width: 110 }} options={[
              { value: 'inspection', label: '检查' },
              { value: 'part_replacement', label: '部件更换' },
              { value: 'defect_repair', label: '缺陷修复' },
              { value: 'system_upgrade', label: '系统升级' },
              { value: 'lubrication', label: '润滑' },
            ]} />
          </Form.Item>
          <Form.Item name="result" initialValue="completed">
            <Select style={{ width: 110 }} options={[
              { value: 'completed', label: '已完成' },
              { value: 'partially_completed', label: '部分完成' },
              { value: 'follow_up_required', label: '需跟进' },
            ]} />
          </Form.Item>
          <Form.Item name="component_id">
            <Input placeholder="部件ID" style={{ width: 120 }} />
          </Form.Item>
          <Form.Item name="component_name">
            <Input placeholder="部件名称" style={{ width: 120 }} />
          </Form.Item>
          <Form.Item name="performed_by">
            <Input placeholder="执行人" style={{ width: 100 }} />
          </Form.Item>
          <Form.Item name="flight_hours" initialValue={0}>
            <Input type="number" placeholder="FH" style={{ width: 80 }} />
          </Form.Item>
          <Form.Item name="parts_replaced">
            <Input placeholder="更换件(逗号分隔)" style={{ width: 160 }} />
          </Form.Item>
          <Button type="primary" htmlType="submit" icon={<ToolOutlined />}>
            保存记录
          </Button>
        </Form>
      </Card>

      <Card title="查询与操作" style={{ marginBottom: 16 }}>
        <Space>
          <Input.Search
            placeholder="输入飞行器序列号"
            value={searchSn}
            onChange={(e) => setSearchSn(e.target.value)}
            onSearch={fetchData}
            enterButton="查询"
            style={{ width: 350 }}
          />
          <Form onFinish={handleGeneratePlan} layout="inline">
            <Form.Item name="aircraft_serial_number" initialValue={searchSn} hidden>
              <Input />
            </Form.Item>
            <Form.Item name="flight_hours" initialValue={0}>
              <Input type="number" placeholder="飞行小时" style={{ width: 100 }} />
            </Form.Item>
            <Button type="primary" htmlType="submit" icon={<ScheduleOutlined />}>
              生成维护计划
            </Button>
          </Form>
        </Space>
      </Card>

      {urgentPlanItems.length > 0 && (
        <Alert
          type="error"
          message={`${urgentPlanItems.length} 项紧急维护计划需要立即执行！`}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="维护记录"
              value={records.length}
              prefix={<HistoryOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="危险部件(疲劳>80%)"
              value={criticalComponents.length}
              valueStyle={{ color: '#cf1322' }}
              prefix={<AlertOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="警告部件(疲劳60-80%)"
              value={warningComponents.length}
              valueStyle={{ color: '#fa8c16' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="维护计划项"
              value={planItems.length}
              valueStyle={{ color: planItems.length > 0 ? '#1890ff' : undefined }}
              prefix={<ScheduleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={
          <Space>
            <SafetyCertificateOutlined />
            <span>剩余寿命评估</span>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Table
          columns={lifeColumns}
          dataSource={lifeEstimates.map((e, i) => ({ ...e, key: e.component_id || i }))}
          loading={loading}
          size="small"
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1000 }}
        />
      </Card>

      <Card
        title={
          <Space>
            <HistoryOutlined />
            <span>维护历史记录</span>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Table
          columns={recordColumns}
          dataSource={records.map((r, i) => ({ ...r, key: r.record_id || i }))}
          loading={loading}
          size="small"
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1000 }}
        />
      </Card>

      <Card
        title={
          <Space>
            <ScheduleOutlined />
            <span>维护计划</span>
          </Space>
        }
      >
        {planItems.length > 0 ? (
          <Table
            columns={planColumns}
            dataSource={planItems.map((p, i) => ({ ...p, key: p.plan_item_id || i }))}
            loading={loading}
            size="small"
            pagination={{ pageSize: 10 }}
            scroll={{ x: 900 }}
          />
        ) : (
          <Empty description="暂无维护计划，请点击"生成维护计划"" />
        )}
      </Card>
    </div>
  )
}