import React, { useState } from 'react';
import { Card, Button, Input, Space, Typography, Table, Tag, Descriptions, Alert } from 'antd';
import { BuildOutlined } from '@ant-design/icons';

const { Title } = Typography;
const API_BASE = '/api/v1';

const AeroGPTEngineerPage: React.FC = () => {
  const [proposalId, setProposalId] = useState('');
  const [spec, setSpec] = useState('{}');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const generateStructure = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ai/engineer/generate-structure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proposal_id: proposalId, spec: JSON.parse(spec) }),
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const columns = [
    { title: 'Component', dataIndex: 'name', key: 'name' },
    { title: 'Type', dataIndex: 'component_type', key: 'type' },
    { title: 'Material', dataIndex: 'material', key: 'material' },
    {
      title: 'Interferences',
      key: 'interferences',
      render: (_: any, r: any) => <Tag color={r.interferences?.length > 0 ? 'red' : 'green'}>{r.interferences?.length || 0}</Tag>,
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}><BuildOutlined /> AeroGPT Engineer</Title>
      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Input placeholder="Proposal ID" value={proposalId} onChange={(e) => setProposalId(e.target.value)} />
          <Input.TextArea rows={4} placeholder='Aircraft spec JSON, e.g. {"wingspan_m": 35.8, "fuselage_length_m": 40, "mtow_kg": 78000}' value={spec} onChange={(e) => setSpec(e.target.value)} />
          <Button type="primary" onClick={generateStructure} loading={loading}>Generate Structure</Button>
        </Space>
      </Card>
      {result && (
        <>
          {result.baseline_frozen_violations?.length > 0 && (
            <Alert message="Baseline Frozen" description={result.baseline_frozen_violations[0]} type="warning" showIcon style={{ marginBottom: 16 }} />
          )}
          <Card title="Generated Structure">
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="Result ID">{result.result_id}</Descriptions.Item>
              <Descriptions.Item label="Status">{result.status}</Descriptions.Item>
              <Descriptions.Item label="Components">{result.components?.length}</Descriptions.Item>
              <Descriptions.Item label="Interferences">{result.interferences?.length}</Descriptions.Item>
            </Descriptions>
            <Table dataSource={result.components || []} columns={columns} rowKey="component_id" style={{ marginTop: 12 }} size="small" />
          </Card>
        </>
      )}
    </div>
  );
};

export default AeroGPTEngineerPage;