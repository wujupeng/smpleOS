import React, { useState } from 'react'
import { Card, Input, Button, Space, Table, Tag, Tabs, Select, Slider, Progress, List, Statistic, Row, Col, Alert, message } from 'antd'
import { SearchOutlined, ThunderboltOutlined, ExperimentOutlined, SafetyCertificateOutlined } from '@ant-design/icons'

const NODE_COLORS: Record<string, string> = {
  requirement: '#1890ff', design: '#52c41a', structure: '#fa8c16',
  material: '#722ed1', manufacturing: '#eb2f96', flight: '#13c2c2', maintenance: '#f5222d',
}

const NODE_LABELS: Record<string, string> = {
  requirement: '需求', design: '设计', structure: '结构',
  material: '材料', manufacturing: '制造', flight: '飞行', maintenance: '维护',
}

interface ImpactNode {
  node_id: string
  node_type: string
  depth: number
  confidence: number
  path: string[]
}

interface Anomaly {
  anomaly_id: string
  anomaly_type: string
  severity: string
  description: string
  remediation: string
  status: string
}

const KnowledgeAnalysisPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('impact')
  const [impactSource, setImpactSource] = useState('')
  const [impactDepth, setImpactDepth] = useState(3)
  const [impactResults, setImpactResults] = useState<ImpactNode[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [qualityMetrics, setQualityMetrics] = useState<any>(null)
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])

  const handleImpactAnalysis = () => {
    if (!impactSource) {
      message.warning('请输入源节点ID')
      return
    }
    const mockResults: ImpactNode[] = [
      { node_id: 'n2', node_type: 'design', depth: 1, confidence: 0.85, path: ['derives_from'] },
      { node_id: 'n3', node_type: 'structure', depth: 2, confidence: 0.68, path: ['derives_from', 'implements'] },
      { node_id: 'n4', node_type: 'material', depth: 3, confidence: 0.54, path: ['derives_from', 'implements', 'uses_material'] },
      { node_id: 'n5', node_type: 'manufacturing', depth: 3, confidence: 0.49, path: ['derives_from', 'implements', 'produced_by'] },
    ]
    setImpactResults(mockResults)
    message.success(`影响分析完成，影响 ${mockResults.length} 个节点`)
  }

  const handleSearch = () => {
    if (!searchQuery) return
    const mockResults = [
      { node_id: 'n1', node_type: 'requirement', name: '翼展要求', score: 0.95 },
      { node_id: 'n2', node_type: 'design', name: '机翼设计方案', score: 0.82 },
      { node_id: 'n3', node_type: 'structure', name: '翼梁结构', score: 0.71 },
    ]
    setSearchResults(mockResults)
  }

  const handleQualityAssess = () => {
    setQualityMetrics({
      completeness: 0.71, consistency: 0.85, timeliness: 0.92,
      connectivity: 0.78, coverage: 0.65, freshness: 0.88, overall_score: 0.79,
    })
    setAnomalies([
      { anomaly_id: 'a1', anomaly_type: 'orphan', severity: 'medium', description: '孤立节点: 电池规格 (material)', remediation: '添加关联或移除', status: 'open' },
      { anomaly_id: 'a2', anomaly_type: 'stale', severity: 'low', description: '过期节点: 旧版飞控参数 (requirement)', remediation: '更新或归档', status: 'open' },
    ])
  }

  const impactColumns = [
    { title: '节点ID', dataIndex: 'node_id', key: 'id' },
    { title: '类型', dataIndex: 'node_type', key: 'type', render: (t: string) => <Tag color={NODE_COLORS[t]}>{NODE_LABELS[t]}</Tag> },
    { title: '传播深度', dataIndex: 'depth', key: 'depth', render: (d: number) => <Tag color={d === 1 ? 'green' : d === 2 ? 'orange' : 'red'}>L{d}</Tag> },
    { title: '置信度', dataIndex: 'confidence', key: 'conf', render: (c: number) => <Progress percent={Math.round(c * 100)} size="small" /> },
    { title: '传播路径', dataIndex: 'path', key: 'path', render: (p: string[]) => p.map((s, i) => <Tag key={i}>{s}</Tag>) },
  ]

  return (
    <div style={{ height: '100%', overflow: 'auto' }}>
      <Tabs activeKey={activeTab} onChange={setActiveTab} style={{ padding: '0 16px' }}>
        <Tabs.TabPane tab={<span><ThunderboltOutlined /> 影响分析</span>} key="impact">
          <Card title="知识影响传播分析" size="small" style={{ marginBottom: 16 }}>
            <Space style={{ marginBottom: 16 }}>
              <Input placeholder="输入源节点ID" value={impactSource} onChange={e => setImpactSource(e.target.value)} style={{ width: 300 }} />
              <div style={{ width: 200 }}>
                <span>传播深度: {impactDepth}</span>
                <Slider min={1} max={10} value={impactDepth} onChange={setImpactDepth} />
              </div>
              <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleImpactAnalysis}>执行影响分析</Button>
            </Space>
            {impactResults.length > 0 && (
              <>
                <Alert message={`影响传播完成：共影响 ${impactResults.length} 个节点`} type="success" style={{ marginBottom: 12 }} showIcon />
                <Table dataSource={impactResults} columns={impactColumns} rowKey="node_id" size="small" pagination={false} />
              </>
            )}
          </Card>
        </Tabs.TabPane>

        <Tabs.TabPane tab={<span><SearchOutlined /> 知识搜索</span>} key="search">
          <Card title="知识搜索" size="small">
            <Space style={{ marginBottom: 16 }}>
              <Input placeholder="输入搜索关键词" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} style={{ width: 400 }} prefix={<SearchOutlined />} />
              <Select placeholder="搜索模式" defaultValue="hybrid" style={{ width: 120 }} options={[
                { value: 'hybrid', label: '混合搜索' },
                { value: 'semantic', label: '语义搜索' },
                { value: 'keyword', label: '关键词搜索' },
              ]} />
              <Button type="primary" onClick={handleSearch}>搜索</Button>
            </Space>
            <List
              dataSource={searchResults}
              renderItem={(item: any) => (
                <List.Item>
                  <List.Item.Meta
                    title={<span><Tag color={NODE_COLORS[item.node_type]}>{NODE_LABELS[item.node_type]}</Tag> {item.name}</span>}
                    description={`相似度: ${(item.score * 100).toFixed(1)}% | ID: ${item.node_id}`}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Tabs.TabPane>

        <Tabs.TabPane tab={<span><SafetyCertificateOutlined /> 质量评估</span>} key="quality">
          <Card title="知识质量评估" size="small" extra={<Button type="primary" onClick={handleQualityAssess}>评估质量</Button>}>
            {qualityMetrics && (
              <>
                <Row gutter={16} style={{ marginBottom: 24 }}>
                  <Col span={4}><Statistic title="完整性" value={qualityMetrics.completeness * 100} suffix="%" precision={1} /></Col>
                  <Col span={4}><Statistic title="一致性" value={qualityMetrics.consistency * 100} suffix="%" precision={1} /></Col>
                  <Col span={4}><Statistic title="时效性" value={qualityMetrics.timeliness * 100} suffix="%" precision={1} /></Col>
                  <Col span={4}><Statistic title="连通性" value={qualityMetrics.connectivity * 100} suffix="%" precision={1} /></Col>
                  <Col span={4}><Statistic title="覆盖率" value={qualityMetrics.coverage * 100} suffix="%" precision={1} /></Col>
                  <Col span={4}><Statistic title="综合评分" value={qualityMetrics.overall_score * 100} suffix="%" precision={1} valueStyle={{ color: qualityMetrics.overall_score >= 0.8 ? '#52c41a' : '#fa8c16' }} /></Col>
                </Row>
                <Card title="知识异常" size="small">
                  <List
                    dataSource={anomalies}
                    renderItem={(a: Anomaly) => (
                      <List.Item actions={[<Button size="small">处理</Button>, <Button size="small">忽略</Button>]}>
                        <List.Item.Meta
                          title={<span><Tag color={a.severity === 'high' ? 'red' : a.severity === 'medium' ? 'orange' : 'blue'}>{a.severity}</Tag> <Tag>{a.anomaly_type}</Tag> {a.description}</span>}
                          description={`建议: ${a.remediation}`}
                        />
                      </List.Item>
                    )}
                  />
                </Card>
              </>
            )}
          </Card>
        </Tabs.TabPane>
      </Tabs>
    </div>
  )
}

export default KnowledgeAnalysisPage