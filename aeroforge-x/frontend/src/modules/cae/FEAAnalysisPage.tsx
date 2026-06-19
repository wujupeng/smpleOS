import { useState } from 'react'
import {
  Card, Form, Select, InputNumber, Button, message, Row, Col, Statistic,
  Tag, Descriptions, Alert, Spin, Progress, Space, Typography, Divider,
  Table, Input,
} from 'antd'
import {
  ThunderboltOutlined, SafetyCertificateOutlined, WarningOutlined,
  CheckCircleOutlined, PlusOutlined, DeleteOutlined,
} from '@ant-design/icons'
import apiClient from '../../services/apiClient'
import CloudMapRenderer from '../../components/cae/CloudMapRenderer'
import VectorFieldRenderer from '../../components/cae/VectorFieldRenderer'

const { Title, Text } = Typography

interface FEAResult {
  task_id: string
  model_id: string
  status: string
  result_summary?: {
    max_stress_pa: number
    max_deformation_m: number
    safety_factor: number
    fatigue_life_cycles: number
    von_mises_max_pa: number
    convergence_status: string
  }
  error_message?: string
}

interface LoadCaseRow {
  key: string
  name: string
  load_type: string
  region: string
  magnitude: number
}

interface BCRow {
  key: string
  name: string
  bc_type: string
  region: string
}

