import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Card, Typography, Space, Tag, Button, Table, Modal, Form,
  Input, Select, InputNumber, message, Row, Col, Statistic,
  Descriptions, Tabs, Empty, Alert, Badge,
} from 'antd'
import {
  ShopOutlined, ShoppingCartOutlined, InboxOutlined,
  PlusOutlined, CheckCircleOutlined, WarningOutlined,
  SearchOutlined,
} from '@ant-design/icons'
import apiClient from '../../services/apiClient'
import { useProjectStore } from '../../stores/projectStore'

const { Title, Text } = Typography

interface SupplierInfo {
  id: string
  name: string
  code: string
  category: string
  qualification_status: string
  performance_metrics: {
    on_time_delivery_rate: number
    quality_pass_rate: number
    avg_response_time_days: number
    overall_score: number
  }
  certifications: Array<{ name: string; certificate_number: string }>
  supplied_materials: string[]
  lead_time_days: number
  min_order_quantity: number
  contact_info: { contact_person: string; email: string; phone: string }
}

interface OrderInfo {
  id: string
  order_code: string
  supplier_id: string
  supplier_name: string
  status: string
  order_items: Array<{
    material_code: string
    material_name: string
    quantity: number
    unit_price: number
    received_quantity: number
  }>
  total_amount: number
  currency: string
  iqc_required: boolean
  iqc_status: string
  created_at: string
}

interface InventoryInfo {
  id: string
  item_code: string
  item_name: string
  warehouse_location: string
  quantity_on_hand: number
  quantity_reserved: number
  quantity_available: number
  reorder_point: number
  safety_stock: number
  unit_cost: number
  is_below_reorder: boolean
  is_below_safety: boolean
}

interface ReorderAdviceInfo {
  item_code: string
  item_name: string
  current_available: number
  reorder_point: number
  safety_stock: number
  suggested_quantity: number
  reason: string
}

