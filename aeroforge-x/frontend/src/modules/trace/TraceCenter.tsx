import { useState } from 'react'
import { Typography, Card, Input, Button, Descriptions, Tag, Alert, Space, message } from 'antd'
import { AuditOutlined, SearchOutlined, LinkOutlined, DisconnectOutlined } from '@ant-design/icons'
import apiClient from '../../services/apiClient'

const { Title } = Typography

interface TraceNode {
  label: string
  properties: Record<string, unknown>
}

export default function TraceCenter() {
  const [serialNumber, setSerialNumber] = useState('')
  const [batchNumber, setBatchNumber] = useState('')
  const [traceChain, setTraceChain] = useState<Record<string, unknown> | null>(null)
  const [batchTrace, setBatchTrace] = useState<Record<string, unknown> | null>(null)
  const [integrity, setIntegrity] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)

  const handleTraceQuery = async () => {
    if (!serialNumber) { message.warning('请输入序列号'); return }
    try {
      setLoading(true)
      const res = await apiClient.get(`/api/v1/trace/${serialNumber}`)
      setTraceChain(res.data.data)
    } catch { message.error('查询失败') }
    finally { setLoading(false) }
  }

  const handleBatchTrace = async () => {
    if (!batchNumber) { message.warning('请输入批次号'); return }
    try {
      setLoading(true)
      const res = await apiClient.get(`/api/v1/trace/batch/${batchNumber}`)
      setBatchTrace(res.data.data)
    } catch { message.error('查询失败') }
    finally { setLoading(false) }
  }

  const handleIntegrityCheck = async () => {
    if (!serialNumber) { message.warning('请输入序列号'); return }
    try {
      setLoading(true)
      const res = await apiClient.get(`/api/v1/trace/integrity/${serialNumber}`)
      setIntegrity(res.data.data)
    } catch { message.error('校验失败') }
    finally { setLoading(false) }
  }

  const renderTraceChain = () => {
    if (!traceChain || traceChain.status === 'not_found') {
      return <Alert message="未找到追溯链" type="warning" showIcon />
    }
    const chains = (traceChain.trace_chain as Record<string, unknown>[]) || []
    if (chains.length === 0) return <Alert message="追溯链为空" type="info" showIcon />
    return (
      <div>
        {chains.map((path: Record<string, unknown>, idx: number) => {
          const nodes = (path.nodes || []) as TraceNode[]
          const relations = (path.relations || []) as string[]
          return (
            <Card key={idx} size="small" style={{ marginBottom: 8 }}>
              <Space wrap>
                {nodes.map((node: TraceNode, i: number) => (
                  <span key={i}>
                    <Tag color="blue">{node.label}</Tag>
                    <span style={{ fontSize: 12 }}>{String(node.properties?.code || node.properties?.serialNumber || node.properties?.name || '')}</span>
                    {i < relations.length && <LinkOutlined style={{ margin: '0 4px', color: '#999' }} />}
                  </span>
                ))}
              </Space>
            </Card>
          )
        })}
      </div>
    )
  }

  return (
    <div>
      <Title level={3}><AuditOutlined /> 追溯</Title>

      <Card title="序列号追溯" style={{ marginBottom: 16 }}>
        <Space style={{ marginBottom: 16 }}>
          <Input placeholder="输入序列号" value={serialNumber} onChange={e => setSerialNumber(e.target.value)} style={{ width: 250 }} />
          <Button type="primary" icon={<SearchOutlined />} onClick={handleTraceQuery} loading={loading}>查询追溯链</Button>
          <Button icon={<DisconnectOutlined />} onClick={handleIntegrityCheck} loading={loading}>完整性校验</Button>
        </Space>
        {renderTraceChain()}
        {integrity && (
          <Alert
            message={integrity.intact ? '追溯链完整' : '追溯链存在断裂'}
            type={integrity.intact ? 'success' : 'error'}
            showIcon
            style={{ marginTop: 8 }}
          />
        )}
      </Card>

      <Card title="批次追溯">
        <Space style={{ marginBottom: 16 }}>
          <Input placeholder="输入批次号" value={batchNumber} onChange={e => setBatchNumber(e.target.value)} style={{ width: 250 }} />
          <Button type="primary" icon={<SearchOutlined />} onClick={handleBatchTrace} loading={loading}>批次正向追溯</Button>
        </Space>
        {batchTrace && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="批次号">{batchTrace.batch_number}</Descriptions.Item>
            <Descriptions.Item label="方向">{batchTrace.direction}</Descriptions.Item>
            <Descriptions.Item label="受影响项数">{(batchTrace.affected_items as unknown[])?.length || 0}</Descriptions.Item>
          </Descriptions>
        )}
      </Card>
    </div>
  )
}
