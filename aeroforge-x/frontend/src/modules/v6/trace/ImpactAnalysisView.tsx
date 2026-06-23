import React, { useEffect, useState } from 'react'
import { Card, List, Tag, Spin } from 'antd'
import { dtHardeningApi } from '../../../api/v6Api'
import type { TraceNode, ImpactAnalysisResult, ImpactEntry } from '../../../api/types'

const NODE_TYPE_COLORS: Record<string, string> = {
  block: 'blue',
  material_lot: 'green',
  ndt_record: 'gold',
  car: 'red',
  evidence: 'purple',
  compliance: 'cyan',
}

interface Props {
  node: TraceNode | null
  onNodeClick: (nodeId: string) => void
}

const ImpactAnalysisView: React.FC<Props> = ({ node, onNodeClick }) => {
  const [result, setResult] = useState<ImpactAnalysisResult | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!node) {
      setResult(null)
      return
    }
    setLoading(true)
    dtHardeningApi.impactAnalysis(node.node_id)
      .then((data: any) => setResult(data))
      .catch(() => setResult(null))
      .finally(() => setLoading(false))
  }, [node])

  if (!node) return null

  const renderEntry = (entry: ImpactEntry, color: string, label: string) => (
    <List.Item
      style={{ padding: '4px 12px', cursor: 'pointer' }}
      onClick={() => onNodeClick(entry.node.node_id)}
    >
      <List.Item.Meta
        title={
          <span>
            <Tag color={color} style={{ marginRight: 4 }}>{label}</Tag>
            <Tag color={NODE_TYPE_COLORS[entry.node.node_type] || 'default'}>
              {entry.node.node_type}
            </Tag>
            {entry.node.label}
          </span>
        }
        description={
          <span style={{ fontSize: 11, color: '#999' }}>
            via {entry.edge_type} — {entry.node.node_id.slice(0, 8)}...
          </span>
        }
      />
    </List.Item>
  )

  return (
    <Card
      title={`Impact Analysis: ${node.label}`}
      size="small"
      style={{ maxHeight: 300, overflow: 'auto' }}
    >
      {loading ? <Spin /> : result ? (
        <>
          {result.direct.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ fontWeight: 600, color: '#ff4d4f', fontSize: 12, marginBottom: 4 }}>
                Direct Impact ({result.direct.length})
              </div>
              <List size="small" dataSource={result.direct} renderItem={e => renderEntry(e, 'red', 'direct')} />
            </div>
          )}
          {result.indirect.length > 0 && (
            <div>
              <div style={{ fontWeight: 600, color: '#fa8c16', fontSize: 12, marginBottom: 4 }}>
                Indirect Impact ({result.indirect.length})
              </div>
              <List size="small" dataSource={result.indirect} renderItem={e => renderEntry(e, 'orange', 'indirect')} />
            </div>
          )}
          {result.direct.length === 0 && result.indirect.length === 0 && (
            <div style={{ color: '#999', textAlign: 'center', padding: 16 }}>No downstream impact</div>
          )}
        </>
      ) : <div style={{ color: '#999', textAlign: 'center' }}>Failed to load</div>}
    </Card>
  )
}

export default ImpactAnalysisView