export default function SupplyChainPage() {
  const { t } = useTranslation()
  const { currentProjectId } = useProjectStore()

  const categoryLabels: Record<string, string> = {
    raw_material: t('supply.rawMaterial'),
    standard_part: t('supply.standardPart'),
    custom_part: t('supply.customPart'),
    equipment: t('supply.equipment'),
  }

  const qualStatusConfig: Record<string, { color: string; label: string }> = {
    qualified: { color: 'green', label: t('status.qualified') },
    conditional: { color: 'orange', label: t('status.conditional') },
    disqualified: { color: 'red', label: t('status.disqualified') },
  }

  const orderStatusConfig: Record<string, { color: string; label: string }> = {
    draft: { color: 'default', label: t('status.draft') },
    submitted: { color: 'processing', label: t('status.submitted') },
    confirmed: { color: 'blue', label: t('status.confirmed') },
    in_transit: { color: 'cyan', label: t('status.inTransit') },
    received: { color: 'green', label: t('status.received') },
    closed: { color: 'default', label: t('status.closed') },
  }

  const [suppliers, setSuppliers] = useState<SupplierInfo[]>([])
  const [orders, setOrders] = useState<OrderInfo[]>([])
  const [inventory, setInventory] = useState<InventoryInfo[]>([])
  const [reorderAdvice, setReorderAdvice] = useState<ReorderAdviceInfo[]>([])
  const [loading, setLoading] = useState(false)

  const [createSupplierModalOpen, setCreateSupplierModalOpen] = useState(false)
  const [createOrderModalOpen, setCreateOrderModalOpen] = useState(false)
  const [supplierForm] = Form.useForm()
  const [orderForm] = Form.useForm()

  const loadSuppliers = useCallback(async () => {
    try {
      const resp = await apiClient.get('/supply/suppliers')
      setSuppliers(resp.data?.data?.suppliers ?? [])
    } catch { /* ignore */ }
  }, [])

  const loadOrders = useCallback(async () => {
    try {
      const resp = await apiClient.get('/supply/orders')
      setOrders(resp.data?.data?.orders ?? [])
    } catch { /* ignore */ }
  }, [])

  const loadInventory = useCallback(async () => {
    try {
      const resp = await apiClient.get('/supply/inventory')
      setInventory(resp.data?.data?.items ?? [])
    } catch { /* ignore */ }
  }, [])

  const loadReorderAdvice = useCallback(async () => {
    try {
      const resp = await apiClient.get('/supply/inventory/reorder-advice')
      setReorderAdvice(resp.data?.data?.advice ?? [])
    } catch { /* ignore */ }
  }, [])

  const loadAll = useCallback(async () => {
    setLoading(true)
    await Promise.all([loadSuppliers(), loadOrders(), loadInventory(), loadReorderAdvice()])
    setLoading(false)
  }, [loadSuppliers, loadOrders, loadInventory, loadReorderAdvice])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  const handleCreateSupplier = async (values: Record<string, unknown>) => {
    try {
      await apiClient.post('/supply/suppliers', {
        ...values,
        tenant_id: currentProjectId || 'default',
      })
      message.success(t('supply.createSupplierSuccess'))
      setCreateSupplierModalOpen(false)
      supplierForm.resetFields()
      loadSuppliers()
    } catch {
      message.error(t('common.error'))
    }
  }

  const handleQualify = async (supplierId: string) => {
    try {
      await apiClient.post(`/supply/suppliers/${supplierId}/qualify`)
      message.success(t('supply.qualifySuccess'))
      loadSuppliers()
    } catch {
      message.error(t('common.error'))
    }
  }

  const handleCreateOrder = async (values: Record<string, unknown>) => {
    try {
      await apiClient.post('/supply/orders', {
        ...values,
        tenant_id: currentProjectId || 'default',
        order_items: values.order_items || [{ material_code: 'AL-6061', quantity: 100, unit_price: 50 }],
      })
      message.success(t('supply.createOrderSuccess'))
      setCreateOrderModalOpen(false)
      orderForm.resetFields()
      loadOrders()
    } catch {
      message.error(t('common.error'))
    }
  }

  const handleSubmitOrder = async (orderId: string) => {
    try {
      await apiClient.post(`/supply/orders/${orderId}/submit`)
      message.success(t('supply.submitOrderSuccess'))
      loadOrders()
    } catch {
      message.error(t('common.error'))
    }
  }

  const handleReceiveGoods = async (orderId: string) => {
    try {
      await apiClient.post(`/supply/orders/${orderId}/receive`)
      message.success(t('supply.receiveSuccess'))
      loadOrders()
      loadInventory()
    } catch {
      message.error(t('common.error'))
    }
  }

  const supplierColumns = [
    { title: t('common.code'), dataIndex: 'code', key: 'code', width: 100 },
    { title: t('common.name'), dataIndex: 'name', key: 'name', width: 150 },
    {
      title: t('supply.category'),
      dataIndex: 'category',
      key: 'category',
      width: 80,
      render: (v: string) => categoryLabels[v] || v,
    },
    {
      title: t('supply.qualStatus'),
      dataIndex: 'qualification_status',
      key: 'qualification_status',
      width: 90,
      render: (v: string) => {
        const cfg = qualStatusConfig[v] || { color: 'default', label: v }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: t('supply.performanceScore'),
      key: 'score',
      width: 90,
      render: (_: unknown, record: SupplierInfo) => (
        <Text strong style={{ color: (record.performance_metrics?.overall_score ?? 0) >= 0.8 ? '#3f8600' : '#cf1322' }}>
          {((record.performance_metrics?.overall_score ?? 0) * 100).toFixed(0)}
        </Text>
      ),
    },
    {
      title: t('supply.leadTimeDays'),
      dataIndex: 'lead_time_days',
      key: 'lead_time_days',
      width: 80,
    },
    {
      title: t('supply.suppliedMaterials'),
      dataIndex: 'supplied_materials',
      key: 'supplied_materials',
      render: (v: string[]) => v?.map(m => <Tag key={m}>{m}</Tag>),
    },
    {
      title: t('common.actions'),
      key: 'actions',
      width: 100,
      render: (_: unknown, record: SupplierInfo) => (
        record.qualification_status !== 'qualified' ? (
          <Button size="small" type="link" onClick={() => handleQualify(record.id)}>
            {t('supply.qualify')}
          </Button>
        ) : null
      ),
    },
  ]

  const orderColumns = [
    { title: t('supply.orderCode'), dataIndex: 'order_code', key: 'order_code', width: 120 },
    { title: t('supply.supplierName'), dataIndex: 'supplier_name', key: 'supplier_name', width: 120 },
    {
      title: t('common.status'),
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (v: string) => {
        const cfg = orderStatusConfig[v] || { color: 'default', label: v }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: t('supply.amount'),
      dataIndex: 'total_amount',
      key: 'total_amount',
      width: 100,
      render: (v: number, record: OrderInfo) => `${v?.toFixed(2)} ${record.currency}`,
    },
    {
      title: t('supply.iqc'),
      key: 'iqc',
      width: 80,
      render: (_: unknown, record: OrderInfo) => {
        if (!record.iqc_required) return <Tag>{t('supply.iqcNotRequired')}</Tag>
        if (record.iqc_status === 'pending') return <Tag color="orange">{t('supply.iqcPending')}</Tag>
        return <Tag color="green">{t('supply.iqcPassed')}</Tag>
      },
    },
    {
      title: t('common.actions'),
      key: 'actions',
      width: 140,
      render: (_: unknown, record: OrderInfo) => (
        <Space>
          {record.status === 'draft' && (
            <Button size="small" type="primary" onClick={() => handleSubmitOrder(record.id)}>{t('common.submit')}</Button>
          )}
          {record.status === 'in_transit' && (
            <Button size="small" type="primary" onClick={() => handleReceiveGoods(record.id)}>{t('common.receive')}</Button>
          )}
        </Space>
      ),
    },
  ]

  const inventoryColumns = [
    { title: t('supply.itemCode'), dataIndex: 'item_code', key: 'item_code', width: 120 },
    { title: t('supply.itemName'), dataIndex: 'item_name', key: 'item_name', width: 150 },
    { title: t('supply.warehouse'), dataIndex: 'warehouse_location', key: 'warehouse_location', width: 100 },
    {
      title: t('supply.onHand'),
      dataIndex: 'quantity_on_hand',
      key: 'quantity_on_hand',
      width: 70,
    },
    {
      title: t('supply.reserved'),
      dataIndex: 'quantity_reserved',
      key: 'quantity_reserved',
      width: 70,
    },
    {
      title: t('supply.available'),
      dataIndex: 'quantity_available',
      key: 'quantity_available',
      width: 70,
      render: (v: number, record: InventoryInfo) => (
        <Text style={{ color: record.is_below_safety ? '#cf1322' : record.is_below_reorder ? '#fa8c16' : undefined }}>
          {v}
        </Text>
      ),
    },
    {
      title: t('supply.reorderPoint'),
      dataIndex: 'reorder_point',
      key: 'reorder_point',
      width: 90,
    },
    {
      title: t('supply.safetyStock'),
      dataIndex: 'safety_stock',
      key: 'safety_stock',
      width: 80,
    },
    {
      title: t('common.status'),
      key: 'status',
      width: 80,
      render: (_: unknown, record: InventoryInfo) => {
        if (record.is_below_safety) return <Badge status="error" text={t('supply.urgent')} />
        if (record.is_below_reorder) return <Badge status="warning" text={t('supply.warning')} />
        return <Badge status="success" text={t('supply.normal')} />
      },
    },
  ]

  const reorderColumns = [
    { title: t('supply.itemCode'), dataIndex: 'item_code', key: 'item_code', width: 120 },
    { title: t('supply.itemName'), dataIndex: 'item_name', key: 'item_name', width: 150 },
    { title: t('supply.currentAvailable'), dataIndex: 'current_available', key: 'current_available', width: 90 },
    { title: t('supply.reorderPoint'), dataIndex: 'reorder_point', key: 'reorder_point', width: 90 },
    { title: t('supply.safetyStock'), dataIndex: 'safety_stock', key: 'safety_stock', width: 90 },
    {
      title: t('supply.suggestedQuantity'),
      dataIndex: 'suggested_quantity',
      key: 'suggested_quantity',
      width: 110,
      render: (v: number) => <Text strong style={{ color: '#1890ff' }}>{v}</Text>,
    },
    { title: t('supply.reason'), dataIndex: 'reason', key: 'reason' },
  ]

  const lowStockCount = inventory.filter(i => i.is_below_reorder).length
  const safetyStockCount = inventory.filter(i => i.is_below_safety).length

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic title={t('supply.supplierCount')} value={suppliers.length} prefix={<ShopOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title={t('supply.orderCount')} value={orders.length} prefix={<ShoppingCartOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('supply.stockAlert')}
              value={lowStockCount}
              prefix={<WarningOutlined />}
              valueStyle={{ color: lowStockCount > 0 ? '#fa8c16' : '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('supply.urgentRestock')}
              value={safetyStockCount}
              prefix={<InboxOutlined />}
              valueStyle={{ color: safetyStockCount > 0 ? '#cf1322' : '#3f8600' }}
            />
          </Card>
        </Col>
      </Row>

      {safetyStockCount > 0 && (
        <Alert
          type="error"
          message={`${safetyStockCount}${t('supply.lowStockWarning')}`}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Tabs
        defaultActiveKey="suppliers"
        items={[
          {
            key: 'suppliers',
            label: <span><ShopOutlined /> {t('supply.suppliers')}</span>,
            children: (
              <Card
                title={t('supply.supplierList')}
                extra={
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateSupplierModalOpen(true)}>
                    {t('supply.createSupplier')}
                  </Button>
                }
              >
                <Table
                  columns={supplierColumns}
                  dataSource={suppliers.map(s => ({ ...s, key: s.id }))}
                  size="small"
                  pagination={{ pageSize: 10 }}
                />
              </Card>
            ),
          },
          {
            key: 'orders',
            label: <span><ShoppingCartOutlined /> {t('supply.purchaseOrders')}</span>,
            children: (
              <Card
                title={t('supply.orderList')}
                extra={
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOrderModalOpen(true)}>
                    {t('supply.createOrder')}
                  </Button>
                }
              >
                <Table
                  columns={orderColumns}
                  dataSource={orders.map(o => ({ ...o, key: o.id }))}
                  size="small"
                  pagination={{ pageSize: 10 }}
                />
              </Card>
            ),
          },
          {
            key: 'inventory',
            label: <span><InboxOutlined /> {t('supply.inventory')}</span>,
            children: (
              <Card title={t('supply.inventoryList')}>
                <Table
                  columns={inventoryColumns}
                  dataSource={inventory.map(i => ({ ...i, key: i.id }))}
                  size="small"
                  pagination={{ pageSize: 10 }}
                />
              </Card>
            ),
          },
          {
            key: 'reorder',
            label: <span><WarningOutlined /> {t('supply.reorderAdvice')}</span>,
            children: (
              <Card title={t('supply.reorderList')}>
                {reorderAdvice.length > 0 ? (
                  <Table
                    columns={reorderColumns}
                    dataSource={reorderAdvice.map((a, i) => ({ ...a, key: i }))}
                    size="small"
                    pagination={false}
                  />
                ) : (
                  <Empty description={t('supply.noReorderAdvice')} />
                )}
              </Card>
            ),
          },
        ]}
      />

      <Modal
        title={t('supply.createSupplier')}
        open={createSupplierModalOpen}
        onCancel={() => setCreateSupplierModalOpen(false)}
        onOk={() => supplierForm.submit()}
      >
        <Form form={supplierForm} layout="vertical" onFinish={handleCreateSupplier}>
          <Form.Item name="name" label={t('supply.supplierName')} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="code" label={t('supply.supplierCode')} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="category" label={t('supply.category')} initialValue="raw_material">
            <Select options={Object.entries(categoryLabels).map(([k, v]) => ({ value: k, label: v }))} />
          </Form.Item>
          <Form.Item name="lead_time_days" label={t('supply.deliveryCycle')} initialValue={30}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="min_order_quantity" label={t('supply.minOrderQty')} initialValue={1}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={t('supply.createOrder')}
        open={createOrderModalOpen}
        onCancel={() => setCreateOrderModalOpen(false)}
        onOk={() => orderForm.submit()}
        width={600}
      >
        <Form form={orderForm} layout="vertical" onFinish={handleCreateOrder}>
          <Form.Item name="supplier_id" label={t('supply.supplierName')} rules={[{ required: true }]}>
            <Select
              options={suppliers.filter(s => s.qualification_status === 'qualified').map(s => ({
                value: s.id, label: `${s.name} (${s.code}) - ${t('supply.score')}: ${((s.performance_metrics?.overall_score ?? 0) * 100).toFixed(0)}`,
              }))}
              placeholder={t('supply.selectQualifiedSupplier')}
            />
          </Form.Item>
          <Form.Item name="supplier_name" label={t('supply.supplierName')}>
            <Input placeholder={t('supply.autoFill')} disabled />
          </Form.Item>
          <Form.Item name="expected_delivery_date" label={t('supply.expectedDeliveryDate')}>
            <Input placeholder="YYYY-MM-DD" />
          </Form.Item>
          <Form.Item name="payment_terms" label={t('supply.paymentTerms')} initialValue="net30">
            <Select options={[
              { value: 'net15', label: 'Net 15' },
              { value: 'net30', label: 'Net 30' },
              { value: 'net60', label: 'Net 60' },
            ]} />
          </Form.Item>
          <Form.Item name="iqc_required" label={t('supply.iqcRequired')} valuePropName="checked" initialValue={true}>
            <Select options={[
              { value: true, label: t('common.yes') },
              { value: false, label: t('common.no') },
            ]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
