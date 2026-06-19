import React, { useState } from 'react';
import { Card, Button, Input, Select, Space, Typography, Table, Tag, Descriptions, Checkbox } from 'antd';
import { ToolOutlined } from '@ant-design/icons';

const { Title } = Typography;
const API_BASE = '/api/v1';

const AeroGPTManufacturingPage: React.FC = () => {
  const [componentType, setComponentType] = useState('wing_spar');
  const [material, setMaterial] = useState('composite_cfrp');
  const [includeTraveler, setIncludeTraveler] = useState(true);
  const [includeNDT, setIncludeNDT] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const generate = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ai/manufacturing/generate-process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ component_type: componentType, material, dimensions: {}, include_traveler: includeTraveler, include_ndt: includeNDT }),
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const stepColumns = [
    { title: '#', dataIndex: 'step_number', key: 'num', width: 50 },
    { title: 'Operation', dataIndex: 'operation', key: 'op' },
    { title: 'Equipment', dataIndex: 'equipment', key: 'eq' },
    { title: 'Est. Hours', dataIndex: 'estimated_time_hours', key: 'hrs' },
    {
      title: 'Feasible',
      dataIndex: 'is_feasible',
      key: 'feasible',
      render: (f: boolean) => <Tag color={f ? 'green' : 'red'}>{f ? 'Yes' : 'No'}</Tag>,
    },
    {
      title: 'Alternative',
      dataIndex: 'alternative_suggestion',
      key: 'alt',
      render: (s: string | null) => s || '-',
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}><ToolOutlined /> AeroGPT Manufacturing</Title>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap>
          <Select value={componentType} onChange={setComponentType} style={{ width: 180 }} options={[
            { value: 'wing_spar', label: 'Wing Spar' },
            { value: 'wing_rib', label: 'Wing Rib' },
            { value: 'fuselage_frame', label: 'Fuselage Frame' },
            { value: 'center_wing_box', label: 'Center Wing Box' },
          ]} />
          <Select value={material} onChange={setMaterial} style={{ width: 180 }} options={[
            { value: 'composite_cfrp', label: 'Composite CFRP' },
            { value: 'aluminum_7075', label: 'Aluminum 7075' },
            { value: 'aluminum_2024', label: 'Aluminum 2024' },
          ]} />
          <Checkbox checked={includeTraveler} onChange={(e) => setIncludeTraveler(e.target.checked)}>Include Traveler</Checkbox>
          <Checkbox checked={includeNDT} onChange={(e) => setIncludeNDT(e.target.checked)}>Include NDT Plan</Checkbox>
          <Button type="primary" onClick={generate} loading={loading}>Generate Process Route</Button>
        </Space>
      </Card>
      {result && (
        <Card title={`Process Route - ${componentType}`}>
          <Descriptions bordered column={3} size="small">
            <Descriptions.Item label="Route ID">{result.route_id}</Descriptions.Item>
            <Descriptions.Item label="Total Hours">{result.total_estimated_hours?.toFixed(1)}</Descriptions.Item>
            <Descriptions.Item label="Feasibility">
              <Tag color={result.feasibility_status === 'feasible' ? 'green' : result.feasibility_status === 'partially_feasible' ? 'orange' : 'red'}>
                {result.feasibility_status}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
          <Table dataSource={result.steps || []} columns={stepColumns} rowKey="step_id" style={{ marginTop: 12 }} size="small" pagination={false} />
          {result.ndt_plan && (
            <Card type="inner" title="NDT Inspection Plan" style={{ marginTop: 12 }}>
              <Table dataSource={result.ndt_plan.inspections || []} columns={[
                { title: 'Area', dataIndex: 'area', key: 'area' },
                { title: 'Method', dataIndex: 'method', key: 'method' },
                { title: 'Acceptance', dataIndex: 'acceptance', key: 'acc' },
                { title: 'Critical', dataIndex: 'critical', key: 'crit', render: (c: boolean) => <Tag color={c ? 'red' : 'green'}>{c ? 'Yes' : 'No'}</Tag> },
              ]} rowKey="area" size="small" pagination={false} />
            </Card>
          )}
        </Card>
      )}
    </div>
  );
};

export default AeroGPTManufacturingPage;