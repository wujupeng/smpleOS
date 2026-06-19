import { useState } from 'react'
import {
  Card, Typography, Space, Tag, Button, Input, Form,
  message, Descriptions, Row, Col, Statistic, Alert,
  Timeline, Table, Empty, Divider, Progress, Tabs,
} from 'antd'
import {
  RobotOutlined, SendOutlined, CheckCircleOutlined,
  CloseCircleOutlined, SyncOutlined, WarningOutlined,
  ExperimentOutlined, HistoryOutlined, SafetyCertificateOutlined,
} from '@ant-design/icons'
import apiClient from '../../services/apiClient'
import { useProjectStore } from '../../stores/projectStore'

const { Title, Text } = Typography

interface RiskMarker {
  marker_id: string
  category: string
  description: string
  severity: string
  suggestion: string
}

interface FeasibilityReport {
  is_feasible: boolean
  design_rule_violations: Array<Record<string, unknown>>
  overall_score: number
  summary: string
}

interface IterationRecord {
  iteration_id: string
  feedback: string
  adjusted_params: Record<string, unknown>
  timestamp: string
}

interface ProposalInfo {
  id: string
  project_id: string
  status: string
  natural_language_input: string
  parsed_spec: Record<string, unknown>
  generated_model_ref: string
  feasibility_report: FeasibilityReport
  risk_markers: RiskMarker[]
  iteration_history: IterationRecord[]
  clarification_questions: string[]
  created_at: string
}

const statusConfig: Record<string, { color: string; label: string; icon: React.ReactNode }> = {
  pending_review: { color: 'orange', label: '待审核', icon: <WarningOutlined /> },
  confirmed: { color: 'green', label: '已确认', icon: <CheckCircleOutlined /> },
  rejected: { color: 'red', label: '已拒绝', icon: <CloseCircleOutlined /> },
  iterating: { color: 'blue', label: '迭代中', icon: <SyncOutlined /> },
}

const severityConfig: Record<string, { color: string; label: string }> = {
  low: { color: 'default', label: '低' },
  medium: { color: 'orange', label: '中' },
  high: { color: 'red', label: '高' },
  critical: { color: 'red', label: '严重' },
}

