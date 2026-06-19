import React, { useState } from 'react';
import {
  Card, Form, Input, InputNumber, Select, Button, Table, Tag, Space,
  Tabs, message, Descriptions, Alert, Row, Col, Statistic, Tooltip
} from 'antd';
import {
  PlusOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
  ThunderboltOutlined, BarChartOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Option } = Select;
const { TabPane } = Tabs;

interface SpecParameter {
  parameter_id: string;
  name: string;
  category: string;
  value: number | null;
  unit: string;
  tolerance: number | null;
  priority: string;
  is_required: boolean;
}

interface AircraftSpecData {
  spec_id: string;
  spec_number: string;
  aircraft_type: string;
  status: string;
  payload_kg: number | null;
  range_km: number | null;
  cruise_speed_kmh: number | null;
  takeoff_distance_m: number | null;
  power_type: string | null;
  budget_cny: number | null;
  derived_constraints: Record<string, number>;
  parameters: SpecParameter[];
  created_at: string;
  updated_at: string;
}

interface Violation {
  parameter: string;
  message: string;
  severity: string;
}

interface SensitivityResult {
  parameter_name: string;
  baseline_value: number | null;
  sensitivity_index: number;
  influence_rank: number;
  performance_impact: Record<string, number>;
}

const SpecPage: React.FC = () => {
  const [form] = Form.useForm();
  const [specs, setSpecs] = useState<AircraftSpecData[]>([]);
  const [currentSpec, setCurrentSpec] = useState<AircraftSpecData | null>(null);
  const [violations, setViolations] = useState<Violation[]>([]);
  const [sensitivityResults, setSensitivityResults] = useState<SensitivityResult[]>([]);
  const [paramForm] = Form.useForm();
  const [parameters, setParameters] = useState<SpecParameter[]>([]);

  const handleCreateSpec = async (values: any) => {
    try {
      const res = await fetch('/api/v1/requirement/specs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...values, parameters }),
      });
      const data = await res.json();
      setSpecs(prev => [data, ...prev]);
      setCurrentSpec(data);
      message.success(`Spec ${data.spec_number} created`);
    } catch {
      message.error('Failed to create spec');
    }
  };

  const handleValidate = async () => {
    if (!currentSpec) return;
    try {
      const res = await fetch(`/api/v1/requirement/specs/${currentSpec.spec_id}/validate`, { method: 'POST' });
      const data = await res.json();
      setViolations(data.violations || []);
      message.info(data.is_valid ? 'Spec is valid' : 'Spec has violations');
    } catch {
      message.error('Validation failed');
    }
  };

  const handleConfirm = async () => {
    if (!currentSpec) return;
    try {
      const res = await fetch(`/api/v1/requirement/specs/${currentSpec.spec_id}/confirm`, { method: 'POST' });
      const data = await res.json();
      setCurrentSpec(data);
      message.success('Spec confirmed');
    } catch (e: any) {
      message.error(e.message || 'Confirm failed');
    }
  };

  const handleSensitivity = async () => {
    if (!currentSpec) return;
    try {
      const res = await fetch('/api/v1/requirement/sensitivity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ spec_id: currentSpec.spec_id }),
      });
      const data = await res.json();
      setSensitivityResults(data.results || []);
      message.success('Sensitivity analysis completed');
    } catch {
      message.error('Sensitivity analysis failed');
    }
  };

  const addParameter = (values: any) => {
    const param: SpecParameter = {
      parameter_id: `temp-${Date.now()}`,
      ...values,
      value: values.value ?? null,
      tolerance: values.tolerance ?? null,
    };
    setParameters(prev => [...prev, param]);
    paramForm.resetFields();
  };

  const removeParameter = (name: string) => {
    setParameters(prev => prev.filter(p => p.name !== name));
  };

  const paramColumns: ColumnsType<SpecParameter> = [
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Category', dataIndex: 'category', key: 'category', render: (v: string) => <Tag>{v}</Tag> },
    { title: 'Value', dataIndex: 'value', key: 'value', render: (v: number | null) => v?.toFixed(2) ?? '-' },
    { title: 'Unit', dataIndex: 'unit', key: 'unit' },
    { title: 'Priority', dataIndex: 'priority', key: 'priority', render: (v: string) => {
      const color = v === 'critical' ? 'red' : v === 'high' ? 'orange' : v === 'medium' ? 'blue' : 'default';
      return <Tag color={color}>{v}</Tag>;
    }},
    { title: 'Required', dataIndex: 'is_required', key: 'is_required', render: (v: boolean) => v ? <CheckCircleOutlined style={{color:'green'}} /> : '-' },
    { title: 'Action', key: 'action', render: (_: any, record: SpecParameter) => (
      <Button size="small" danger onClick={() => removeParameter(record.name)}>Remove</Button>
    )},
  ];

  const violationColumns: ColumnsType<Violation> = [
    { title: 'Parameter', dataIndex: 'parameter', key: 'parameter' },
    { title: 'Message', dataIndex: 'message', key: 'message' },
    { title: 'Severity', dataIndex: 'severity', key: 'severity', render: (v: string) => {
      const color = v === 'error' ? 'red' : v === 'warning' ? 'orange' : 'blue';
      return <Tag color={color}>{v}</Tag>;
    }},
  ];

  const sensitivityColumns: ColumnsType<SensitivityResult> = [
    { title: 'Rank', dataIndex: 'influence_rank', key: 'rank', width: 60 },
    { title: 'Parameter', dataIndex: 'parameter_name', key: 'param' },
    { title: 'Baseline', dataIndex: 'baseline_value', key: 'baseline', render: (v: number | null) => v?.toFixed(4) ?? '-' },
    { title: 'Sensitivity Index', dataIndex: 'sensitivity_index', key: 'si', render: (v: number) => (
      <span style={{ fontWeight: v > 0.5 ? 'bold' : 'normal', color: v > 1 ? 'red' : 'inherit' }}>
        {v.toFixed(6)}
      </span>
    )},
  ];

  const statusColorMap: Record<string, string> = {
    draft: 'default', submitted: 'processing', approved: 'success',
    confirmed: 'success', frozen: 'cyan', rejected: 'error',
  };

  return (
    <div style={{ padding: 24 }}>
      <Tabs defaultActiveKey="create">
        <TabPane tab="Create Spec" key="create">
          <Card title="Aircraft Specification" style={{ marginBottom: 16 }}>
            <Form form={form} layout="vertical" onFinish={handleCreateSpec}>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item name="aircraft_type" label="Aircraft Type" rules={[{ required: true }]}>
                    <Select>
                      <Option value="fixed_wing">Fixed Wing</Option>
                      <Option value="glider">Glider</Option>
                      <Option value="evtol">eVTOL</Option>
                      <Option value="uav">UAV</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item name="power_type" label="Power Type">
                    <Select allowClear>
                      <Option value="electric">Electric</Option>
                      <Option value="hybrid">Hybrid</Option>
                      <Option value="gasoline">Gasoline</Option>
                      <Option value="diesel">Diesel</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col span={6}><Form.Item name="payload_kg" label="Payload (kg)"><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
                <Col span={6}><Form.Item name="range_km" label="Range (km)"><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
                <Col span={6}><Form.Item name="cruise_speed_kmh" label="Cruise Speed (km/h)"><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
                <Col span={6}><Form.Item name="takeoff_distance_m" label="Takeoff Distance (m)"><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
              </Row>
              <Row gutter={16}>
                <Col span={8}><Form.Item name="budget_cny" label="Budget (CNY)"><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
              </Row>
            </Form>
          </Card>

          <Card title="Parameters" style={{ marginBottom: 16 }} extra={
            <Button icon={<PlusOutlined />} onClick={() => {}}>Add Parameter</Button>
          }>
            <Form form={paramForm} layout="inline" onFinish={addParameter} style={{ marginBottom: 16 }}>
              <Form.Item name="name" rules={[{ required: true }]}><Input placeholder="Name" /></Form.Item>
              <Form.Item name="category"><Select style={{width:120}} defaultValue="performance">
                <Option value="performance">Performance</Option>
                <Option value="structural">Structural</Option>
                <Option value="aerodynamic">Aerodynamic</Option>
                <Option value="propulsion">Propulsion</Option>
              </Select></Form.Item>
              <Form.Item name="value"><InputNumber placeholder="Value" /></Form.Item>
              <Form.Item name="unit"><Input placeholder="Unit" style={{width:80}} /></Form.Item>
              <Form.Item name="priority"><Select style={{width:100}} defaultValue="medium">
                <Option value="critical">Critical</Option>
                <Option value="high">High</Option>
                <Option value="medium">Medium</Option>
                <Option value="low">Low</Option>
              </Select></Form.Item>
              <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>Add</Button>
            </Form>
            <Table columns={paramColumns} dataSource={parameters} rowKey="name" size="small" pagination={false} />
          </Card>

          <Space>
            <Button type="primary" onClick={() => form.submit()}>Create Spec</Button>
            {currentSpec && <>
              <Button icon={<ExclamationCircleOutlined />} onClick={handleValidate}>Validate</Button>
              <Button type="primary" icon={<CheckCircleOutlined />} onClick={handleConfirm}
                disabled={currentSpec.status !== 'approved'}>Confirm</Button>
              <Button icon={<BarChartOutlined />} onClick={handleSensitivity}>Sensitivity Analysis</Button>
            </>}
          </Space>
        </TabPane>

        {currentSpec && <TabPane tab="Spec Detail" key="detail">
          <Card title={`Spec: ${currentSpec.spec_number}`}>
            <Descriptions bordered column={3}>
              <Descriptions.Item label="Status">
                <Tag color={statusColorMap[currentSpec.status] || 'default'}>{currentSpec.status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Aircraft Type">{currentSpec.aircraft_type}</Descriptions.Item>
              <Descriptions.Item label="Version">{currentSpec.version}</Descriptions.Item>
              <Descriptions.Item label="Payload">{currentSpec.payload_kg} kg</Descriptions.Item>
              <Descriptions.Item label="Range">{currentSpec.range_km} km</Descriptions.Item>
              <Descriptions.Item label="Cruise Speed">{currentSpec.cruise_speed_kmh} km/h</Descriptions.Item>
            </Descriptions>
          </Card>
          {Object.keys(currentSpec.derived_constraints).length > 0 && (
            <Card title="Derived Constraints" style={{ marginTop: 16 }}>
              <Row gutter={16}>
                {Object.entries(currentSpec.derived_constraints).map(([key, val]) => (
                  <Col span={6} key={key}><Statistic title={key} value={val as number} precision={2} /></Col>
                ))}
              </Row>
            </Card>
          )}
        </TabPane>}

        {violations.length > 0 && <TabPane tab="Validation" key="validation">
          <Card title="Validation Results">
            <Alert type={violations.some(v => v.severity === 'error') ? 'error' : 'warning'}
              message={`${violations.length} violation(s) found`} style={{ marginBottom: 16 }} />
            <Table columns={violationColumns} dataSource={violations} rowKey="parameter" size="small" />
          </Card>
        </TabPane>}

        {sensitivityResults.length > 0 && <TabPane tab="Sensitivity" key="sensitivity">
          <Card title="Sensitivity Analysis Results">
            <Table columns={sensitivityColumns} dataSource={sensitivityResults} rowKey="parameter_name" size="small" />
          </Card>
        </TabPane>}
      </Tabs>
    </div>
  );
};

export default SpecPage;