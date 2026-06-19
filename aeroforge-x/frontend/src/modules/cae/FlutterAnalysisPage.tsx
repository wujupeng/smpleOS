import { useState } from 'react'
import {
  Card, Form, Select, InputNumber, Button, message, Row, Col, Statistic,
  Tag, Descriptions, Alert, Space, Typography, Divider, List,
} from 'antd'
import { SwapOutlined, WarningOutlined, CheckCircleOutlined } from '@ant-design/icons'
import apiClient from '../../services/apiClient'

const { Title, Text } = Typography

interface FlutterResult {
  task_id: string
  model_id: string
  status: string
  result_summary?: {
    flutter_speed_ms: number
    flutter_frequency_hz: number
    flutter_margin: number
    critical_mode: number
    divergence_speed_ms: number
    meets_airworthiness: boolean
    damping_trend: { speed_ms: number; damping: number; mode: number }[]
    frequency_trend: { speed_ms: number; frequency_hz: number; mode: number }[]
  }
}

export default function FlutterAnalysisPage() {
  const [form] = Form.useForm()
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<FlutterResult | null>(null)

  const handleSubmit = async (values: Record<string, unknown>) => {
    setSubmitting(true)
    try {
      const res = await apiClient.post('/cae/flutter/submit', values)
      const data = res.data?.data || res.data
      setResult(data)
      message.success('颤振分析已完成')
    } catch {
      message.error('分析失败')
    } finally {
      setSubmitting(false)
    }
  }

  const meetsAirworthiness = result?.result_summary?.meets_airworthiness

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Title level={4}><SwapOutlined /> 颤振分析</Title>

      <Card title="分析配置">
        <Form form={form} layout="vertical" onFinish={handleSubmit} initialValues={{
          aerodynamic_model: 'quasi_steady', max_speed_ms: 300, min_speed_ms: 0, speed_steps: 20,
        }}>
          <Row gutter={16}>
            <Col span={6}>
              <Form.Item name="model_id" label="模型" rules={[{ required: true }]}>
                <Select options={[
                  { value: 'model-001', label: 'Wing-001' },
                  { value: 'model-003', label: 'Full-Aircraft-003' },
                ]} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="aerodynamic_model" label="气动模型">
                <Select options={[
                  { value: 'steady', label: '定常' },
                  { value: 'quasi_steady', label: '准定常' },
                  { value: 'unsteady', label: '非定常' },
                ]} />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name={['speed_range', 'min_speed_ms']} label="最小速度(m/s)">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name={['speed_range', 'max_speed_ms']} label="最大速度(m/s)">
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name={['speed_range', 'speed_steps']} label="速度步数">
                <InputNumber min={5} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={submitting} icon={<SwapOutlined />}>
              提交颤振分析
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {result?.result_summary && (
        <>
          {!meetsAirworthiness && (
            <Alert type="error" message="适航性不满足" description="颤振速度不满足适航要求，颤振裕度不足" icon={<WarningOutlined />} showIcon />
          )}

          <Card title="分析结果" style={{ marginTop: 16 }}>
            <Row gutter={16}>
              <Col span={6}>
                <Statistic title="颤振速度 (m/s)" value={result.result_summary.flutter_speed_ms} precision={1}
                  valueStyle={{ color: meetsAirworthiness ? '#3f8600' : '#cf1322' }}
                  prefix={meetsAirworthiness ? <CheckCircleOutlined /> : <WarningOutlined />} />
              </Col>
              <Col span={6}>
                <Statistic title="颤振频率 (Hz)" value={result.result_summary.flutter_frequency_hz} precision={2} />
              </Col>
              <Col span={6}>
                <Statistic title="颤振裕度" value={result.result_summary.flutter_margin} precision={2}
                  suffix="%" valueStyle={{ color: result.result_summary.flutter_margin > 0.15 ? '#3f8600' : '#cf1322' }} />
              </Col>
              <Col span={6}>
                <Statistic title="临界模态" value={result.result_summary.critical_mode} />
              </Col>
            </Row>
            <Divider />
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="发散速度(m/s)">{result.result_summary.divergence_speed_ms}</Descriptions.Item>
              <Descriptions.Item label="适航性">
                <Tag color={meetsAirworthiness ? 'success' : 'error'}>
                  {meetsAirworthiness ? '满足' : '不满足'}
                </Tag>
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="V-g 图数据（速度-阻尼/频率）" style={{ marginTop: 16 }}>
            <Row gutter={16}>
              <Col span={12}>
                <Card size="small" title="速度-阻尼曲线">
                  <div style={{ height: 200, overflow: 'auto' }}>
                    <List size="small" dataSource={result.result_summary.damping_trend.slice(0, 20)}
                      renderItem={(item: { speed_ms: number; damping: number; mode: number }) => (
                        <List.Item>V={item.speed_ms} m/s | g={item.damping.toFixed(4)} | Mode {item.mode}</List.Item>
                      )} />
                  </div>
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small" title="速度-频率曲线">
                  <div style={{ height: 200, overflow: 'auto' }}>
                    <List size="small" dataSource={result.result_summary.frequency_trend.slice(0, 20)}
                      renderItem={(item: { speed_ms: number; frequency_hz: number; mode: number }) => (
                        <List.Item>V={item.speed_ms} m/s | f={item.frequency_hz.toFixed(2)} Hz | Mode {item.mode}</List.Item>
                      )} />
                  </div>
                </Card>
              </Col>
            </Row>
          </Card>
        </>
      )}
    </Space>
  )
}