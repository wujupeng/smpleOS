import React, { useState, useRef, useEffect } from 'react';
import {
  Card, Form, InputNumber, Select, Button, Table, Tag, Space,
  Tabs, message, Descriptions, Row, Col, Statistic, List, Badge, Steps
} from 'antd';
import {
  RocketOutlined, BuildOutlined, ThunderboltOutlined,
  ApiOutlined, CheckCircleOutlined, ExperimentOutlined
} from '@ant-design/icons';

const { Option } = Select;
const { TabPane } = Tabs;

interface AirframeData {
  airframe_id: string;
  fuselage_params: { length_m: number; diameter_m: number; fineness_ratio: number };
  wing_params: { span_m: number; aspect_ratio: number; area_m2: number; taper_ratio: number; sweep_angle_deg: number; root_chord_m: number; tip_chord_m: number };
  tail_params: { h_tail_area_m2: number; v_tail_area_m2: number };
  status: string;
}

interface StructureData {
  structure_id: string;
  component_type: string;
  material: string;
  geometry: Record<string, any>;
  status: string;
}

interface PowertrainData {
  powertrain_id: string;
  motor_spec: { motor_type: string; max_thrust_n: number; kv_rating: number; efficiency_pct: number };
  battery_spec: { chemistry: string; capacity_mah: number; voltage_v: number; max_discharge_c: number };
  thrust_params: { motor_count: number; total_max_thrust_n: number; thrust_to_weight_ratio: number };
  status: string;
}

interface WireHarnessData {
  harness_id: string;
  harness_type: string;
  wire_count: number;
  connector_count: number;
  total_weight_kg: number;
  status: string;
}

