import { useState } from 'react'
import { Typography, Form, InputNumber, Select, Button, Card, Steps, message, Descriptions, Tag, Alert, Space } from 'antd'
import { RocketOutlined, CheckCircleOutlined, ThunderboltOutlined } from '@ant-design/icons'
import apiClient from '../../services/apiClient'

const { Title } = Typography
const { Option } = Select

interface Violation {
  parameter: string
  message: string
  severity: string
  suggestion: string
}

interface SpecData {
  id: string
  spec_code: string
  aircraft_type: string
  payload_kg: number
  range_km: number
  cruise_speed_kmh: number
  takeoff_distance_m: number
  power_type: string
  budget_cny: number | null
  status: string
  derived_constraints: Record<string, unknown>
}

export default function DesignCenter() {
  const [currentStep, setCurrentStep] = useState(0)
  const [specData, setSpecData] = useState<SpecData | null>(null)
  const [violations, setViolations] = useState<Violation[]>([])
  const [recommendation, setRecommendation] = useState<Record<string, unknown> | null>(null)
  const [modelStatus, setModelStatus] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const handleValidateAndRecommend = async () => {
    try {
      const values = await form.validateFields()
      setLoading(true)
      const recRes = await apiClient.post('/api/v1/aircraft-type/recommend', values)
      setRecommendation(recRes.data.data)
      if (values.aircraft_type !== recRes.data.data.recommended_type) {
        message.info(`建议类型: ${recRes.data.data.recommended_type}，已自动切换`)
        form.setFieldsValue({ aircraft_type: recRes.data.data.recommended_type })
      }
      setCurrentStep(1)
    } catch {
      message.error('请检查输入参数')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateSpec = async () => {
    try {
      setLoading(true)
      const values = await form.validateFields()
      const res = await apiClient.post('/api/v1/specs', values)
      setSpecData(res.data.data)
      message.success('需求规格书已创建')
      setCurrentStep(2)
    } catch {
      message.error('创建失败')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirmSpec = async () => {
    if (!specData) return
    try {
      setLoading(true)
      const res = await apiClient.post(`/api/v1/specs/${specData.id}/confirm`)
      setSpecData(res.data.data)
      message.success('需求规格书已确认')
      setCurrentStep(3)
    } catch {
      message.error('确认失败')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateModel = async () => {
    if (!specData) return
    try {
      setLoading(true)
      await apiClient.post('/api/v1/models/generate', {
        spec_id: specData.id,
        aircraft_type: specData.aircraft_type,
        payload_kg: specData.payload_kg,
        range_km: specData.range_km,
        cruise_speed_kmh: specData.cruise_speed_kmh,
      })
      setModelStatus('completed')
      message.success('3D模型已生成')
      setCurrentStep(4)
    } catch {
      message.error('模型生成失败')
    } finally {
      setLoading(false)
    }
  }

  const handleValidateRules = async () => {
    try {
      const res = await apiClient.post('/api/v1/rules/validate', {
        model_params: { aspect_ratio: 12, wing_sweep_deg: 3, taper_ratio: 0.5, wing_loading: 200, fineness_ratio: 8 },
      })
      setViolations(res.data.data.violations || [])
    } catch {
      message.error('规则校验失败')
    }
  }

  const statusColorMap: Record<string, string> = { draft: 'default', confirmed: 'processing', frozen: 'success' }

  return (
    <div>
      <Title level={3}><RocketOutlined /> 设计中心</Title>
      <Steps current={currentStep} style={{ marginBottom: 24 }} items={[
        { title: '需求输入' }, { title: '类型推荐' }, { title: '创建规格书' }, { title: '确认规格' }, { title: '生成模型' },
      ]} />

      {currentStep === 0 && (
        <Card title="飞行器需求参数">
          <Form form={form} layout="vertical">
            <Form.Item name="aircraft_type" label="飞行器类型" initialValue="fixed_wing">
              <Select><Option value="fixed_wing">固定翼</Option><Option value="evtol">eVTOL</Option><Option value="glider">滑翔机</Option><Option value="uav">无人机</Option></Select>
            </Form.Item>
            <Form.Item name="payload_kg" label="载荷 (kg)" rules={[{ required: true }]}><InputNumber min={1} max={50000} style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="range_km" label="航程 (km)" rules={[{ required: true }]}><InputNumber min={10} max={20000} style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="cruise_speed_kmh" label="巡航速度 (km/h)" rules={[{ required: true }]}><InputNumber min={50} max={900} style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="takeoff_distance_m" label="起飞距离 (m)" rules={[{ required: true }]}><InputNumber min={10} max={3000} style={{ width: '100%' }} /></Form.Item>
            <Form.Item name="power_type" label="动力类型" initialValue="electric">
              <Select><Option value="electric">电动</Option><Option value="hybrid">混合动力</Option><Option value="gasoline">汽油</Option><Option value="diesel">柴油</Option></Select>
            </Form.Item>
            <Form.Item name="budget_cny" label="预算 (元)"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item>
            <Form.Item><Button type="primary" onClick={handleValidateAndRecommend} loading={loading}>校验并推荐类型</Button></Form.Item>
          </Form>
        </Card>
      )}

      {currentStep === 1 && recommendation && (
        <Card title="飞行器类型推荐">
          <Alert message={`推荐类型: ${recommendation.recommended_type}`} description={recommendation.reason as string} type="info" showIcon style={{ marginBottom: 16 }} />
          <Descriptions bordered column={1} title="推荐参数模板">
            {recommendation.template?.default_params && Object.entries(recommendation.template.default_params as Record<string, unknown>).map(([key, value]) => (
              <Descriptions.Item key={key} label={key}>{String(value)}</Descriptions.Item>
            ))}
          </Descriptions>
          <Space style={{ marginTop: 16 }}>
            <Button onClick={() => setCurrentStep(0)}>返回修改</Button>
            <Button type="primary" onClick={handleCreateSpec} loading={loading}>创建需求规格书</Button>
          </Space>
        </Card>
      )}

      {currentStep === 2 && specData && (
        <Card title="需求规格书">
          <Descriptions bordered column={2}>
            <Descriptions.Item label="规格编号">{specData.spec_code}</Descriptions.Item>
            <Descriptions.Item label="状态"><Tag color={statusColorMap[specData.status]}>{specData.status}</Tag></Descriptions.Item>
            <Descriptions.Item label="飞行器类型">{specData.aircraft_type}</Descriptions.Item>
            <Descriptions.Item label="载荷">{specData.payload_kg} kg</Descriptions.Item>
            <Descriptions.Item label="航程">{specData.range_km} km</Descriptions.Item>
            <Descriptions.Item label="巡航速度">{specData.cruise_speed_kmh} km/h</Descriptions.Item>
            <Descriptions.Item label="起飞距离">{specData.takeoff_distance_m} m</Descriptions.Item>
            <Descriptions.Item label="动力类型">{specData.power_type}</Descriptions.Item>
          </Descriptions>
          <Space style={{ marginTop: 16 }}>
            <Button onClick={() => setCurrentStep(1)}>返回</Button>
            <Button type="primary" icon={<CheckCircleOutlined />} onClick={handleConfirmSpec} loading={loading}>确认规格书</Button>
          </Space>
        </Card>
      )}

      {currentStep === 3 && specData && (
        <Card title="规格已确认 - 生成3D模型">
          <Alert message="规格书已确认，可以生成参数化3D模型" type="success" showIcon style={{ marginBottom: 16 }} />
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleGenerateModel} loading={loading} size="large">生成3D模型</Button>
        </Card>
      )}

      {currentStep === 4 && (
        <Card title="模型已生成">
          <Alert message="参数化3D模型已成功生成" type="success" showIcon style={{ marginBottom: 16 }} />
          <Space>
            <Button onClick={handleValidateRules}>执行设计规则校验</Button>
            <Button onClick={() => { setCurrentStep(0); setSpecData(null); setModelStatus(''); setViolations([]) }}>新建设计</Button>
          </Space>
          {violations.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <Title level={5}>规则校验结果</Title>
              {violations.map((v, i) => (
                <Alert key={i} message={`${v.parameter}: ${v.message}`} description={v.suggestion} type={v.severity === 'error' ? 'error' : 'warning'} style={{ marginBottom: 8 }} showIcon />
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
