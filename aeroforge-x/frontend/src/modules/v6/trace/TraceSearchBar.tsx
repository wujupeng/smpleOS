import React, { useEffect, useState } from 'react'
import { Select, Input, List, Tag, Space } from 'antd'
import { dtHardeningApi } from '../../../api/v6Api'
import type { TraceNode } from '../../../api/types'

const NODE_TYPE_COLORS: Record<string, string> = {
  block: 'blue',
  material_lot: 'green',
  ndt_record: 'gold',
  car: 'red',
  evidence: 'purple',
  compliance: 'cyan',
}

interface Props {
  allNodes: TraceNode[]
  onNodeSelect: (nodeId: string) => void
}

const TraceSearchBar: React.FC<Props> = ({ allNodes, onNodeSelect }) => {
  const [typeFilter, setTypeFilter] = useState<string | undefined>(undefined)
  const [searchText, setSearchText] = useState('')

  const filtered = allNodes.filter(n => {
    if (typeFilter && n.node_type !== typeFilter) return false
    if (searchText && !n.label.toLowerCase().includes(searchText.toLowerCase()) && !n.node_id.includes(searchText)) return false
    return true
  })

  return (
    <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', padding: '8px 0' }}>
      <Select
        placeholder="Node type"
        allowClear
        style={{ width: 160 }}
        value={typeFilter}
        onChange={setTypeFilter}
        options={[
          { value: 'block', label: 'Block' },
          { value: 'material_lot', label: 'Material Lot' },
          { value: 'ndt_record', label: 'NDT Record' },
          { value: 'car', label: 'CAR' },
          { value: 'evidence', label: 'Evidence' },
          { value: 'compliance', label: 'Compliance' },
        ]}
      />
      <Input.Search
        placeholder="Search by label or ID..."
        style={{ width: 280 }}
        value={searchText}
        onChange={e => setSearchText(e.target.value)}
        allowClear
      />
      {filtered.length > 0 && (
        <div style={{ maxHeight: 200, overflow: 'auto', border: '1px solid #d9d9d9', borderRadius: 4, minWidth: 300 }}>
          <List
            size="small"
            dataSource={filtered.slice(0, 20)}
            renderItem={(node: TraceNode) => (
              <List.Item
                style={{ padding: '4px 12px', cursor: 'pointer' }}
                onClick={() => onNodeSelect(node.node_id)}
              >
                <Space>
                  <Tag color={NODE_TYPE_COLORS[node.node_type] || 'default'}>{node.node_type}</Tag>
                  <span style={{ fontSize: 12 }}>{node.label}</span>
                </Space>
              </List.Item>
            )}
          />
        </div>
      )}
    </div>
  )
}

export default TraceSearchBar