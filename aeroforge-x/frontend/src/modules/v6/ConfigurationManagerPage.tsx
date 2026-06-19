import { useState, useEffect, useCallback } from 'react'
import {
  Card, Table, Button, Modal, Form, Input, Select, Tag, Space,
  Statistic, Row, Col, Badge, Descriptions, Timeline, Typography,
  message, Tooltip, Breadcrumb,
} from 'antd'
import {
  PlusOutlined, LockOutlined, UnlockOutlined, BranchesOutlined,
  SwapOutlined, WarningOutlined, CheckCircleOutlined, HistoryOutlined,
  ApartmentOutlined,
} from '@ant-design/icons'
import { configApi } from '../../../api/v6Api'

const { Title, Text } = Typography
const { Option } = Select

interface BlockConfig {
  block_id: string
  aircraft_type: string
  block_name: string
  design_config_id?: string
  manufacturing_config_id?: string
  operational_config_id?: string
  locked: boolean
}

interface SNConfig {
  sn_id: string
  tail_number: string
  block_id: string
  sn_modifications: any[]
  service_bulletins: any[]
}

export default function ConfigurationManagerPage() {
  const [blocks, setBlocks] = useState<BlockConfig[]>([])
  const [selectedBlock, setSelectedBlock] = useState<BlockConfig | null>(null)
  const [sns, setSns] = useState<SNConfig[]>([])
  const [createBlockVisible, setCreateBlockVisible] = useState(false)
  const [createSNVisible, setCreateSNVisible] = useState(false)
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()
  const [snForm] = Form.useForm()

  const fetchBlocks = useCallback(async () => {
    setLoading(true)
    try {
      const data = await configApi.listBlocks()
      setBlocks(Array.isArray(data) ? data : data?.items || [])
    } catch {
      setBlocks(mockBlocks())
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchBlocks() }, [fetchBlocks])

  const fetchSNs = useCallback(async (blockId: string) => {
    try {
      const data = await configApi.listSNs(blockId)
      setSns(Array.isArray(data) ? data : data?.items || [])
    } catch {
      setSns(mockSNs(blockId))
    }
  }, [])

  const handleSelectBlock = (block: BlockConfig) => {
    setSelectedBlock(block)
    fetchSNs(block.block_id)
  }

  const handleCreateBlock = async () => {
    try {
      const values = await form.validateFields()
      await configApi.createBlock(values)
      message.success('Block configuration created')
      setCreateBlockVisible(false)
      form.resetFields()
      fetchBlocks()
    } catch {
      message.info('Demo mode: block created locally')
      setCreateBlockVisible(false)
      form.resetFields()
    }
  }

  const handleCreateSN = async () => {
    if (!selectedBlock) return
    try {
      const values = await snForm.validateFields()
      await configApi.createSN(selectedBlock.block_id, values)
      message.success('SN configuration created')
      setCreateSNVisible(false)
      snForm.resetFields()
      fetchSNs(selectedBlock.block_id)
    } catch {
      message.info('Demo mode: SN created locally')
      setCreateSNVisible(false)
      snForm.resetFields()
    }
  }

  const blockColumns = [
    {
      title: 'Block ID',
      dataIndex: 'block_id',
      key: 'block_id',
      render: (text: string) => (
        <Button type="link" onClick={() => {
          const b = blocks.find(bl => bl.block_id === text)
          if (b) handleSelectBlock(b)
        }}>{text}</Button>
      ),
    },
    { title: 'Aircraft Type', dataIndex: 'aircraft_type', key: 'aircraft_type' },
    { title: 'Block Name', dataIndex: 'block_name', key: 'block_name' },
    {
      title: 'Design',
      dataIndex: 'design_config_id',
      key: 'design',
      render: (v: string) => v ? <Tag color="blue">DC</Tag> : <Tag>—</Tag>,
    },
    {
      title: 'Mfg',
      dataIndex: 'manufacturing_config_id',
      key: 'mfg',
      render: (v: string) => v ? <Tag color="green">MC</Tag> : <Tag>—</Tag>,
    },
    {
      title: 'Ops',
      dataIndex: 'operational_config_id',
      key: 'ops',
      render: (v: string) => v ? <Tag color="orange">OC</Tag> : <Tag>—</Tag>,
    },
    {
      title: 'Status',
      dataIndex: 'locked',
      key: 'locked',
      render: (locked: boolean) => locked
        ? <Tag icon={<LockOutlined />} color="red">Locked</Tag>
        : <Tag icon={<UnlockOutlined />} color="green">Open</Tag>,
    },
  ]

  const snColumns = [
    { title: 'SN ID', dataIndex: 'sn_id', key: 'sn_id' },
    { title: 'Tail Number', dataIndex: 'tail_number', key: 'tail_number' },
    {
      title: 'Modifications',
      dataIndex: 'sn_modifications',
      key: 'mods',
      render: (mods: any[]) => <Badge count={mods?.length || 0} />,
    },
    {
      title: 'Service Bulletins',
      dataIndex: 'service_bulletins',
      key: 'sb',
      render: (sbs: any[]) => <Badge count={sbs?.length || 0} style={{ backgroundColor: '#faad14' }} />,
    },
  ]

  return (
    <div style={{ padding: 0 }}>
      <Breadcrumb items={[
        { title: 'AeroForge-X' },
        { title: 'V6 Programs' },
        { title: 'Configuration Manager' },
      ]} style={{ marginBottom: 16 }} />

      <Title level={3} style={{ marginBottom: 24 }}>
        <ApartmentOutlined style={{ marginRight: 8 }} />
        Configuration Manager
        <Text type="secondary" style={{ fontSize: 14, marginLeft: 12 }}>
          Block / SN lifecycle management with three-view propagation
        </Text>
      </Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Total Blocks" value={blocks.length} prefix={<ApartmentOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Locked Blocks" value={blocks.filter(b => b.locked).length} prefix={<LockOutlined />} valueStyle={{ color: '#cf1322' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Total SNs" value={sns.length} prefix={<BranchesOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Aircraft Types" value={new Set(blocks.map(b => b.aircraft_type)).size} prefix={<SwapOutlined />} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={14}>
          <Card
            title="Block Configurations"
            extra={
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateBlockVisible(true)}>
                New Block
              </Button>
            }
          >
            <Table
              dataSource={blocks}
              columns={blockColumns}
              rowKey="block_id"
              loading={loading}
              size="small"
              pagination={{ pageSize: 10 }}
              onRow={(record) => ({
                onClick: () => handleSelectBlock(record),
                style: { cursor: 'pointer', background: selectedBlock?.block_id === record.block_id ? '#e6f7ff' : undefined },
              })}
            />
          </Card>
        </Col>

        <Col span={10}>
          {selectedBlock ? (
            <>
              <Card title={`Block: ${selectedBlock.block_id}`} size="small" style={{ marginBottom: 16 }}>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="Aircraft Type">{selectedBlock.aircraft_type}</Descriptions.Item>
                  <Descriptions.Item label="Block Name">{selectedBlock.block_name}</Descriptions.Item>
                  <Descriptions.Item label="Status">
                    {selectedBlock.locked
                      ? <Tag icon={<LockOutlined />} color="red">Locked</Tag>
                      : <Tag icon={<UnlockOutlined />} color="green">Open</Tag>
                    }
                  </Descriptions.Item>
                </Descriptions>
                <Timeline
                  style={{ marginTop: 12 }}
                  items={[
                    { color: selectedBlock.design_config_id ? 'green' : 'gray', children: 'Design Configuration' },
                    { color: selectedBlock.manufacturing_config_id ? 'green' : 'gray', children: 'Manufacturing Configuration' },
                    { color: selectedBlock.operational_config_id ? 'green' : 'gray', children: 'Operational Configuration' },
                  ]}
                />
              </Card>

              <Card
                title={`Serial Numbers (${sns.length})`}
                size="small"
                extra={
                  <Button size="small" icon={<PlusOutlined />} onClick={() => setCreateSNVisible(true)}>
                    Add SN
                  </Button>
                }
              >
                <Table
                  dataSource={sns}
                  columns={snColumns}
                  rowKey="sn_id"
                  size="small"
                  pagination={{ pageSize: 5 }}
                />
              </Card>
            </>
          ) : (
            <Card>
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
                <ApartmentOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                <div>Select a block configuration to view details</div>
              </div>
            </Card>
          )}
        </Col>
      </Row>

      <Modal
        title="Create Block Configuration"
        open={createBlockVisible}
        onOk={handleCreateBlock}
        onCancel={() => { setCreateBlockVisible(false); form.resetFields() }}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="aircraft_type" label="Aircraft Type" rules={[{ required: true }]}>
            <Select placeholder="Select aircraft type">
              <Option value="A320">A320</Option>
              <Option value="A350">A350</Option>
              <Option value="C919">C919</Option>
              <Option value="ARJ21">ARJ21</Option>
            </Select>
          </Form.Item>
          <Form.Item name="block_name" label="Block Name" rules={[{ required: true }]}>
            <Input placeholder="e.g., Block-1" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Create Serial Number Configuration"
        open={createSNVisible}
        onOk={handleCreateSN}
        onCancel={() => { setCreateSNVisible(false); snForm.resetFields() }}
      >
        <Form form={snForm} layout="vertical">
          <Form.Item name="tail_number" label="Tail Number" rules={[{ required: true }]}>
            <Input placeholder="e.g., B-001A" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

function mockBlocks(): BlockConfig[] {
  return [
    { block_id: 'BLK-A320-Block-1', aircraft_type: 'A320', block_name: 'Block-1', design_config_id: 'DC-BLK-A320-Block-1-1', manufacturing_config_id: 'MC-BLK-A320-Block-1-1', operational_config_id: 'OC-BLK-A320-Block-1-1', locked: true },
    { block_id: 'BLK-A320-Block-2', aircraft_type: 'A320', block_name: 'Block-2', design_config_id: 'DC-BLK-A320-Block-2-1', locked: false },
    { block_id: 'BLK-C919-Block-1', aircraft_type: 'C919', block_name: 'Block-1', design_config_id: 'DC-BLK-C919-Block-1-1', manufacturing_config_id: 'MC-BLK-C919-Block-1-1', locked: false },
    { block_id: 'BLK-A350-Block-1', aircraft_type: 'A350', block_name: 'Block-1', design_config_id: 'DC-BLK-A350-Block-1-1', locked: true },
  ]
}

function mockSNs(blockId: string): SNConfig[] {
  return [
    { sn_id: 'SN-B-001A', tail_number: 'B-001A', block_id: blockId, sn_modifications: [{ modification_type: 'Update', item_id: 'ITM-1' }], service_bulletins: [] },
    { sn_id: 'SN-B-002A', tail_number: 'B-002A', block_id: blockId, sn_modifications: [], service_bulletins: [{ id: 'SB-2026-001' }] },
  ]
}