import React, { useEffect, useState } from 'react'
import { Tree, Card, Descriptions, Empty, Spin, Tag, List } from 'antd'
import { configApi, dtApi } from '../../api/v6Api'
import type { MaterialLot } from '../../api/types'

const MaterialTracePage: React.FC = () => {
  const [treeData, setTreeData] = useState<any[]>([])
  const [selectedLot, setSelectedLot] = useState<MaterialLot | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const hierarchy: any = await configApi.getHierarchy('B737')
      const blocks = hierarchy.blocks || []
      const tree = [{
        title: 'B737',
        key: 'B737',
        children: await Promise.all(blocks.map(async (b: any) => {
          let materials: MaterialLot[] = []
          try {
            materials = await dtApi.getBlockMaterials(b.block_id) as any
          } catch {}
          return {
            title: b.block_name,
            key: b.block_id,
            children: materials.map((m: MaterialLot) => ({
              title: `${m.lot_id} (${m.material_name})`,
              key: m.lot_id,
              isLeaf: true,
              data: m,
            })),
          }
        })),
      }]
      setTreeData(tree)
    } catch (e) {
      console.error('Failed to load material trace:', e)
    } finally {
      setLoading(false)
    }
  }

  const onSelect = (selectedKeys: React.Key[], info: any) => {
    if (info.node?.data) {
      setSelectedLot(info.node.data)
    }
  }

  const statusColor: Record<string, string> = {
    received: 'blue', inspected: 'cyan', accepted: 'green',
    rejected: 'red', quarantined: 'orange',
  }

  return (
    <div style={{ display: 'flex', gap: 16, height: 'calc(100vh - 120px)' }}>
      <Card title="Material Trace" style={{ width: 350, overflow: 'auto' }}>
        {loading ? <Spin /> : (
          treeData.length > 0 ? (
            <Tree treeData={treeData} onSelect={onSelect} defaultExpandAll />
          ) : <Empty description="No data" />
        )}
      </Card>
      <Card title="Material Lot Details" style={{ flex: 1, overflow: 'auto' }}>
        {selectedLot ? (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="Lot ID">{selectedLot.lot_id}</Descriptions.Item>
            <Descriptions.Item label="Material Code">{selectedLot.material_code}</Descriptions.Item>
            <Descriptions.Item label="Material Name">{selectedLot.material_name}</Descriptions.Item>
            <Descriptions.Item label="Supplier">{selectedLot.supplier_id}</Descriptions.Item>
            <Descriptions.Item label="Certificate No">{selectedLot.certificate_no}</Descriptions.Item>
            <Descriptions.Item label="Status">
              <Tag color={statusColor[selectedLot.status] || 'default'}>{selectedLot.status}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Manufacture Date">{selectedLot.manufacture_date}</Descriptions.Item>
            <Descriptions.Item label="Received Date">{selectedLot.received_date}</Descriptions.Item>
          </Descriptions>
        ) : <Empty description="Select a material lot to view details" />}
      </Card>
    </div>
  )
}

export default MaterialTracePage