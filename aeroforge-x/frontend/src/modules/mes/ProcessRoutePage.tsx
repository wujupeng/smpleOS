import { useState } from 'react'
import {
  Typography, Card, Button, Tag, Space, Input, message, Empty, Row, Col,
  Table, Descriptions, Form, Select,
} from 'antd'
import {
  ToolOutlined, ThunderboltOutlined, SafetyCertificateOutlined,
  CheckCircleOutlined, SearchOutlined,
} from '@ant-design/icons'
import apiClient from '../../services/apiClient'

const { Title } = Typography

const opTypeConfig: Record<string, { color: string; label: string }> = {
  assembly: { color: 'blue', label: '装配' },
  machining: { color: 'cyan', label: '加工' },
  inspection: { color: 'orange', label: '检验' },
  installation: { color: 'green', label: '安装' },
  testing: { color: 'purple', label: '测试' },
  quality_gate: { color: 'red', label: '质量门控' },
}

export default function ProcessRoutePage() {
  const [routes, setRoutes] = useState<Record<string, unknown>[]>([])
  const [selectedRoute, setSelectedRoute] = useState<Record<string, unknown> | null>(null)
  const [mbomId, setMbomId] = useState('')
  const [generating, setGenerating] = useState(false)

  const handleGenerate = async () => {
    if (!mbomId) { message.warning('请输入mBOM ID'); return }
    setGenerating(true)
    try {
      const resp = await apiClient.post('/mes/routes/generate', {
        mbom_id: mbomId,
        mbom_data: { id: mbom_id, mbom_code: mbomId, root_item: { children: [
          { item_code: 'MBOM-WING', name: '左翼装配组件', children: [] },
          { item_code: 'MBOM-FUSE', name: '机身前段装配组件', children: [] },
          { item_code: 'MBOM-TAIL', name: '尾翼装配组件', children: [] },
        ]}},
        created_by: 'engineer',
      })
      const routeData = resp.data?.data
      if (routeData) {
        setSelectedRoute(routeData)
        message.success('工艺路线已生成')
      }
    } catch {
      message.error('生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const opColumns = [
    { title: '序号', dataIndex: 'sequence', key: 'sequence', width: 60 },
    { title: '工序名称', dataIndex: 'operation_name', key: 'operation_name' },
    {
      title: '类型',
      dataIndex: 'operation_type',
      key: 'operation_type',
      render: (t: string) => {
        const cfg = opTypeConfig[t] || { color: 'default', label: t }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    { title: '工位', dataIndex: 'station', key: 'station' },
    { title: '设备', dataIndex: 'equipment', key: 'equipment' },
    { title: '预估工时(h)', dataIndex: 'estimated_hours', key: 'estimated_hours' },
    {
      title: '检验点',
      key: 'qc',
      render: (_: unknown, record: Record<string, unknown>) =>
        record.is_quality_checkpoint
          ? <Tag color="orange" icon={<SafetyCertificateOutlined />}>IPQC</Tag>
          : record.is_mandatory_gate
          ? <Tag color="red" icon={<CheckCircleOutlined />}>FQC</Tag>
          : null,
    },
  ]

  return (
    <div>
      <Card title="工艺路线自动生成" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Input placeholder="输入mBOM ID" value={mbomId} onChange={(e) => setMbomId(e.target.value)} style={{ width: 200 }} />
          <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleGenerate} loading={generating}>
            生成工艺路线
          </Button>
        </Space>
      </Card>

      {selectedRoute && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="路线编码">{selectedRoute.route_code as string}</Descriptions.Item>
                  <Descriptions.Item label="工序数">{selectedRoute.operation_count as number}</Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="总工时">{selectedRoute.total_estimated_hours as number}h</Descriptions.Item>
                  <Descriptions.Item label="状态">
                    <Tag color={selectedRoute.status === 'published' ? 'green' : 'blue'}>{selectedRoute.status as string}</Tag>
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
          </Row>

          <Card title="工序列表">
            <Table
              columns={opColumns}
              dataSource={(selectedRoute.operations as Record<string, unknown>[])?.map((op, i) => ({ ...op, key: i })) || []}
              pagination={false}
              size="small"
            />
          </Card>
        </>
      )}

      {!selectedRoute && (
        <Card>
          <Empty description="请输入mBOM ID并生成工艺路线" />
        </Card>
      )}
    </div>
  )
}