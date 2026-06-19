import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Card, Typography, Space, Tag, Button, Table, Modal, Form,
  Input, Select, InputNumber, message, Row, Col, Statistic,
  Descriptions, Tabs, Empty, Alert, Badge,
} from 'antd'
import {
  LineChartOutlined, PlusOutlined, WarningOutlined,
  CheckCircleOutlined, ExperimentOutlined,
} from '@ant-design/icons'
import apiClient from '../../../services/apiClient'
import { useProjectStore } from '../../../stores/projectStore'

const { Title, Text } = Typography

interface ChartInfo {
  id: string
  chart_type: string
  process_name: string
  characteristic_name: string
  specification_limits: { usl: number; lsl: number; target: number }
  control_limits: { ucl: number; lcl: number; cl: number }
  sample_size: number
  sampling_frequency: string
  status: string
  out_of_control_rules: Array<{ rule_id: number; name: string; enabled: boolean }>
  measurements: MeasurementInfo[]
}

interface MeasurementInfo {
  id: string
  sample_group: number
  measurement_values: number[]
  mean: number
  range_val: number
  std_dev: number
  is_out_of_control: boolean
  violation_rules: number[]
  measured_at: string
}

interface CapabilityInfo {
  cp: number
  cpk: number
  pp: number
  ppk: number
  grade: string
}

