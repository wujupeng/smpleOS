import React, { useState } from 'react';
import { Card, Button, Input, Space, Typography, Table, Tag, Descriptions, Progress, Checkbox } from 'antd';
import { SafetyCertificateOutlined } from '@ant-design/icons';

const { Title } = Typography;
const API_BASE = '/api/v1';

const AeroGPTCertificationPage: React.FC = () => {
  const [aircraftType, setAircraftType] = useState('narrow_body');
  const [includePlan, setIncludePlan] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const generate = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ai/certification/generate-compliance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ aircraft_type: aircraftType, regulation: 'FAR-25', include_plan: includePlan }),
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const columns = [
    { title: 'Section', dataIndex: 'section', key: 'section', width: 100 },
    { title: 'Requirement', dataIndex: 'requirement', key: 'req' },
    { title: 'Category', dataIndex: 'category', key: 'cat', render: (c: string) => <Tag>{c}</Tag> },
    {
      title: 'Status',
      dataIndex: 'compliance_status',
      key: 'status',
      render: (s: string) => <Tag color={s === 'compliant' ? 'green' : s === 'open' ? 'orange' : 'default'}>{s}</Tag>,
    },
    {
      title: 'Evidence Gap',
      dataIndex: 'evidence_gap',
      key: 'gap',
      render: (g: boolean) => g ? <Tag color="red">Gap</Tag> : <Tag color="green">Covered</Tag>,
    },
    {
      title: 'Suggested Source',
      dataIndex: 'suggested_evidence_source',
      key: 'src',
      render: (s: string | null) => s || '-',
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}><SafetyCertificateOutlined /> AeroGPT Certification</Title>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Input placeholder="Aircraft Type" value={aircraftType} onChange={(e) => setAircraftType(e.target.value)} style={{ width: 200 }} />
          <Checkbox checked={includePlan} onChange={(e) => setIncludePlan(e.target.checked)}>Include Certification Plan</Checkbox>
          <Button type="primary" onClick={generate} loading={loading}>Generate Compliance Matrix</Button>
        </Space>
      </Card>
      {result && (
        <>
          <Card style={{ marginBottom: 16 }}>
            <Descriptions bordered column={3} size="small">
              <Descriptions.Item label="Matrix ID">{result.matrix_id}</Descriptions.Item>
              <Descriptions.Item label="Regulation">{result.regulation}</Descriptions.Item>
              <Descriptions.Item label="Coverage">
                <Progress percent={Math.round(result.coverage_percentage || 0)} size="small" />
              </Descriptions.Item>
              <Descriptions.Item label="Total Items">{result.total_items}</Descriptions.Item>
              <Descriptions.Item label="Compliant">{result.compliant_items}</Descriptions.Item>
              <Descriptions.Item label="Gaps">
                <Tag color={result.gap_items > 0 ? 'red' : 'green'}>{result.gap_items}</Tag>
              </Descriptions.Item>
            </Descriptions>
          </Card>
          <Card title="Compliance Items">
            <Table dataSource={result.items || []} columns={columns} rowKey="item_id" size="small" pagination={{ pageSize: 10 }} />
          </Card>
          {result.certification_plan && (
            <Card title="Certification Plan" style={{ marginTop: 16 }}>
              <Descriptions bordered column={2} size="small">
                <Descriptions.Item label="Plan ID">{result.certification_plan.plan_id}</Descriptions.Item>
                <Descriptions.Item label="Duration">{result.certification_plan.estimated_duration_months} months</Descriptions.Item>
              </Descriptions>
              <Table
                dataSource={result.certification_plan.phases || []}
                columns={[
                  { title: 'Phase', dataIndex: 'phase', key: 'phase' },
                  { title: 'Duration (months)', dataIndex: 'duration_months', key: 'dur' },
                  { title: 'Activities', dataIndex: 'activities', key: 'act', render: (a: string[]) => a?.join('; ') },
                ]}
                rowKey="phase"
                size="small"
                pagination={false}
                style={{ marginTop: 12 }}
              />
            </Card>
          )}
        </>
      )}
    </div>
  );
};

export default AeroGPTCertificationPage;