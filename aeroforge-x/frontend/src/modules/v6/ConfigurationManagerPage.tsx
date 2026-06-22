import { useState, useEffect, useCallback } from 'react'
import {
  Card, Tree, Button, Modal, Form, Input, Select, Tag, Space,
  Statistic, Row, Col, Descriptions, Timeline, Typography,
  message, Tooltip, Breadcrumb, Spin, Empty, Alert,
} from 'antd'
import type { TreeProps } from 'antd'
import {
  PlusOutlined, LockOutlined, UnlockOutlined, BranchesOutlined,
  ApartmentOutlined, EditOutlined, ReloadOutlined, CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons'
import { configApi, baselineApi } from '../../api/v6Api'
import type {
  BlockConfiguration,
  ConfigurationHierarchy,
  SerialNumberConfiguration,
  PatchBlockRequest,
} from '../../api/types'

const { Title, Text } = Typography
const { Option } = Select

type TreeNodeType = 'aircraft' | 'block' | 'sn'

interface TreeNodeData {
  type: TreeNodeType
  id: string
  label: string
  aircraftType?: string
}

export default function ConfigurationManagerPage() {
  const [hierarchy, setHierarchy] = useState<ConfigurationHierarchy | null>(null)
  const [aircraftType, setAircraftType] = useState<string>('B737')
  const [selectedBlock, setSelectedBlock] = useState<BlockConfiguration | null>(null)
  const [selectedSN, setSelectedSN] = useState<SerialNumberConfiguration | null>(null)
  const [loading, setLoading] = useState(false)
  const [treeLoading, setTreeLoading] = useState(false)
  const [createBlockVisible, setCreateBlockVisible] = useState(false)
  const [createSNVisible, setCreateSNVisible] = useState(false)
  const [editBlockVisible, setEditBlockVisible] = useState(false)
  const [establishBaselineVisible, setEstablishBaselineVisible] = useState(false)
  const [form] = Form.useForm()
  const [snForm] = Form.useForm()
  const [editForm] = Form.useForm()
  const [baselineForm] = Form.useForm()

  const fetchHierarchy = useCallback(async (type?: string) => {
    const at = type || aircraftType
    if (!at) return
    setTreeLoading(true)
    try {
      const data = await configApi.getHierarchy(at) as ConfigurationHierarchy
      setHierarchy(data)
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 404) {
        setHierarchy(null)
        message.info(`Aircraft type "${at}" not found. Create a block first.`)
      } else {
        message.error('Failed to load hierarchy')
        setHierarchy(null)
      }
    } finally {
      setTreeLoading(false)
    }
  }, [aircraftType])

  useEffect(() => { fetchHierarchy() }, [fetchHierarchy])

  const fetchBlockDetail = useCallback(async (blockId: string) => {
    setLoading(true)
    try {
      const data = await configApi.getBlock(blockId) as BlockConfiguration
      setSelectedBlock(data)
    } catch {
      message.error('Failed to load block detail')
    } finally {
      setLoading(false)
    }
  }, [])

  const treeData: TreeProps['treeData'] = hierarchy ? [
    {
      key: `aircraft-${hierarchy.aircraft_type}`,
      title: (
        <span>
          <ApartmentOutlined style={{ marginRight: 4 }} />
          <strong>{hierarchy.aircraft_type}</strong>
          <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
            {hierarchy.blocks.length} blocks / {hierarchy.total_serial_numbers} SNs
          </Text>
        </span>
      ),
      children: hierarchy.blocks.map(block => ({
        key: `block-${block.block_id}`,
        title: (
          <span>
            {block.locked
              ? <LockOutlined style={{ color: '#cf1322', marginRight: 4 }} />
              : <UnlockOutlined style={{ color: '#52c41a', marginRight: 4 }} />
            }
            {block.block_name}
            <Text type="secondary" style={{ marginLeft: 8, fontSize: 11 }}>
              {block.block_id}
            </Text>
          </span>
        ),
        children: [],
      })),
    },
  ] : []

  const handleSelect: TreeProps['onSelect'] = (selectedKeys) => {
    if (selectedKeys.length === 0) return
    const key = selectedKeys[0] as string
    if (key.startsWith('block-')) {
      const blockId = key.replace('block-', '')
      setSelectedSN(null)
      fetchBlockDetail(blockId)
    } else if (key.startsWith('aircraft-')) {
      setSelectedBlock(null)
      setSelectedSN(null)
    }
  }

  const handleCreateBlock = async () => {
    try {
      const values = await form.validateFields()
      await configApi.createBlock(values)
      message.success('Block configuration created')
      setCreateBlockVisible(false)
      form.resetFields()
      fetchHierarchy(values.aircraft_type)
      if (values.aircraft_type !== aircraftType) {
        setAircraftType(values.aircraft_type)
      }
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status) {
        message.error(`Create failed (${status})`)
      }
    }
  }

  const handleCreateSN = async () => {
    if (!selectedBlock) return
    try {
      const values = await snForm.validateFields()
      await configApi.createSN({
        block_id: selectedBlock.block_id,
        tail_number: values.tail_number,
      })
      message.success('SN configuration created')
      setCreateSNVisible(false)
      snForm.resetFields()
      fetchHierarchy()
      fetchBlockDetail(selectedBlock.block_id)
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status) {
        message.error(`Create SN failed (${status})`)
      }
    }
  }

  const handleEditBlock = async () => {
    if (!selectedBlock) return
    try {
      const values = await editForm.validateFields()
      const patchData: PatchBlockRequest = {
        expected_version: selectedBlock.version,
        ...values,
      }
      await configApi.patchBlock(selectedBlock.block_id, patchData)
      message.success('Block updated successfully')
      setEditBlockVisible(false)
      editForm.resetFields()
      fetchHierarchy()
      fetchBlockDetail(selectedBlock.block_id)
    } catch (err: unknown) {
      const axiosErr = err as { response?: { status?: number; data?: { detail?: string } } }
      if (axiosErr.response?.status === 409) {
        Modal.error({
          title: 'Version Conflict',
          content: (
            <div>
              <p><ExclamationCircleOutlined style={{ color: '#faad14', marginRight: 8 }} />
                配置已被其它用户修改，请刷新后重试
              </p>
              <p style={{ color: '#999', fontSize: 12 }}>{axiosErr.response.data?.detail}</p>
            </div>
          ),
          okText: '刷新',
          onOk: () => {
            fetchBlockDetail(selectedBlock.block_id)
          },
        })
      } else if (axiosErr.response?.status === 422) {
        message.error(`Protected column: ${axiosErr.response.data?.detail}`)
      } else if (axiosErr.response?.status) {
        message.error(`Update failed (${axiosErr.response.status})`)
      }
    }
  }

  const handleEstablishBaseline = async () => {
    if (!selectedBlock) return
    try {
      const values = await baselineForm.validateFields()
      const req = { block_id: selectedBlock.block_id, established_by: values.established_by }
      if (values.baseline_type === 'FBL') {
        await baselineApi.establishFBL(req)
      } else if (values.baseline_type === 'FCL') {
        await baselineApi.establishFCL(req)
      } else {
        await baselineApi.establishFSDL(req)
      }
      message.success(`${values.baseline_type} baseline established`)
      setEstablishBaselineVisible(false)
      baselineForm.resetFields()
      fetchHierarchy()
      fetchBlockDetail(selectedBlock.block_id)
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status) {
        message.error(`Establish baseline failed (${status})`)
      }
    }
  }

  const openEditModal = () => {
    if (!selectedBlock) return
    editForm.setFieldsValue({
      block_name: selectedBlock.block_name,
    })
    setEditBlockVisible(true)
  }

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

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Total Blocks" value={hierarchy?.blocks.length ?? 0} prefix={<ApartmentOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Locked Blocks" value={hierarchy?.blocks.filter(b => b.locked).length ?? 0} prefix={<LockOutlined />} valueStyle={{ color: '#cf1322' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Total SNs" value={hierarchy?.total_serial_numbers ?? 0} prefix={<BranchesOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Aircraft Type" value={hierarchy?.aircraft_type ?? '—'} prefix={<ApartmentOutlined />} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={10}>
          <Card
            title="Configuration Tree"
            size="small"
            extra={
              <Space>
                <Select
                  value={aircraftType}
                  onChange={(v) => { setAircraftType(v); fetchHierarchy(v) }}
                  style={{ width: 140 }}
                  size="small"
                >
                  <Option value="B737">B737</Option>
                  <Option value="A320">A320</Option>
                  <Option value="A350">A350</Option>
                  <Option value="C919">C919</Option>
                  <Option value="ARJ21">ARJ21</Option>
                </Select>
                <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchHierarchy()} />
                <Button type="primary" size="small" icon={<PlusOutlined />} onClick={() => setCreateBlockVisible(true)}>
                  New Block
                </Button>
              </Space>
            }
          >
            <Spin spinning={treeLoading}>
              {treeData && treeData.length > 0 ? (
                <Tree
                  defaultExpandAll
                  treeData={treeData}
                  onSelect={handleSelect}
                  style={{ minHeight: 300 }}
                />
              ) : (
                <Empty description="No configuration data. Create a block to start." style={{ padding: 40 }} />
              )}
            </Spin>
          </Card>
        </Col>

        <Col span={14}>
          {selectedBlock ? (
            <Spin spinning={loading}>
              <Card
                title={
                  <Space>
                    <span>{selectedBlock.block_id}</span>
                    {selectedBlock.locked
                      ? <Tag icon={<LockOutlined />} color="red">Locked</Tag>
                      : <Tag icon={<UnlockOutlined />} color="green">Open</Tag>
                    }
                  </Space>
                }
                size="small"
                extra={
                  <Space>
                    <Button size="small" icon={<EditOutlined />} onClick={openEditModal} disabled={selectedBlock.locked}>
                      Edit
                    </Button>
                    <Button size="small" icon={<PlusOutlined />} onClick={() => setCreateSNVisible(true)}>
                      Add SN
                    </Button>
                    <Button size="small" onClick={() => setEstablishBaselineVisible(true)}>
                      Baseline
                    </Button>
                    <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchBlockDetail(selectedBlock.block_id)} />
                  </Space>
                }
              >
                <Descriptions column={2} size="small" bordered>
                  <Descriptions.Item label="Block ID">{selectedBlock.block_id}</Descriptions.Item>
                  <Descriptions.Item label="Block Name">{selectedBlock.block_name}</Descriptions.Item>
                  <Descriptions.Item label="Aircraft Type">{selectedBlock.aircraft_type}</Descriptions.Item>
                  <Descriptions.Item label="Locked">
                    {selectedBlock.locked ? 'Yes' : 'No'}
                  </Descriptions.Item>
                  <Descriptions.Item label="Version">{selectedBlock.version ?? '—'}</Descriptions.Item>
                  <Descriptions.Item label="Updated At">{selectedBlock.updated_at ? new Date(selectedBlock.updated_at).toLocaleString() : '—'}</Descriptions.Item>
                </Descriptions>

                <div style={{ marginTop: 16 }}>
                  <Text strong style={{ marginBottom: 8, display: 'block' }}>Three-View Configuration Status</Text>
                  <Timeline
                    items={[
                      {
                        color: selectedBlock.design_config ? 'green' : 'gray',
                        children: (
                          <Space>
                            <span>Design Configuration</span>
                            {selectedBlock.design_config && (
                              <Tag color="blue">{selectedBlock.design_config.config_id}</Tag>
                            )}
                          </Space>
                        ),
                      },
                      {
                        color: selectedBlock.manufacturing_config ? 'green' : 'gray',
                        children: (
                          <Space>
                            <span>Manufacturing Configuration</span>
                            {selectedBlock.manufacturing_config && (
                              <Tag color="green">{selectedBlock.manufacturing_config.config_id}</Tag>
                            )}
                          </Space>
                        ),
                      },
                      {
                        color: selectedBlock.operational_config ? 'green' : 'gray',
                        children: (
                          <Space>
                            <span>Operational Configuration</span>
                            {selectedBlock.operational_config && (
                              <Tag color="orange">{selectedBlock.operational_config.config_id}</Tag>
                            )}
                          </Space>
                        ),
                      },
                    ]}
                  />
                </div>
              </Card>
            </Spin>
          ) : (
            <Card>
              <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
                <ApartmentOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                <div>Select a block from the tree to view details</div>
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
              <Option value="B737">B737</Option>
              <Option value="A320">A320</Option>
              <Option value="A350">A350</Option>
              <Option value="C919">C919</Option>
              <Option value="ARJ21">ARJ21</Option>
            </Select>
          </Form.Item>
          <Form.Item name="block_name" label="Block Name" rules={[{ required: true }]}>
            <Input placeholder="e.g., MAIN-WING" />
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
          <Form.Item label="Block ID">
            <Input value={selectedBlock?.block_id} disabled />
          </Form.Item>
          <Form.Item name="tail_number" label="Tail Number" rules={[{ required: true }]}>
            <Input placeholder="e.g., B-001A" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Edit Block Configuration"
        open={editBlockVisible}
        onOk={handleEditBlock}
        onCancel={() => { setEditBlockVisible(false); editForm.resetFields() }}
      >
        <Alert
          message="Optimistic Locking"
          description={`Current version: ${selectedBlock?.version ?? 'N/A'}. If another user modifies this block before you save, you will receive a conflict error.`}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Form form={editForm} layout="vertical">
          <Form.Item label="Block ID">
            <Input value={selectedBlock?.block_id} disabled />
          </Form.Item>
          <Form.Item name="block_name" label="Block Name" rules={[{ required: true }]}>
            <Input placeholder="Enter new block name" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Establish Baseline"
        open={establishBaselineVisible}
        onOk={handleEstablishBaseline}
        onCancel={() => { setEstablishBaselineVisible(false); baselineForm.resetFields() }}
      >
        <Form form={baselineForm} layout="vertical">
          <Form.Item label="Block ID">
            <Input value={selectedBlock?.block_id} disabled />
          </Form.Item>
          <Form.Item name="baseline_type" label="Baseline Type" rules={[{ required: true }]} initialValue="FBL">
            <Select>
              <Option value="FBL">FBL - Functional Baseline (SRR)</Option>
              <Option value="FCL">FCL - Functional Configuration (PDR)</Option>
              <Option value="FSDL">FSDL - Functional System Design (CDR)</Option>
            </Select>
          </Form.Item>
          <Form.Item name="established_by" label="Established By" rules={[{ required: true }]}>
            <Input placeholder="e.g., engineer-1" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
