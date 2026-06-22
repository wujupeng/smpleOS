import React, { useEffect, useState } from 'react'
import { Card, Descriptions, Empty, Spin, Tag, List, Input, Button } from 'antd'
import { dtApi } from '../../api/v6Api'
import type { ComplianceRequirement, Evidence } from '../../api/types'

const CertificationTracePage: React.FC = () => {
  const [reqId, setReqId] = useState('FAA-25.853')
  const [compliance, setCompliance] = useState<ComplianceRequirement | null>(null)
  const [allRequirements, setAllRequirements] = useState<ComplianceRequirement[]>([])
  const [selectedEvidence, setSelectedEvidence] = useState<Evidence | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadCompliance(reqId)
    loadAllRequirements()
  }, [])

  const loadCompliance = async (id: string) => {
    if (!id) return
    setLoading(true)
    try {
      const data = await dtApi.getCompliance(id) as any
      setCompliance(data)
    } catch (e) {
      console.error('Failed to load compliance:', e)
      setCompliance(null)
    } finally {
      setLoading(false)
    }
  }

  const loadAllRequirements = async () => {
    try {
      const data = await dtApi.listComplianceRequirements() as any
      setAllRequirements(Array.isArray(data) ? data : [])
    } catch {}
  }

  const statusColor: Record<string, string> = {
    compliant: 'green', non_compliant: 'red', partial: 'orange', pending: 'blue',
  }

  return (
    <div style={{ display: 'flex', gap: 16, height: 'calc(100vh - 120px)' }}>
      <Card title="Certification Trace" style={{ width: 350, overflow: 'auto' }}>
        <div style={{ marginBottom: 12, display: 'flex', gap: 8 }}>
          <Input value={reqId} onChange={(e) => setReqId(e.target.value)} placeholder="Requirement ID" />
          <Button type="primary" onClick={() => loadCompliance(reqId)}>Search</Button>
        </div>
        {allRequirements.length > 0 && (
          <List size="small" dataSource={allRequirements} renderItem={(item) => (
            <List.Item style={{ cursor: 'pointer' }} onClick={() => { setReqId(item.requirement_id); loadCompliance(item.requirement_id) }}>
              <Tag color={statusColor[item.compliance_status]}>{item.compliance_status}</Tag>
              {item.requirement_id}
            </List.Item>
          )} />
        )}
      </Card>
      <Card title="Compliance Details" style={{ flex: 1, overflow: 'auto' }}>
        {loading ? <Spin /> : compliance ? (
          <>
            <Descriptions column={1} bordered size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="Requirement ID">{compliance.requirement_id}</Descriptions.Item>
              <Descriptions.Item label="Regulation">{compliance.regulation}</Descriptions.Item>
              <Descriptions.Item label="Description">{compliance.description}</Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={statusColor[compliance.compliance_status]}>{compliance.compliance_status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Responsible">{compliance.responsible_person || '-'}</Descriptions.Item>
              <Descriptions.Item label="Updated">{compliance.updated_at || '-'}</Descriptions.Item>
            </Descriptions>
            <Card title="Evidence Package" size="small">
              {compliance.evidences && compliance.evidences.length > 0 ? (
                <List size="small" dataSource={compliance.evidences} renderItem={(ev: Evidence) => (
                  <List.Item style={{ cursor: 'pointer' }} onClick={() => setSelectedEvidence(ev)}>
                    <div>
                      <Tag color="blue">{ev.content_type}</Tag>
                      {ev.file_name} ({(ev.file_size / 1024).toFixed(1)} KB)
                    </div>
                  </List.Item>
                )} />
              ) : <Empty description="No evidence" image={Empty.PRESENTED_IMAGE_SIMPLE} />}
            </Card>
            {selectedEvidence && (
              <Card title="Evidence Detail" size="small" style={{ marginTop: 8 }}>
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="Evidence ID">{selectedEvidence.evidence_id}</Descriptions.Item>
                  <Descriptions.Item label="File Name">{selectedEvidence.file_name}</Descriptions.Item>
                  <Descriptions.Item label="Content Type">{selectedEvidence.content_type}</Descriptions.Item>
                  <Descriptions.Item label="File Size">{selectedEvidence.file_size} bytes</Descriptions.Item>
                  <Descriptions.Item label="Uploaded">{selectedEvidence.upload_timestamp}</Descriptions.Item>
                </Descriptions>
              </Card>
            )}
          </>
        ) : <Empty description="No compliance data" />}
      </Card>
    </div>
  )
}

export default CertificationTracePage