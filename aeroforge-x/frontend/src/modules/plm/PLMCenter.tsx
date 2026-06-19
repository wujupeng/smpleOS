import { useState } from 'react'
import {
  Typography, Card, Button, Tag, Space, Input, message, Empty, Row, Col,
  Table, Descriptions, Alert, Statistic, Form, Tabs, Select, Modal,
} from 'antd'
import {
  AuditOutlined, CheckCircleOutlined, WarningOutlined,
  SwapOutlined, SafetyCertificateOutlined, ThunderboltOutlined,
  LockOutlined, UnlockOutlined, NotificationOutlined,
} from '@ant-design/icons'
import apiClient from '../../services/apiClient'

const { Title, Text } = Typography

const ecrStatusConfig: Record<string, { color: string; label: string }> = {
  submitted: { color: 'blue', label: '已提交' },
  under_review: { color: 'orange', label: '审批中' },
  approved: { color: 'green', label: '已批准' },
  rejected: { color: 'red', label: '已拒绝' },
  withdrawn: { color: 'default', label: '已撤回' },
}

const approvalLevelConfig: Record<string, { color: string; label: string }> = {
  standard: { color: 'blue', label: '标准审批' },
  elevated: { color: 'orange', label: '升级审批' },
  airworthiness: { color: 'red', label: '适航审批' },
}

