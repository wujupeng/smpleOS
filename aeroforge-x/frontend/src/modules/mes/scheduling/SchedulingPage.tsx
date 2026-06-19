import { useState, useEffect, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Card, Typography, Space, Tag, Button, Table, Modal, Form,
  Input, Select, InputNumber, message, Row, Col, Statistic,
  Descriptions, Tabs, Empty, Alert,
} from 'antd'
import {
  ScheduleOutlined, PlusOutlined, ThunderboltOutlined,
  WarningOutlined, CheckCircleOutlined, BarChartOutlined,
} from '@ant-design/icons'
import apiClient from '../../../services/apiClient'
import { useProjectStore } from '../../../stores/projectStore'

const { Text } = Typography

interface ScheduleInfo {
  id: string
  name: string
  status: string
  objective_function: string
  makespan_hours: number
  total_cost: number
  work_orders: WorkOrderInfo[]
  resources: ResourceInfo[]
  constraints: ConstraintInfo[]
  gantt_data: GanttItem[]
  resource_utilization: Record<string, number>
  conflicts: ConflictInfo[]
}

interface WorkOrderInfo {
  work_order_id: string
  work_order_code: string
  priority: number
  due_date: string
  operations: OperationInfo[]
}

interface OperationInfo {
  operation_name: string
  workstation: string
  duration_hours: number
  start_time: number
  end_time: number
}

interface ResourceInfo {
  resource_id: string
  resource_name: string
  resource_type: string
  capacity: number
  skills: string[]
}

interface ConstraintInfo {
  constraint_type: string
  constraint_expression: string
  priority: string
  description: string
}

interface GanttItem {
  work_order_id: string
  work_order_code: string
  operation_name: string
  workstation: string
  start_time: number
  end_time: number
  duration_hours: number
  is_critical: boolean
}

interface ConflictInfo {
  type: string
  description: string
}

function GanttCanvas({ ganttData, resources }: { ganttData: GanttItem[]; resources: ResourceInfo[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const { t } = useTranslation()

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || !ganttData?.length) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const width = canvas.width
    const height = canvas.height
    const padding = { top: 30, right: 20, bottom: 40, left: 120 }

    ctx.clearRect(0, 0, width, height)
    ctx.fillStyle = '#fafafa'
    ctx.fillRect(0, 0, width, height)

    const workstations = [...new Set(ganttData.map(g => g.workstation))]
    const maxTime = Math.max(...ganttData.map(g => g.end_time), 1)

    const plotW = width - padding.left - padding.right
    const plotH = height - padding.top - padding.bottom
    const rowH = Math.min(40, plotH / Math.max(workstations.length, 1))

    const scaleX = (t: number) => padding.left + (t / maxTime) * plotW

    ctx.strokeStyle = '#e8e8e8'
    ctx.lineWidth = 1
    for (let i = 0; i <= 5; i++) {
      const x = padding.left + (i / 5) * plotW
      ctx.beginPath()
      ctx.moveTo(x, padding.top)
      ctx.lineTo(x, height - padding.bottom)
      ctx.stroke()

      ctx.fillStyle = '#666'
      ctx.font = '10px monospace'
      ctx.textAlign = 'center'
      ctx.fillText(`${Math.round((i / 5) * maxTime)}h`, x, height - padding.bottom + 15)
    }

    workstations.forEach((ws, idx) => {
      const y = padding.top + idx * rowH

      ctx.fillStyle = '#f5f5f5'
      ctx.fillRect(padding.left, y, plotW, rowH - 2)

      ctx.fillStyle = '#333'
      ctx.font = '11px sans-serif'
      ctx.textAlign = 'right'
      ctx.fillText(ws, padding.left - 8, y + rowH / 2 + 4)

      ctx.strokeStyle = '#e8e8e8'
      ctx.beginPath()
      ctx.moveTo(padding.left, y + rowH - 2)
      ctx.lineTo(width - padding.right, y + rowH - 2)
      ctx.stroke()
    })

    const colors = ['#1890ff', '#52c41a', '#fa8c16', '#722ed1', '#13c2c2', '#eb2f96']
    const woColors: Record<string, string> = {}
    let colorIdx = 0

    ganttData.forEach(g => {
      if (!woColors[g.work_order_code]) {
        woColors[g.work_order_code] = colors[colorIdx % colors.length]
        colorIdx++
      }

      const wsIdx = workstations.indexOf(g.workstation)
      if (wsIdx === -1) return

      const x = scaleX(g.start_time)
      const endX = scaleX(g.end_time)
      const y = padding.top + wsIdx * rowH + 4
      const barH = rowH - 10

      ctx.fillStyle = g.is_critical ? '#ff4d4f' : woColors[g.work_order_code]
      ctx.globalAlpha = 0.85
      ctx.beginPath()
      ctx.roundRect(x, y, endX - x, barH, 3)
      ctx.fill()
      ctx.globalAlpha = 1.0

      ctx.strokeStyle = g.is_critical ? '#cf1322' : 'rgba(0,0,0,0.15)'
      ctx.lineWidth = g.is_critical ? 2 : 1
      ctx.beginPath()
      ctx.roundRect(x, y, endX - x, barH, 3)
      ctx.stroke()

      if (endX - x > 40) {
        ctx.fillStyle = '#fff'
        ctx.font = '10px sans-serif'
        ctx.textAlign = 'left'
        ctx.fillText(g.operation_name, x + 4, y + barH / 2 + 3)
      }
    })

    ctx.fillStyle = '#333'
    ctx.font = '11px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(t('scheduling.timeHours'), width / 2, height - 5)
  }, [ganttData, resources, t])

  if (!ganttData?.length) {
    return <Empty description={t('scheduling.noGanttData')} />
  }

  return (
    <canvas
      ref={canvasRef}
      width={900}
      height={350}
      style={{ width: '100%', maxWidth: 900, border: '1px solid #e8e8e8', borderRadius: 4 }}
    />
  )
}

