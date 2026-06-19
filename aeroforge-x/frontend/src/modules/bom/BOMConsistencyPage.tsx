import { useState } from 'react'
import {
  Typography, Card, Button, Tag, Space, Input, message, Empty, Row, Col,
  Table, Descriptions, Alert, Statistic, Form,
} from 'antd'
import {
  CheckCircleOutlined, WarningOutlined, SyncOutlined,
  SwapOutlined, AuditOutlined,
} from '@ant-design/icons'
import apiClient from '../../services/apiClient'

const { Title, Text } = Typography

interface ConsistencyReport {
  is_consistent: boolean
  ebom_item_count: number
  mbom_item_count: number
  sbom_item_count: number
  mapping_completeness: Record<string, unknown>
  attribute_consistency: Record<string, unknown>
  diff_items: DiffItem[]
  errors: string[]
  warnings: string[]
}

interface DiffItem {
  item_code: string
  item_name: string
  diff_type: string
  source_bom: string
  target_bom: string
  details: Record<string, unknown>
  suggestion: string
}

interface SyncSuggestions {
  total_diffs: number
  auto_sync_count: number
  manual_confirm_count: number
  auto_sync_items: DiffItem[]
  manual_confirm_items: DiffItem[]
  recommendation: string
}

const diffTypeConfig: Record<string, { color: string; label: string }> = {
  added: { color: 'green', label: '新增' },
  removed: { color: 'red', label: '删除' },
  modified: { color: 'orange', label: '修改' },
  unmapped: { color: 'volcano', label: '未映射' },
}

