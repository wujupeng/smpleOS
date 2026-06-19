import { useState } from 'react'
import { Typography, Card, Button, Tree, Descriptions, Tag, Space, Input, message, Empty, Tabs } from 'antd'
import { ApartmentOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import apiClient from '../../services/apiClient'
import MBOMPage from './MBOMPage'
import SBOMPage from './SBOMPage'
import BOMConsistencyPage from './BOMConsistencyPage'

const { Title } = Typography

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
}

interface TreeNode {
  title: React.ReactNode
  key: string
  children: TreeNode[]
}

function bomNodeToTreeNode(node: BOMNode): TreeNode {
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
    key: node.item_code,
    children: (node.children || []).map(bomNodeToTreeNode),
  }
}

export default function BomCenter() {
  const [bomTree, setBomTree] = useState<BOMNode | null>(null)
  const [treeData, setTreeData] = useState<TreeNode[]>([])
  const [selectedNode, setSelectedNode] = useState<BOMNode | null>(null)
  const [specId, setSpecId] = useState('')
  const [loading, setLoading] = useState(false)
  const [searchSn, setSearchSn] = useState('')

  const handleGenerateEBOM = async () => {
    if (!specId) { message.warning('请输入Spec ID'); return }
    try {
      setLoading(true)
      const modelRes = await apiClient.post('/api/v1/models/generate', {
        spec_id: specId,
        aircraft_type: 'fixed_wing',
        payload_kg: 120,
        range_km: 200,
        cruise_speed_kmh: 120,
      })
      const bomRes = await apiClient.post('/api/v1/bom/ebom/generate', {
        spec_id: specId,
        model_data: modelRes.data,
      })
      const root = bomRes.data.data?.root_item
      if (root) {
        setBomTree(root)
        setTreeData([bomNodeToTreeNode(root)])
        message.success('eBOM已生成')
      }
    } catch {
      message.error('eBOM生成失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSearchBom = async () => {
    if (!searchSn) return
    try {
      const res = await apiClient.get(`/api/v1/bom/ebom/${searchSn}`)
      const root = res.data.data
      if (root) {
        setBomTree(root)
        setTreeData([bomNodeToTreeNode(root)])
      }
    } catch {
      message.error('查询失败')
    }
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
    if (bomTree && selectedKeys.length > 0) {
      const node = findNode(bomTree, selectedKeys[0] as string)
      setSelectedNode(node)
    }
  }

  return (
    <div>
      <Title level={3}><ApartmentOutlined /> PLM / BOM</Title>
      <Tabs
        defaultActiveKey="ebom"
        items={[
          {
            key: 'ebom',
            label: 'eBOM',
            children: (
              <>
                <Card title="eBOM操作" style={{ marginBottom: 16 }}>
                  <Space wrap>
                    <Input placeholder="输入Spec ID" value={specId} onChange={e => setSpecId(e.target.value)} style={{ width: 200 }} />
                    <Button type="primary" icon={<PlusOutlined />} onClick={handleGenerateEBOM} loading={loading}>生成eBOM</Button>
                    <Input placeholder="查询eBOM ID" value={searchSn} onChange={e => setSearchSn(e.target.value)} style={{ width: 200 }} />
                    <Button icon={<SearchOutlined />} onClick={handleSearchBom}>查询</Button>
                  </Space>
                </Card>

                <div style={{ display: 'flex', gap: 16 }}>
                  <Card title="BOM结构树" style={{ flex: 1, minHeight: 400 }}>
                    {treeData.length > 0 ? (
                      <Tree showLine defaultExpandAll treeData={treeData} onSelect={handleSelect} />
                    ) : (
                      <Empty description="暂无BOM数据，请先生成eBOM" />
                    )}
                  </Card>

                  {selectedNode && (
                    <Card title="BOM项属性" style={{ width: 350 }}>
                      <Descriptions bordered column={1} size="small">
                        <Descriptions.Item label="物料编码">{selectedNode.item_code}</Descriptions.Item>
                        <Descriptions.Item label="名称">{selectedNode.name}</Descriptions.Item>
                        <Descriptions.Item label="类型">{selectedNode.part_type}</Descriptions.Item>
                        <Descriptions.Item label="数量">{selectedNode.quantity} {selectedNode.unit}</Descriptions.Item>
                        <Descriptions.Item label="版本">{selectedNode.version}</Descriptions.Item>
                        <Descriptions.Item label="BOM类型">{selectedNode.bom_type}</Descriptions.Item>
                      </Descriptions>
                      {selectedNode.attributes && Object.keys(selectedNode.attributes).length > 0 && (
                        <Descriptions bordered column={1} size="small" title="附加属性" style={{ marginTop: 8 }}>
                          {Object.entries(selectedNode.attributes).map(([k, v]) => (
                            <Descriptions.Item key={k} label={k}>{String(v)}</Descriptions.Item>
                          ))}
                        </Descriptions>
                      )}
                    </Card>
                  )}
                </div>
              </>
            ),
          },
          {
            key: 'mbom',
            label: 'mBOM 制造BOM',
            children: <MBOMPage />,
          },
          {
            key: 'sbom',
            label: 'sBOM 备件BOM',
            children: <SBOMPage />,
          },
          {
            key: 'consistency',
            label: '一致性校验',
            children: <BOMConsistencyPage />,
          },
        ]}
      />
    </div>
  )
}