function ControlChartCanvas({ chart }: { chart: ChartInfo }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !chart || !chart.measurements?.length) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const width = canvas.width
    const height = canvas.height
    const padding = { top: 30, right: 30, bottom: 40, left: 60 }
    const plotW = width - padding.left - padding.right
    const plotH = height - padding.top - padding.bottom

    ctx.clearRect(0, 0, width, height)
    ctx.fillStyle = '#fafafa'
    ctx.fillRect(0, 0, width, height)

    const measurements = chart.measurements
    const means = measurements.map(m => m.mean)
    const cl = chart.control_limits.cl
    const ucl = chart.control_limits.ucl
    const lcl = chart.control_limits.lcl
    const usl = chart.specification_limits.usl
    const lsl = chart.specification_limits.lsl

    const allValues = [...means, ucl, lcl, usl, lsl, cl]
    const minVal = Math.min(...allValues) - Math.abs(cl) * 0.05
    const maxVal = Math.max(...allValues) + Math.abs(cl) * 0.05

    const scaleX = (i: number) => padding.left + (i / Math.max(means.length - 1, 1)) * plotW
    const scaleY = (v: number) => padding.top + plotH - ((v - minVal) / (maxVal - minVal)) * plotH

    ctx.strokeStyle = '#e8e8e8'
    ctx.lineWidth = 1
    for (let i = 0; i <= 5; i++) {
      const y = padding.top + (i / 5) * plotH
      ctx.beginPath()
      ctx.moveTo(padding.left, y)
      ctx.lineTo(width - padding.right, y)
      ctx.stroke()
    }

    if (usl && lsl) {
      ctx.strokeStyle = '#ff4d4f'
      ctx.lineWidth = 1
      ctx.setLineDash([5, 3])
      const yUs = scaleY(usl)
      const yLs = scaleY(lsl)
      ctx.beginPath()
      ctx.moveTo(padding.left, yUs)
      ctx.lineTo(width - padding.right, yUs)
      ctx.stroke()
      ctx.beginPath()
      ctx.moveTo(padding.left, yLs)
      ctx.lineTo(width - padding.right, yLs)
      ctx.stroke()
      ctx.setLineDash([])

      ctx.fillStyle = '#ff4d4f'
      ctx.font = '10px monospace'
      ctx.fillText(`USL=${usl}`, width - padding.right + 2, yUs + 3)
      ctx.fillText(`LSL=${lsl}`, width - padding.right + 2, yLs + 3)
    }

    ctx.strokeStyle = '#52c41a'
    ctx.lineWidth = 1.5
    ctx.setLineDash([8, 4])
    const yUcl = scaleY(ucl)
    const yLcl = scaleY(lcl)
    ctx.beginPath()
    ctx.moveTo(padding.left, yUcl)
    ctx.lineTo(width - padding.right, yUcl)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(padding.left, yLcl)
    ctx.lineTo(width - padding.right, yLcl)
    ctx.stroke()
    ctx.setLineDash([])

    ctx.fillStyle = '#52c41a'
    ctx.font = '10px monospace'
    ctx.fillText(`UCL=${ucl.toFixed(3)}`, 2, yUcl + 3)
    ctx.fillText(`LCL=${lcl.toFixed(3)}`, 2, yLcl + 3)

    ctx.strokeStyle = '#1890ff'
    ctx.lineWidth = 1
    const yCl = scaleY(cl)
    ctx.beginPath()
    ctx.moveTo(padding.left, yCl)
    ctx.lineTo(width - padding.right, yCl)
    ctx.stroke()

    ctx.fillStyle = '#1890ff'
    ctx.fillText(`CL=${cl.toFixed(3)}`, 2, yCl + 3)

    ctx.strokeStyle = '#1890ff'
    ctx.lineWidth = 1.5
    ctx.beginPath()
    means.forEach((val, i) => {
      const x = scaleX(i)
      const y = scaleY(val)
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    })
    ctx.stroke()

    measurements.forEach((m, i) => {
      const x = scaleX(i)
      const y = scaleY(m.mean)
      ctx.beginPath()
      ctx.arc(x, y, 4, 0, Math.PI * 2)
      if (m.is_out_of_control) {
        ctx.fillStyle = '#ff4d4f'
        ctx.fill()
        ctx.strokeStyle = '#ff4d4f'
        ctx.lineWidth = 2
        ctx.stroke()
        ctx.beginPath()
        ctx.arc(x, y, 8, 0, Math.PI * 2)
        ctx.strokeStyle = '#ff4d4f'
        ctx.lineWidth = 1.5
        ctx.stroke()
      } else {
        ctx.fillStyle = '#1890ff'
        ctx.fill()
      }
    })

    ctx.fillStyle = '#333'
    ctx.font = '11px sans-serif'
    ctx.textAlign = 'center'
    measurements.forEach((m, i) => {
      const x = scaleX(i)
      ctx.fillText(String(m.sample_group), x, height - padding.bottom + 15)
    })

    ctx.textAlign = 'center'
    ctx.fillText('Sample', width / 2, height - 5)

    ctx.save()
    ctx.translate(12, height / 2)
    ctx.rotate(-Math.PI / 2)
    ctx.fillText('Value', 0, 0)
    ctx.restore()
  }, [chart])

  return (
    <canvas
      ref={canvasRef}
      width={800}
      height={400}
      style={{ width: '100%', maxWidth: 800, border: '1px solid #e8e8e8', borderRadius: 4 }}
    />
  )
}

