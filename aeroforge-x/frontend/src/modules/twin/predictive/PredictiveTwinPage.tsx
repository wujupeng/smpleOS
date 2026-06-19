import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Card, Typography, Space, Tag, Button, Table, Form,
  Input, Select, InputNumber, message, Row, Col, Statistic,
  Descriptions, Tabs, Empty, Alert, Progress, Badge,
} from 'antd'
import {
  SafetyCertificateOutlined, ExperimentOutlined,
  ThunderboltOutlined, WarningOutlined, CheckCircleOutlined,
  DashboardOutlined, FieldTimeOutlined,
} from '@ant-design/icons'
import apiClient from '../../../services/apiClient'

const { Text } = Typography

interface RULInfo {
  rul_hours: number
  confidence_lower: number
  confidence_upper: number
  current_health: number
  component: string
}

interface FailureProbInfo {
  probability_7d: number
  probability_30d: number
  probability_90d: number
  exceeds_threshold: boolean
  severity: string
}

interface MaintenanceWindowInfo {
  component: string
  recommended_date: string
  earliest_date: string
  latest_date: string
  risk_if_deferred: number
  cost_estimate: number
  priority: number
}

interface SimStatusInfo {
  status: string
  step_count: number
  model_calibrations: number
  accumulated_deviation: number
}

interface SimResultInfo {
  predicted_state: Record<string, number>
  deviation: Record<string, number>
  deviation_exceeds_threshold: boolean
  step_number: number
}

function DegradationCurveCanvas({ health, threshold }: { health: number; threshold: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const w = canvas.width, h = canvas.height
    const pad = { top: 20, right: 20, bottom: 30, left: 50 }
    const pw = w - pad.left - pad.right
    const ph = h - pad.top - pad.bottom

    ctx.clearRect(0, 0, w, h)
    ctx.fillStyle = '#fafafa'
    ctx.fillRect(0, 0, w, h)

    const scaleX = (t: number) => pad.left + (t / 1000) * pw
    const scaleY = (v: number) => pad.top + ph - v * ph

    ctx.strokeStyle = '#e8e8e8'
    ctx.lineWidth = 1
    for (let i = 0; i <= 5; i++) {
      const y = pad.top + (i / 5) * ph
      ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke()
    }

    const thresholdY = scaleY(threshold)
    ctx.strokeStyle = '#ff4d4f'
    ctx.lineWidth = 1.5
    ctx.setLineDash([5, 3])
    ctx.beginPath(); ctx.moveTo(pad.left, thresholdY); ctx.lineTo(w - pad.right, thresholdY); ctx.stroke()
    ctx.setLineDash([])
    ctx.fillStyle = '#ff4d4f'
    ctx.font = '10px sans-serif'
    ctx.fillText(`Threshold=${threshold}`, w - pad.right - 80, thresholdY - 5)

    const rulEst = health > threshold ? (health - threshold) / 0.001 : 0
    const currentHour = Math.max(0, 1000 - rulEst)

    ctx.strokeStyle = '#1890ff'
    ctx.lineWidth = 2
    ctx.beginPath()
    for (let t = 0; t <= currentHour; t += 5) {
      const hv = Math.max(0, 1.0 - 0.001 * t)
      const x = scaleX(t), y = scaleY(hv)
      if (t === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
    }
    ctx.stroke()

    ctx.strokeStyle = '#52c41a'
    ctx.lineWidth = 1.5
    ctx.setLineDash([4, 3])
    ctx.beginPath()
    for (let t = currentHour; t <= 1000; t += 5) {
      const hv = Math.max(0, health - 0.001 * (t - currentHour))
      const x = scaleX(t), y = scaleY(hv)
      if (t === currentHour) ctx.moveTo(x, y); else ctx.lineTo(x, y)
    }
    ctx.stroke()
    ctx.setLineDash([])

    const cx = scaleX(currentHour), cy = scaleY(health)
    ctx.beginPath(); ctx.arc(cx, cy, 5, 0, Math.PI * 2)
    ctx.fillStyle = '#1890ff'; ctx.fill()

    ctx.fillStyle = '#333'; ctx.font = '11px sans-serif'; ctx.textAlign = 'center'
    ctx.fillText('Flight Hours', w / 2, h - 5)
    ctx.save(); ctx.translate(12, h / 2); ctx.rotate(-Math.PI / 2)
    ctx.fillText('Health', 0, 0); ctx.restore()
  }, [health, threshold])

  return <canvas ref={canvasRef} width={500} height={250} style={{ width: '100%', maxWidth: 500, border: '1px solid #e8e8e8', borderRadius: 4 }} />
}

