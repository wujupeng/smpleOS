import React, { useState } from 'react';
import { Card, Button, Input, Select, Space, Typography, Descriptions, Tag, Alert } from 'antd';
import { CheckCircleOutlined } from '@ant-design/icons';

const { Title } = Typography;
const { TextArea } = Input;
const API_BASE = '/api/v1';

const ComplianceVerificationPage: React.FC = () => {
  const [itemId, setItemId] = useState('');
  const [verType, setVerType] = useState('design');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const verify = async () => {
    setLoading(true);
    try {
      const endpoint = verType === 'design' ? 'design' : verType === 'manufacturing' ? 'manufacturing' : 'test';
      const dataKey = verType === 'design' ? 'design_data' : verType === 'manufacturing' ? 'manufacturing_data' : 'test_data';
      const res = await fetch(`${API_BASE}/certification/verify/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: itemId, [dataKey]: { evidence_documents: ['report.pdf', 'analysis.xlsx'] } }),
      });
      const data = await res.json();
      setResult(data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}><CheckCircleOutlined /> Compliance Verification</Title>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Input placeholder="Compliance Item ID" value={itemId} onChange={(e) => setItemId(e.target.value)} style={{ width: 250 }} />
          <Select value={verType} onChange={setVerType} style={{ width: 160 }} options={[
            { value: 'design', label: 'Design Compliance' },
            { value: 'manufacturing', label: 'Manufacturing Compliance' },
            { value: 'test', label: 'Test Compliance' },
          ]} />
          <Button type="primary" onClick={verify} loading={loading}>Verify Compliance</Button>
        </Space>
      </Card>
      {result && (
        <Card title="Verification Result">
          {result.evidence_gap && <Alert message="Evidence Gap Detected" description="Required evidence is missing. Compliance declaration is blocked." type="warning" showIcon style={{ marginBottom: 12 }} />}
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="Item ID">{result.item_id}</Descriptions.Item>
            <Descriptions.Item label="Type">{result.verification_type}</Descriptions.Item>
            <Descriptions.Item label="Result"><Tag color={result.result === 'compliant' ? 'green' : result.result === 'non_compliant' ? 'red' : 'orange'}>{result.result}</Tag></Descriptions.Item>
            <Descriptions.Item label="Compliant"><Tag color={result.is_compliant ? 'green' : 'red'}>{result.is_compliant ? 'Yes' : 'No'}</Tag></Descriptions.Item>
          </Descriptions>
          {result.findings?.length > 0 && (
            <Card type="inner" title="Findings" style={{ marginTop: 12 }}>
              {result.findings.map((f: string, i: number) => <Alert key={i} message={f} type="warning" style={{ marginBottom: 8 }} />)}
            </Card>
          )}
        </Card>
      )}
    </div>
  );
};

export default ComplianceVerificationPage;