export default function BOMConsistencyPage() {
  const [ebomId, setEbomId] = useState('')
  const [mbomId, setMbomId] = useState('')
  const [sbomId, setSbomId] = useState('')
  const [report, setReport] = useState<ConsistencyReport | null>(null)
  const [diffs, setDiffs] = useState<DiffItem[]>([])
  const [suggestions, setSuggestions] = useState<SyncSuggestions | null>(null)
  const [loading, setLoading] = useState(false)

  const handleCheck = async () => {
    if (!ebomId) {
      message.warning('请输入eBOM ID')
      return
    }
    setLoading(true)
    try {
      const resp = await apiClient.post('/bom/consistency/check', {
        ebom_id: ebomId,
        mbom_id: mbomId || undefined,
        sbom_id: sbomId || undefined,
      })
      setReport(resp.data?.data ?? null)

      const diffResp = await apiClient.get('/bom/consistency/diff', {
        params: { ebom_id: ebomId, mbom_id: mbomId || undefined, sbom_id: sbomId || undefined },
      })
      const diffData = diffResp.data?.data
      setDiffs(diffData?.diffs ?? [])
      setSuggestions(diffData?.suggestions ?? null)
    } catch {
      message.error('一致性校验失败')
    } finally {
      setLoading(false)
    }
  }

  const diffColumns = [
    { title: '物料编码', dataIndex: 'item_code', key: 'item_code' },
    { title: '名称', dataIndex: 'item_name', key: 'item_name' },
    {
      title: '差异类型',
      dataIndex: 'diff_type',
      key: 'diff_type',
      render: (t: string) => {
        const cfg = diffTypeConfig[t] || { color: 'default', label: t }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    { title: '来源BOM', dataIndex: 'source_bom', key: 'source_bom' },
    { title: '目标BOM', dataIndex: 'target_bom', key: 'target_bom' },
    {
      title: '原因',
      dataIndex: 'details',
      key: 'details',
      render: (d: Record<string, unknown>) => (d?.reason as string) || '-',
    },
    {
      title: '同步建议',
      dataIndex: 'suggestion',
      key: 'suggestion',
      render: (s: string) => s === 'auto_sync'
        ? <Tag color="green" icon={<SyncOutlined />}>自动同步</Tag>
        : <Tag color="orange" icon={<WarningOutlined />}>手动确认</Tag>,
    },
  ]

  const ebomToMbom = report?.mapping_completeness?.ebom_to_mbom as Record<string, unknown> | undefined
  const mbomToSbom = report?.mapping_completeness?.mbom_to_sbom as Record<string, unknown> | undefined
  const attrConsistency = report?.attribute_consistency as Record<string, unknown> | undefined

  return (
    <div>
      <Card title="BOM 一致性校验" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Input placeholder="eBOM ID" value={ebomId} onChange={(e) => setEbomId(e.target.value)} style={{ width: 160 }} />
          <Input placeholder="mBOM ID (可选)" value={mbomId} onChange={(e) => setMbomId(e.target.value)} style={{ width: 160 }} />
          <Input placeholder="sBOM ID (可选)" value={sbomId} onChange={(e) => setSbomId(e.target.value)} style={{ width: 160 }} />
          <Button type="primary" icon={<AuditOutlined />} onClick={handleCheck} loading={loading}>
            执行校验
          </Button>
        </Space>
      </Card>

      {report && (
        <>
          {report.is_consistent ? (
            <Alert type="success" message="BOM 一致性校验通过" showIcon style={{ marginBottom: 16 }} />
          ) : (
            <Alert
              type="warning"
              message={`BOM 一致性校验发现 ${report.warnings.length} 个问题`}
              description={report.warnings.join('; ')}
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card>
                <Statistic title="eBOM 项数" value={report.ebom_item_count} />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic title="mBOM 项数" value={report.mbom_item_count} />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic title="sBOM 项数" value={report.sbom_item_count} />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="属性不一致"
                  value={(attrConsistency?.inconsistency_count as number) || 0}
                  valueStyle={{ color: ((attrConsistency?.inconsistency_count as number) || 0) > 0 ? '#cf1322' : '#3f8600' }}
                />
              </Card>
            </Col>
          </Row>

          <Row gutter={16} style={{ marginBottom: 16 }}>
            {ebomToMbom && (
              <Col span={12}>
                <Card title="eBOM → mBOM 映射完整性" size="small">
                  <Descriptions column={2} size="small">
                    <Descriptions.Item label="eBOM总项数">{ebomToMbom.total_ebom_items as number}</Descriptions.Item>
                    <Descriptions.Item label="已映射">{ebomToMbom.mapped_items as number}</Descriptions.Item>
                    <Descriptions.Item label="未映射">
                      <Tag color={(ebomToMbom.unmapped_items as number) > 0 ? 'red' : 'green'}>
                        {ebomToMbom.unmapped_items as number}
                      </Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="完整率">{ebomToMbom.completeness_percent as number}%</Descriptions.Item>
                  </Descriptions>
                </Card>
              </Col>
            )}
            {mbomToSbom && (
              <Col span={12}>
                <Card title="mBOM → sBOM 映射完整性" size="small">
                  <Descriptions column={2} size="small">
                    <Descriptions.Item label="mBOM总项数">{mbomToSbom.total_mbom_items as number}</Descriptions.Item>
                    <Descriptions.Item label="sBOM总项数">{mbomToSbom.total_sbom_items as number}</Descriptions.Item>
                    <Descriptions.Item label="sBOM独有">{mbomToSbom.sbom_only_items as number}</Descriptions.Item>
                    <Descriptions.Item label="mBOM独有">{mbomToSbom.mbom_only_items as number}</Descriptions.Item>
                  </Descriptions>
                </Card>
              </Col>
            )}
          </Row>
        </>
      )}

      {suggestions && (
        <Card title="同步建议" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={12}>
              <Card size="small">
                <Statistic
                  title="可自动同步"
                  value={suggestions.auto_sync_count}
                  valueStyle={{ color: '#3f8600' }}
                  prefix={<SyncOutlined />}
                />
              </Card>
            </Col>
            <Col span={12}>
              <Card size="small">
                <Statistic
                  title="需手动确认"
                  value={suggestions.manual_confirm_count}
                  valueStyle={{ color: suggestions.manual_confirm_count > 0 ? '#cf1322' : '#3f8600' }}
                  prefix={<WarningOutlined />}
                />
              </Card>
            </Col>
          </Row>
          {suggestions.recommendation && (
            <Text type="secondary" style={{ marginTop: 8, display: 'block' }}>{suggestions.recommendation}</Text>
          )}
        </Card>
      )}

      <Card title="差异项列表">
        <Table
          columns={diffColumns}
          dataSource={diffs.map((d, i) => ({ ...d, key: i }))}
          pagination={{ pageSize: 10 }}
          size="small"
          locale={{ emptyText: '无差异项' }}
        />
      </Card>
    </div>
  )
}