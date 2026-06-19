import React, { useState, useCallback, useRef, useEffect } from 'react'
import { Card, Select, Button, Space, Tag, Drawer, Descriptions, Input, Modal, Form, message, Tooltip, Badge } from 'antd'
import { PlusOutlined, SearchOutlined, ExpandOutlined, CompressOutlined, CameraOutlined } from '@ant-design/icons'

const NODE_COLORS: Record<string, string> = {
  requirement: '#1890ff',
  design: '#52c41a',
  structure: '#fa8c16',
  material: '#722ed1',
  manufacturing: '#eb2f96',
  flight: '#13c2c2',
  maintenance: '#f5222d',
}

const NODE_LABELS: Record<string, string> = {
  requirement: '需求',
  design: '设计',
  structure: '结构',
  material: '材料',
  manufacturing: '制造',
  flight: '飞行',
  maintenance: '维护',
}

interface KnowledgeNode {
  id: string
  type: string
  name: string
  properties: Record<string, any>
  tags: string[]
  confidence: number
}

interface KnowledgeLink {
  id: string
  source: string
  target: string
  type: string
  confidence: number
}

const KnowledgeGraphPage: React.FC = () => {
  const [nodes, setNodes] = useState<KnowledgeNode[]>([])
  const [links, setLinks] = useState<KnowledgeLink[]>([])
  const [selectedNode, setSelectedNode] = useState<KnowledgeNode | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [linkModalOpen, setLinkModalOpen] = useState(false)
  const [filterType, setFilterType] = useState<string | undefined>(undefined)
  const [searchText, setSearchText] = useState('')
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [form] = Form.useForm()
  const [linkForm] = Form.useForm()
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({})

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    canvas.width = canvas.offsetWidth
    canvas.height = canvas.offsetHeight
    drawGraph(ctx, canvas.width, canvas.height)
  }, [nodes, links, positions, filterType, searchText])

  const drawGraph = useCallback((ctx: CanvasRenderingContext2D, width: number, height: number) => {
    ctx.clearRect(0, 0, width, height)
    const filteredNodes = nodes.filter(n => {
      if (filterType && n.type !== filterType) return false
      if (searchText && !n.name.toLowerCase().includes(searchText.toLowerCase())) return false
      return true
    })
    const filteredIds = new Set(filteredNodes.map(n => n.id))
    const filteredLinks = links.filter(l => filteredIds.has(l.source) && filteredIds.has(l.target))

    if (filteredNodes.length === 0) {
      ctx.fillStyle = '#999'
      ctx.font = '16px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText('暂无知识图谱数据，请创建节点和关联', width / 2, height / 2)
      return
    }

    const centerX = width / 2
    const centerY = height / 2
    const radius = Math.min(width, height) * 0.35

    const posMap: Record<string, { x: number; y: number }> = {}
    filteredNodes.forEach((node, i) => {
      if (positions[node.id]) {
        posMap[node.id] = positions[node.id]
      } else {
        const angle = (2 * Math.PI * i) / filteredNodes.length
        posMap[node.id] = {
          x: centerX + radius * Math.cos(angle),
          y: centerY + radius * Math.sin(angle),
        }
      }
    })

    filteredLinks.forEach(link => {
      const src = posMap[link.source]
      const tgt = posMap[link.target]
      if (!src || !tgt) return
      ctx.beginPath()
      ctx.moveTo(src.x, src.y)
      ctx.lineTo(tgt.x, tgt.y)
      ctx.strokeStyle = `rgba(150, 150, 150, ${Math.max(0.2, link.confidence)})`
      ctx.lineWidth = 1 + link.confidence
      ctx.stroke()
      const midX = (src.x + tgt.x) / 2
      const midY = (src.y + tgt.y) / 2
      ctx.fillStyle = '#999'
      ctx.font = '10px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(link.type, midX, midY - 4)
    })

    filteredNodes.forEach(node => {
      const pos = posMap[node.id]
      if (!pos) return
      const color = NODE_COLORS[node.type] || '#999'
      ctx.beginPath()
      ctx.arc(pos.x, pos.y, 20, 0, 2 * Math.PI)
      ctx.fillStyle = color + '33'
      ctx.fill()
      ctx.strokeStyle = color
      ctx.lineWidth = 2
      ctx.stroke()
      ctx.fillStyle = '#333'
      ctx.font = '11px sans-serif'
      ctx.textAlign = 'center'
      const displayName = node.name.length > 8 ? node.name.slice(0, 8) + '...' : node.name
      ctx.fillText(displayName, pos.x, pos.y + 4)
      ctx.fillStyle = color
      ctx.font = '9px sans-serif'
      ctx.fillText(NODE_LABELS[node.type] || node.type, pos.x, pos.y + 18)
    })
  }, [nodes, links, positions, filterType, searchText])

  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const filteredNodes = nodes.filter(n => {
      if (filterType && n.type !== filterType) return false
      if (searchText && !n.name.toLowerCase().includes(searchText.toLowerCase())) return false
      return true
    })
    for (const node of filteredNodes) {
      const pos = positions[node.id]
      if (pos && Math.abs(pos.x - x) < 20 && Math.abs(pos.y - y) < 20) {
        setSelectedNode(node)
        setDrawerOpen(true)
        return
      }
    }
  }, [nodes, positions, filterType, searchText])

  const handleCreateNode = useCallback(async () => {
    try {
      const values = await form.validateFields()
      const newNode: KnowledgeNode = {
        id: `node-${Date.now()}`,
        type: values.node_type,
        name: values.name,
        properties: {},
        tags: values.tags || [],
        confidence: values.confidence || 1.0,
      }
      setNodes(prev => [...prev, newNode])
      message.success(`节点 ${values.name} 创建成功`)
      setCreateModalOpen(false)
      form.resetFields()
    } catch {
      // validation failed
    }
  }, [form])

  const handleCreateLink = useCallback(async () => {
    try {
      const values = await linkForm.validateFields()
      const newLink: KnowledgeLink = {
        id: `link-${Date.now()}`,
        source: values.source_node_id,
        target: values.target_node_id,
        type: values.link_type,
        confidence: values.confidence || 1.0,
      }
      setLinks(prev => [...prev, newLink])
      message.success('关联创建成功')
      setLinkModalOpen(false)
      linkForm.resetFields()
    } catch {
      // validation failed
    }
  }, [linkForm, nodes])

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Card size="small" bodyStyle={{ padding: '8px 16px' }}>
        <Space>
          <Select
            placeholder="按节点类型过滤"
            allowClear
            style={{ width: 160 }}
            value={filterType}
            onChange={setFilterType}
            options={Object.entries(NODE_LABELS).map(([value, label]) => ({ value, label }))}
          />
          <Input
            placeholder="搜索节点名称"
            prefix={<SearchOutlined />}
            style={{ width: 200 }}
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
          />
          <Button icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>创建节点</Button>
          <Button icon={<PlusOutlined />} onClick={() => setLinkModalOpen(true)}>创建关联</Button>
          <Tooltip title="快照">
            <Button icon={<CameraOutlined />}>快照</Button>
          </Tooltip>
        </Space>
      </Card>

      <Card bodyStyle={{ padding: 0, flex: 1, position: 'relative' }} style={{ flex: 1 }}>
        <div style={{ position: 'absolute', top: 8, right: 8, zIndex: 10 }}>
          <Space>
            {Object.entries(NODE_LABELS).map(([type, label]) => (
              <Tag key={type} color={NODE_COLORS[type]}>{label}</Tag>
            ))}
          </Space>
        </div>
        <canvas
          ref={canvasRef}
          onClick={handleCanvasClick}
          style={{ width: '100%', height: '100%', cursor: 'pointer' }}
        />
      </Card>

      <Card size="small">
        <Space size="large">
          <span>节点: <Badge count={nodes.length} style={{ backgroundColor: '#1890ff' }} /></span>
          <span>关联: <Badge count={links.length} style={{ backgroundColor: '#52c41a' }} /></span>
          <span>类型覆盖: {new Set(nodes.map(n => n.type)).size}/7</span>
        </Space>
      </Card>

      <Drawer
        title={selectedNode ? `${NODE_LABELS[selectedNode.type] || ''} - ${selectedNode.name}` : '节点详情'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={400}
      >
        {selectedNode && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="ID">{selectedNode.id}</Descriptions.Item>
            <Descriptions.Item label="类型">
              <Tag color={NODE_COLORS[selectedNode.type]}>{NODE_LABELS[selectedNode.type]}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="名称">{selectedNode.name}</Descriptions.Item>
            <Descriptions.Item label="置信度">{(selectedNode.confidence * 100).toFixed(1)}%</Descriptions.Item>
            <Descriptions.Item label="标签">
              {selectedNode.tags.map(t => <Tag key={t}>{t}</Tag>)}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>

      <Modal title="创建知识节点" open={createModalOpen} onOk={handleCreateNode} onCancel={() => setCreateModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="node_type" label="节点类型" rules={[{ required: true }]}>
            <Select options={Object.entries(NODE_LABELS).map(([v, l]) => ({ value: v, label: l }))} />
          </Form.Item>
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="tags" label="标签">
            <Select mode="tags" placeholder="输入标签" />
          </Form.Item>
          <Form.Item name="confidence" label="置信度" initialValue={1.0}>
            <Select options={[
              { value: 1.0, label: '1.0 - 确认' },
              { value: 0.8, label: '0.8 - 高' },
              { value: 0.5, label: '0.5 - 中' },
              { value: 0.3, label: '0.3 - 低' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="创建知识关联" open={linkModalOpen} onOk={handleCreateLink} onCancel={() => setLinkModalOpen(false)}>
        <Form form={linkForm} layout="vertical">
          <Form.Item name="source_node_id" label="源节点" rules={[{ required: true }]}>
            <Select options={nodes.map(n => ({ value: n.id, label: `${n.name} (${NODE_LABELS[n.type]})` }))} />
          </Form.Item>
          <Form.Item name="target_node_id" label="目标节点" rules={[{ required: true }]}>
            <Select options={nodes.map(n => ({ value: n.id, label: `${n.name} (${NODE_LABELS[n.type]})` }))} />
          </Form.Item>
          <Form.Item name="link_type" label="关联类型" rules={[{ required: true }]}>
            <Select options={[
              { value: 'derives_from', label: '派生自' },
              { value: 'constrains', label: '约束' },
              { value: 'implements', label: '实现' },
              { value: 'uses_material', label: '使用材料' },
              { value: 'produced_by', label: '由...生产' },
              { value: 'monitored_by', label: '由...监控' },
              { value: 'maintained_by', label: '由...维护' },
              { value: 'affects', label: '影响' },
              { value: 'depends_on', label: '依赖于' },
            ]} />
          </Form.Item>
          <Form.Item name="confidence" label="置信度" initialValue={1.0}>
            <Select options={[
              { value: 1.0, label: '1.0 - 确认' },
              { value: 0.8, label: '0.8 - 高' },
              { value: 0.5, label: '0.5 - 中' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default KnowledgeGraphPage