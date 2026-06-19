import { useState } from 'react'
import {
  Card, Form, Select, InputNumber, Button, message, Row, Col, Statistic,
  Tag, Descriptions, Alert, Space, Typography, Divider, List,
} from 'antd'
import { FireOutlined, WarningOutlined, CheckCircleOutlined } from '@ant-design/icons'
import apiClient from '../../services/apiClient'
import CloudMapRenderer from '../../components/cae/CloudMapRenderer'

const { Title, Text } = Typography

interface ThermalResult {
  task_id: string
  model_id: string
  status: string
  result_summary?: {
    max_temperature_c: number
    min_temperature_c: number
    avg_temperature_c: number
    max_heat_flux_w_m2: number
    max_thermal_gradient_c_m: number
    overheated_regions: { region: string; temperature_c: number; limit_c: number }[]
    thermal_management_suggestions: string[]
    convergence_status: string
  }
}

export default function ThermalAnalysisPage() {
  const [form] = Form.useForm()
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<ThermalResult | null>(null)

  const handleSubmit = async (values: Record<string, unknown>) => {
    setSubmitting(true)
    try {
      const res = await apiClient.post('/cae/thermal/submit', values)
      const data = res.data?.data || res.data
      setResult(data)
      message.success('热分析已完成')
    } catch {
      message.error('分析失败')
    } finally {
      setSubmitting(false)
    }
  }

  const hasOverheated = (result?.result_summary?.overheated_regions?.length ?? 0) > 0

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Title level={4}><FireOutlined /> 热分析</Title>

      <Card title="分析配置">
        <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{
          analysis_type: 'steady_state',
        }}>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="model_id" label="模型" rules={[{ required: true }]}>
                <Select options={[
                  { value: 'model-001', label: 'Battery-Pack-001' },
                  { value: 'model-002', label: 'Motor-Housing-002' },
                ]} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="analysis_type" label="分析类型">
                <Select options={[
                  { value: 'steady_state', label: '稳态分析' },
                  { value: 'transient', label: '瞬态分析' },
                ]} />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left" plain>热源配置</Divider>
          <Row gutter={16}>
            <Col span={6}><Form.Item name={['heat_sources', 0, 'name']} label="热源名称" initialValue="battery"><Input /></Form.Item></Col>
            <Col span={6}><Form.Item name={['heat_sources', 0, 'source_type']} label="类型" initialValue="volumetric"><Select options={[
              { value: 'volumetric', label: '体积热源' },
              { value: 'surface', label: '面热源' },
            ]} /></Form.Item></Col>
            <Col span={6}><Form.Item name={['heat_sources', 0, 'power_watts']} label="功率(W)" initialValue={500}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
          </Row>

          <Divider orientation="left" plain>冷却参数</Divider>
          <Row gutter={16}>
            <Col span={6}><Form.Item name={['coolant', 'coolant_type']} label="冷却液类型" initialValue="water"><Select options={[
              { value: 'water', label: '水' },
              { value: 'glycol', label: '乙二醇' },
              { value: 'air', label: '空气' },
            ]} /></Form.Item></Col>
            <Col span={6}><Form.Item name={['coolant', 'flow_rate_lpm']} label="流量(L/min)" initialValue={5}><InputNumber min={0} style={{ width: '100%' }} /></Form.Item></Col>
            <Col span={6}><Form.Item name={['coolant', 'inlet_temp_c']} label="入口温度(°C)" initialValue={20}><InputNumber style={{ width: '100%' }} /></Form.Item></Col>
          </Row>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={submitting} icon={<FireOutlined />}>
              提交热分析
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {result?.result_summary && (
        <>
          {hasOverheated && (
            <Alert type="warning" message="检测到过热区域" description="部分区域温度超过安全限值，请查看热管理建议" icon={<WarningOutlined />} showIcon />
          )}

          <Card title="分析结果">
            <Row gutter={16}>
              <Col span={6}>
                <Statistic title="最高温度(°C)" value={result.result_summary.max_temperature_c} precision={1}
                  valueStyle={{ color: result.result_summary.max_temperature_c > 120 ? '#cf1322' : '#3f8600' }}
                  prefix={result.result_summary.max_temperature_c > 120 ? <WarningOutlined /> : <CheckCircleOutlined />} />
              </Col>
              <Col span={6}>
                <Statistic title="最低温度(°C)" value={result.result_summary.min_temperature_c} precision={1} />
              </Col>
              <Col span={6}>
                <Statistic title="平均温度(°C)" value={result.result_summary.avg_temperature_c} precision={1} />
              </Col>
              <Col span={6}>
                <Statistic title="最大热流密度(W/m²)" value={result.result_summary.max_heat_flux_w_m2} precision={0} />
              </Col>
            </Row>
            <Divider />
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="最大热梯度(°C/m)">{result.result_summary.max_thermal_gradient_c_m.toFixed(1)}</Descriptions.Item>
              <Descriptions.Item label="收敛状态">
                <Tag color={result.result_summary.convergence_status === 'converged' ? 'success' : 'warning'}>
                  {result.result_summary.convergence_status}
                </Tag>
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {hasOverheated && (
            <Card title="过热区域" style={{ marginTop: 16 }}>
              <List size="small" bordered dataSource={result.result_summary.overheated_regions}
                renderItem={(item: { region: string; temperature_c: number; limit_c: number }) => (
                  <List.Item>
                    <Tag color="red">{item.region}</Tag>
                    温度 {item.temperature_c}°C / 限值 {item.limit_c}°C
                    <Tag color="error">超标 {(item.temperature_c - item.limit_c).toFixed(1)}°C</Tag>
                  </List.Item>
                )} />
            </Card>
          )}

          <Card title="温度场可视化" style={{ marginTop: 16 }}>
            <CloudMapRenderer width={500} height={300} />
          </Card>

          <Card title="热管理建议" style={{ marginTop: 16 }}>
            <List size="small" bordered dataSource={result.result_summary.thermal_management_suggestions}
              renderItem={(item: string) => (
                <List.Item><Text>{item}</Text></List.Item>
              )} />
          </Card>
        </>
      )}
    </Space>
  )
}