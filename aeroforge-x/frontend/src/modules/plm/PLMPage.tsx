import React, { useState } from 'react'
import { Card, Table, Button, Space, Modal, Form, Input, Select, Tag, Tabs, Descriptions, Timeline, Badge, message, Row, Col, Tree } from 'antd'
import { PlusOutlined, LockOutlined, SwapOutlined, CheckCircleOutlined, HistoryOutlined } from '@ant-design/icons'

const STATUS_COLORS: Record<string, string> = { draft: 'default', submitted: 'processing', under_review: 'warning', approved: 'success', rejected: 'error' }
const STATUS_LABELS: Record<string, string> = { draft: '草稿', submitted: '已提交', under_review: '审查中', approved: '已批准', rejected: '已拒绝' }
const PRIORITY_COLORS: Record<string, string> = { low: 'blue', medium: 'orange', high: 'red', critical: 'magenta' }

interface ECR { ecr_id: string; ecr_number: string; title: string; change_type: string; approval_status: string; priority: string; safety_critical: boolean }

const PLMChangePage: React.FC = () => {
  const [ecrs] = useState<ECR[]>([
    { ecr_id: '1', ecr_number: 'ECR-001', title: '翼展增加至2.6m', change_type: 'engineering_change', approval_status: 'approved', priority: 'high', safety_critical: true },
    { ecr_id: '2', ecr_number: 'ECR-002', title: '电机功率参数修正', change_type: 'correction', approval_status: 'under_review', priority: 'medium', safety_critical: false },
  ])
  const [createOpen, setCreateOpen] = useState(false)
  const [form] = Form.useForm()

  const columns = [
    { title: 'ECR编号', dataIndex: 'ecr_number', key: 'num' },
    { title: '标题', dataIndex: 'title', key: 'title' },
    { title: '类型', dataIndex: 'change_type', key: 'type', render: (t: string) => <Tag>{t}</Tag> },
    { title: '优先级', dataIndex: 'priority', key: 'priority', render: (p: string) => <Tag color={PRIORITY_COLORS[p]}>{p}</Tag> },
    { title: '安全关键', dataIndex: 'safety_critical', key: 'safety', render: (s: boolean) => s ? <Tag color="red">安全关键</Tag> : <Tag>否</Tag> },
    { title: '状态', dataIndex: 'approval_status', key: 'status', render: (s: string) => <Tag color={STATUS_COLORS[s]}>{STATUS_LABELS[s]}</Tag> },
    { title: '操作', key: 'action', render: (_: any, r: ECR) => (
      <Space>
        {r.approval_status === 'under_review' && <Button size="small" type="link">审批</Button>}
        <Button size="small" type="link">影响分析</Button>
      </Space>
    )},
  ]

  return (
    <Card title="工程变更管理" extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>创建ECR</Button>}>
      <Table dataSource={ecrs} columns={columns} rowKey="ecr_id" size="small" />
      <Modal title="创建工程变更请求" open={createOpen} onOk={() => { setCreateOpen(false); message.success('创建成功') }} onCancel={() => setCreateOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="ecr_number" label="ECR编号" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="title" label="标题" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="change_type" label="变更类型" rules={[{ required: true }]}>
            <Select options={[{ value: 'engineering_change', label: '工程变更' }, { value: 'correction', label: '纠正' }, { value: 'safety_mandated', label: '安全强制' }]} />
          </Form.Item>
          <Form.Item name="priority" label="优先级" initialValue="medium">
            <Select options={[{ value: 'low', label: '低' }, { value: 'medium', label: '中' }, { value: 'high', label: '高' }, { value: 'critical', label: '关键' }]} />
          </Form.Item>
          <Form.Item name="safety_critical" label="安全关键" valuePropName="checked"><input type="checkbox" /></Form.Item>
          <Form.Item name="description" label="描述"><Input.TextArea /></Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}

const BOMViewPage: React.FC = () => {
  const [bomType, setBomType] = useState('ebom')
  const treeData = [
    { title: 'AF-X01 完整飞行器', key: '0', children: [
      { title: '机翼组件 (x2)', key: '1', children: [
        { title: '翼梁 (CFRP)', key: '1-1' },
        { title: '翼肋 (Al 7075)', key: '1-2' },
        { title: '蒙皮 (CFRP)', key: '1-3' },
      ]},
      { title: '机身组件', key: '2', children: [
        { title: '隔框 (Al 7075)', key: '2-1' },
        { title: '蒙皮 (CFRP)', key: '2-2' },
      ]},
      { title: '动力系统', key: '3', children: [
        { title: '电机 EM-07 (x4)', key: '3-1' },
        { title: '电池 BAT-04', key: '3-2' },
        { title: '电调 ESC-12 (x4)', key: '3-3' },
      ]},
    ]},
  ]

  return (
    <Card title="BOM管理" extra={
      <Space>
        <Select value={bomType} onChange={setBomType} style={{ width: 120 }} options={[
          { value: 'ebom', label: '工程BOM' }, { value: 'mbom', label: '制造BOM' }, { value: 'sbom', label: '服务BOM' },
        ]} />
        <Button icon={<SwapOutlined />}>转换</Button>
        <Button icon={<CheckCircleOutlined />}>同步</Button>
      </Space>
    }>
      <Row gutter={16}>
        <Col span={16}>
          <Tree treeData={treeData} defaultExpandAll showLine />
        </Col>
        <Col span={8}>
          <Card size="small" title="BOM统计">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="类型">{bomType === 'ebom' ? '工程BOM' : bomType === 'mbom' ? '制造BOM' : '服务BOM'}</Descriptions.Item>
              <Descriptions.Item label="行项数">12</Descriptions.Item>
              <Descriptions.Item label="版本">V1</Descriptions.Item>
              <Descriptions.Item label="状态">草稿</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
      </Row>
    </Card>
  )
}

const PLMPage: React.FC = () => {
  return (
    <div style={{ height: '100%', overflow: 'auto', padding: 16 }}>
      <Tabs defaultActiveKey="changes">
        <Tabs.TabPane tab="变更管理" key="changes"><PLMChangePage /></Tabs.TabPane>
        <Tabs.TabPane tab="BOM管理" key="bom"><BOMViewPage /></Tabs.TabPane>
      </Tabs>
    </div>
  )
}

export default PLMPage