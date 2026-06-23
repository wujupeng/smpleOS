import React, { useEffect, useState } from 'react'
import { Card, Row, Col, Progress, Statistic } from 'antd'
import { CheckCircleOutlined, WarningOutlined, NodeIndexOutlined, SafetyCertificateOutlined } from '@ant-design/icons'
import { dtHardeningApi } from '../../../api/v6Api'
import type { TraceDashboard } from '../../../api/types'

const DigitalThreadDashboard: React.FC = () => {
  const [data, setData] = useState<TraceDashboard | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    dtHardeningApi.getTraceDashboard()
      .then((d: any) => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [])

  if (!data) return null

  const coverageColor = data.thread_coverage >= 80 ? '#52c41a' : data.thread_coverage >= 50 ? '#faad14' : '#ff4d4f'
  const complianceColor = data.compliance_progress >= 80 ? '#52c41a' : data.compliance_progress >= 50 ? '#faad14' : '#ff4d4f'

  return (
    <Row gutter={12} style={{ marginBottom: 12 }}>
      <Col span={6}>
        <Card size="small" loading={loading}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ marginBottom: 4 }}>
              <NodeIndexOutlined style={{ fontSize: 20, color: coverageColor }} />
            </div>
            <Progress
              type="circle"
              percent={data.thread_coverage}
              size={80}
              strokeColor={coverageColor}
              format={p => `${p}%`}
            />
            <div style={{ marginTop: 8, fontWeight: 600, fontSize: 13 }}>Thread Coverage</div>
            <div style={{ fontSize: 11, color: '#999' }}>
              {data.blocks_traced} / {data.total_blocks} blocks traced
            </div>
          </div>
        </Card>
      </Col>
      <Col span={6}>
        <Card size="small" loading={loading}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ marginBottom: 4 }}>
              <CheckCircleOutlined style={{ fontSize: 20, color: '#1890ff' }} />
            </div>
            <Statistic
              value={data.trace_depth}
              suffix="levels"
              valueStyle={{ fontSize: 32, color: '#1890ff' }}
            />
            <div style={{ marginTop: 4, fontWeight: 600, fontSize: 13 }}>Trace Depth</div>
            <div style={{ fontSize: 11, color: '#999' }}>Max traversal depth</div>
          </div>
        </Card>
      </Col>
      <Col span={6}>
        <Card size="small" loading={loading}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ marginBottom: 4 }}>
              <WarningOutlined style={{ fontSize: 20, color: data.open_cars > 0 ? '#ff4d4f' : '#52c41a' }} />
            </div>
            <Statistic
              value={data.open_cars}
              suffix={`/ ${data.total_cars}`}
              valueStyle={{ fontSize: 32, color: data.open_cars > 0 ? '#ff4d4f' : '#52c41a' }}
            />
            <div style={{ marginTop: 4, fontWeight: 600, fontSize: 13 }}>Open CARs</div>
            <div style={{ fontSize: 11, color: '#999' }}>Corrective actions pending</div>
          </div>
        </Card>
      </Col>
      <Col span={6}>
        <Card size="small" loading={loading}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ marginBottom: 4 }}>
              <SafetyCertificateOutlined style={{ fontSize: 20, color: complianceColor }} />
            </div>
            <Progress
              type="circle"
              percent={data.compliance_progress}
              size={80}
              strokeColor={complianceColor}
              format={p => `${p}%`}
            />
            <div style={{ marginTop: 8, fontWeight: 600, fontSize: 13 }}>Compliance Progress</div>
            <div style={{ fontSize: 11, color: '#999' }}>
              {data.compliant_requirements} / {data.total_requirements} requirements
            </div>
          </div>
        </Card>
      </Col>
    </Row>
  )
}

export default DigitalThreadDashboard