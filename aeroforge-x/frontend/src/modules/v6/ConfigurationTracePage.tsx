import React, { useEffect, useState } from 'react'
import { Tree, Card, Descriptions, Empty, Spin, Tag } from 'antd'
import { configApi } from '../../api/v6Api'
import type { BlockConfiguration } from '../../api/types'

const ConfigurationTracePage: React.FC = () => {
  const [treeData, setTreeData] = useState<any[]>([])
  const [selectedBlock, setSelectedBlock] = useState<BlockConfiguration | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadHierarchy('B737')
  }, [])

  const loadHierarchy = async (aircraftType: string) => {
    setLoading(true)
    try {
      const data: any = await configApi.getHierarchy(aircraftType)
      const blocks = data.blocks || []
      const tree = [{
        title: aircraftType,
        key: aircraftType,
        children: blocks.map((b: any) => ({
          title: `${b.block_name} (v${b.version || 1})`,
          key: b.block_id,
          isLeaf: true,
          data: b,
        })),
      }]
      setTreeData(tree)
    } catch (e) {
      console.error('Failed to load hierarchy:', e)
    } finally {
      setLoading(false)
    }
  }

  const onSelect = (selectedKeys: React.Key[], info: any) => {
    if (info.node?.data) {
      setSelectedBlock(info.node.data)
    }
  }

  return (
    <div style={{ display: 'flex', gap: 16, height: 'calc(100vh - 120px)' }}>
      <Card title="Configuration Hierarchy" style={{ width: 350, overflow: 'auto' }}>
        {loading ? <Spin /> : (
          treeData.length > 0 ? (
            <Tree treeData={treeData} onSelect={onSelect} defaultExpandAll />
          ) : <Empty description="No data" />
        )}
      </Card>
      <Card title="Block Details" style={{ flex: 1, overflow: 'auto' }}>
        {selectedBlock ? (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="Block ID">{selectedBlock.block_id}</Descriptions.Item>
            <Descriptions.Item label="Block Name">{selectedBlock.block_name}</Descriptions.Item>
            <Descriptions.Item label="Aircraft Type">{selectedBlock.aircraft_type}</Descriptions.Item>
            <Descriptions.Item label="Version">
              <Tag color="blue">v{selectedBlock.version || 1}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Locked">
              <Tag color={selectedBlock.locked ? 'red' : 'green'}>{selectedBlock.locked ? 'Yes' : 'No'}</Tag>
            </Descriptions.Item>
          </Descriptions>
        ) : <Empty description="Select a block to view details" />}
      </Card>
    </div>
  )
}

export default ConfigurationTracePage