export default function AIEnginePage() {
  const [inputText, setInputText] = useState('')
  const [proposal, setProposal] = useState<ProposalInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [iterateInput, setIterateInput] = useState('')
  const { currentProjectId } = useProjectStore()

  const handleGenerate = async () => {
    if (!inputText.trim()) {
      message.warning('请输入飞行器需求描述')
      return
    }
    setLoading(true)
    try {
      const resp = await apiClient.post('/ai/aerogpt/generate', {
        project_id: currentProjectId || 'default',
        tenant_id: 'default',
        natural_language_input: inputText,
        created_by: 'current-user',
      })
      setProposal(resp.data?.data ?? null)
      message.success('方案生成完成')
    } catch {
      message.error('方案生成失败')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirm = async () => {
    if (!proposal) return
    try {
      await apiClient.post(`/ai/proposals/${proposal.id}/confirm`)
      setProposal({ ...proposal, status: 'confirmed' })
      message.success('方案已确认')
    } catch {
      message.error('确认失败')
    }
  }

  const handleReject = async () => {
    if (!proposal) return
    try {
      await apiClient.post(`/ai/proposals/${proposal.id}/reject`, { reason: '用户拒绝' })
      setProposal({ ...proposal, status: 'rejected' })
      message.info('方案已拒绝')
    } catch {
      message.error('拒绝失败')
    }
  }

  const handleIterate = async () => {
    if (!proposal || !iterateInput.trim()) return
    setLoading(true)
    try {
      const resp = await apiClient.post(`/ai/proposals/${proposal.id}/iterate`, {
        feedback: iterateInput,
      })
      setProposal(resp.data?.data ?? null)
      setIterateInput('')
      message.success('迭代完成')
    } catch {
      message.error('迭代失败')
    } finally {
      setLoading(false)
    }
  }

  const paramLabels: Record<string, string> = {
    payload_kg: '载荷(kg)',
    range_km: '航程(km)',
    cruise_speed_kmh: '巡航速度(km/h)',
    takeoff_distance_m: '起飞距离(m)',
    power_type: '动力类型',
    aircraft_type: '飞行器类型',
    vtol: '垂直起降',
    wing_span: '翼展(m)',
    passenger_count: '乘客数',
  }

  const specColumns = [
    {
      title: '参数',
      dataIndex: 'param',
      key: 'param',
      render: (p: string) => paramLabels[p] || p,
    },
    {
      title: '值',
      dataIndex: 'value',
      key: 'value',
      render: (v: unknown) => {
        if (typeof v === 'boolean') return v ? '是' : '否'
        return String(v)
      },
    },
  ]

  const riskColumns = [
    { title: 'ID', dataIndex: 'marker_id', key: 'marker_id', width: 100 },
    { title: '类别', dataIndex: 'category', key: 'category', width: 140 },
    { title: '描述', dataIndex: 'description', key: 'description' },
    {
      title: '严重度',
      dataIndex: 'severity',
      key: 'severity',
      width: 80,
      render: (s: string) => {
        const cfg = severityConfig[s] || { color: 'default', label: s }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    { title: '建议', dataIndex: 'suggestion', key: 'suggestion', ellipsis: true },
  ]

  const specData = proposal?.parsed_spec
    ? Object.entries(proposal.parsed_spec).map(([k, v]) => ({ key: k, param: k, value: v }))
    : []

  const iterationTimeline = proposal?.iteration_history?.map((iter, idx) => ({
    key: idx,
    color: 'blue' as const,
    children: (
      <div>
        <Text strong>迭代 {iter.iteration_id}</Text>
        <br />
        <Text type="secondary">反馈: {iter.feedback}</Text>
        <br />
        <Text type="secondary" style={{ fontSize: 12 }}>
          调整: {JSON.stringify(iter.adjusted_params)}
        </Text>
        <br />
        <Text type="secondary" style={{ fontSize: 12 }}>
          {iter.timestamp ? new Date(iter.timestamp).toLocaleString() : '-'}
        </Text>
      </div>
    ),
  })) || []

  return (
    <div>
      <Card
        title={
          <Space>
            <RobotOutlined style={{ fontSize: 20 }} />
            <span>AeroGPT 自然语言设计引擎</span>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Input.TextArea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="描述您想要的飞行器，例如：设计一架载重120kg、航程200km、时速120km的电动固定翼飞行器，起飞距离不超过80米"
            rows={4}
            style={{ fontSize: 14 }}
          />
          <Space>
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleGenerate}
              loading={loading}
              size="large"
            >
              生成方案
            </Button>
            <Text type="secondary">支持中文自然语言描述飞行器需求</Text>
          </Space>
        </Space>
      </Card>

      {proposal && (
        <>
          {proposal.status === 'pending_review' && (
            <Alert
              type="warning"
              message="AI方案待审核"
              description="此方案由AI生成，需人工审核确认后才可进入正式设计流程"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}
          {proposal.status === 'confirmed' && (
            <Alert
              type="success"
              message="方案已确认"
              description="方案已通过审核，可进入正式设计流程"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="可行性评分"
                  value={proposal.feasibility_report?.overall_score ?? 0}
                  suffix="/ 100"
                  valueStyle={{
                    color: (proposal.feasibility_report?.overall_score ?? 0) >= 60 ? '#3f8600' : '#cf1322',
                  }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="风险标记"
                  value={proposal.risk_markers?.length ?? 0}
                  valueStyle={{ color: (proposal.risk_markers?.length ?? 0) > 0 ? '#cf1322' : '#3f8600' }}
                  prefix={<WarningOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="迭代次数"
                  value={proposal.iteration_history?.length ?? 0}
                  prefix={<HistoryOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="状态"
                  value={statusConfig[proposal.status]?.label || proposal.status}
                  valueStyle={{ color: statusConfig[proposal.status]?.color === 'green' ? '#3f8600' : undefined }}
                />
              </Card>
            </Col>
          </Row>

          <Tabs
            defaultActiveKey="spec"
            items={[
              {
                key: 'spec',
                label: '解析参数',
                children: (
                  <Card>
                    <Table
                      columns={specColumns}
                      dataSource={specData}
                      pagination={false}
                      size="small"
                    />
                    {proposal.clarification_questions?.length > 0 && (
                      <>
                        <Divider>需要澄清的问题</Divider>
                        {proposal.clarification_questions.map((q, i) => (
                          <Alert key={i} type="info" message={q} style={{ marginBottom: 8 }} showIcon />
                        ))}
                      </>
                    )}
                  </Card>
                ),
              },
              {
                key: 'feasibility',
                label: '可行性评估',
                children: (
                  <Card>
                    <Descriptions bordered column={1} size="small">
                      <Descriptions.Item label="可行性">
                        {proposal.feasibility_report?.is_feasible ? (
                          <Tag color="green" icon={<CheckCircleOutlined />}>可行</Tag>
                        ) : (
                          <Tag color="red" icon={<CloseCircleOutlined />}>不可行</Tag>
                        )}
                      </Descriptions.Item>
                      <Descriptions.Item label="评分">
                        <Progress
                          percent={proposal.feasibility_report?.overall_score ?? 0}
                          strokeColor={(proposal.feasibility_report?.overall_score ?? 0) >= 60 ? '#52c41a' : '#ff4d4f'}
                        />
                      </Descriptions.Item>
                      <Descriptions.Item label="摘要">{proposal.feasibility_report?.summary || '-'}</Descriptions.Item>
                    </Descriptions>
                    {proposal.feasibility_report?.design_rule_violations?.length > 0 && (
                      <>
                        <Divider>设计规则违反</Divider>
                        {proposal.feasibility_report.design_rule_violations.map((v, i) => (
                          <Alert
                            key={i}
                            type={v.severity === 'error' ? 'error' : 'warning'}
                            message={String(v.rule || 'Unknown')}
                            description={`${v.parameter}: ${v.value}`}
                            style={{ marginBottom: 8 }}
                            showIcon
                          />
                        ))}
                      </>
                    )}
                  </Card>
                ),
              },
              {
                key: 'risks',
                label: '风险标记',
                children: (
                  <Card>
                    <Table
                      columns={riskColumns}
                      dataSource={proposal.risk_markers?.map((r, i) => ({ ...r, key: r.marker_id || i })) || []}
                      size="small"
                      pagination={false}
                    />
                  </Card>
                ),
              },
              {
                key: 'iterate',
                label: '迭代交互',
                children: (
                  <Card>
                    <Space direction="vertical" style={{ width: '100%' }} size="middle">
                      <Input.TextArea
                        value={iterateInput}
                        onChange={(e) => setIterateInput(e.target.value)}
                        placeholder="输入修改意见，例如：增加载荷到150kg，航程增加到300km"
                        rows={3}
                      />
                      <Button
                        type="primary"
                        icon={<SyncOutlined />}
                        onClick={handleIterate}
                        loading={loading}
                        disabled={proposal.status === 'confirmed' || proposal.status === 'rejected'}
                      >
                        迭代调整
                      </Button>
                      {iterationTimeline.length > 0 && (
                        <>
                          <Divider>迭代历史</Divider>
                          <Timeline items={iterationTimeline} />
                        </>
                      )}
                      {iterationTimeline.length === 0 && (
                        <Empty description="暂无迭代记录" />
                      )}
                    </Space>
                  </Card>
                ),
              },
            ]}
          />

          <Card style={{ marginTop: 16 }}>
            <Space>
              {proposal.status === 'pending_review' || proposal.status === 'iterating' ? (
                <>
                  <Button type="primary" icon={<CheckCircleOutlined />} onClick={handleConfirm}>
                    确认方案
                  </Button>
                  <Button danger icon={<CloseCircleOutlined />} onClick={handleReject}>
                    拒绝方案
                  </Button>
                </>
              ) : null}
            </Space>
          </Card>
        </>
      )}

      {!proposal && (
        <Card>
          <Empty
            image={<RobotOutlined style={{ fontSize: 64, color: '#1890ff' }} />}
            description="输入自然语言描述，AeroGPT将为您生成飞行器设计方案"
          />
        </Card>
      )}
    </div>
  )
}