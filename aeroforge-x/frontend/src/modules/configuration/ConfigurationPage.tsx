import React, { useState } from 'react'
import { Card, Table, Button, Space, Modal, Form, Input, Select, Tag, Tabs, Descriptions, Badge, message, Drawer, List, Alert, Row, Col, Statistic } from 'antd'
import { PlusOutlined, LockOutlined, UnlockOutlined, SwapOutlined, CheckCircleOutlined } from '@ant-design/icons'

const ITEM_TYPE_LABELS: Record<string, string> = {
  aircraft: '飞行器', wing: '机翼', tail: '尾翼', fuselage: '机身',
  powertrain: '动力系统', flight_control: '飞控', avionics: '航电',
  wire_harness: '线束', battery: '电池', motor: '电机', esc: '电调',
  propeller: '螺旋桨', sensor: '传感器', software: '软件', hardware: '硬件',
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'default', released: 'processing', baselined: 'success', obsolete: 'error',
}

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿', released: '已发布', baselined: '已基线化', obsolete: '已废弃',
}

interface ConfigItem {
  item_id: string
  item_number: string
  item_name: string
  item_type: string
  current_version: number
  status: string
  lifecycle: string
  owner_id: string | null
  properties: Record<string, any>
}

interface Baseline {
  baseline_id: string
  baseline_name: string
  baseline_type: string
  status: string
  item_count: number
  frozen_at: string | null
}

interface Change {
  change_id: string
  change_type: string
  title: string
  status: string
  priority: string
  impact_level: string
}

