import { useState, useEffect } from 'react'
import {
  Card, Table, Tag, Row, Col, Statistic, Progress, Typography,
  Breadcrumb, Select, Space, Timeline, Badge, Tooltip, Tabs,
} from 'antd'
import {
  SafetyCertificateOutlined, CheckCircleOutlined, ClockCircleOutlined,
  FileProtectOutlined, AuditOutlined, WarningOutlined, LockOutlined,
} from '@ant-design/icons'
import { certApi } from '../../api/v6Api'

const { Title, Text } = Typography

interface ChecklistItem {
  clause: string
  requirement: string
  status: 'Compliant' | 'Partial' | 'NonCompliant' | 'NotAssessed'
  evidence_count: number
}

interface EvidencePackage {
  package_id: string
  checklist_id: string
  project_id: string
  is_complete: boolean
  is_locked: boolean
  version: number
}

export default function CertificationDashboardPage() {
  const [checklistItems, setChecklistItems] = useState<ChecklistItem[]>([])
  const [packages, setPackages] = useState<EvidencePackage[]>([])
  const [selectedRegulation, setSelectedRegulation] = useState('CS-25')

  useEffect(() => {
    setChecklistItems(mockChecklistItems())
    setPackages(mockPackages())
  }, [selectedRegulation])

  const compliantCount = checklistItems.filter(i => i.status === 'Compliant').length
  const partialCount = checklistItems.filter(i => i.status === 'Partial').length
  const nonCompliantCount = checklistItems.filter(i => i.status === 'NonCompliant').length
  const notAssessedCount = checklistItems.filter(i => i.status === 'NotAssessed').length
  const totalItems = checklistItems.length
  const compliancePercent = totalItems > 0 ? Math.round(compliantCount / totalItems * 100) : 0

  const columns = [
    {
      title: 'Clause',
      dataIndex: 'clause',
      key: 'clause',
      render: (text: string) => <Text strong style={{ fontFamily: 'monospace' }}>{text}</Text>,
    },
    { title: 'Requirement', dataIndex: 'requirement', key: 'requirement' },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const config: Record<string, { color: string; icon: any }> = {
          Compliant: { color: 'success', icon: <CheckCircleOutlined /> },
          Partial: { color: 'warning', icon: <ClockCircleOutlined /> },
          NonCompliant: { color: 'error', icon: <WarningOutlined /> },
          NotAssessed: { color: 'default', icon: <AuditOutlined /> },
        }
        const c = config[status] || config.NotAssessed
        return <Tag icon={c.icon} color={c.color}>{status}</Tag>
      },
    },
    {
      title: 'Evidence',
      dataIndex: 'evidence_count',
      key: 'evidence',
      render: (count: number) => <Badge count={count} style={{ backgroundColor: count > 0 ? '#52c41a' : '#d9d9d9' }} />,
    },
  ]

  const pkgColumns = [
    { title: 'Package ID', dataIndex: 'package_id', key: 'package_id' },
    { title: 'Project', dataIndex: 'project_id', key: 'project_id' },
    {
      title: 'Complete',
      dataIndex: 'is_complete',
      key: 'complete',
      render: (v: boolean) => v ? <Tag color="success">Yes</Tag> : <Tag>No</Tag>,
    },
    {
      title: 'Locked',
      dataIndex: 'is_locked',
      key: 'locked',
      render: (v: boolean) => v ? <Tag icon={<LockOutlined />} color="red">Locked</Tag> : <Tag>Open</Tag>,
    },
    { title: 'Version', dataIndex: 'version', key: 'version' },
  ]

  return (
    <div style={{ padding: 0 }}>
      <Breadcrumb items={[
        { title: 'AeroForge-X' },
        { title: 'V6 Programs' },
        { title: 'Certification Dashboard' },
      ]} style={{ marginBottom: 16 }} />

      <Title level={3} style={{ marginBottom: 24 }}>
        <SafetyCertificateOutlined style={{ marginRight: 8 }} />
        Certification Dashboard
        <Text type="secondary" style={{ fontSize: 14, marginLeft: 12 }}>
          Compliance tracking, evidence assembly, and airworthiness verification
        </Text>
      </Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Compliance Rate" value={compliancePercent} suffix="%" prefix={<CheckCircleOutlined />} valueStyle={{ color: compliancePercent >= 80 ? '#3f8600' : '#cf1322' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Compliant" value={compliantCount} prefix={<CheckCircleOutlined />} valueStyle={{ color: '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Partial / Non-Compliant" value={partialCount + nonCompliantCount} prefix={<WarningOutlined />} valueStyle={{ color: '#faad14' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" hoverable>
            <Statistic title="Evidence Packages" value={packages.length} prefix={<FileProtectOutlined />} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={16}>
          <Card title="Compliance Progress" size="small">
            <Progress
              percent={compliancePercent}
              strokeColor={{ '0%': '#108ee9', '100%': '#87d068' }}
              style={{ marginBottom: 12 }}
            />
            <Row gutter={16}>
              <Col span={6}><Progress percent={totalItems > 0 ? Math.round(compliantCount / totalItems * 100) : 0} size="small" format={() => `${compliantCount} Compliant`} strokeColor="#52c41a" /></Col>
              <Col span={6}><Progress percent={totalItems > 0 ? Math.round(partialCount / totalItems * 100) : 0} size="small" format={() => `${partialCount} Partial`} strokeColor="#faad14" /></Col>
              <Col span={6}><Progress percent={totalItems > 0 ? Math.round(nonCompliantCount / totalItems * 100) : 0} size="small" format={() => `${nonCompliantCount} Non-Compliant`} strokeColor="#ff4d4f" /></Col>
              <Col span={6}><Progress percent={totalItems > 0 ? Math.round(notAssessedCount / totalItems * 100) : 0} size="small" format={() => `${notAssessedCount} Not Assessed`} strokeColor="#d9d9d9" /></Col>
            </Row>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="Certification Timeline" size="small">
            <Timeline
              items={[
                { color: 'green', children: 'CS-25.571 Damage Tolerance - Verified' },
                { color: 'green', children: 'CS-25.613 Material Strength - Evidence Complete' },
                { color: 'yellow', children: 'CS-25.1309 Equipment & Systems - In Progress' },
                { color: 'gray', children: 'CS-25.729 Retracting Mechanism - Pending' },
                { color: 'gray', children: 'CS-25.853 Flammability - Not Started' },
              ]}
            />
          </Card>
        </Col>
      </Row>

      <Tabs
        items={[
          {
            key: 'checklist',
            label: 'Compliance Checklist',
            children: (
              <Card
                extra={
                  <Select value={selectedRegulation} onChange={setSelectedRegulation} style={{ width: 200 }}>
                    <Select.Option value="CS-25">EASA CS-25</Select.Option>
                    <Select.Option value="FAR-25">FAA Part 25</Select.Option>
                    <Select.Option value="CS-23">EASA CS-23</Select.Option>
                  </Select>
                }
              >
                <Table dataSource={checklistItems} columns={columns} rowKey="clause" size="small" pagination={{ pageSize: 10 }} />
              </Card>
            ),
          },
          {
            key: 'evidence',
            label: 'Evidence Packages',
            children: (
              <Card>
                <Table dataSource={packages} columns={pkgColumns} rowKey="package_id" size="small" pagination={{ pageSize: 8 }} />
              </Card>
            ),
          },
        ]}
      />
    </div>
  )
}

function mockChecklistItems(): ChecklistItem[] {
  return [
    { clause: 'CS-25.571', requirement: 'Damage tolerance and fatigue evaluation of structure', status: 'Compliant', evidence_count: 5 },
    { clause: 'CS-25.613', requirement: 'Material strength properties and material design values', status: 'Compliant', evidence_count: 3 },
    { clause: 'CS-25.619', requirement: 'Special factors for castings', status: 'Partial', evidence_count: 1 },
    { clause: 'CS-25.1309', requirement: 'Equipment, systems, and installations', status: 'Partial', evidence_count: 2 },
    { clause: 'CS-25.729', requirement: 'Retracting mechanism', status: 'NonCompliant', evidence_count: 0 },
    { clause: 'CS-25.853', requirement: 'Compartment interiors - flammability', status: 'NotAssessed', evidence_count: 0 },
    { clause: 'CS-25.856', requirement: 'Thermal/acoustic insulation materials', status: 'NotAssessed', evidence_count: 0 },
    { clause: 'CS-25.601', requirement: 'General - structure design', status: 'Compliant', evidence_count: 4 },
    { clause: 'CS-25.603', requirement: 'Materials and workmanship', status: 'Compliant', evidence_count: 6 },
    { clause: 'CS-25.609', requirement: 'Protection of structure', status: 'Partial', evidence_count: 1 },
  ]
}

function mockPackages(): EvidencePackage[] {
  return [
    { package_id: 'PKG-001', checklist_id: 'CL-CS25-001', project_id: 'PRJ-A320', is_complete: true, is_locked: true, version: 3 },
    { package_id: 'PKG-002', checklist_id: 'CL-CS25-002', project_id: 'PRJ-A320', is_complete: false, is_locked: false, version: 1 },
    { package_id: 'PKG-003', checklist_id: 'CL-CS25-003', project_id: 'PRJ-C919', is_complete: false, is_locked: false, version: 2 },
  ]
}