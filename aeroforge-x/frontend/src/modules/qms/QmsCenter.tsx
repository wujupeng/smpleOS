import { useState } from 'react'
import { Typography, Card, Button, Form, Input, Select, Tag, Descriptions, Alert, Space, Table, message, Tabs } from 'antd'
import { SafetyCertificateOutlined, CheckCircleOutlined, WarningOutlined } from '@ant-design/icons'
import apiClient from '../../services/apiClient'

const { Title } = Typography

export default function QmsCenter() {
  const [iqcResult, setIqcResult] = useState<Record<string, unknown> | null>(null)
  const [fqcResult, setFqcResult] = useState<Record<string, unknown> | null>(null)
  const [capaList, setCapaList] = useState<Record<string, unknown>[]>([])
  const [loading, setLoading] = useState(false)
  const [iqcForm] = Form.useForm()
  const [fqcForm] = Form.useForm()

  const handleIQC = async (values: { item_code: string; inspector: string }) => {
    try {
      setLoading(true)
      const planRes = await apiClient.post('/api/v1/qms/iqc/plans', { item_code: values.item_code })
      const resultRes = await apiClient.post('/api/v1/qms/iqc/results', {
        item_code: values.item_code,
        inspector: values.inspector,
        measurements: { dimension: 10.05, weight: 2.3 },
        criteria: { dimension: 10.0, weight: 2.3 },
        plan_id: planRes.data.data?.id,
      })
      setIqcResult(resultRes.data.data)
      message.success(resultRes.data.data?.material_released ? 'IQC合格，物料已放行' : 'IQC不合格，物料被拦截')
    } catch { message.error('IQC检验失败') }
    finally { setLoading(false) }
  }

  const handleFQC = async (values: { item_code: string; inspector: string }) => {
    try {
      setLoading(true)
      const planRes = await apiClient.post('/api/v1/qms/fqc/plans', { item_code: values.item_code })
      const resultRes = await apiClient.post('/api/v1/qms/fqc/results', {
        item_code: values.item_code, inspector: values.inspector,
        measurements: { dimension: 10.0 }, criteria: { dimension: 10.0 }, plan_id: planRes.data.data?.id,
      })
      setFqcResult(resultRes.data.data)
      message.success('FQC检验完成')
    } catch { message.error('FQC检验失败') }
    finally { setLoading(false) }
  }

  const handleCreateCapa = async () => {
    try {
      const res = await apiClient.post('/api/v1/qms/capa', {})
      setCapaList(prev => [...prev, res.data.data])
      message.success('CAPA已创建')
    } catch { message.error('创建失败') }
  }

  const resultColorMap: Record<string, string> = { pass: 'success', fail: 'error', marginal: 'warning' }

  return (
    <div>
      <Title level={3}><SafetyCertificateOutlined /> QMS 质量管理</Title>
      <Tabs items={[
        {
          key: 'iqc', label: 'IQC 来料检验',
          children: (
            <Card title="IQC检验执行">
              <Form form={iqcForm} onFinish={handleIQC} layout="inline" style={{ marginBottom: 16 }}>
                <Form.Item name="item_code" rules={[{ required: true }]}><Input placeholder="物料编码" /></Form.Item>
                <Form.Item name="inspector" rules={[{ required: true }]}><Input placeholder="检验员" /></Form.Item>
                <Form.Item><Button type="primary" htmlType="submit" loading={loading}>执行IQC</Button></Form.Item>
              </Form>
              {iqcResult && (
                <Alert
                  message={`IQC结果: ${iqcResult.record?.result?.toUpperCase()}`}
                  description={iqcResult.material_released ? '物料已放行，可投入生产' : '物料被拦截，禁止投入生产'}
                  type={resultColorMap[iqcResult.record?.result as string] || 'info'}
                  showIcon
                  icon={iqcResult.material_released ? <CheckCircleOutlined /> : <WarningOutlined />}
                />
              )}
            </Card>
          ),
        },
        {
          key: 'fqc', label: 'FQC 终检',
          children: (
            <Card title="FQC检验执行">
              <Form form={fqcForm} onFinish={handleFQC} layout="inline" style={{ marginBottom: 16 }}>
                <Form.Item name="item_code" rules={[{ required: true }]}><Input placeholder="物料编码" /></Form.Item>
                <Form.Item name="inspector" rules={[{ required: true }]}><Input placeholder="检验员" /></Form.Item>
                <Form.Item><Button type="primary" htmlType="submit" loading={loading}>执行FQC</Button></Form.Item>
              </Form>
              {fqcResult && (
                <Alert message={`FQC结果: ${fqcResult.record?.result?.toUpperCase()}`}
                  type={resultColorMap[fqcResult.record?.result as string] || 'info'} showIcon />
              )}
            </Card>
          ),
        },
        {
          key: 'capa', label: 'CAPA',
          children: (
            <Card title="CAPA纠正预防措施" extra={<Button type="primary" onClick={handleCreateCapa}>创建CAPA</Button>}>
              <Table dataSource={capaList} rowKey="id" size="small" columns={[
                { title: 'CAPA编号', dataIndex: 'capa_code' },
                { title: '状态', dataIndex: 'status', render: (v: string) => <Tag color={v === 'closed' ? 'success' : v === 'open' ? 'default' : 'processing'}>{v}</Tag> },
                { title: '根因', dataIndex: 'root_cause' },
                { title: '纠正措施', dataIndex: 'corrective_action' },
              ]} />
            </Card>
          ),
        },
      ]} />
    </div>
  )
}