const ConfigItemsPage: React.FC = () => {
  const [items, setItems] = useState<ConfigItem[]>([
    { item_id: 'ci-001', item_number: 'AF-X01-WING', item_name: '主翼组件', item_type: 'wing', current_version: 3, status: 'baselined', lifecycle: 'production', owner_id: 'u1', properties: { span: 2400, material: 'CFRP' } },
    { item_id: 'ci-002', item_number: 'AF-X01-MOTOR', item_name: '推进电机', item_type: 'motor', current_version: 2, status: 'released', lifecycle: 'production', owner_id: 'u2', properties: { power: 15000, rpm: 6000 } },
    { item_id: 'ci-003', item_number: 'AF-X01-BAT', item_name: '锂电池组', item_type: 'battery', current_version: 1, status: 'draft', lifecycle: 'development', owner_id: 'u3', properties: { capacity: 50000, voltage: 400 } },
  ])
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [form] = Form.useForm()

  const columns = [
    { title: '编号', dataIndex: 'item_number', key: 'num' },
    { title: '名称', dataIndex: 'item_name', key: 'name' },
    { title: '类型', dataIndex: 'item_type', key: 'type', render: (t: string) => <Tag>{ITEM_TYPE_LABELS[t] || t}</Tag> },
    { title: '版本', dataIndex: 'current_version', key: 'ver', render: (v: number) => `V${v}` },
    { title: '状态', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color={STATUS_COLORS[s]}>{STATUS_LABELS[s]}</Tag> },
    { title: '生命周期', dataIndex: 'lifecycle', key: 'lifecycle', render: (l: string) => {
      const labels: Record<string, string> = { development: '研发', production: '生产', service: '服役', retired: '退役' }
      return labels[l] || l
    }},
    { title: '操作', key: 'action', render: (_: any, record: ConfigItem) => (
      <Space>
        {record.status === 'draft' && <Button size="small" type="link">发布</Button>}
        {record.status === 'released' && <Button size="small" type="link">基线化</Button>}
        <Button size="small" type="link">详情</Button>
      </Space>
    )},
  ]

  return (
    <Card title="配置项管理" extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>创建配置项</Button>}>
      <Table dataSource={items} columns={columns} rowKey="item_id" size="small" />
      <Modal title="创建配置项" open={createModalOpen} onOk={() => { setCreateModalOpen(false); message.success('创建成功') }} onCancel={() => setCreateModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="item_number" label="编号" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="item_name" label="名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="item_type" label="类型" rules={[{ required: true }]}>
            <Select options={Object.entries(ITEM_TYPE_LABELS).map(([v, l]) => ({ value: v, label: l }))} />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}

const ConfigBaselinesPage: React.FC = () => {
  const [baselines] = useState<Baseline[]>([
    { baseline_id: 'bl-001', baseline_name: 'AF-X01 产品基线 v1.0', baseline_type: 'product', status: 'frozen', item_count: 15, frozen_at: '2026-05-01' },
    { baseline_id: 'bl-002', baseline_name: 'AF-X01 功能基线 v2.0', baseline_type: 'functional', status: 'open', item_count: 8, frozen_at: null },
  ])

  const columns = [
    { title: '基线名称', dataIndex: 'baseline_name', key: 'name' },
    { title: '类型', dataIndex: 'baseline_type', key: 'type', render: (t: string) => <Tag>{t}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', render: (s: string) => <Badge status={s === 'frozen' ? 'success' : 'processing'} text={s === 'frozen' ? '已冻结' : '开放'} /> },
    { title: '配置项数', dataIndex: 'item_count', key: 'count' },
    { title: '冻结时间', dataIndex: 'frozen_at', key: 'frozen' },
    { title: '操作', key: 'action', render: (_: any, r: Baseline) => (
      <Space>
        {r.status === 'open' && <Button size="small" icon={<LockOutlined />}>冻结</Button>}
        {r.status === 'frozen' && <Button size="small" icon={<UnlockOutlined />}>解冻</Button>}
        <Button size="small">对比</Button>
      </Space>
    )},
  ]

  return (
    <Card title="配置基线管理" extra={<Button type="primary" icon={<PlusOutlined />}>创建基线</Button>}>
      <Table dataSource={baselines} columns={columns} rowKey="baseline_id" size="small" />
    </Card>
  )
}

const ConfigChangesPage: React.FC = () => {
  const [changes] = useState<Change[]>([
    { change_id: 'ch-001', change_type: 'engineering_change', title: '翼展增加至2.6m', status: 'approved', priority: 'high', impact_level: 'major' },
    { change_id: 'ch-002', change_type: 'correction', title: '电机功率参数修正', status: 'proposed', priority: 'medium', impact_level: 'minor' },
  ])

  const priorityColors: Record<string, string> = { low: 'blue', medium: 'orange', high: 'red', critical: 'magenta' }
  const statusLabels: Record<string, string> = { proposed: '提议', under_review: '审查中', approved: '已批准', rejected: '已拒绝', implementing: '实施中', completed: '已完成' }

  const columns = [
    { title: '变更标题', dataIndex: 'title', key: 'title' },
    { title: '类型', dataIndex: 'change_type', key: 'type', render: (t: string) => <Tag>{t}</Tag> },
    { title: '优先级', dataIndex: 'priority', key: 'priority', render: (p: string) => <Tag color={priorityColors[p]}>{p}</Tag> },
    { title: '影响级别', dataIndex: 'impact_level', key: 'impact' },
    { title: '状态', dataIndex: 'status', key: 'status', render: (s: string) => <Tag>{statusLabels[s] || s}</Tag> },
    { title: '操作', key: 'action', render: (_: any, r: Change) => (
      <Space>
        {r.status === 'proposed' && <Button size="small" type="link">传播分析</Button>}
        {r.status === 'under_review' && <Button size="small" type="link">审批</Button>}
        {r.status === 'approved' && <Button size="small" type="link">实施</Button>}
      </Space>
    )},
  ]

  return (
    <Card title="配置变更管理" extra={<Button type="primary" icon={<PlusOutlined />}>创建变更</Button>}>
      <Table dataSource={changes} columns={columns} rowKey="change_id" size="small" />
    </Card>
  )
}

const ConfigurationPage: React.FC = () => {
  return (
    <div style={{ height: '100%', overflow: 'auto', padding: 16 }}>
      <Tabs defaultActiveKey="items">
        <Tabs.TabPane tab="配置项" key="items"><ConfigItemsPage /></Tabs.TabPane>
        <Tabs.TabPane tab="配置基线" key="baselines"><ConfigBaselinesPage /></Tabs.TabPane>
        <Tabs.TabPane tab="配置变更" key="changes"><ConfigChangesPage /></Tabs.TabPane>
      </Tabs>
    </div>
  )
}

export default ConfigurationPage