export default function FEAAnalysisPage() {
  const [form] = Form.useForm()
  const [submitting, setSubmitting] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('')
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState<FEAResult | null>(null)
  const [loadCases, setLoadCases] = useState<LoadCaseRow[]>([])
  const [boundaryConditions, setBoundaryConditions] = useState<BCRow[]>([])

  const addLoadCase = () => {
    setLoadCases([...loadCases, {
      key: `lc_${Date.now()}`, name: `Load_${loadCases.length + 1}`,
      load_type: 'pressure', region: '', magnitude: 50000,
    }])
  }

  const removeLoadCase = (key: string) => {
    setLoadCases(loadCases.filter(lc => lc.key !== key))
  }

  const addBC = () => {
    setBoundaryConditions([...boundaryConditions, {
      key: `bc_${Date.now()}`, name: `BC_${boundaryConditions.length + 1}`,
      bc_type: 'fixed', region: '',
    }])
  }

  const removeBC = (key: string) => {
    setBoundaryConditions(boundaryConditions.filter(bc => bc.key !== key))
  }

  const handleSubmit = async (values: Record<string, unknown>) => {
    setSubmitting(true)
    try {
      const payload = {
        ...values,
        load_cases: loadCases.map(lc => ({
          name: lc.name, load_type: lc.load_type, region: lc.region,
          values: { magnitude: lc.magnitude },
        })),
        boundary_conditions: boundaryConditions.map(bc => ({
          name: bc.name, bc_type: bc.bc_type, region: bc.region,
        })),
      }
      const res = await apiClient.post('/cae/fea/submit', payload)
      const tid = res.data?.data?.task_id || res.data?.task_id
      setTaskId(tid)
      setStatus(res.data?.data?.status || 'queued')
      setProgress(0)
      setResult(null)
      message.success('FEA 分析任务已提交')
      pollStatus(tid)
    } catch {
      message.error('提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  const pollStatus = (tid: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await apiClient.get(`/cae/fea/${tid}/status`)
        const data = res.data?.data || {}
        setStatus(data.status || '')
        setProgress(data.progress_percent || 0)
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval)
          if (data.status === 'completed') {
            fetchResult(tid)
          }
        }
      } catch {
        clearInterval(interval)
      }
    }, 2000)
  }

  const fetchResult = async (tid: string) => {
    try {
      const res = await apiClient.get(`/cae/fea/${tid}/result`)
      setResult(res.data?.data || null)
    } catch { /* ignore */ }
  }

  const hasSafetyDeviation = result?.result_summary && result.result_summary.safety_factor < 1.5

  const loadColumns = [
    { title: '名称', dataIndex: 'name', render: (_: string, r: LoadCaseRow) => <Input value={r.name} onChange={e => { r.name = e.target.value; setLoadCases([...loadCases]) }} size="small" /> },
    { title: '类型', dataIndex: 'load_type', render: (_: string, r: LoadCaseRow) => <Select value={r.load_type} onChange={v => { r.load_type = v; setLoadCases([...loadCases]) }} size="small" style={{ width: 130 }} options={[
      { value: 'concentrated_force', label: '集中力' },
      { value: 'distributed_force', label: '分布力' },
      { value: 'pressure', label: '压力' },
      { value: 'thermal', label: '温度载荷' },
      { value: 'inertial', label: '惯性载荷' },
    ]} /> },
    { title: '区域', dataIndex: 'region', render: (_: string, r: LoadCaseRow) => <Input value={r.region} onChange={e => { r.region = e.target.value; setLoadCases([...loadCases]) }} size="small" /> },
    { title: '大小', dataIndex: 'magnitude', render: (_: number, r: LoadCaseRow) => <InputNumber value={r.magnitude} onChange={v => { r.magnitude = v || 0; setLoadCases([...loadCases]) }} size="small" style={{ width: 100 }} /> },
    { title: '', render: (_: unknown, r: LoadCaseRow) => <Button danger size="small" icon={<DeleteOutlined />} onClick={() => removeLoadCase(r.key)} /> },
  ]

  const bcColumns = [
    { title: '名称', dataIndex: 'name', render: (_: string, r: BCRow) => <Input value={r.name} onChange={e => { r.name = e.target.value; setBoundaryConditions([...boundaryConditions]) }} size="small" /> },
    { title: '类型', dataIndex: 'bc_type', render: (_: string, r: BCRow) => <Select value={r.bc_type} onChange={v => { r.bc_type = v; setBoundaryConditions([...boundaryConditions]) }} size="small" style={{ width: 120 }} options={[
      { value: 'fixed', label: '固定约束' },
      { value: 'symmetry', label: '对称约束' },
      { value: 'contact', label: '接触约束' },
    ]} /> },
    { title: '区域', dataIndex: 'region', render: (_: string, r: BCRow) => <Input value={r.region} onChange={e => { r.region = e.target.value; setBoundaryConditions([...boundaryConditions]) }} size="small" /> },
    { title: '', render: (_: unknown, r: BCRow) => <Button danger size="small" icon={<DeleteOutlined />} onClick={() => removeBC(r.key)} /> },
  ]

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Title level={4}><ThunderboltOutlined /> FEA 结构分析</Title>

      <Card title="分析配置">
        <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{
          analysis_type: 'strength', solver_type: 'FEniCS',
        }}>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="model_id" label="模型" rules={[{ required: true }]}>
                <Select options={[
                  { value: 'model-001', label: 'Wing-Spar-001' },
                  { value: 'model-002', label: 'Fuselage-Frame-002' },
                  { value: 'model-003', label: 'Landing-Gear-003' },
                ]} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="analysis_type" label="分析类型">
                <Select options={[
                  { value: 'strength', label: '强度分析' },
                  { value: 'fatigue', label: '疲劳分析' },
                  { value: 'deformation', label: '变形分析' },
                ]} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="solver_type" label="求解器">
                <Select options={[
                  { value: 'FEniCS', label: 'FEniCS' },
                  { value: 'CalculiX', label: 'CalculiX' },
                ]} />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left" plain>材料属性</Divider>
          <Row gutter={16}>
            <Col span={4}><Form.Item name={['material', 'name']} label="材料" initialValue="steel"><Select options={[
              { value: 'steel', label: '钢 (AISI 304)' },
              { value: 'aluminum', label: '铝合金 (7075-T6)' },
              { value: 'titanium', label: '钛合金 (Ti-6Al-4V)' },
              { value: 'composite', label: '碳纤维复合材料' },
            ]} /></Form.Item></Col>
            <Col span={4}><Form.Item name={['material', 'elastic_modulus_pa']} label="弹性模量(Pa)" initialValue={200e9}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={3}><Form.Item name={['material', 'poisson_ratio']} label="泊松比" initialValue={0.3}><InputNumber step={0.01} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={4}><Form.Item name={['material', 'density_kg_m3']} label="密度(kg/m³)" initialValue={7850}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={5}><Form.Item name={['material', 'yield_strength_pa']} label="屈服强度(Pa)" initialValue={250e6}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
          </Row>

          <Divider orientation="left" plain>载荷工况 <Button size="small" icon={<PlusOutlined />} onClick={addLoadCase}>添加</Button></Divider>
          <Table dataSource={loadCases} columns={loadColumns} size="small" pagination={false} />

          <Divider orientation="left" plain style={{ marginTop: 16 }}>边界条件 <Button size="small" icon={<PlusOutlined />} onClick={addBC}>添加</Button></Divider>
          <Table dataSource={boundaryConditions} columns={bcColumns} size="small" pagination={false} />

          <Form.Item style={{ marginTop: 16 }}>
            <Button type="primary" htmlType="submit" loading={submitting} icon={<ThunderboltOutlined />}>
              提交 FEA 分析
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {taskId && (
        <Card title="任务状态">
          <Descriptions column={3} bordered size="small">
            <Descriptions.Item label="任务 ID">{taskId.slice(0, 12)}...</Descriptions.Item>
            <Descriptions.Item label="状态"><Tag color={status === 'completed' ? 'success' : status === 'failed' ? 'error' : 'processing'}>{status}</Tag></Descriptions.Item>
            <Descriptions.Item label="进度"><Progress percent={Math.round(progress)} size="small" style={{ width: 120 }} /></Descriptions.Item>
          </Descriptions>
          {status !== 'completed' && status !== 'failed' && <Spin tip="分析进行中..." style={{ display: 'block', marginTop: 16 }} />}
        </Card>
      )}

      {result?.result_summary && (
        <>
          {hasSafetyDeviation && (
            <Alert type="warning" message="安全系数不足" description={`安全系数 (${result.result_summary.safety_factor.toFixed(2)}) 低于设计要求 (1.5)，建议增加材料厚度或优化结构`} icon={<WarningOutlined />} showIcon style={{ marginBottom: 16 }} />
          )}

          <Card title="分析结果" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic title="最大应力 (MPa)" value={result.result_summary.max_stress_pa / 1e6} precision={1} valueStyle={{ color: result.result_summary.max_stress_pa > 200e6 ? '#cf1322' : '#3f8600' }} />
              </Col>
              <Col span={6}>
                <Statistic title="最大变形 (mm)" value={result.result_summary.max_deformation_m * 1000} precision={3} />
              </Col>
              <Col span={6}>
                <Statistic title="安全系数" value={result.result_summary.safety_factor} precision={2} valueStyle={{ color: hasSafetyDeviation ? '#cf1322' : '#3f8600' }} prefix={hasSafetyDeviation ? <WarningOutlined /> : <SafetyCertificateOutlined />} />
              </Col>
              <Col span={6}>
                <Statistic title="疲劳寿命 (cycles)" value={result.result_summary.fatigue_life_cycles} precision={0} />
              </Col>
            </Row>
          </Card>

          <Card title="结果可视化">
            <Row gutter={16}>
              <Col span={12}>
                <Card size="small" title="von Mises 应力云图">
                  <CloudMapRenderer width={450} height={300} />
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" title="变形图 (放大100x)">
                  <VectorFieldRenderer width={450} height={300} />
                </Card>
              </Col>
            </Row>
          </Card>
        </>
      )}
    </Space>
  )
}