export default function PredictiveTwinPage() {
  const { t } = useTranslation()

  const [aircraftSn, setAircraftSn] = useState('AC-001')
  const [component, setComponent] = useState('engine')

  const [rulData, setRulData] = useState<RULInfo | null>(null)
  const [failureData, setFailureData] = useState<FailureProbInfo | null>(null)
  const [maintenanceWindows, setMaintenanceWindows] = useState<MaintenanceWindowInfo[]>([])
  const [anomalies, setAnomalies] = useState<Array<Record<string, unknown>>>([])

  const [simStatus, setSimStatus] = useState<SimStatusInfo | null>(null)
  const [simResults, setSimResults] = useState<SimResultInfo[]>([])

  const [modelBuilt, setModelBuilt] = useState(false)
  const [simSetup, setSimSetup] = useState(false)

  const handleBuildModel = async () => {
    try {
      await apiClient.post('/twins/predictive/model', {
        aircraft_sn: aircraftSn,
        component: component,
        model_type: 'linear',
      })
      setModelBuilt(true)
      message.success(t('predictive.buildModelSuccess'))
    } catch {
      message.error(t('predictive.buildModelFailed'))
    }
  }

  const handlePredictRUL = async () => {
    try {
      const resp = await apiClient.get(`/twins/${aircraftSn}/rul`, { params: { component } })
      setRulData(resp.data?.data)
    } catch {
      message.error(t('predictive.rulFailed'))
    }
  }

  const handlePredictFailure = async () => {
    try {
      const resp = await apiClient.get(`/twins/${aircraftSn}/failure-probability`, { params: { component } })
      setFailureData(resp.data?.data)
    } catch {
      message.error(t('predictive.failureProbFailed'))
    }
  }

  const handleOptimizeMaintenance = async () => {
    try {
      const resp = await apiClient.post(`/${aircraftSn}/maintenance-optimization`, { aircraft_sn: aircraftSn })
      setMaintenanceWindows(resp.data?.data?.windows ?? [])
    } catch {
      message.error(t('predictive.maintenanceOptFailed'))
    }
  }

  const handleSetupSim = async () => {
    try {
      await apiClient.post('/twins/simulation/setup', { aircraft_sn: aircraftSn })
      setSimSetup(true)
      message.success(t('predictive.setupSimSuccess'))
    } catch {
      message.error(t('predictive.setupSimFailed'))
    }
  }

  const handleStartSim = async () => {
    try {
      await apiClient.post(`/twins/${aircraftSn}/simulation/start`)
      message.success(t('predictive.startSimSuccess'))
      loadSimStatus()
    } catch {
      message.error(t('predictive.startSimFailed'))
    }
  }

  const handleRunStep = async () => {
    try {
      const resp = await apiClient.post('/twins/simulation/step', {
        aircraft_sn: aircraftSn,
        current_state: {
          altitude_m: 1000 + Math.random() * 100,
          airspeed_ms: 50 + Math.random() * 5,
          heading_deg: 90 + Math.random() * 10,
          pitch_deg: 2 + Math.random(),
          engine_rpm: 3000,
          fuel_kg: 100,
        },
      })
      const newResult = resp.data?.data
      if (newResult) {
        setSimResults(prev => [...prev.slice(-19), newResult])
      }
    } catch {
      message.error(t('predictive.simStepFailed'))
    }
  }

  const handleCalibrate = async () => {
    try {
      await apiClient.post(`/twins/${aircraftSn}/simulation/calibrate`)
      message.success(t('predictive.calibrateSuccess'))
    } catch {
      message.error(t('predictive.calibrateFailed'))
    }
  }

  const loadSimStatus = async () => {
    try {
      const resp = await apiClient.get(`/twins/${aircraftSn}/simulation/status`)
      setSimStatus(resp.data?.data)
    } catch { /* ignore */ }
  }

  const maintenanceColumns = [
    { title: t('predictive.componentCol'), dataIndex: 'component', key: 'component', width: 100 },
    { title: t('predictive.recommendedDate'), dataIndex: 'recommended_date', key: 'recommended_date', width: 180, render: (v: string) => v ? new Date(v).toLocaleDateString() : '-' },
    { title: t('predictive.risk'), dataIndex: 'risk_if_deferred', key: 'risk_if_deferred', width: 80, render: (v: number) => <Text style={{ color: v > 0.5 ? '#cf1322' : v > 0.2 ? '#fa8c16' : '#3f8600' }}>{(v * 100).toFixed(1)}%</Text> },
    { title: t('predictive.cost'), dataIndex: 'cost_estimate', key: 'cost_estimate', width: 100, render: (v: number) => `¥${v?.toFixed(0)}` },
    { title: t('predictive.priorityCol'), dataIndex: 'priority', key: 'priority', width: 70, render: (v: number) => <Tag color={v >= 3 ? 'red' : v >= 2 ? 'orange' : 'green'}>P{v}</Tag> },
  ]

  const healthPct = rulData ? Math.round(rulData.current_health * 100) : 0

  const severityLabel = (s: string) => {
    if (s === 'emergency') return t('predictive.emergency')
    if (s === 'critical') return t('predictive.critical')
    if (s === 'warning') return t('predictive.warningLevel')
    return '-'
  }

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Text strong>{t('predictive.aircraftSN')}</Text>
          <Input value={aircraftSn} onChange={e => setAircraftSn(e.target.value)} style={{ width: 150 }} />
          <Text strong>{t('predictive.component')}</Text>
          <Select value={component} onChange={setComponent} style={{ width: 150 }}
            options={[
              { value: 'engine', label: t('predictive.engine') },
              { value: 'wing', label: t('predictive.wing') },
              { value: 'landing_gear', label: t('predictive.landingGear') },
              { value: 'avionics', label: t('predictive.avionics') },
            ]}
          />
          <Button type="primary" onClick={handleBuildModel}>{t('predictive.buildModel')}</Button>
        </Space>
      </Card>

      <Tabs
        defaultActiveKey="predictive"
        items={[
          {
            key: 'predictive',
            label: <span><SafetyCertificateOutlined /> {t('predictive.title')}</span>,
            children: (
              <div>
                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title={t('predictive.currentHealth')}
                        value={healthPct}
                        suffix="%"
                        valueStyle={{ color: healthPct >= 70 ? '#3f8600' : healthPct >= 40 ? '#fa8c16' : '#cf1322' }}
                        prefix={<DashboardOutlined />}
                      />
                      {rulData && <Progress percent={healthPct} strokeColor={healthPct >= 70 ? '#52c41a' : healthPct >= 40 ? '#fa8c16' : '#ff4d4f'} size="small" style={{ marginTop: 8 }} />}
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title={t('predictive.rul')}
                        value={rulData?.rul_hours ?? '-'}
                        suffix="h"
                        prefix={<FieldTimeOutlined />}
                      />
                      {rulData && <Text type="secondary" style={{ fontSize: 12 }}>{t('predictive.confidenceInterval')}: {rulData.confidence_lower?.toFixed(0)}h - {rulData.confidence_upper?.toFixed(0)}h</Text>}
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title={t('predictive.failureProb30d')}
                        value={failureData ? (failureData.probability_30d * 100).toFixed(1) : '-'}
                        suffix="%"
                        valueStyle={{ color: failureData && failureData.probability_30d > 0.1 ? '#cf1322' : '#3f8600' }}
                        prefix={<WarningOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title={t('predictive.alertLevel')}
                        value={failureData ? severityLabel(failureData.severity) : '-'}
                        valueStyle={{
                          color: failureData?.severity === 'emergency' ? '#cf1322' :
                            failureData?.severity === 'critical' ? '#fa8c16' : undefined,
                        }}
                      />
                    </Card>
                  </Col>
                </Row>

                <Space style={{ marginBottom: 16 }}>
                  <Button icon={<FieldTimeOutlined />} onClick={handlePredictRUL} disabled={!modelBuilt}>{t('predictive.predictRUL')}</Button>
                  <Button icon={<WarningOutlined />} onClick={handlePredictFailure} disabled={!modelBuilt}>{t('predictive.predictFailure')}</Button>
                  <Button icon={<SafetyCertificateOutlined />} onClick={handleOptimizeMaintenance} disabled={!modelBuilt}>{t('predictive.optimizeMaintenance')}</Button>
                </Space>

                {rulData && (
                  <Card title={t('predictive.degradationCurve')} style={{ marginBottom: 16 }}>
                    <DegradationCurveCanvas health={rulData.current_health} threshold={0.3} />
                  </Card>
                )}

                {failureData && (
                  <Card title={t('predictive.failureProbability')} style={{ marginBottom: 16 }}>
                    <Descriptions bordered column={3} size="small">
                      <Descriptions.Item label={t('predictive.days7')}>{(failureData.probability_7d * 100).toFixed(2)}%</Descriptions.Item>
                      <Descriptions.Item label={t('predictive.days30')}>{(failureData.probability_30d * 100).toFixed(2)}%</Descriptions.Item>
                      <Descriptions.Item label={t('predictive.days90')}>{(failureData.probability_90d * 100).toFixed(2)}%</Descriptions.Item>
                    </Descriptions>
                    {failureData.exceeds_threshold && (
                      <Alert type="error" message={t('predictive.failureExceedsThreshold')} description={t('predictive.failureExceedsDesc')} showIcon style={{ marginTop: 12 }} />
                    )}
                  </Card>
                )}

                {maintenanceWindows.length > 0 && (
                  <Card title={t('predictive.optimizedMaintenancePlan')}>
                    <Table columns={maintenanceColumns} dataSource={maintenanceWindows.map((w, i) => ({ ...w, key: i }))} size="small" pagination={false} />
                  </Card>
                )}
              </div>
            ),
          },
          {
            key: 'simulation',
            label: <span><ExperimentOutlined /> {t('predictive.simulation')}</span>,
            children: (
              <div>
                <Space style={{ marginBottom: 16 }}>
                  <Button onClick={handleSetupSim}>{t('predictive.setupSim')}</Button>
                  <Button type="primary" onClick={handleStartSim} disabled={!simSetup}>{t('predictive.startSim')}</Button>
                  <Button icon={<ThunderboltOutlined />} onClick={handleRunStep} disabled={!simSetup}>{t('predictive.singleStep')}</Button>
                  <Button onClick={handleCalibrate} disabled={!simSetup}>{t('predictive.calibrate')}</Button>
                </Space>

                {simStatus && (
                  <Row gutter={16} style={{ marginBottom: 16 }}>
                    <Col span={6}>
                      <Card>
                        <Statistic title={t('predictive.simStatus')} value={simStatus.status === 'running' ? t('status.running') : simStatus.status} />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic title={t('predictive.simSteps')} value={simStatus.step_count} />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic title={t('predictive.calibrationCount')} value={simStatus.model_calibrations} />
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card>
                        <Statistic
                          title={t('predictive.accumulatedDeviation')}
                          value={simStatus.accumulated_deviation}
                          precision={4}
                          valueStyle={{ color: simStatus.accumulated_deviation > 1.0 ? '#cf1322' : '#3f8600' }}
                        />
                      </Card>
                    </Col>
                  </Row>
                )}

                {simResults.length > 0 && (
                  <Card title={t('predictive.simResults')}>
                    <Table
                      columns={[
                        { title: t('predictive.stepNumber'), dataIndex: 'step_number', key: 'step', width: 60 },
                        {
                          title: t('predictive.altitude'),
                          key: 'alt',
                          width: 80,
                          render: (_: unknown, r: SimResultInfo) => r.predicted_state?.altitude_m?.toFixed(1),
                        },
                        {
                          title: t('predictive.speed'),
                          key: 'spd',
                          width: 80,
                          render: (_: unknown, r: SimResultInfo) => r.predicted_state?.airspeed_ms?.toFixed(1),
                        },
                        {
                          title: t('predictive.deviationExceeds'),
                          key: 'dev',
                          width: 80,
                          render: (_: unknown, r: SimResultInfo) => r.deviation_exceeds_threshold ? <Tag color="red">{t('common.yes')}</Tag> : <Tag color="green">{t('common.no')}</Tag>,
                        },
                      ]}
                      dataSource={simResults.map((r, i) => ({ ...r, key: i }))}
                      size="small"
                      pagination={{ pageSize: 10 }}
                    />
                  </Card>
                )}

                {!simSetup && (
                  <Card>
                    <Empty description={t('predictive.setupSimFirst')} />
                  </Card>
                )}
              </div>
            ),
          },
        ]}
      />
    </div>
  )
}