const DesignModelPage: React.FC = () => {
  const [specForm] = Form.useForm();
  const [airframe, setAirframe] = useState<AirframeData | null>(null);
  const [structures, setStructures] = useState<StructureData[]>([]);
  const [powertrain, setPowertrain] = useState<PowertrainData | null>(null);
  const [harness, setHarness] = useState<WireHarnessData | null>(null);
  const [validationResult, setValidationResult] = useState<any>(null);
  const [activeTab, setActiveTab] = useState('airframe');

  const handleGenerateAirframe = async (values: any) => {
    try {
      const res = await fetch('/api/v1/design/airframe/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const data = await res.json();
      setAirframe(data);
      message.success('Airframe generated');
    } catch {
      message.error('Airframe generation failed');
    }
  };

  const handleGenerateStructure = async () => {
    if (!airframe) { message.warning('Generate airframe first'); return; }
    try {
      const res = await fetch('/api/v1/design/structure/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(airframe.wing_params),
      });
      const data = await res.json();
      setStructures(data.structures || []);
      message.success(`${data.total_count} structures generated`);
    } catch {
      message.error('Structure generation failed');
    }
  };

  const handleGeneratePowertrain = async (values: any) => {
    try {
      const res = await fetch('/api/v1/design/powertrain/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const data = await res.json();
      setPowertrain(data);
      message.success('Powertrain generated');
    } catch {
      message.error('Powertrain generation failed');
    }
  };

  const handleGenerateHarness = async () => {
    if (!powertrain) { message.warning('Generate powertrain first'); return; }
    try {
      const res = await fetch('/api/v1/design/wire-harness/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ motor_count: powertrain.thrust_params.motor_count, powertrain_params: powertrain }),
      });
      const data = await res.json();
      setHarness(data);
      message.success('Wire harness generated');
    } catch {
      message.error('Wire harness generation failed');
    }
  };

  const handleValidate = async () => {
    if (!airframe) return;
    try {
      const res = await fetch('/api/v1/design/models/dummy/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain: 'airframe' }),
      });
      const data = await res.json();
      setValidationResult(data);
      message.info(data.is_valid ? 'Design is valid' : 'Design has violations');
    } catch {
      message.error('Validation failed');
    }
  };

  const structureColumns = [
    { title: 'Type', dataIndex: 'component_type', key: 'type', render: (v: string) => <Tag color="blue">{v}</Tag> },
    { title: 'Material', dataIndex: 'material', key: 'material' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (v: string) => <Tag>{v}</Tag> },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Steps current={['airframe','structure','powertrain','harness'].indexOf(activeTab)} style={{ marginBottom: 24 }}
        items={[
          { title: 'Airframe', icon: <RocketOutlined /> },
          { title: 'Structure', icon: <BuildOutlined /> },
          { title: 'Powertrain', icon: <ThunderboltOutlined /> },
          { title: 'Wire Harness', icon: <ApiOutlined /> },
        ]}
      />

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="Airframe" key="airframe">
          <Card title="Generate Airframe" style={{ marginBottom: 16 }}>
            <Form form={specForm} layout="vertical" onFinish={handleGenerateAirframe}>
              <Row gutter={16}>
                <Col span={6}><Form.Item name="aircraft_type" label="Type" initialValue="fixed_wing">
                  <Select><Option value="fixed_wing">Fixed Wing</Option><Option value="evtol">eVTOL</Option><Option value="uav">UAV</Option><Option value="glider">Glider</Option></Select>
                </Form.Item></Col>
                <Col span={6}><Form.Item name="payload_kg" label="Payload (kg)" initialValue={10}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
                <Col span={6}><Form.Item name="range_km" label="Range (km)" initialValue={100}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
                <Col span={6}><Form.Item name="cruise_speed_kmh" label="Speed (km/h)" initialValue={100}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
              </Row>
              <Button type="primary" htmlType="submit" icon={<RocketOutlined />}>Generate Airframe</Button>
            </Form>
          </Card>
          {airframe && <Card title="Airframe Result">
            <Descriptions bordered column={2}>
              <Descriptions.Item label="Fuselage Length">{airframe.fuselage_params.length_m} m</Descriptions.Item>
              <Descriptions.Item label="Fuselage Diameter">{airframe.fuselage_params.diameter_m} m</Descriptions.Item>
              <Descriptions.Item label="Wing Span">{airframe.wing_params.span_m} m</Descriptions.Item>
              <Descriptions.Item label="Aspect Ratio">{airframe.wing_params.aspect_ratio}</Descriptions.Item>
              <Descriptions.Item label="Wing Area">{airframe.wing_params.area_m2} m²</Descriptions.Item>
              <Descriptions.Item label="Taper Ratio">{airframe.wing_params.taper_ratio}</Descriptions.Item>
              <Descriptions.Item label="H-Tail Area">{airframe.tail_params.h_tail_area_m2} m²</Descriptions.Item>
              <Descriptions.Item label="V-Tail Area">{airframe.tail_params.v_tail_area_m2} m²</Descriptions.Item>
            </Descriptions>
          </Card>}
        </TabPane>

        <TabPane tab="Structure" key="structure" disabled={!airframe}>
          <Card title="Generate Structure" extra={<Button onClick={handleValidate} icon={<ExperimentOutlined />}>Validate Design</Button>}>
            <Button type="primary" onClick={handleGenerateStructure} icon={<BuildOutlined />}>Generate Structures</Button>
          </Card>
          {structures.length > 0 && <Card title="Structure Components" style={{ marginTop: 16 }}>
            <Table columns={structureColumns} dataSource={structures} rowKey="structure_id" size="small" />
          </Card>}
        </TabPane>

        <TabPane tab="Powertrain" key="powertrain" disabled={!airframe}>
          <Card title="Generate Powertrain">
            <Form layout="vertical" onFinish={handleGeneratePowertrain}>
              <Row gutter={16}>
                <Col span={8}><Form.Item name="payload_kg" label="Payload (kg)" initialValue={10}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
                <Col span={8}><Form.Item name="cruise_speed_kmh" label="Speed (km/h)" initialValue={100}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
                <Col span={8}><Form.Item name="range_km" label="Range (km)" initialValue={50}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
              </Row>
              <Button type="primary" htmlType="submit" icon={<ThunderboltOutlined />}>Generate Powertrain</Button>
            </Form>
          </Card>
          {powertrain && <Card title="Powertrain Result" style={{ marginTop: 16 }}>
            <Row gutter={16}>
              <Col span={8}><Statistic title="Motor Thrust" value={powertrain.motor_spec.max_thrust_n} suffix="N" /></Col>
              <Col span={8}><Statistic title="Battery Capacity" value={powertrain.battery_spec.capacity_mah} suffix="mAh" /></Col>
              <Col span={8}><Statistic title="T/W Ratio" value={powertrain.thrust_params.thrust_to_weight_ratio} precision={3} /></Col>
            </Row>
          </Card>}
        </TabPane>

        <TabPane tab="Wire Harness" key="harness" disabled={!powertrain}>
          <Card title="Generate Wire Harness">
            <Button type="primary" onClick={handleGenerateHarness} icon={<ApiOutlined />}>Generate Wire Harness</Button>
          </Card>
          {harness && <Card title="Wire Harness Result" style={{ marginTop: 16 }}>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="Type">{harness.harness_type}</Descriptions.Item>
              <Descriptions.Item label="Wire Count">{harness.wire_count}</Descriptions.Item>
              <Descriptions.Item label="Connector Count">{harness.connector_count}</Descriptions.Item>
              <Descriptions.Item label="Total Weight">{harness.total_weight_kg} kg</Descriptions.Item>
            </Descriptions>
          </Card>}
        </TabPane>
      </Tabs>

      {validationResult && <Card title="Design Validation" style={{ marginTop: 16 }}>
        <Alert type={validationResult.is_valid ? 'success' : 'error'}
          message={validationResult.is_valid ? 'Design is valid' : 'Design has violations'} style={{ marginBottom: 16 }} />
        {validationResult.violations?.length > 0 && <Table
          columns={[
            { title: 'Rule', dataIndex: 'rule_id', key: 'rule' },
            { title: 'Severity', dataIndex: 'severity', key: 'severity', render: (v: string) => <Tag color={v === 'error' ? 'red' : 'orange'}>{v}</Tag> },
            { title: 'Message', dataIndex: 'message', key: 'message' },
            { title: 'Suggestion', dataIndex: 'suggestion', key: 'suggestion' },
          ]}
          dataSource={validationResult.violations} rowKey="rule_id" size="small"
        />}
      </Card>}
    </div>
  );
};

export default DesignModelPage;