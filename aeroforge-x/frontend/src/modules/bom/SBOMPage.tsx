import { useState } from 'react'
import {
  Typography, Card, Button, Tree, Descriptions, Tag, Space, Input,
  message, Empty, Row, Col, Select, Form,
} from 'antd'
import {
  SafetyCertificateOutlined, SearchOutlined, ThunderboltOutlined,
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
  is_virtual?: boolean
}

function sbomNodeToTreeNode(node: BOMNode): { title: React.ReactNode; key: string; children: any[] } {
  const spareCat = node.attributes?.spare_part_category as string
  const cycle = node.attributes?.replacement_cycle_fh as number
  const strategy = node.attributes?.maintenance_strategy as string

  const catColor: Record<string, string> = { essential: 'red', recommended: 'orange', optional: 'blue' }
  const strategyLabel: Record<string, string> = {
    scheduled_replacement: '定期更换',
    condition_based: '视情维修',
    failure_based: '故障维修',
  }

  return {
    title: (
      <span>
        <Tag color={catColor[spareCat] || 'default'}>{spareCat || '—'}</Tag>
        {node.name}
        {cycle > 0 && <Tag color="blue">{cycle} FH</Tag>}
        {strategy && <Tag color="green">{strategyLabel[strategy] || strategy}</Tag>}
        {node.quantity > 1 && <span style={{ marginLeft: 8, color: '#999' }}>x{node.quantity}</span>}
        <span style={{ marginLeft: 8, fontSize: 12, color: '#999' }}>{node.item_code}</span>
      </span>
    ),
    key: `sbom-${node.item_code}`,
    children: (node.children || []).map(sbomNodeToTreeNode),
  }
}

export default function SBOMPage() {
  const [ebomId, setEbomId] = useState('')
  const [sbomId, setSbomId] = useState('')
  const [sbomTree, setSbomTree] = useState<BOMNode | null>(null)
  const [selectedNode, setSelectedNode] = useState<BOMNode | null>(null)
  const [generating, setGenerating] = useState(false)
  const [environment, setEnvironment] = useState('standard')

  const handleGenerate = async () => {
    if (!ebomId) {
      message.warning('请输入eBOM ID')
      return
    }
    setGenerating(true)
    try {
      const resp = await apiClient.post('/bom/sbom/generate', {
        ebom_id: ebomId,
        environment,
        created_by: 'engineer',
      })
      const newSbomId = resp.data?.data?.task_id || resp.data?.task_id
      if (newSbomId) {
        setSbomId(newSbomId)
        message.success('sBOM生成完成')
        await fetchSBOMTree(newSbomId)
      }
    } catch {
      message.error('sBOM生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const fetchSBOMTree = async (id: string) => {
    try {
      const resp = await apiClient.get(`/bom/sbom/${id}/tree`)
      if (resp.data?.data?.tree) {
        setSbomTree(resp.data.data.tree)
      }
    } catch {
      message.error('获取sBOM数据失败')
    }
  }

  const handleFetchSBOM = async () => {
    if (!sbomId) return
    await fetchSBOMTree(sbomId)
  }

  const findNode = (node: BOMNode, code: string): BOMNode | null => {
    if (node.item_code === code) return node
    for (const child of node.children || []) {
      const found = findNode(child, code)
      if (found) return found
    }
    return null
  }

  const handleSelect = (selectedKeys: React.Key[]) => {
    if (sbomTree && selectedKeys.length > 0) {
      const code = (selectedKeys[0] as string).replace('sbom-', '')
      const node = findNode(sbomTree, code)
      setSelectedNode(node)
    }
  }

  return (
    <div>
      <Card title="sBOM 生成" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Input
            placeholder="输入eBOM ID"
            value={ebomId}
            onChange={(e) => setEbomId(e.target.value)}
            style={{ width: 200 }}
          />
          <Select
            value={environment}
            onChange={setEnvironment}
            style={{ width: 160 }}
            options={[
              { value: 'standard', label: '标准环境' },
              { value: 'corrosive', label: '腐蚀环境' },
              { value: 'high_temperature', label: '高温环境' },
              { value: 'high_humidity', label: '高湿环境' },
              { value: 'arid', label: '干旱环境' },
            ]}
          />
          <Button
            type="primary"
            icon={<SafetyCertificateOutlined />}
            onClick={handleGenerate}
            loading={generating}
          >
            生成sBOM
          </Button>
          <Input
            placeholder="输入sBOM ID查询"
            value={sbomId}
            onChange={(e) => setSbomId(e.target.value)}
            style={{ width: 200 }}
          />
          <Button icon={<SearchOutlined />} onClick={handleFetchSBOM}>查询sBOM</Button>
        </Space>
      </Card>

      <Row gutter={16}>
        <Col span={16}>
          <Card title="sBOM 结构树（备件属性 + 更换周期）" style={{ minHeight: 400 }}>
            {sbomTree ? (
              <Tree showLine defaultExpandAll treeData={[sbomNodeToTreeNode(sbomTree)]} onSelect={handleSelect} />
            ) : (
              <Empty description="请生成或查询sBOM" />
            )}
          </Card>
        </Col>
        <Col span={8}>
          {selectedNode && (
            <Card title="备件属性详情">
              <Descriptions bordered column={1} size="small">
                <Descriptions.Item label="物料编码">{selectedNode.item_code}</Descriptions.Item>
                <Descriptions.Item label="名称">{selectedNode.name}</Descriptions.Item>
                <Descriptions.Item label="类型">{selectedNode.part_type}</Descriptions.Item>
                <Descriptions.Item label="数量">{selectedNode.quantity} {selectedNode.unit}</Descriptions.Item>
                {selectedNode.attributes && Object.entries(selectedNode.attributes).map(([k, v]) => (
                  <Descriptions.Item key={k} label={k}>
                    {v !== null && v !== undefined && v !== '' ? String(v) : '—'}
                  </Descriptions.Item>
                ))}
              </Descriptions>
            </Card>
          )}
          {!selectedNode && (
            <Card>
              <Empty description="选择sBOM节点查看备件属性" />
            </Card>
          )}
        </Col>
      </Row>
    </div>
  )
}