import { useState } from 'react'
import { Tabs, Card, Typography, Space, Tag, Table, Button, Select, InputNumber, Form, message, Progress, Descriptions } from 'antd'
import { ExperimentOutlined, ThunderboltOutlined, FireOutlined, SwapOutlined, CloudOutlined } from '@ant-design/icons'
import apiClient from '../../services/apiClient'
import CFDAnalysisPage from './CFDAnalysisPage'
import FEAAnalysisPage from './FEAAnalysisPage'
import FlutterAnalysisPage from './FlutterAnalysisPage'
import ThermalAnalysisPage from './ThermalAnalysisPage'
import MultiphysicsAnalysisPage from './MultiphysicsAnalysisPage'

const { Title, Text } = Typography

interface CAETask {
  task_id: string
  task_type: string
  status: string
  priority: number
  progress?: number
  submitted_at?: string
  estimated_duration_seconds?: number
}

const analysisTypeOptions = [
  { value: 'cfd', label: 'CFD 空气动力分析', icon: <CloudOutlined />, color: 'blue' },
  { value: 'fea', label: 'FEA 结构分析', icon: <ThunderboltOutlined />, color: 'green' },
  { value: 'flutter', label: '颤振分析', icon: <SwapOutlined />, color: 'orange' },
  { value: 'thermal', label: '热分析', icon: <FireOutlined />, color: 'red' },
  { value: 'multiphysics', label: '多物理场耦合', icon: <ExperimentOutlined />, color: 'purple' },
]

