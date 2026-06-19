import { useState } from 'react'
import {
  Typography, Card, Button, Tree, Descriptions, Tag, Space, Input,
  message, Empty, Row, Col, Table, Alert, Tabs, Modal, Select, Form,
} from 'antd'
import {
  ApartmentOutlined, SwapOutlined, WarningOutlined,
  CheckCircleOutlined, PlusOutlined, SearchOutlined, ExperimentOutlined,
} from '@ant-design/icons'
import apiClient from '../../services/apiClient'

const { Title, Text } = Typography

interface BOMNode {
  item_code: string
  name: string
  bom_type: string
  quantity: number
  unit: string
  version: string
  part_type: string
  attributes: Record<string, unknown>
  children: BOMNode[]
  station?: string
  assembly_order?: number
  is_virtual?: boolean
  mapping_status?: string
  ebom_item_code?: string
}

interface TreeNode {
  title: React.ReactNode
  key: string
  children: TreeNode[]
}

function ebomNodeToTreeNode(node: BOMNode): TreeNode {
  const typeColor: Record<string, string> = { assembly: 'blue', structural: 'green', skin: 'orange', part: 'default' }
  return {
    title: (
      <span>
        <Tag color={typeColor[node.part_type] || 'default'}>{node.part_type}</Tag>
        {node.name}
        {node.quantity > 1 && <span style={{ marginLeft: 8, color: '#999' }}>x{node.quantity}</span>}
        <span style={{ marginLeft: 8, fontSize: 12, color: '#999' }}>{node.item_code}</span>
      </span>
    ),
    key: `ebom-${node.item_code}`,
    children: (node.children || []).map(ebomNodeToTreeNode),
  }
}

function mbomNodeToTreeNode(node: BOMNode): TreeNode {
  const typeColor: Record<string, string> = {
    assembly: 'blue', structural: 'green', skin: 'orange',
    virtual_assembly: 'purple', part: 'default',
  }
  return {
    title: (
      <span>
        {node.is_virtual && <Tag color="purple">虚拟</Tag>}
        <Tag color={typeColor[node.part_type] || 'default'}>{node.part_type}</Tag>
        {node.name}
        {node.station && <Tag color="cyan">{node.station}</Tag>}
        {node.quantity > 1 && <span style={{ marginLeft: 8, color: '#999' }}>x{node.quantity}</span>}
        {node.mapping_status === 'unmapped' && <Tag color="red" icon={<WarningOutlined />}>未映射</Tag>}
        <span style={{ marginLeft: 8, fontSize: 12, color: '#999' }}>{node.item_code}</span>
      </span>
    ),
    key: `mbom-${node.item_code}`,
    children: (node.children || []).map(mbomNodeToTreeNode),
  }
}

