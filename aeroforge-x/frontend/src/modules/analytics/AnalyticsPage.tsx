import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Card, Typography, Space, Tag, Button, Table, Modal, Form,
  Input, Select, message, Row, Col, Statistic,
  Tabs, Empty, Alert, Progress,
} from 'antd'
import {
  BarChartOutlined, FileTextOutlined, PlusOutlined,
  ThunderboltOutlined, DownloadOutlined, ShareAltOutlined,
  CheckCircleOutlined, WarningOutlined,
} from '@ant-design/icons'
import apiClient from '../../services/apiClient'
import { useProjectStore } from '../../stores/projectStore'

const { Text } = Typography

interface MetricsData {
  design_progress_pct?: number
  violation_rate?: number
  cae_completion_rate?: number
  work_order_completion_rate?: number
  on_time_rate?: number
  avg_workstation_utilization?: number
  iqc_pass_rate?: number
  capa_close_rate?: number
  avg_cpk?: number
  trace_completeness_rate?: number
  avg_query_time_ms?: number
  po_on_time_rate?: number
  avg_inventory_turnover?: number
  [key: string]: unknown
}

interface ReportInfo {
  id: string
  name: string
  report_type: string
  format: string
  status: string
  file_key: string
  schedule_cron: string
  share_token: string
  generated_at: string
}

interface CrossDomainLink {
  source: string
  impact: string
  correlation: string
  description: string
}

