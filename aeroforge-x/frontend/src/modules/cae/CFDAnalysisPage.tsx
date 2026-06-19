import { useState } from 'react'
import {
  Card, Form, Select, InputNumber, Button, message, Row, Col, Statistic,
  Tag, Descriptions, Alert, Spin, Progress, Space, Typography, Divider,
} from 'antd'
import {
  CloudOutlined, RocketOutlined, ArrowUpOutlined, ArrowDownOutlined,
  WarningOutlined, CheckCircleOutlined,
} from '@ant-design/icons'
import apiClient from '../../services/apiClient'
import CloudMapRenderer from '../../components/cae/CloudMapRenderer'
import ContourRenderer from '../../components/cae/ContourRenderer'
import VectorFieldRenderer from '../../components/cae/VectorFieldRenderer'

const { Title, Text } = Typography

interface CFDResult {
  task_id: string
  model_id: string
  status: string
  result_summary?: {
    lift_coefficient: number
    drag_coefficient: number
    moment_coefficient: number
    lift_to_drag_ratio: number
    convergence_status: string
  }
  error_message?: string
}

export default function CFDAnalysisPage() {
  const [form] = Form.useForm()
  const [submitting, setSubmitting] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('')
  const [progress, setProgress] = useState(0)
  const [result, setResult] = useState<CFDResult | null>(null)
  const [polling, setPolling] = useState(false)

  const handleSubmit = async (values: Record<string, unknown>) => {
    setSubmitting(true)
    try {
      const res = await apiClient.post('/cae/cfd/submit', values)
      const tid = res.data?.data?.task_id || res.data?.task_id
      setTaskId(tid)
      setStatus(res.data?.data?.status || res.data?.status || 'queued')
      setProgress(0)
      setResult(null)
      message.success('CFD 分析任务已提交')
      startPolling(tid)
    } catch {
      message.error('提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  const startPolling = (tid: string) => {
    setPolling(true)
    const interval = setInterval(async () => {
      try {
        const res = await apiClient.get(`/cae/cfd/${tid}/status`)
        const data = res.data?.data || {}
        setStatus(data.status || '')
        setProgress(data.progress_percent || 0)
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval)
          setPolling(false)
          if (data.status === 'completed') {
            fetchResult(tid)
          }
        }
      } catch {
        clearInterval(interval)
        setPolling(false)
      }
    }, 2000)
  }

  const fetchResult = async (tid: string) => {
    try {
      const res = await apiClient.get(`/cae/cfd/${tid}/result`)
      setResult(res.data?.data || null)
    } catch { /* ignore */ }
  }

  const handleRetry = async () => {
    if (!taskId) return
    try {
      const res = await apiClient.post(`/cae/cfd/${taskId}/retry`)
      const newTid = res.data?.data?.task_id || res.data?.task_id
      setTaskId(newTid)
      setStatus('queued')
      setProgress(0)
      setResult(null)
      message.info('任务已重试')
      startPolling(newTid)
    } catch {
      message.error('重试失败')
    }
  }

  const hasDeviation = result?.result_summary && result.result_summary.lift_to_drag_ratio < 10

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Title level={4}><CloudOutlined /> CFD 空气动力分析</Title>

      <Card title="分析配置" style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{
          analysis_type: 'steady', solver_type: 'simpleFoam',
          turbulence_model: 'kOmegaSST', n_proc: 1,
          altitude_m: 0, mach_number: 0.3, angle_of_attack_deg: 5,
        }}>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="model_id" label="模型" rules={[{ required: true }]}>
                <Select options={[
                  { value: 'model-001', label: 'Wing-001' },
                  { value: 'model-002', label: 'Fuselage-002' },
                  { value: 'model-003', label: 'Full-Aircraft-003' },
                ]} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="analysis_type" label="分析类型">
                <Select options={[
                  { value: 'steady', label: '稳态分析' },
                  { value: 'unsteady', label: '瞬态分析' },
                ]} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="solver_type" label="求解器">
                <Select options={[
                  { value: 'simpleFoam', label: 'simpleFoam (稳态不可压)' },
                  { value: 'rhoSimpleFoam', label: 'rhoSimpleFoam (稳态可压)' },
                  { value: 'pimpleFoam', label: 'pimpleFoam (瞬态不可压)' },
                ]} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="turbulence_model" label="湍流模型">
                <Select options={[
                  { value: 'kOmegaSST', label: 'kOmegaSST' },
                  { value: 'kEpsilon', label: 'kEpsilon' },
                  { value: 'SpalartAllmaras', label: 'SpalartAllmaras' },
                ]} />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="altitude_m" label="高度(m)">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="mach_number" label="马赫数">
                <InputNumber min={0} max={5} step={0.01} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="angle_of_attack_deg" label="攻角(°)">
                <InputNumber step={0.5} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="n_proc" label="并行数">
                <InputNumber min={1} max={64} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={submitting} icon={<RocketOutlined />}>
              提交分析
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {taskId && (
        <Card title="任务状态" style={{ marginBottom: 16 }}>
          <Descriptions column={3} bordered size="small">
            <Descriptions.Item label="任务 ID">{taskId.slice(0, 12)}...</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={status === 'completed' ? 'success' : status === 'failed' ? 'error' : 'processing'}>
                {status}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="进度">
              <Progress percent={Math.round(progress)} size="small" style={{ width: 120 }} />
            </Descriptions.Item>
          </Descriptions>
          {polling && <Spin tip="分析进行中..." style={{ display: 'block', marginTop: 16 }} />}
          {status === 'failed' && (
            <Button type="primary" danger onClick={handleRetry} style={{ marginTop: 16 }}>
              重试
            </Button>
          )}
        </Card>
      )}

      {result?.result_summary && (
        <>
          {hasDeviation && (
            <Alert
              type="warning"
              message="设计偏差警告"
              description={`升阻比 (${result.result_summary.lift_to_drag_ratio.toFixed(2)}) 低于设计目标 (10.0)，建议优化翼型参数`}
              icon={<WarningOutlined />}
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          <Card title="分析结果" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic
                  title="升力系数 Cl"
                  value={result.result_summary.lift_coefficient}
                  precision={4}
                  valueStyle={{ color: '#1890ff' }}
                  prefix={<ArrowUpOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="阻力系数 Cd"
                  value={result.result_summary.drag_coefficient}
                  precision={4}
                  valueStyle={{ color: '#cf1322' }}
                  prefix={<ArrowDownOutlined />}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="力矩系数 Cm"
                  value={result.result_summary.moment_coefficient}
                  precision={4}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="升阻比 L/D"
                  value={result.result_summary.lift_to_drag_ratio}
                  precision={2}
                  valueStyle={{ color: hasDeviation ? '#cf1322' : '#3f8600' }}
                  prefix={hasDeviation ? <WarningOutlined /> : <CheckCircleOutlined />}
                />
              </Col>
            </Row>
            <Divider />
            <Descriptions size="small" bordered>
              <Descriptions.Item label="收敛状态">
                <Tag color={result.result_summary.convergence_status === 'converged' ? 'success' : 'warning'}>
                  {result.result_summary.convergence_status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="湍流模型">{result.result_summary.convergence_status}</Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="流场可视化" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={8}>
                <Card size="small" title="压力云图">
                  <CloudMapRenderer width={350} height={250} />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small" title="等值线图">
                  <ContourRenderer width={350} height={250} />
                </Card>
              </Col>
              <Col span={8}>
                <Card size="small" title="速度矢量场">
                  <VectorFieldRenderer width={350} height={250} />
                </Card>
              </Col>
            </Row>
          </Card>
        </>
      )}
    </Space>
  )
}