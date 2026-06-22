import React, { useEffect, useState } from 'react'
import { Card, Descriptions, Empty, Spin, Tag, Timeline, Input, Button } from 'antd'
import { dtApi } from '../../api/v6Api'
import type { QualityThreadResponse, NDTRecord, CorrectiveActionRequest } from '../../api/types'

const QualityTracePage: React.FC = () => {
  const [lotId, setLotId] = useState('AL-2024-002')
  const [qualityData, setQualityData] = useState<QualityThreadResponse | null>(null)
  const [selectedItem, setSelectedItem] = useState<NDTRecord | CorrectiveActionRequest | null>(null)
  const [loading, setLoading] = useState(false)

  const loadQuality = async (id: string) => {
    if (!id) return
    setLoading(true)
    try {
      const data = await dtApi.getQualityThread(id) as any
      setQualityData(data)
    } catch (e) {
      console.error('Failed to load quality thread:', e)
      setQualityData(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadQuality(lotId)
  }, [])

  const resultColor: Record<string, string> = { pass: 'green', fail: 'red', conditional: 'orange' }
  const carStatusColor: Record<string, string> = { open: 'red', in_progress: 'orange', closed: 'green' }

  const buildTimeline = () => {
    if (!qualityData || !qualityData.ndt_records.length) return <Empty description="No NDT records" />

    const items: any[] = []
    qualityData.ndt_records.forEach((ndt) => {
      items.push({
        color: resultColor[ndt.result] || 'gray',
        children: (
          <div onClick={() => setSelectedItem(ndt)} style={{ cursor: 'pointer' }}>
            <Tag color={resultColor[ndt.result]}>{ndt.result.toUpperCase()}</Tag>
            {ndt.test_type} - {ndt.inspector}
            {ndt.cars?.map((car) => (
              <div key={car.car_id} style={{ marginLeft: 16, marginTop: 4 }} onClick={(e) => { e.stopPropagation(); setSelectedItem(car) }}>
                <Tag color={carStatusColor[car.status]}>{car.status.toUpperCase()}</Tag>
                CAR: {car.description.slice(0, 40)}...
              </div>
            ))}
          </div>
        ),
      })
    })
    return <Timeline items={items} />
  }

  return (
    <div style={{ display: 'flex', gap: 16, height: 'calc(100vh - 120px)' }}>
      <Card title="Quality Trace" style={{ width: 450, overflow: 'auto' }}>
        <div style={{ marginBottom: 12, display: 'flex', gap: 8 }}>
          <Input value={lotId} onChange={(e) => setLotId(e.target.value)} placeholder="Material Lot ID" />
          <Button type="primary" onClick={() => loadQuality(lotId)}>Search</Button>
        </div>
        {loading ? <Spin /> : buildTimeline()}
      </Card>
      <Card title="Details" style={{ flex: 1, overflow: 'auto' }}>
        {selectedItem ? (
          'ndt_record_id' in selectedItem ? (
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="NDT Record ID">{(selectedItem as NDTRecord).ndt_record_id}</Descriptions.Item>
              <Descriptions.Item label="Test Type">{(selectedItem as NDTRecord).test_type}</Descriptions.Item>
              <Descriptions.Item label="Result"><Tag color={resultColor[(selectedItem as NDTRecord).result]}>{(selectedItem as NDTRecord).result}</Tag></Descriptions.Item>
              <Descriptions.Item label="Inspector">{(selectedItem as NDTRecord).inspector}</Descriptions.Item>
              <Descriptions.Item label="Test Date">{(selectedItem as NDTRecord).test_date}</Descriptions.Item>
              <Descriptions.Item label="Notes">{(selectedItem as NDTRecord).notes || '-'}</Descriptions.Item>
            </Descriptions>
          ) : (
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="CAR ID">{(selectedItem as CorrectiveActionRequest).car_id}</Descriptions.Item>
              <Descriptions.Item label="Description">{(selectedItem as CorrectiveActionRequest).description}</Descriptions.Item>
              <Descriptions.Item label="Status"><Tag color={carStatusColor[(selectedItem as CorrectiveActionRequest).status]}>{(selectedItem as CorrectiveActionRequest).status}</Tag></Descriptions.Item>
              <Descriptions.Item label="Responsible">{(selectedItem as CorrectiveActionRequest).responsible_person}</Descriptions.Item>
              <Descriptions.Item label="Created">{(selectedItem as CorrectiveActionRequest).created_at}</Descriptions.Item>
              <Descriptions.Item label="Closed">{(selectedItem as CorrectiveActionRequest).closed_at || '-'}</Descriptions.Item>
            </Descriptions>
          )
        ) : <Empty description="Select an item to view details" />}
      </Card>
    </div>
  )
}

export default QualityTracePage