export default function SchedulingPage() {
  const { t } = useTranslation()
  const { currentProjectId } = useProjectStore()

  const objectiveLabels: Record<string, string> = {
    min_makespan: t('scheduling.minMakespan'),
    min_cost: t('scheduling.minCost'),
    max_resource_util: t('scheduling.maxResourceUtil'),
  }

  const statusConfig: Record<string, { color: string; label: string }> = {
    draft: { color: 'default', label: t('status.draft') },
    optimized: { color: 'processing', label: t('status.optimized') },
    confirmed: { color: 'green', label: t('status.confirmed') },
    executing: { color: 'blue', label: t('status.executing') },
  }

  const [schedules, setSchedules] = useState<ScheduleInfo[]>([])
  const [selectedSchedule, setSelectedSchedule] = useState<ScheduleInfo | null>(null)
  const [loading, setLoading] = useState(false)

  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [woModalOpen, setWoModalOpen] = useState(false)
  const [scheduleForm] = Form.useForm()
  const [woForm] = Form.useForm()

  const loadSchedules = useCallback(async () => {
    try {
      const resp = await apiClient.get('/mes/schedules')
      setSchedules(resp.data?.data?.schedules ?? [])
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    loadSchedules()
  }, [loadSchedules])

  const loadScheduleDetail = async (scheduleId: string) => {
    setLoading(true)
    try {
      const resp = await apiClient.get(`/mes/schedules/${scheduleId}`)
      setSelectedSchedule(resp.data?.data)
    } catch {
      message.error(t('scheduling.loadScheduleFailed'))
    } finally {
      setLoading(false)
    }
  }

  const handleCreateSchedule = async (values: Record<string, unknown>) => {
    try {
      await apiClient.post('/mes/schedules', {
        ...values,
        tenant_id: currentProjectId || 'default',
        project_id: currentProjectId || 'default',
      })
      message.success(t('scheduling.createScheduleSuccess'))
      setCreateModalOpen(false)
      scheduleForm.resetFields()
      loadSchedules()
    } catch {
      message.error(t('common.error'))
    }
  }

  const handleOptimize = async () => {
    if (!selectedSchedule) return
    try {
      const resp = await apiClient.post(`/mes/schedules/${selectedSchedule.id}/optimize`)
      setSelectedSchedule(resp.data?.data)
      message.success(t('scheduling.optimizeSuccess'))
    } catch {
      message.error(t('common.error'))
    }
  }

  const handleAddWorkOrder = async (values: Record<string, unknown>) => {
    if (!selectedSchedule) return
    try {
      const opsStr = String(values.operations || '')
      let operations = []
      if (opsStr) {
        try {
          operations = JSON.parse(opsStr)
        } catch {
          message.error(t('scheduling.invalidOpsFormat'))
          return
        }
      }
      await apiClient.post(`/mes/schedules/${selectedSchedule.id}/work-orders`, {
        ...values,
        operations,
      })
      message.success(t('scheduling.addWoSuccess'))
      setWoModalOpen(false)
      woForm.resetFields()
      loadScheduleDetail(selectedSchedule.id)
    } catch {
      message.error(t('common.error'))
    }
  }

  const scheduleColumns = [
    { title: t('common.name'), dataIndex: 'name', key: 'name', width: 150 },
    {
      title: t('common.status'),
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (v: string) => {
        const cfg = statusConfig[v] || { color: 'default', label: v }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: t('scheduling.objectiveFunction'),
      dataIndex: 'objective_function',
      key: 'objective_function',
      width: 130,
      render: (v: string) => objectiveLabels[v] || v,
    },
    {
      title: t('scheduling.makespan'),
      dataIndex: 'makespan_hours',
      key: 'makespan_hours',
      width: 100,
      render: (v: number) => v > 0 ? `${v}h` : '-',
    },
    {
      title: t('scheduling.woCount'),
      key: 'wo_count',
      width: 80,
      render: (_: unknown, record: ScheduleInfo) => record.work_orders?.length ?? 0,
    },
    {
      title: t('common.actions'),
      key: 'actions',
      width: 80,
      render: (_: unknown, record: ScheduleInfo) => (
        <Button size="small" type="link" onClick={() => loadScheduleDetail(record.id)}>
          {t('common.view')}
        </Button>
      ),
    },
  ]

  const conflictColumns = [
    {
      title: t('common.status'),
      dataIndex: 'type',
      key: 'type',
      width: 120,
      render: (v: string) => v === 'resource_conflict' ? <Tag color="orange">{t('scheduling.resourceConflict')}</Tag> : <Tag color="red">{t('scheduling.dueDateConflict')}</Tag>,
    },
    { title: t('common.description'), dataIndex: 'description', key: 'description' },
  ]

  const avgUtil = selectedSchedule?.resource_utilization
    ? Object.values(selectedSchedule.resource_utilization).reduce((a: number, b: number) => a + b, 0) / Object.keys(selectedSchedule.resource_utilization).length
    : 0

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title={t('scheduling.scheduleCount')} value={schedules.length} prefix={<ScheduleOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('scheduling.makespan')} value={selectedSchedule?.makespan_hours ?? 0} suffix="h" prefix={<BarChartOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('scheduling.resourceUtilization')}
              value={avgUtil}
              suffix="%"
              precision={1}
              valueStyle={{ color: avgUtil >= 70 ? '#3f8600' : avgUtil >= 40 ? '#fa8c16' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('scheduling.conflictCount')}
              value={selectedSchedule?.conflicts?.length ?? 0}
              prefix={<WarningOutlined />}
              valueStyle={{ color: (selectedSchedule?.conflicts?.length ?? 0) > 0 ? '#cf1322' : '#3f8600' }}
            />
          </Card>
        </Col>
      </Row>

      <Tabs
        defaultActiveKey="list"
        items={[
          {
            key: 'list',
            label: <span><ScheduleOutlined /> {t('scheduling.scheduleList')}</span>,
            children: (
              <Card
                title={t('scheduling.productionSchedule')}
                extra={
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
                    {t('scheduling.createSchedule')}
                  </Button>
                }
              >
                <Table
                  columns={scheduleColumns}
                  dataSource={schedules.map(s => ({ ...s, key: s.id }))}
                  size="small"
                  pagination={{ pageSize: 10 }}
                />
              </Card>
            ),
          },
          {
            key: 'detail',
            label: <span><BarChartOutlined /> {t('scheduling.scheduleList')}</span>,
            children: (
              <div>
                {!selectedSchedule ? (
                  <Card><Empty description={t('scheduling.selectSchedule')} /></Card>
                ) : (
                  <>
                    <Card
                      title={selectedSchedule.name}
                      extra={
                        <Space>
                          <Button icon={<PlusOutlined />} onClick={() => setWoModalOpen(true)}>
                            {t('scheduling.addWorkOrder')}
                          </Button>
                          <Button
                            type="primary"
                            icon={<ThunderboltOutlined />}
                            onClick={handleOptimize}
                            disabled={selectedSchedule.status === 'optimized'}
                          >
                            {t('scheduling.optimize')}
                          </Button>
                        </Space>
                      }
                      style={{ marginBottom: 16 }}
                    >
                      <Descriptions bordered column={3} size="small">
                        <Descriptions.Item label={t('common.status')}>
                          <Tag color={statusConfig[selectedSchedule.status]?.color}>
                            {statusConfig[selectedSchedule.status]?.label}
                          </Tag>
                        </Descriptions.Item>
                        <Descriptions.Item label={t('scheduling.objectiveFunction')}>
                          {objectiveLabels[selectedSchedule.objective_function] || selectedSchedule.objective_function}
                        </Descriptions.Item>
                        <Descriptions.Item label={t('scheduling.totalCost')}>
                          ¥{selectedSchedule.total_cost?.toFixed(2) || '0.00'}
                        </Descriptions.Item>
                      </Descriptions>
                    </Card>

                    <Card title={t('scheduling.ganttChart')} style={{ marginBottom: 16 }}>
                      <GanttCanvas
                        ganttData={selectedSchedule.gantt_data || []}
                        resources={selectedSchedule.resources || []}
                      />
                    </Card>

                    {selectedSchedule.resource_utilization &&
                      Object.keys(selectedSchedule.resource_utilization).length > 0 && (
                      <Card title={t('scheduling.resourceUtilization')} style={{ marginBottom: 16 }}>
                        <Row gutter={16}>
                          {Object.entries(selectedSchedule.resource_utilization).map(([rid, util]) => (
                            <Col span={6} key={rid}>
                              <Statistic
                                title={rid}
                                value={util}
                                suffix="%"
                                precision={1}
                                valueStyle={{ color: util >= 70 ? '#3f8600' : util >= 40 ? '#fa8c16' : '#cf1322' }}
                              />
                            </Col>
                          ))}
                        </Row>
                      </Card>
                    )}

                    {selectedSchedule.conflicts?.length > 0 && (
                      <Card title={t('scheduling.conflictDetection')} style={{ marginBottom: 16 }}>
                        <Alert
                          type="warning"
                          message={t('scheduling.conflictAlert', { count: selectedSchedule.conflicts.length })}
                          style={{ marginBottom: 12 }}
                          showIcon
                        />
                        <Table
                          columns={conflictColumns}
                          dataSource={selectedSchedule.conflicts.map((c, i) => ({ ...c, key: i }))}
                          size="small"
                          pagination={false}
                        />
                      </Card>
                    )}
                  </>
                )}
              </div>
            ),
          },
        ]}
      />

      <Modal
        title={t('scheduling.createSchedule')}
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        onOk={() => scheduleForm.submit()}
      >
        <Form form={scheduleForm} layout="vertical" onFinish={handleCreateSchedule}>
          <Form.Item name="name" label={t('scheduling.scheduleName')} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="objective_function" label={t('scheduling.objectiveFunction')} initialValue="min_makespan">
            <Select options={Object.entries(objectiveLabels).map(([k, v]) => ({ value: k, label: v }))} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={t('scheduling.addWorkOrder')}
        open={woModalOpen}
        onCancel={() => setWoModalOpen(false)}
        onOk={() => woForm.submit()}
        width={600}
      >
        <Form form={woForm} layout="vertical" onFinish={handleAddWorkOrder}>
          <Form.Item name="work_order_id" label={t('scheduling.workOrderId')} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="work_order_code" label={t('scheduling.workOrderCode')}>
            <Input />
          </Form.Item>
          <Form.Item name="priority" label={t('scheduling.priority')} initialValue={0}>
            <InputNumber min={0} max={10} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="due_date" label={t('scheduling.dueDate')}>
            <Input placeholder="YYYY-MM-DD" />
          </Form.Item>
          <Form.Item name="operations" label={t('scheduling.operations')}>
            <Input.TextArea
              rows={4}
              placeholder='[{"operation_name":"CNC","workstation":"WS-01","duration_hours":4.0}]'
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