function BaselinePage() {
  const [baselines, setBaselines] = useState<Record<string, unknown>[]>([])
  const [selectedBaseline, setSelectedBaseline] = useState<Record<string, unknown> | null>(null)
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)

  const fetchBaselines = async () => {
    try {
      const resp = await apiClient.get('/plm/baselines')
      setBaselines(resp.data?.data?.baselines || [])
    } catch {
      message.error('获取基线列表失败')
    }
  }

  const handleEstablish = async (values: { name: string; description: string }) => {
    setLoading(true)
    try {
      await apiClient.post('/plm/baselines', values)
      message.success('基线已建立')
      fetchBaselines()
    } catch {
      message.error('建立基线失败')
    } finally {
      setLoading(false)
    }
  }

  const handleFreeze = async (id: string) => {
    try {
      await apiClient.post(`/plm/baselines/${id}/freeze`)
      message.success('基线已冻结')
      fetchBaselines()
    } catch {
      message.error('冻结失败')
    }
  }

  const handleUnfreeze = async (id: string) => {
    try {
      await apiClient.post(`/plm/baselines/${id}/unfreeze?approved_by=manager`)
      message.success('基线已解冻')
      fetchBaselines()
    } catch {
      message.error('解冻失败')
    }
  }

  const columns = [
    { title: '基线编码', dataIndex: 'baseline_code', key: 'baseline_code' },
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '对象数', dataIndex: 'object_count', key: 'object_count' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => s === 'frozen'
        ? <Tag color="red" icon={<LockOutlined />}>已冻结</Tag>
        : <Tag color="green" icon={<UnlockOutlined />}>开放</Tag>,
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: Record<string, unknown>) => (
        <Space>
          {record.status === 'open' && (
            <Button size="small" type="primary" onClick={() => handleFreeze(record.id as string)}>冻结</Button>
          )}
          {record.status === 'frozen' && (
            <Button size="small" onClick={() => handleUnfreeze(record.id as string)}>解冻</Button>
          )}
          <Button size="small" onClick={async () => {
            const resp = await apiClient.get(`/plm/baselines/${record.id}`)
            setSelectedBaseline(resp.data?.data)
          }}>详情</Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Card title="建立基线" style={{ marginBottom: 16 }}>
        <Form form={form} onFinish={handleEstablish} layout="inline">
          <Form.Item name="name" rules={[{ required: true }]}>
            <Input placeholder="基线名称" style={{ width: 200 }} />
          </Form.Item>
          <Form.Item name="description">
            <Input placeholder="描述" style={{ width: 300 }} />
          </Form.Item>
          <Button type="primary" htmlType="submit" icon={<AuditOutlined />} loading={loading}>建立基线</Button>
          <Button onClick={fetchBaselines} style={{ marginLeft: 8 }}>刷新列表</Button>
        </Form>
      </Card>

      <Card title="基线列表">
        <Table columns={columns} dataSource={baselines.map((b, i) => ({ ...b, key: i }))} size="small" pagination={{ pageSize: 10 }} />
      </Card>

      <Modal
        open={!!selectedBaseline}
        title={`基线详情: ${selectedBaseline?.baseline_code || ''}`}
        onCancel={() => setSelectedBaseline(null)}
        footer={null}
        width={600}
      >
        {selectedBaseline && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="编码">{selectedBaseline.baseline_code as string}</Descriptions.Item>
            <Descriptions.Item label="名称">{selectedBaseline.name as string}</Descriptions.Item>
            <Descriptions.Item label="状态">{selectedBaseline.status as string}</Descriptions.Item>
            <Descriptions.Item label="对象数">{selectedBaseline.object_count as number}</Descriptions.Item>
            <Descriptions.Item label="冻结时间">{(selectedBaseline.frozen_at as string) || '-'}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}

function ECRPage() {
  const [ecrs, setEcrs] = useState<Record<string, unknown>[]>([])
  const [impactData, setImpactData] = useState<Record<string, unknown> | null>(null)
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)

  const fetchECRs = async () => {
    try {
      const resp = await apiClient.get('/plm/ecr')
      setEcrs(resp.data?.data?.ecrs || [])
    } catch {
      message.error('获取ECR列表失败')
    }
  }

  const handleSubmit = async (values: { title: string; description: string; submitter: string }) => {
    setLoading(true)
    try {
      await apiClient.post('/plm/ecr', values)
      message.success('ECR已提交')
      fetchECRs()
    } catch {
      message.error('提交ECR失败')
    } finally {
      setLoading(false)
    }
  }

  const handleApprove = async (id: string) => {
    try {
      await apiClient.post(`/plm/ecr/${id}/approve`, { approved_by: 'manager' })
      message.success('ECR已批准')
      fetchECRs()
    } catch {
      message.error('审批失败')
    }
  }

  const handleReject = async (id: string) => {
    try {
      await apiClient.post(`/plm/ecr/${id}/reject`, { reason: '不符合变更要求' })
      message.success('ECR已拒绝')
      fetchECRs()
    } catch {
      message.error('拒绝失败')
    }
  }

  const handleViewImpact = async (id: string) => {
    try {
      const resp = await apiClient.get(`/plm/ecr/${id}/impact`)
      setImpactData(resp.data?.data)
    } catch {
      message.error('获取影响分析失败')
    }
  }

  const columns = [
    { title: 'ECR编码', dataIndex: 'ecr_code', key: 'ecr_code' },
    { title: '标题', dataIndex: 'title', key: 'title' },
    { title: '提交人', dataIndex: 'submitter', key: 'submitter' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => {
        const cfg = ecrStatusConfig[s] || { color: 'default', label: s }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: '审批级别',
      dataIndex: 'approval_level',
      key: 'approval_level',
      render: (l: string) => {
        const cfg = approvalLevelConfig[l] || { color: 'default', label: l }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: Record<string, unknown>) => (
        <Space>
          {(record.status === 'submitted' || record.status === 'under_review') && (
            <>
              <Button size="small" type="primary" onClick={() => handleApprove(record.id as string)}>批准</Button>
              <Button size="small" danger onClick={() => handleReject(record.id as string)}>拒绝</Button>
            </>
          )}
          <Button size="small" onClick={() => handleViewImpact(record.id as string)}>影响分析</Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Card title="提交 ECR" style={{ marginBottom: 16 }}>
        <Form form={form} onFinish={handleSubmit} layout="inline">
          <Form.Item name="title" rules={[{ required: true }]}>
            <Input placeholder="变更标题" style={{ width: 200 }} />
          </Form.Item>
          <Form.Item name="description">
            <Input placeholder="变更描述" style={{ width: 300 }} />
          </Form.Item>
          <Form.Item name="submitter" initialValue="engineer">
            <Input placeholder="提交人" style={{ width: 120 }} />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={loading}>提交ECR</Button>
          <Button onClick={fetchECRs} style={{ marginLeft: 8 }}>刷新</Button>
        </Form>
      </Card>

      <Card title="ECR 列表">
        <Table columns={columns} dataSource={ecrs.map((e, i) => ({ ...e, key: i }))} size="small" pagination={{ pageSize: 10 }} />
      </Card>

      <Modal
        open={!!impactData}
        title="变更影响分析"
        onCancel={() => setImpactData(null)}
        footer={null}
        width={700}
      >
        {impactData && (
          <>
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={6}><Statistic title="受影响零部件" value={(impactData.affected_parts as unknown[])?.length || 0} /></Col>
              <Col span={6}><Statistic title="受影响BOM项" value={(impactData.affected_bom_items as unknown[])?.length || 0} /></Col>
              <Col span={6}><Statistic title="受影响工艺" value={(impactData.affected_processes as unknown[])?.length || 0} /></Col>
              <Col span={6}><Statistic title="受影响WIP" value={(impactData.affected_wip_batches as unknown[])?.length || 0} /></Col>
            </Row>
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="影响等级">
                <Tag color={impactData.impact_level === 'critical' ? 'red' : impactData.impact_level === 'high' ? 'orange' : 'blue'}>
                  {impactData.impact_level as string}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="安全关键件">
                {impactData.safety_critical ? <Tag color="red" icon={<WarningOutlined />}>是</Tag> : <Tag color="green">否</Tag>}
              </Descriptions.Item>
            </Descriptions>
            {impactData.summary && <Alert type="info" message={impactData.summary as string} style={{ marginTop: 12 }} />}
          </>
        )}
      </Modal>
    </div>
  )
}

export default function PLMCenter() {
  return (
    <div>
      <Title level={3} style={{ marginBottom: 16 }}>
        <AuditOutlined style={{ marginRight: 8 }} />
        PLM 变更管理
      </Title>
      <Tabs
        defaultActiveKey="ecr"
        items={[
          { key: 'ecr', label: 'ECR 变更请求', children: <ECRPage /> },
          { key: 'baseline', label: '基线管理', children: <BaselinePage /> },
        ]}
      />
    </div>
  )
}