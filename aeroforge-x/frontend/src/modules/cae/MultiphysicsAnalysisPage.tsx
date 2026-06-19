import { useState } from 'react'
import {
  Card, Form, Select, InputNumber, Button, message, Row, Col, Statistic,
  Tag, Descriptions, Alert, Space, Typography, Divider, List, Table,
} from 'antd'
import { ExperimentOutlined, CheckCircleOutlined, WarningOutlined } from '@ant-design/icons'
import apiClient from '../../services/apiClient'
import CloudMapRenderer from '../../components/cae/CloudMapRenderer'
import VectorFieldRenderer from '../../components/cae/VectorFieldRenderer'

const { Title, Text } = Typography

interface MultiphysicsResult {
  task_id: string
  model_id: string
  status: string
  result_summary?: {
    converged: boolean
    iterations_completed: number
    final_residual: number
    coupled_results: {
      thermal_results: Record<string, unknown>
      structural_results: Record<string, unknown>
      aerodynamic_results: Record<string, unknown>
    }
    convergence_history: { iteration: number; coupling_residual: number }[]
    solver_statuses: { solver_name: string; status: string; current_iteration: number; residual: number }[]
  }
}

export default function MultiphysicsAnalysisPage() {
  const [form] = Form.useForm()
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<MultiphysicsResult | null>(null)

  const handleSubmit = async (values: Record<string, unknown>) => {
    setSubmitting(true)
    try {
      const res = await apiClient.post('/cae/multiphysics/submit', values)
      const data = res.data?.data || res.data
      setResult(data)
      message.success('多物理场耦合分析已完成')
    } catch {
      message.error('分析失败')
    } finally {
      setSubmitting(false)
    }
  }

  const converged = result?.result_summary?.converged

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Title level={4}><ExperimentOutlined /> 多物理场耦合分析</Title>

      <Card title="耦合分析配置">
        <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{
          coupling_type: 'aero_structural', coupling_scheme: 'explicit_weak',
          max_iterations: 10, residual_tolerance: 0.0001, relaxation_factor: 0.7,
        }}>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="model_id" label="模型" rules={[{ required: true }]}>
                <Select options={[
                  { value: 'model-001', label: 'Full-Aircraft-001' },
                  { value: 'model-002', label: 'Wing-Assembly-002' },
                ]} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="coupling_type" label="耦合类型">
                <Select options={[
                  { value: 'aero_structural', label: '气动-结构耦合' },
                  { value: 'thermal_structural', label: '热-结构耦合' },
                  { value: 'aero_thermal_structural', label: '气动-热-结构三场耦合' },
                ]} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="coupling_scheme" label="耦合方案">
                <Select options={[
                  { value: 'explicit_weak', label: '显式松耦合' },
                  { value: 'implicit_strong', label: '隐式强耦合' },
                ]} />
              </Form.Item>
            </Col>
          </Row>
          <Divider orientation="left" plain>收敛准则</Divider>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name={['convergence_criteria', 'max_iterations']} label="最大迭代次数">
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name={['convergence_criteria', 'residual_tolerance']} label="残差容限">
                <InputNumber step={1e-5} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name={['convergence_criteria', 'relaxation_factor']} label="松弛因子">
                <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={submitting} icon={<ExperimentOutlined />}>
              提交耦合分析
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {result?.result_summary && (
        <>
          {!converged && (
            <Alert type="warning" message="耦合未收敛" description={`经过 ${result.result_summary.iterations_completed} 次迭代仍未收敛，最终残差: ${result.result_summary.final_residual.toExponential(2)}`} icon={<WarningOutlined />} showIcon />
          )}

          <Card title="耦合结果">
            <Row gutter={16}>
              <Col span={6}>
                <Statistic title="收敛状态" value={converged ? '已收敛' : '未收敛'}
                  valueStyle={{ color: converged ? '#3f8600' : '#cf1322' }}
                  prefix={converged ? <CheckCircleOutlined /> : <WarningOutlined />} />
              </Col>
              <Col span={6}>
                <Statistic title="迭代次数" value={result.result_summary.iterations_completed} />
              </Col>
              <Col span={6}>
                <Statistic title="最终残差" value={result.result_summary.final_residual} precision={6} />
              </Col>
              <Col span={6}>
                <Statistic title="参与求解器" value={result.result_summary.solver_statuses.length} />
              </Col>
            </Row>
          </Card>

          <Card title="求解器状态" style={{ marginTop: 16 }}>
            <Table dataSource={result.result_summary.solver_statuses} size="small" pagination={false} rowKey="solver_name"
              columns={[
                { title: '求解器', dataIndex: 'solver_name' },
                { title: '状态', dataIndex: 'status', render: (v: string) => <Tag color={v === 'completed' ? 'success' : 'processing'}>{v}</Tag> },
                { title: '迭代步', dataIndex: 'current_iteration' },
                { title: '残差', dataIndex: 'residual', render: (v: number) => v.toExponential(4) },
              ]} />
          </Card>

          <Card title="收敛历史" style={{ marginTop: 16 }}>
            <List size="small" bordered dataSource={result.result_summary.convergence_history}
              renderItem={(item: { iteration: number; coupling_residual: number }) => (
                <List.Item>迭代 {item.iteration}: 残差 = {item.coupling_residual.toExponential(4)}</List.Item>
              )} />
          </Card>

          <Card title="耦合场可视化" style={{ marginTop: 16 }}>
            <Row gutter={16}>
              <Col span={12}>
                <Card size="small" title="耦合应力场"><CloudMapRenderer width={450} height={280} /></Card>
              </Col>
              <Col span={12}>
                <Card size="small" title="耦合变形场"><VectorFieldRenderer width={450} height={280} /></Card>
              </Col>
            </Row>
          </Card>
        </>
      )}
    </Space>
  )
}