import { useState, useEffect, useCallback } from 'react'
import {
  Card, Table, Tag, Space, Statistic, Row, Col, Progress, Button,
  Typography, Breadcrumb, Input, Select, Tooltip, Badge, Steps,
} from 'antd'
import {
  LinkOutlined, CheckCircleOutlined, WarningOutlined,
  CloseCircleOutlined, SearchOutlined, NodeIndexOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons'
import { certApi } from '../../api/v6Api'

const { Title, Text } = Typography
const { Option } = Select

interface TraceNode {
  node_id: string
  node_type: string
  name: string
  status: string
}

interface TraceLink {
  source_id: string
  target_id: string
  link_type: string
  confidence: number
}

export default function RequirementsTraceabilityPage() {
  const [nodes, setNodes] = useState<TraceNode[]>([])
  const [links, setLinks] = useState<TraceLink[]>([])
  const [searchText, setSearchText] = useState('')
  const [filterType, setFilterType] = useState<string>('all')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setNodes(mockNodes())
    setLinks(mockLinks())
  }, [])

  const coveragePercent = nodes.length > 0
    ? Math.round(nodes.filter(n => n.status === 'Covered').length / nodes.length * 100)
    : 0

  const filteredNodes = nodes.filter(n => {
    const matchSearch = !searchText || n.name.toLowerCase().includes(searchText.toLowerCase()) || n.node_id.toLowerCase().includes(searchText.toLowerCase())
    const matchType = filterType === 'all' || n.node_type === filterType
    return matchSearch && matchType
  })

  const nodeTypeCounts = nodes.reduce((acc, n) => {
    acc[n.node_type] = (acc[n.node_type] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  const columns = [
    {
      title: 'Node ID',
      dataIndex: 'node_id',
      key: 'node_id',
      render: (text: string) => <Button type="link" size="small">{text}</Button>,
    },
    {
      title: 'Type',
      dataIndex: 'node_type',
      key: 'node_type',
      render: (type: string) => {
        const colors: Record<string, string> = {
          Requirement: 'blue', DesignElement: 'cyan', TestCase: 'green',
          EvidenceItem: 'orange', CertificationItem: 'purple',
        }
        return <Tag color={colors[type] || 'default'}>{type}</Tag>
      },
    },
    { title: 'Name', dataIndex: 'name', key: 'name' },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        if (status === 'Covered') return <Tag icon={<CheckCircleOutlined />} color="success">Covered</Tag>
        if (status === 'Partial') return <Tag icon={<WarningOutlined />} color="warning">Partial</Tag>
        return <Tag icon={<CloseCircleOutlined />} color="error">Gap</Tag>
      },
    },
    {
      title: 'Trace Links',
      key: 'links',
      render: (_: any, record: TraceNode) => {
        const incoming = links.filter(l => l.target_id === record.node_id).length
        const outgoing = links.filter(l => l.source_id === record.node_id).length
        return (
          <Space>
            <Tooltip title="Incoming links"><Badge count={incoming} style={{ backgroundColor: '#1890ff' }} /></Tooltip>
            <Tooltip title="Outgoing links"><Badge count={outgoing} style={{ backgroundColor: '#52c41a' }} /></Tooltip>
          </Space>
        )
      },
    },
  ]

  return (
    <div style={{ padding: 0 }}>
      <Breadcrumb items={[
        { title: 'AeroForge-X' },
        { title: 'V6 Programs' },
        { title: 'Requirements Traceability' },
      ]} style={{ marginBottom: 16 }} />

      <Title level={3} style={{ marginBottom: 24 }}>
        <NodeIndexOutlined style={{ marginRight: 8 }} />
        Requirements Traceability Matrix
        <Text type="secondary" style={{ fontSize: 14, marginLeft: 12 }}>
          Forward & backward traceability with coverage analysis
        </Text>
      </Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Total Nodes" value={nodes.length} prefix={<NodeIndexOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Coverage" value={coveragePercent} suffix="%" prefix={<CheckCircleOutlined />} valueStyle={{ color: coveragePercent >= 80 ? '#3f8600' : '#cf1322' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Trace Links" value={links.length} prefix={<LinkOutlined />} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Gaps" value={nodes.filter(n => n.status === 'Gap').length} prefix={<WarningOutlined />} valueStyle={{ color: '#cf1322' }} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={24}>
          <Card title="Traceability Coverage by Type" size="small">
            <Row gutter={16}>
              {Object.entries(nodeTypeCounts).map(([type, count]) => {
                const covered = nodes.filter(n => n.node_type === type && n.status === 'Covered').length
                const pct = Math.round(covered / count * 100)
                return (
                  <Col span={4} key={type}>
                    <div style={{ textAlign: 'center' }}>
                      <Progress type="circle" percent={pct} size={64} strokeColor={pct >= 80 ? '#52c41a' : '#faad14'} />
                      <div style={{ marginTop: 8, fontSize: 12 }}>{type}</div>
                      <div style={{ fontSize: 10, color: '#999' }}>{covered}/{count}</div>
                    </div>
                  </Col>
                )
              })}
            </Row>
          </Card>
        </Col>
      </Row>

      <Card
        title="Traceability Nodes"
        extra={
          <Space>
            <Input
              placeholder="Search nodes..."
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
              style={{ width: 200 }}
              allowClear
            />
            <Select value={filterType} onChange={setFilterType} style={{ width: 150 }}>
              <Option value="all">All Types</Option>
              <Option value="Requirement">Requirement</Option>
              <Option value="DesignElement">Design Element</Option>
              <Option value="TestCase">Test Case</Option>
              <Option value="EvidenceItem">Evidence</Option>
              <Option value="CertificationItem">Certification</Option>
            </Select>
          </Space>
        }
      >
        <Table
          dataSource={filteredNodes}
          columns={columns}
          rowKey="node_id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 12 }}
        />
      </Card>
    </div>
  )
}

function mockNodes(): TraceNode[] {
  return [
    { node_id: 'REQ-STR-001', node_type: 'Requirement', name: 'Structural Integrity - Wing Box', status: 'Covered' },
    { node_id: 'REQ-STR-002', node_type: 'Requirement', name: 'Fatigue Life - Fuselage', status: 'Covered' },
    { node_id: 'REQ-AER-001', node_type: 'Requirement', name: 'Aerodynamic Efficiency - Cruise', status: 'Partial' },
    { node_id: 'REQ-SYS-001', node_type: 'Requirement', name: 'Avionics Redundancy', status: 'Gap' },
    { node_id: 'DES-WING-001', node_type: 'DesignElement', name: 'Wing Spar Design', status: 'Covered' },
    { node_id: 'DES-FUSE-001', node_type: 'DesignElement', name: 'Fuselage Frame Design', status: 'Covered' },
    { node_id: 'TC-STR-001', node_type: 'TestCase', name: 'Static Load Test - Wing', status: 'Covered' },
    { node_id: 'TC-STR-002', node_type: 'TestCase', name: 'Fatigue Test - Fuselage', status: 'Partial' },
    { node_id: 'EVI-001', node_type: 'EvidenceItem', name: 'Static Test Report STR-2026-001', status: 'Covered' },
    { node_id: 'EVI-002', node_type: 'EvidenceItem', name: 'Fatigue Analysis Report', status: 'Partial' },
    { node_id: 'CERT-25-571', node_type: 'CertificationItem', name: 'CS-25.571 Damage Tolerance', status: 'Covered' },
    { node_id: 'CERT-25-1309', node_type: 'CertificationItem', name: 'CS-25.1309 Equipment & Systems', status: 'Gap' },
  ]
}

function mockLinks(): TraceLink[] {
  return [
    { source_id: 'REQ-STR-001', target_id: 'DES-WING-001', link_type: 'satisfies', confidence: 0.95 },
    { source_id: 'REQ-STR-002', target_id: 'DES-FUSE-001', link_type: 'satisfies', confidence: 0.90 },
    { source_id: 'DES-WING-001', target_id: 'TC-STR-001', link_type: 'verified_by', confidence: 1.0 },
    { source_id: 'DES-FUSE-001', target_id: 'TC-STR-002', link_type: 'verified_by', confidence: 0.85 },
    { source_id: 'TC-STR-001', target_id: 'EVI-001', link_type: 'produces', confidence: 1.0 },
    { source_id: 'TC-STR-002', target_id: 'EVI-002', link_type: 'produces', confidence: 0.80 },
    { source_id: 'EVI-001', target_id: 'CERT-25-571', link_type: 'demonstrates', confidence: 0.95 },
    { source_id: 'EVI-002', target_id: 'CERT-25-571', link_type: 'demonstrates', confidence: 0.70 },
  ]
}