function TaskSubmitPage() {
  const [form] = Form.useForm()
  const [submitting, setSubmitting] = useState(false)
  const [analysisType, setAnalysisType] = useState('cfd')

  const handleSubmit = async (values: Record<string, unknown>) => {
    setSubmitting(true)
    try {
      const endpoint = `/cae/${analysisType}/submit`
      await apiClient.post(endpoint, values)
      message.success('分析任务已提交')
    } catch {
      message.error('提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card title="提交 CAE 分析任务" style={{ marginBottom: 16 }}>
      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        <Form.Item label="分析类型" required>
          <Select
            value={analysisType}
            onChange={setAnalysisType}
            options={analysisTypeOptions.map(o => ({ value: o.value, label: o.label }))}
          />
        </Form.Item>
        <Form.Item name="model_id" label="模型 ID" rules={[{ required: true }]}>
          <Select
            placeholder="选择模型"
            options={[
              { value: 'model-001', label: 'Wing-001' },
              { value: 'model-002', label: 'Fuselage-002' },
            ]}
          />
        </Form.Item>
        <Form.Item name="priority" label="优先级" initialValue={2}>
          <InputNumber min={0} max={3} />
        </Form.Item>
        <Form.Item name="n_proc" label="并行进程数" initialValue={1}>
          <InputNumber min={1} max={64} />
        </Form.Item>
        {analysisType === 'cfd' && (
          <>
            <Form.Item name="solver" label="求解器" initialValue="simpleFoam">
              <Select options={[
                { value: 'simpleFoam', label: 'simpleFoam (稳态不可压)' },
                { value: 'rhoSimpleFoam', label: 'rhoSimpleFoam (稳态可压)' },
                { value: 'pimpleFoam', label: 'pimpleFoam (瞬态不可压)' },
              ]} />
            </Form.Item>
            <Form.Item name="turbulence_model" label="湍流模型" initialValue="kOmegaSST">
              <Select options={[
                { value: 'kOmegaSST', label: 'kOmegaSST' },
                { value: 'kEpsilon', label: 'kEpsilon' },
                { value: 'SpalartAllmaras', label: 'SpalartAllmaras' },
              ]} />
            </Form.Item>
          </>
        )}
        {analysisType === 'fea' && (
          <Form.Item name="problem_type" label="问题类型" initialValue="linear_elasticity">
            <Select options={[
              { value: 'linear_elasticity', label: '线弹性' },
              { value: 'thermal', label: '热分析' },
              { value: 'modal', label: '模态分析' },
              { value: 'buckling', label: '屈曲分析' },
            ]} />
          </Form.Item>
        )}
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={submitting} icon={<ExperimentOutlined />}>
            提交分析
          </Button>
        </Form.Item>
      </Form>
    </Card>
  )
}

function TaskQueuePage() {
  const [tasks] = useState<CAETask[]>([])
  const [workers, setWorkers] = useState<Record<string, unknown>[]>([])

  const fetchWorkers = async () => {
    try {
      const res = await apiClient.get('/cae/workers/status')
      setWorkers(res.data?.data?.workers || [])
    } catch { /* ignore */ }
  }

  const columns = [
    { title: '任务 ID', dataIndex: 'task_id', key: 'task_id', render: (v: string) => v.slice(0, 8) + '...' },
    { title: '类型', dataIndex: 'task_type', key: 'task_type', render: (v: string) => <Tag color="blue">{v.toUpperCase()}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => {
      const colorMap: Record<string, string> = { queued: 'default', running: 'processing', completed: 'success', failed: 'error' }
      return <Tag color={colorMap[v] || 'default'}>{v}</Tag>
    }},
    { title: '优先级', dataIndex: 'priority', key: 'priority', render: (v: number) => {
      const labels = ['紧急', '高', '普通', '低']
      const colors = ['red', 'orange', 'blue', 'default']
      return <Tag color={colors[v]}>{labels[v]}</Tag>
    }},
    { title: '进度', dataIndex: 'progress', key: 'progress', render: (v: number) => v ? <Progress percent={v} size="small" /> : '-' },
  ]

  return (
    <Card title="CAE 任务队列" extra={<Button onClick={fetchWorkers} size="small">刷新 Worker</Button>}>
      {workers.length > 0 && (
        <Descriptions size="small" bordered style={{ marginBottom: 16 }}>
          <Descriptions.Item label="在线 Worker">{workers.length}</Descriptions.Item>
          <Descriptions.Item label="活跃任务">{workers.reduce((s: number, w: Record<string, unknown>) => s + ((w.active_tasks as number) || 0), 0)}</Descriptions.Item>
        </Descriptions>
      )}
      <Table dataSource={tasks} columns={columns} rowKey="task_id" size="small" pagination={{ pageSize: 10 }} />
    </Card>
  )
}

function ResultsOverviewPage() {
  const [results] = useState<Record<string, unknown>[]>([])

  const columns = [
    { title: '任务 ID', dataIndex: 'task_id', key: 'task_id', render: (v: string) => v?.slice(0, 8) + '...' },
    { title: '类型', dataIndex: 'task_type', key: 'task_type' },
    { title: '状态', dataIndex: 'status', key: 'status' },
    { title: '关键指标', dataIndex: 'summary', key: 'summary' },
    { title: '完成时间', dataIndex: 'completed_at', key: 'completed_at' },
  ]

  return (
    <Card title="CAE 分析结果概览">
      <Table dataSource={results} columns={columns} rowKey="task_id" size="small" />
    </Card>
  )
}

export default function CAECenter() {
  const tabItems = [
    { key: 'submit', label: '任务提交', children: <TaskSubmitPage /> },
    { key: 'cfd', label: 'CFD 分析', children: <CFDAnalysisPage /> },
    { key: 'fea', label: 'FEA 分析', children: <FEAAnalysisPage /> },
    { key: 'flutter', label: '颤振分析', children: <FlutterAnalysisPage /> },
    { key: 'thermal', label: '热分析', children: <ThermalAnalysisPage /> },
    { key: 'multiphysics', label: '多物理场耦合', children: <MultiphysicsAnalysisPage /> },
    { key: 'queue', label: '任务队列', children: <TaskQueuePage /> },
    { key: 'results', label: '结果概览', children: <ResultsOverviewPage /> },
  ]

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Title level={3}><ExperimentOutlined /> CAE 分析中心</Title>
      <Text type="secondary">提交和管理 CFD/FEA/颤振/热/多物理场耦合分析任务</Text>
      <Tabs items={tabItems} />
    </Space>
  )
}