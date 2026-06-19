import React, { useState } from 'react';
import { Card, Button, Input, Space, Typography, Table, Tag, Descriptions, Alert } from 'antd';
import { RocketOutlined } from '@ant-design/icons';

const { Title } = Typography;
const API_BASE = '/api/v1';

const AeroGPTTestPilotPage: React.FC = () => {
  const [aircraftType, setAircraftType] = useState('narrow_body');
  const [loading, setLoading] = useState(false);
  const [plan, setPlan] = useState<any>(null);

  const generate = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ai/testpilot/generate-test-plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ aircraft_type: aircraftType, certification_requirements: ['25.201', '25.203', '25.337', '25.341', '25.629'] }),
      });
      const data = await res.json();
      setPlan(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const tpColumns = [
    { title: '#', dataIndex: 'test_point_number', key: 'num', width: 40 },
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Objective', dataIndex: 'objective', key: 'obj' },
    {
      title: 'In Envelope',
      dataIndex: 'within_flight_envelope',
      key: 'env',
      render: (w: boolean) => <Tag color={w ? 'green' : 'red'}>{w ? 'Yes' : 'No'}</Tag>,
    },
    {
      title: 'Cert Refs',
      dataIndex: 'certification_requirement_refs',
      key: 'refs',
      render: (refs: string[]) => refs?.map((r) => <Tag key={r}>{r}</Tag>),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}><RocketOutlined /> AeroGPT TestPilot</Title>
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Input placeholder="Aircraft Type" value={aircraftType} onChange={(e) => setAircraftType(e.target.value)} style={{ width: 200 }} />
          <Button type="primary" onClick={generate} loading={loading}>Generate Flight Test Plan</Button>
        </Space>
      </Card>
      {plan && (
        <>
          <Card style={{ marginBottom: 16 }}>
            <Descriptions bordered column={3} size="small">
              <Descriptions.Item label="Plan ID">{plan.plan_id}</Descriptions.Item>
              <Descriptions.Item label="Total Sorties">{plan.total_sorties}</Descriptions.Item>
              <Descriptions.Item label="Total Test Points">{plan.total_test_points}</Descriptions.Item>
            </Descriptions>
          </Card>
          {plan.uncovered_requirements?.length > 0 && (
            <Alert
              message="Uncovered Certification Requirements"
              description={plan.uncovered_requirements.join(', ')}
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}
          {plan.sorties?.map((sortie: any) => (
            <Card key={sortie.sortie_id} title={`Sortie ${sortie.sortie_number}: ${sortie.subject}`} style={{ marginBottom: 12 }}>
              <Table dataSource={sortie.test_points || []} columns={tpColumns} rowKey="point_id" size="small" pagination={false} />
            </Card>
          ))}
        </>
      )}
    </div>
  );
};

export default AeroGPTTestPilotPage;