export default function MBOMPage() {
  const [ebomId, setEbomId] = useState('')
  const [mbomId, setMbomId] = useState('')
  const [ebomTree, setEbomTree] = useState<BOMNode | null>(null)
  const [mbomTree, setMbomTree] = useState<BOMNode | null>(null)
  const [unmappedItems, setUnmappedItems] = useState<Record<string, unknown>[]>([])
  const [validationResult, setValidationResult] = useState<Record<string, unknown> | null>(null)
  const [transforming, setTransforming] = useState(false)
  const [confirmForm] = Form.useForm()

  const handleTransform = async () => {
    if (!ebomId) {
      message.warning('请输入eBOM ID')
      return
    }
    setTransforming(true)
    try {
      const resp = await apiClient.post('/bom/mbom/transform', {
        ebom_id: ebomId,
        created_by: 'engineer',
      })
      const newMbomId = resp.data?.data?.task_id || resp.data?.task_id
      if (newMbomId) {
        setMbomId(newMbomId)
        message.success('mBOM转换完成')
        await fetchMBOMData(newMbomId)
      }
    } catch {
      message.error('mBOM转换失败')
    } finally {
      setTransforming(false)
    }
  }

  const fetchMBOMData = async (id: string) => {
    try {
      const [treeResp, unmappedResp, validationResp] = await Promise.all([
        apiClient.get(`/bom/mbom/${id}/tree`).catch(() => null),
        apiClient.get(`/bom/mbom/${id}/unmapped`).catch(() => null),
        apiClient.get(`/bom/mbom/${id}/validation`).catch(() => null),
      ])
      if (treeResp?.data?.data?.tree) {
        setMbomTree(treeResp.data.data.tree)
      }
      if (unmappedResp?.data?.data) {
        setUnmappedItems(unmappedResp.data.data.unmapped_items || [])
      }
      if (validationResp?.data?.data) {
        setValidationResult(validationResp.data.data.validation_result)
      }
    } catch {
      message.error('获取mBOM数据失败')
    }
  }

  const handleFetchMBOM = async () => {
    if (!mbomId) return
    await fetchMBOMData(mbomId)
  }

  const handleConfirmMapping = async (values: { item_code: string; target_station: string }) => {
    try {
      await apiClient.post(`/bom/mbom/${mbomId}/confirm-mapping`, values)
      message.success('映射已确认')
      await fetchMBOMData(mbomId)
    } catch {
      message.error('确认映射失败')
    }
  }

  const handlePublishMBOM = async () => {
    try {
      await apiClient.post(`/bom/mbom/${mbomId}/publish`)
      message.success('mBOM已发布')
      await fetchMBOMData(mbomId)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '发布失败'
      message.error(detail)
    }
  }

  const unmappedColumns = [
    { title: 'eBOM物料编码', dataIndex: 'ebom_item_code', key: 'ebom_item_code' },
    { title: '名称', dataIndex: 'ebom_item_name', key: 'ebom_item_name' },
    { title: '原因', dataIndex: 'reason', key: 'reason' },
    { title: '建议操作', dataIndex: 'suggested_action', key: 'suggested_action' },
  ]

  const completeness = validationResult?.completeness_check as Record<string, unknown> | undefined
  const orderCheck = validationResult?.order_check as Record<string, unknown> | undefined
  const virtualCheck = validationResult?.virtual_node_check as Record<string, unknown> | undefined

  return (
    <div>
      <Card title="eBOM → mBOM 转换" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Input
            placeholder="输入eBOM ID"
            value={ebomId}
            onChange={(e) => setEbomId(e.target.value)}
            style={{ width: 200 }}
          />
          <Button
            type="primary"
            icon={<SwapOutlined />}
            onClick={handleTransform}
            loading={transforming}
          >
            转换为mBOM
          </Button>
          <Input
            placeholder="输入mBOM ID查询"
            value={mbomId}
            onChange={(e) => setMbomId(e.target.value)}
            style={{ width: 200 }}
          />
          <Button icon={<SearchOutlined />} onClick={handleFetchMBOM}>查询mBOM</Button>
          {mbomId && (
            <Button type="primary" icon={<CheckCircleOutlined />} onClick={handlePublishMBOM}>
              发布mBOM
            </Button>
          )}
        </Space>
      </Card>

      {unmappedItems.length > 0 && (
        <Alert
          type="warning"
          message={`存在 ${unmappedItems.length} 项未映射物料，需手动确认后才能发布mBOM`}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="eBOM 结构树" style={{ minHeight: 300 }}>
            {ebomTree ? (
              <Tree showLine defaultExpandAll treeData={[ebomNodeToTreeNode(ebomTree)]} />
            ) : (
              <Empty description="请先生成eBOM" />
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="mBOM 结构树（按装配工艺重组）" style={{ minHeight: 300 }}>
            {mbomTree ? (
              <Tree showLine defaultExpandAll treeData={[mbomNodeToTreeNode(mbomTree)]} />
            ) : (
              <Empty description="请执行eBOM→mBOM转换" />
            )}
          </Card>
        </Col>
      </Row>

      {validationResult && (
        <Card title="转换校验结果" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={8}>
              <Card size="small" title="物料完整性">
                {completeness && (
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="eBOM总项数">{completeness.total_ebom_items as number}</Descriptions.Item>
                    <Descriptions.Item label="已映射">{completeness.mapped_items as number}</Descriptions.Item>
                    <Descriptions.Item label="未映射">
                      <Tag color={(completeness.unmapped_items as number) > 0 ? 'red' : 'green'}>
                        {completeness.unmapped_items as number}
                      </Tag>
                    </Descriptions.Item>
                  </Descriptions>
                )}
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" title="装配顺序">
                {orderCheck && (
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="工位数">{orderCheck.total_stations as number}</Descriptions.Item>
                    <Descriptions.Item label="顺序违规">
                      <Tag color={((orderCheck.order_violations as string[]).length) > 0 ? 'red' : 'green'}>
                        {(orderCheck.order_violations as string[]).length}
                      </Tag>
                    </Descriptions.Item>
                  </Descriptions>
                )}
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" title="虚拟节点">
                {virtualCheck && (
                  <Descriptions column={1} size="small">
                    <Descriptions.Item label="虚拟节点数">{virtualCheck.total_virtual_nodes as number}</Descriptions.Item>
                    <Descriptions.Item label="空虚拟节点">
                      <Tag color={(virtualCheck.empty_virtual_nodes as number) > 0 ? 'orange' : 'green'}>
                        {virtualCheck.empty_virtual_nodes as number}
                      </Tag>
                    </Descriptions.Item>
                  </Descriptions>
                )}
              </Card>
            </Col>
          </Row>
        </Card>
      )}

      <Card title="未映射项处理" style={{ marginBottom: 16 }}>
        <Table
          columns={unmappedColumns}
          dataSource={unmappedItems.map((item, i) => ({ ...item, key: i }))}
          pagination={false}
          size="small"
          locale={{ emptyText: '无未映射项' }}
        />
        {unmappedItems.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <Form form={confirmForm} onFinish={handleConfirmMapping} layout="inline">
              <Form.Item name="item_code" rules={[{ required: true }]}>
                <Input placeholder="物料编码" style={{ width: 180 }} />
              </Form.Item>
              <Form.Item name="target_station" rules={[{ required: true }]}>
                <Select placeholder="目标工位" style={{ width: 200 }} options={[
                  { value: 'STN-WING-01', label: '左翼装配工位' },
                  { value: 'STN-WING-02', label: '右翼装配工位' },
                  { value: 'STN-FUSE-01', label: '机身前段装配工位' },
                  { value: 'STN-FUSE-02', label: '机身后段装配工位' },
                  { value: 'STN-TAIL-01', label: '尾翼装配工位' },
                ]} />
              </Form.Item>
              <Button type="primary" htmlType="submit" icon={<CheckCircleOutlined />}>
                确认映射
              </Button>
            </Form>
          </div>
        )}
      </Card>
    </div>
  )
}