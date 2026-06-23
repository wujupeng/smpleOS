import React from 'react'
import { Descriptions, Tag, Empty } from 'antd'
import type { TraceNode, ConfigurationIdentity, IdentityMapping } from '../../../api/types'

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
  identity: ConfigurationIdentity | null
  identityMappings: IdentityMapping[]
}

const TraceNodeDetailPanel: React.FC<Props> = ({ node, identity, identityMappings }) => {
  if (!node) {
    return <Empty description="Select a node to view details" style={{ marginTop: 40 }} />
  }

  const props = node.properties || {}

  return (
    <div style={{ padding: 12 }}>
      <Descriptions column={1} bordered size="small">
        <Descriptions.Item label="Node ID">
          <span style={{ fontSize: 11, fontFamily: 'monospace' }}>{node.node_id}</span>
        </Descriptions.Item>
        <Descriptions.Item label="Type">
          <Tag color={NODE_TYPE_COLORS[node.node_type] || 'default'}>{node.node_type}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="Label">{node.label}</Descriptions.Item>
        <Descriptions.Item label="Domain">{String(props.domain || '—')}</Descriptions.Item>
        <Descriptions.Item label="Domain ID">{String(props.domain_id || '—')}</Descriptions.Item>
        {identity && (
          <Descriptions.Item label="Identity">
            <Tag color="geekblue">{identity.canonical_label}</Tag>
          </Descriptions.Item>
        )}
      </Descriptions>

      {identityMappings.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 13 }}>Identity Cross-Domain Alignment</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 8 }}>
            {['block', 'material_lot', 'ndt_record', 'car'].map(domain => {
              const mapping = identityMappings.find(m => m.domain === domain)
              return (
                <div
                  key={domain}
                  style={{
                    padding: '6px 8px',
                    borderRadius: 4,
                    background: mapping ? '#f6ffed' : '#fafafa',
                    border: `1px solid ${mapping ? '#b7eb8f' : '#d9d9d9'}`,
                    fontSize: 11,
                  }}
                >
                  <div style={{ fontWeight: 600, color: '#666', marginBottom: 2 }}>{domain}</div>
                  <div style={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>
                    {mapping ? mapping.domain_id : '—'}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

export default TraceNodeDetailPanel