export default function AnalyticsPage() {
  const { t } = useTranslation()
  const { currentProjectId } = useProjectStore()

  const [designMetrics, setDesignMetrics] = useState<MetricsData | null>(null)
  const [mfgMetrics, setMfgMetrics] = useState<MetricsData | null>(null)
  const [qualityMetrics, setQualityMetrics] = useState<MetricsData | null>(null)
  const [traceMetrics, setTraceMetrics] = useState<MetricsData | null>(null)
  const [supplyMetrics, setSupplyMetrics] = useState<MetricsData | null>(null)
  const [crossDomainLinks, setCrossDomainLinks] = useState<CrossDomainLink[]>([])

  const [reports, setReports] = useState<ReportInfo[]>([])
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [reportForm] = Form.useForm()

  const loadMetrics = useCallback(async () => {
    const params = currentProjectId ? { project_id: currentProjectId } : {}
    try {
      const [d, m, q, tr, s, c] = await Promise.all([
        apiClient.get('/analytics/design', { params }),
        apiClient.get('/analytics/manufacturing', { params }),
        apiClient.get('/analytics/quality', { params }),
        apiClient.get('/analytics/traceability', { params }),
        apiClient.get('/analytics/supply-chain', { params }),
        apiClient.get('/analytics/cross-domain', { params }),
      ])
      setDesignMetrics(d.data?.data)
      setMfgMetrics(m.data?.data)
      setQualityMetrics(q.data?.data)
      setTraceMetrics(tr.data?.data)
      setSupplyMetrics(s.data?.data)
      setCrossDomainLinks(c.data?.data?.cross_domain_links ?? [])
    } catch { /* ignore */ }
  }, [currentProjectId])

  const loadReports = useCallback(async () => {
    try {
      const resp = await apiClient.get('/analytics/reports')
      setReports(resp.data?.data?.reports ?? [])
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    loadMetrics()
    loadReports()
  }, [loadMetrics, loadReports])

  const handleCreateReport = async (values: Record<string, unknown>) => {
    try {
      const resp = await apiClient.post('/analytics/reports', {
        ...values,
        tenant_id: currentProjectId || 'default',
        parameters: { project_id: currentProjectId || 'default' },
      })
      const reportId = resp.data?.data?.id
      if (reportId) {
        await apiClient.post(`/analytics/reports/${reportId}/generate`)
        message.success(t('analytics.reportGenSuccess'))
      }
      setCreateModalOpen(false)
      reportForm.resetFields()
      loadReports()
    } catch {
      message.error(t('analytics.reportGenFailed'))
    }
  }

  const handleShare = async (reportId: string) => {
    try {
      const resp = await apiClient.post(`/analytics/reports/${reportId}/share`)
      const token = resp.data?.data?.share_token
      if (token) {
        message.success(t('analytics.shareSuccess', { token }))
      }
    } catch {
      message.error(t('analytics.shareFailed'))
    }
  }

  const reportColumns = [
    { title: t('analytics.reportName'), dataIndex: 'name', key: 'name', width: 180 },
    { title: t('analytics.reportType'), dataIndex: 'report_type', key: 'report_type', width: 120 },
    {
      title: t('analytics.format'),
      dataIndex: 'format',
      key: 'format',
      width: 70,
      render: (v: string) => <Tag>{v?.toUpperCase()}</Tag>,
    },
    {
      title: t('common.status'),
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (v: string) => v === 'completed' ? <Tag color="green">{t('status.completed')}</Tag> : v === 'failed' ? <Tag color="red">{t('status.failed')}</Tag> : <Tag color="processing">{t('status.generating')}</Tag>,
    },
    {
      title: t('analytics.schedule'),
      dataIndex: 'schedule_cron',
      key: 'schedule_cron',
      width: 100,
      render: (v: string) => v ? <Tag color="blue">{v}</Tag> : <Text type="secondary">-</Text>,
    },
    {
      title: t('common.actions'),
      key: 'actions',
      width: 120,
      render: (_: unknown, record: ReportInfo) => (
        <Space>
          {record.status === 'completed' && (
            <Button size="small" icon={<DownloadOutlined />}>{t('common.download')}</Button>
          )}
          <Button size="small" icon={<ShareAltOutlined />} onClick={() => handleShare(record.id)}>{t('analytics.share')}</Button>
        </Space>
      ),
    },
  ]

  const linkColumns = [
    { title: t('analytics.sourceDomain'), dataIndex: 'source', key: 'source', width: 120 },
    { title: t('analytics.impactDomain'), dataIndex: 'impact', key: 'impact', width: 120 },
    {
      title: t('analytics.correlation'),
      dataIndex: 'correlation',
      key: 'correlation',
      width: 80,
      render: (v: string) => <Tag color={v === 'high' ? 'red' : v === 'medium' ? 'orange' : 'green'}>{v}</Tag>,
    },
    { title: t('common.description'), dataIndex: 'description', key: 'description' },
  ]

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('analytics.designProgress')}
              value={designMetrics?.design_progress_pct ?? 0}
              suffix="%"
              prefix={<BarChartOutlined />}
              valueStyle={{ color: (designMetrics?.design_progress_pct ?? 0) >= 70 ? '#3f8600' : '#fa8c16' }}
            />
            <Progress percent={designMetrics?.design_progress_pct ?? 0} size="small" style={{ marginTop: 8 }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('analytics.woCompletionRate')}
              value={mfgMetrics?.work_order_completion_rate ?? 0}
              suffix="%"
              valueStyle={{ color: (mfgMetrics?.work_order_completion_rate ?? 0) >= 80 ? '#3f8600' : '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('analytics.iqcPassRate')}
              value={qualityMetrics?.iqc_pass_rate ?? 0}
              suffix="%"
              valueStyle={{ color: (qualityMetrics?.iqc_pass_rate ?? 0) >= 95 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title={t('analytics.poOnTimeRate')}
              value={supplyMetrics?.po_on_time_rate ?? 0}
              suffix="%"
              valueStyle={{ color: (supplyMetrics?.po_on_time_rate ?? 0) >= 80 ? '#3f8600' : '#fa8c16' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic title={t('analytics.violationRate')} value={designMetrics?.violation_rate ?? 0} suffix="%" valueStyle={{ color: (designMetrics?.violation_rate ?? 0) > 10 ? '#cf1322' : '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title={t('analytics.workstationUtil')} value={mfgMetrics?.avg_workstation_utilization ?? 0} suffix="%" />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title={t('analytics.avgCpk')} value={qualityMetrics?.avg_cpk ?? 0} precision={2} valueStyle={{ color: (qualityMetrics?.avg_cpk ?? 0) >= 1.33 ? '#3f8600' : '#fa8c16' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title={t('analytics.traceCompleteness')} value={traceMetrics?.trace_completeness_rate ?? 0} suffix="%" />
          </Card>
        </Col>
      </Row>

      <Tabs
        defaultActiveKey="cross-domain"
        items={[
          {
            key: 'cross-domain',
            label: <span><BarChartOutlined /> {t('analytics.crossDomain')}</span>,
            children: (
              <Card title={t('analytics.crossDomainChain')}>
                {crossDomainLinks.length > 0 ? (
                  <>
                    <Alert
                      type="info"
                      message={t('analytics.crossDomainCount', { count: crossDomainLinks.length })}
                      style={{ marginBottom: 12 }}
                      showIcon
                    />
                    <Table
                      columns={linkColumns}
                      dataSource={crossDomainLinks.map((l, i) => ({ ...l, key: i }))}
                      size="small"
                      pagination={false}
                    />
                  </>
                ) : (
                  <Empty description={t('analytics.noCrossDomainData')} />
                )}
              </Card>
            ),
          },
          {
            key: 'reports',
            label: <span><FileTextOutlined /> {t('analytics.reports')}</span>,
            children: (
              <Card
                title={t('analytics.reportList')}
                extra={
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
                    {t('analytics.createReport')}
                  </Button>
                }
              >
                <Table
                  columns={reportColumns}
                  dataSource={reports.map(r => ({ ...r, key: r.id }))}
                  size="small"
                  pagination={{ pageSize: 10 }}
                />
              </Card>
            ),
          },
          {
            key: 'detail',
            label: <span><BarChartOutlined /> {t('analytics.detailMetrics')}</span>,
            children: (
              <Row gutter={16}>
                <Col span={12}>
                  <Card title={t('analytics.designMetrics')} size="small">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Text>{t('analytics.designProgressLabel')}: <Text strong>{designMetrics?.design_progress_pct ?? 0}%</Text></Text>
                      <Text>{t('analytics.violationRateLabel')}: <Text strong style={{ color: (designMetrics?.violation_rate ?? 0) > 10 ? '#cf1322' : '#3f8600' }}>{designMetrics?.violation_rate ?? 0}%</Text></Text>
                      <Text>{t('analytics.caeCompletionRate')}: <Text strong>{designMetrics?.cae_completion_rate ?? 0}%</Text></Text>
                      <Text>{t('analytics.avgIterations')}: <Text strong>{designMetrics?.avg_iterations ?? 0}</Text></Text>
                    </Space>
                  </Card>
                </Col>
                <Col span={12}>
                  <Card title={t('analytics.mfgMetrics')} size="small">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Text>{t('analytics.woCompletionLabel')}: <Text strong>{mfgMetrics?.work_order_completion_rate ?? 0}%</Text></Text>
                      <Text>{t('analytics.onTimeRate')}: <Text strong>{mfgMetrics?.on_time_rate ?? 0}%</Text></Text>
                      <Text>{t('analytics.workstationUtilLabel')}: <Text strong>{mfgMetrics?.avg_workstation_utilization ?? 0}%</Text></Text>
                      <Text>{t('analytics.avgDeviation')}: <Text strong>{mfgMetrics?.avg_deviation_mm ?? 0}mm</Text></Text>
                    </Space>
                  </Card>
                </Col>
                <Col span={12} style={{ marginTop: 16 }}>
                  <Card title={t('analytics.qualityMetrics')} size="small">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Text>{t('analytics.iqcPassLabel')}: <Text strong>{qualityMetrics?.iqc_pass_rate ?? 0}%</Text></Text>
                      <Text>{t('analytics.capaCloseRate')}: <Text strong>{qualityMetrics?.capa_close_rate ?? 0}%</Text></Text>
                      <Text>{t('analytics.avgCpkLabel')}: <Text strong>{qualityMetrics?.avg_cpk ?? 0}</Text></Text>
                    </Space>
                  </Card>
                </Col>
                <Col span={12} style={{ marginTop: 16 }}>
                  <Card title={t('analytics.supplyMetrics')} size="small">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Text>{t('analytics.poOnTimeLabel')}: <Text strong>{supplyMetrics?.po_on_time_rate ?? 0}%</Text></Text>
                      <Text>{t('analytics.inventoryTurnover')}: <Text strong>{supplyMetrics?.avg_inventory_turnover ?? 0}</Text></Text>
                      <Text>{t('analytics.shortageAffectedWo')}: <Text strong>{supplyMetrics?.shortage_affected_wo ?? 0}</Text></Text>
                    </Space>
                  </Card>
                </Col>
              </Row>
            ),
          },
        ]}
      />

      <Modal
        title={t('analytics.createReport')}
        open={createModalOpen}
        onCancel={() => setCreateModalOpen(false)}
        onOk={() => reportForm.submit()}
      >
        <Form form={reportForm} layout="vertical" onFinish={handleCreateReport}>
          <Form.Item name="name" label={t('analytics.reportName')} rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="report_type" label={t('analytics.reportType')} rules={[{ required: true }]}>
            <Select options={[
              { value: 'project_weekly', label: t('analytics.projectWeekly') },
              { value: 'quality_monthly', label: t('analytics.qualityMonthly') },
              { value: 'supplier_quarterly', label: t('analytics.supplierQuarterly') },
              { value: 'production_daily', label: t('analytics.productionDaily') },
              { value: 'trace_audit', label: t('analytics.traceAudit') },
            ]} />
          </Form.Item>
          <Form.Item name="template_id" label={t('analytics.reportTemplate')}>
            <Select options={[
              { value: 'project_weekly', label: t('analytics.projectWeekly') },
              { value: 'quality_monthly', label: t('analytics.qualityMonthly') },
              { value: 'supplier_quarterly', label: t('analytics.supplierQuarterly') },
              { value: 'production_daily', label: t('analytics.productionDaily') },
              { value: 'trace_audit', label: t('analytics.traceAudit') },
            ]} />
          </Form.Item>
          <Form.Item name="format" label={t('analytics.outputFormat')} initialValue="pdf">
            <Select options={[
              { value: 'pdf', label: 'PDF' },
              { value: 'excel', label: 'Excel' },
              { value: 'html', label: 'HTML' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