export default function SPCPage() {
  const { t } = useTranslation()
  const { currentProjectId } = useProjectStore()

  const chartTypeLabels: Record<string, string> = {
    x_bar_r: t('spc.chartTypeXbarR'),
    x_bar_s: t('spc.chartTypeXbarS'),
    p: t('spc.chartTypeP'),
    c: t('spc.chartTypeC'),
    u: t('spc.chartTypeU'),
    ewma: t('spc.chartTypeEwma'),
    cusum: t('spc.chartTypeCusum'),
  }

  const oocRuleLabels: Record<number, string> = {
    1: t('spc.rule1'),
    2: t('spc.rule2'),
    3: t('spc.rule3'),
    4: t('spc.rule4'),
    5: t('spc.rule5'),
    6: t('spc.rule6'),
    7: t('spc.rule7'),
    8: t('spc.rule8'),
  }

  const [charts, setCharts] = useState<ChartInfo[]>([])
  const [selectedChart, setSelectedChart] = useState<ChartInfo | null>(null)
  const [capability, setCapability] = useState<CapabilityInfo | null>(null)
  const [loading, setLoading] = useState(false)

  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [measureModalOpen, setMeasureModalOpen] = useState(false)
  const [chartForm] = Form.useForm()
  const [measureForm] = Form.useForm()

  const loadCharts = useCallback(async () => {
    try {
      const resp = await apiClient.get('/qms/spc/charts')
      setCharts(resp.data?.data?.charts ?? [])
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    loadCharts()
  }, [loadCharts])

  const loadChartDetail = async (chartId: string) => {
    setLoading(true)
    try {
      const resp = await apiClient.get(`/qms/spc/charts/${chartId}`)
      const chartData = resp.data?.data
      setSelectedChart(chartData)

      try {
        const capResp = await apiClient.get(`/qms/spc/charts/${chartId}/capability`)
        setCapability(capResp.data?.data)
      } catch {
        setCapability(null)
      }
    } catch {
      message.error(t('spc.loadChartFailed'))
    } finally {
      setLoading(false)
    }
  }

  const handleCreateChart = async (values: Record<string, unknown>) => {
    try {
      await apiClient.post('/qms/spc/charts', {
        ...values,
        tenant_id: currentProjectId || 'default',
        project_id: currentProjectId || 'default',
      })
      message.success(t('spc.createChartSuccess'))
      setCreateModalOpen(false)
      chartForm.resetFields()
      loadCharts()
    } catch {
      message.error(t('common.error'))
    }
  }

  const handleAddMeasurement = async (values: Record<string, unknown>) => {
    if (!selectedChart) return
    try {
      const valuesStr = String(values.measurement_values)
      const parsedValues = valuesStr.split(',').map((v: string) => parseFloat(v.trim())).filter((v: number) => !isNaN(v))
      if (parsedValues.length === 0) {
        message.error(t('spc.invalidMeasureValues'))
        return
      }
      await apiClient.post(`/qms/spc/charts/${selectedChart.id}/measurements`, {
        sample_group: values.sample_group,
        measurement_values: parsedValues,
      })
      message.success(t('spc.addMeasureSuccess'))
      setMeasureModalOpen(false)
      measureForm.resetFields()
      loadChartDetail(selectedChart.id)
    } catch {
      message.error(t('common.error'))
    }
  }

  const handleCalculateLimits = async () => {
    if (!selectedChart) return
    try {
      await apiClient.post(`/qms/spc/charts/${selectedChart.id}/calculate-limits`)
      message.success(t('spc.calcLimitsSuccess'))
      loadChartDetail(selectedChart.id)
    } catch {
      message.error(t('common.error'))
    }
  }

  const chartListColumns = [
    { title: t('spc.process'), dataIndex: 'process_name', key: 'process_name', width: 120 },
    { title: t('spc.characteristic'), dataIndex: 'characteristic_name', key: 'characteristic_name', width: 120 },
    {
      title: t('spc.chartType'),
      dataIndex: 'chart_type',
      key: 'chart_type',
      width: 120,
      render: (v: string) => chartTypeLabels[v] || v,
    },
    {
      title: t('common.status'),
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (v: string) => v === 'active' ? <Tag color="green">{t('status.active')}</Tag> : <Tag color="orange">{t('status.suspended')}</Tag>,
    },
    {
      title: t('common.actions'),
      key: 'actions',
      width: 80,
      render: (_: unknown, record: ChartInfo) => (
        <Button size="small" type="link" onClick={() => loadChartDetail(record.id)}>
          {t('common.view')}
        </Button>
      ),
    },
  ]

  const measurementColumns = [
    { title: t('spc.sampleGroup'), dataIndex: 'sample_group', key: 'sample_group', width: 70 },
    {
      title: t('spc.mean'),
      dataIndex: 'mean',
      key: 'mean',
      width: 90,
      render: (v: number) => v?.toFixed(4),
    },
    {
      title: t('spc.range'),
      dataIndex: 'range_val',
      key: 'range_val',
      width: 80,
      render: (v: number) => v?.toFixed(4),
    },
    {
      title: t('spc.stdDev'),
      dataIndex: 'std_dev',
      key: 'std_dev',
      width: 80,
      render: (v: number) => v?.toFixed(4),
    },
    {
      title: t('common.status'),
      key: 'status',
      width: 80,
      render: (_: unknown, record: MeasurementInfo) => (
        record.is_out_of_control
          ? <Tag color="red" icon={<WarningOutlined />}>{t('spc.outOfControl')}</Tag>
          : <Tag color="green" icon={<CheckCircleOutlined />}>{t('spc.inControl')}</Tag>
      ),
    },
    {
      title: t('spc.violationRules'),
      dataIndex: 'violation_rules',
      key: 'violation_rules',
      render: (rules: number[]) => rules?.map(r => (
        <Tag key={r} color="red">{r}. {oocRuleLabels[r]}</Tag>
      )),
    },
  ]

  const oocCount = selectedChart?.measurements?.filter(m => m.is_out_of_control).length ?? 0

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title={t('spc.chartCount')} value={charts.length} prefix={<LineChartOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('spc.measurementCount')} value={selectedChart?.measurements?.length ?? 0} prefix={<ExperimentOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('spc.oocCount')}
              value={oocCount}
              prefix={<WarningOutlined />}
              valueStyle={{ color: oocCount > 0 ? '#cf1322' : '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('spc.processCapabilityCpk')}
              value={capability?.cpk ?? '-'}
              suffix={capability ? '' : ''}
              valueStyle={{
                color: !capability ? undefined :
                  capability.cpk >= 1.33 ? '#3f8600' :
                  capability.cpk >= 1.0 ? '#fa8c16' : '#cf1322',
              }}
            />
          </Card>
        </Col>
      </Row>

      <Tabs
        defaultActiveKey="charts"
        items={[
          {
            key: 'charts',
            label: <span><LineChartOutlined /> {t('spc.controlCharts')}</span>,
            children: (
              <Card
                title={t('spc.chartList')}
                extra={
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
                    {t('spc.createChart')}
                  </Button>
                }
              >
                <Table
                  columns={chartListColumns}
                  dataSource={charts.map(c => ({ ...c, key: c.id }))}
                  size="small"
                  pagination={{ pageSize: 10 }}
                />
              </Card>
            ),
          },
          {
            key: 'detail',
            label: <span><ExperimentOutlined /> {t('spc.chartDetail')}</span>,
            children: (
              <div>
                {!selectedChart ? (
                  <Card>
                    <Empty description={t('spc.selectChart')} />
                  </Card>
                ) : (
                  <>
                    <Card
                      title={`${selectedChart.process_name} - ${selectedChart.characteristic_name}`}
                      extra={
                        <Space>
                          <Button onClick={handleCalculateLimits}>{t('spc.calculateLimits')}</Button>
                          <Button type="primary" icon={<PlusOutlined />} onClick={() => setMeasureModalOpen(true)}>
                            {t('spc.addMeasurement')}
                          </Button>
                        </Space>
                      }
                      style={{ marginBottom: 16 }}
                    >
                      <Descriptions bordered column={3} size="small" style={{ marginBottom: 16 }}>
                        <Descriptions.Item label={t('spc.chartType')}>{chartTypeLabels[selectedChart.chart_type]}</Descriptions.Item>
                        <Descriptions.Item label={t('spc.sampleSize')}>{selectedChart.sample_size}</Descriptions.Item>
                        <Descriptions.Item label={t('spc.samplingFreq')}>{selectedChart.sampling_frequency}</Descriptions.Item>
                        <Descriptions.Item label={t('spc.usl')}>{selectedChart.specification_limits?.usl}</Descriptions.Item>
                        <Descriptions.Item label={t('spc.target')}>{selectedChart.specification_limits?.target}</Descriptions.Item>
                        <Descriptions.Item label={t('spc.lsl')}>{selectedChart.specification_limits?.lsl}</Descriptions.Item>
                        <Descriptions.Item label={t('spc.ucl')}>{selectedChart.control_limits?.ucl?.toFixed(4)}</Descriptions.Item>
                        <Descriptions.Item label={t('spc.cl')}>{selectedChart.control_limits?.cl?.toFixed(4)}</Descriptions.Item>
                        <Descriptions.Item label={t('spc.lcl')}>{selectedChart.control_limits?.lcl?.toFixed(4)}</Descriptions.Item>
                      </Descriptions>

                      {oocCount > 0 && (
                        <Alert
                          type="error"
                          message={t('spc.oocAlert', { count: oocCount })}
                          description={t('spc.oocAlertDesc')}
                          showIcon
                          style={{ marginBottom: 16 }}
                        />
                      )}

                      <ControlChartCanvas chart={selectedChart} />
                    </Card>

                    {capability && (
                      <Card title={t('spc.processCapability')} style={{ marginBottom: 16 }}>
                        <Row gutter={16}>
                          <Col span={6}>
                            <Statistic title="Cp" value={capability.cp} precision={4} />
                          </Col>
                          <Col span={6}>
                            <Statistic
                              title="Cpk"
                              value={capability.cpk}
                              precision={4}
                              valueStyle={{ color: capability.cpk >= 1.33 ? '#3f8600' : capability.cpk >= 1.0 ? '#fa8c16' : '#cf1322' }}
                            />
                          </Col>
                          <Col span={6}>
                            <Statistic title="Pp" value={capability.pp} precision={4} />
                          </Col>
                          <Col span={6}>
                            <Statistic title="Ppk" value={capability.ppk} precision={4} />
                          </Col>
                        </Row>
                        <div style={{ marginTop: 12 }}>
                          <Badge
                            status={capability.cpk >= 1.33 ? 'success' : capability.cpk >= 1.0 ? 'warning' : 'error'}
                            text={`${t('spc.grade')}: ${capability.grade}`}
                          />
                        </div>
                      </Card>
                    )}

                    <Card title={t('spc.measurementCount')}>
                      <Table
                        columns={measurementColumns}
                        dataSource={selectedChart.measurements?.map(m => ({ ...m, key: m.id })) || []}
                        size="small"
                        pagination={{ pageSize: 10 }}
                      />
                    </Card>
                  </>
                )}
              </div>
            ),
          },
        ]}
      />

      <Modal
        title={t('spc.createChart')}
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        onOk={() => chartForm.submit()}
        width={600}
      >
        <Form form={chartForm} layout="vertical" onFinish={handleCreateChart}>
          <Form.Item name="process_name" label={t('spc.processName')} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="characteristic_name" label={t('spc.characteristicName')} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="chart_type" label={t('spc.chartType')} initialValue="x_bar_r">
            <Select options={Object.entries(chartTypeLabels).map(([k, v]) => ({ value: k, label: v }))} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name={['specification_limits', 'usl']} label={t('spc.usl')} rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name={['specification_limits', 'target']} label={t('spc.target')} rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name={['specification_limits', 'lsl']} label={t('spc.lsl')} rules={[{ required: true }]}>
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="sample_size" label={t('spc.sampleSize')} initialValue={5}>
            <InputNumber min={2} max={25} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={t('spc.addMeasurement')}
        open={measureModalOpen}
        onCancel={() => setMeasureModalOpen(false)}
        onOk={() => measureForm.submit()}
      >
        <Form form={measureForm} layout="vertical" onFinish={handleAddMeasurement}>
          <Form.Item name="sample_group" label={t('spc.sampleGroupNo')} rules={[{ required: true }]}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="measurement_values" label={t('spc.measureValues')} rules={[{ required: true }]}>
            <Input placeholder="10.0, 10.01, 9.99, 10.0, 10.02" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
