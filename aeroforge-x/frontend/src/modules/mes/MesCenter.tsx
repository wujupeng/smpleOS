import { useState, useEffect } from 'react'
import { Typography, Card, Table, Button, Modal, Form, Input, InputNumber, Select, Tag, Space, Descriptions, Progress, message, Tabs } from 'antd'
import { ToolOutlined, PlusOutlined, SendOutlined } from '@ant-design/icons'
import apiClient from '../../services/apiClient'
import ProcessRoutePage from './ProcessRoutePage'

const { Title } = Typography

interface WorkOrder {
  id: string
  order_code: string
  product_model: string
  quantity: number
  priority: string
  status: string
  station_id: string | null
  progress_percent: number
  created_at: string
}

interface Station {
  id: string
  name: string
  equipment: string
  status: string
  current_task: string | null
  estimated_idle_minutes: number
}

const statusColorMap: Record<string, string> = {
  created: 'default', dispatched: 'processing', in_progress: 'blue', completed: 'success', closed: 'default',
}

export default function MesCenter() {
  const [orders, setOrders] = useState<WorkOrder[]>([])
  const [stations, setStations] = useState<Station[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [createOpen, setCreateOpen] = useState(false)
  const [dispatchOpen, setDispatchOpen] = useState(false)
  const [selectedOrder, setSelectedOrder] = useState<WorkOrder | null>(null)
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()

  const fetchOrders = async () => {
    try {
      const res = await apiClient.get('/api/v1/mes/orders', { params: { page, page_size: 20 } })
      setOrders(res.data.data || [])
      setTotal(res.data.total || 0)
    } catch { /* ignore */ }
  }

  const fetchStations = async () => {
    try {
      const res = await apiClient.get('/api/v1/mes/stations')
      setStations(res.data.data || [])
    } catch { /* ignore */ }
  }

  useEffect(() => { fetchOrders(); fetchStations() }, [page])

  const handleCreate = async (values: { product_model: string; quantity: number; priority: string }) => {
    try {
      await apiClient.post('/api/v1/mes/orders', values)
      message.success('工单已创建')
      setCreateOpen(false)
      form.resetFields()
      fetchOrders()
    } catch { message.error('创建失败') }
  }

  const handleDispatch = async (stationId: string) => {
    if (!selectedOrder) return
    try {
      await apiClient.post(`/api/v1/mes/orders/${selectedOrder.id}/dispatch`, { station_id: stationId, material_available: true })
      message.success('工单已派发')
      setDispatchOpen(false)
      setSelectedOrder(null)
      fetchOrders()
      fetchStations()
    } catch (err: any) { message.error(err.response?.data?.message || '派发失败') }
  }

  const handleStatusUpdate = async (orderId: string, action: string) => {
    try {
      await apiClient.put(`/api/v1/mes/orders/${orderId}/status`, { action })
      message.success('状态已更新')
      fetchOrders()
    } catch { message.error('更新失败') }
  }

  const orderColumns = [
    { title: '工单编号', dataIndex: 'order_code', key: 'order_code' },
    { title: '产品型号', dataIndex: 'product_model', key: 'product_model' },
    { title: '数量', dataIndex: 'quantity', key: 'quantity' },
    { title: '优先级', dataIndex: 'priority', key: 'priority', render: (v: string) => <Tag color={v === 'urgent' ? 'red' : v === 'high' ? 'orange' : 'default'}>{v}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={statusColorMap[v]}>{v}</Tag> },
    { title: '进度', dataIndex: 'progress_percent', key: 'progress', render: (v: number) => <Progress percent={v} size="small" /> },
    {
      title: '操作', key: 'action',
      render: (_: unknown, record: WorkOrder) => (
        <Space>
          {record.status === 'created' && <Button size="small" icon={<SendOutlined />} onClick={() => { setSelectedOrder(record); setDispatchOpen(true) }}>派发</Button>}
          {record.status === 'dispatched' && <Button size="small" type="primary" onClick={() => handleStatusUpdate(record.id, 'start')}>开始</Button>}
          {record.status === 'in_progress' && <Button size="small" onClick={() => handleStatusUpdate(record.id, 'complete')}>完工</Button>}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Title level={3}><ToolOutlined /> MES 制造执行</Title>
      <Tabs
        defaultActiveKey="workorders"
        items={[
          {
            key: 'workorders',
            label: '工单管理',
            children: (
              <>
                <Card title="工位看板" style={{ marginBottom: 16 }}>
                  <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                    {stations.map(s => (
                      <Card key={s.id} size="small" style={{ width: 180, borderLeft: `3px solid ${s.status === 'idle' ? '#52c41a' : '#faad14'}` }}>
                        <Descriptions column={1} size="small">
                          <Descriptions.Item label="工位">{s.name}</Descriptions.Item>
                          <Descriptions.Item label="设备">{s.equipment || '-'}</Descriptions.Item>
                          <Descriptions.Item label="状态"><Tag color={s.status === 'idle' ? 'success' : 'warning'}>{s.status}</Tag></Descriptions.Item>
                          <Descriptions.Item label="当前任务">{s.current_task || '-'}</Descriptions.Item>
                        </Descriptions>
                      </Card>
                    ))}
                  </div>
                </Card>

                <Card title="工单管理" extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>创建工单</Button>}>
                  <Table dataSource={orders} columns={orderColumns} rowKey="id" pagination={{ current: page, total, pageSize: 20, onChange: setPage }} size="small" />
                </Card>
              </>
            ),
          },
          {
            key: 'process-routes',
            label: '工艺路线',
            children: <ProcessRoutePage />,
          },
        ]}
      />

      <Modal title="创建工单" open={createOpen} onCancel={() => setCreateOpen(false)} footer={null}>
        <Form form={form} onFinish={handleCreate} layout="vertical">
          <Form.Item name="product_model" label="产品型号" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="quantity" label="数量" initialValue={1}><InputNumber min={1} style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="priority" label="优先级" initialValue="normal">
            <Select options={[{ value: 'low', label: '低' }, { value: 'normal', label: '普通' }, { value: 'high', label: '高' }, { value: 'urgent', label: '紧急' }]} />
          </Form.Item>
          <Form.Item><Button type="primary" htmlType="submit">创建</Button></Form.Item>
        </Form>
      </Modal>

      <Modal title="派发工单" open={dispatchOpen} onCancel={() => { setDispatchOpen(false); setSelectedOrder(null) }} footer={null}>
        {selectedOrder && (
          <div>
            <p>工单: {selectedOrder.order_code}</p>
            <Title level={5}>选择工位</Title>
            <Space direction="vertical" style={{ width: '100%' }}>
              {stations.filter(s => s.status === 'idle').map(s => (
                <Card key={s.id} size="small" hoverable onClick={() => handleDispatch(s.id)}>
                  <span>{s.name} - {s.equipment}</span>
                </Card>
              ))}
              {stations.filter(s => s.status === 'idle').length === 0 && <p style={{ color: '#999' }}>暂无空闲工位</p>}
            </Space>
          </div>
        )}
      </Modal>
    </div>
  )
}
