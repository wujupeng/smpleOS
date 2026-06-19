import React, { useState } from 'react';
import { Card, Form, InputNumber, Button, Row, Col, Statistic, Table, Tabs, Tag, Alert } from 'antd';
import { RocketOutlined, ExperimentOutlined } from '@ant-design/icons';

const { TabPane } = Tabs;

const FlightDynamicsPage: React.FC = () => {
  const [trimResult, setTrimResult] = useState<any>(null);
  const [simResult, setSimResult] = useState<any>(null);
  const [dynResult, setDynResult] = useState<any>(null);

  const handleTrim = async (values: any) => {
    const res = await fetch('/api/v1/verification/flight-dynamics/trim', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values),
    });
    setTrimResult(await res.json());
  };

  const handle6DOF = async (values: any) => {
    const res = await fetch('/api/v1/verification/flight-dynamics/simulate-6dof', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values),
    });
    setSimResult(await res.json());
  };

  const handleDynamic = async (values: any) => {
    const res = await fetch('/api/v1/verification/flight-dynamics/dynamic-response', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values),
    });
    setDynResult(await res.json());
  };

  const simColumns = [
    { title: 'Time (s)', dataIndex: 'time_s', key: 'time' },
    { title: 'φ (°)', dataIndex: 'phi_deg', key: 'phi' },
    { title: 'θ (°)', dataIndex: 'theta_deg', key: 'theta' },
    { title: 'ψ (°)', dataIndex: 'psi_deg', key: 'psi' },
    { title: 'u (m/s)', dataIndex: 'u_m_s', key: 'u' },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Tabs defaultActiveKey="trim">
        <TabPane tab="Trim Analysis" key="trim">
          <Card title="Trim Analysis">
            <Form layout="vertical" onFinish={handleTrim}>
              <Row gutter={16}>
                <Col span={8}><Form.Item name="mtow_kg" label="MTOW (kg)" initialValue={25}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
                <Col span={8}><Form.Item name="wing_area_m2" label="Wing Area (m²)" initialValue={0.5}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
                <Col span={8}><Form.Item name="cruise_speed_ms" label="Speed (m/s)" initialValue={30}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
              </Row>
              <Button type="primary" htmlType="submit" icon={<RocketOutlined />}>Run Trim</Button>
            </Form>
          </Card>
          {trimResult && <Card style={{marginTop:16}}>
            <Row gutter={16}>
              <Col span={6}><Statistic title="Alpha" value={trimResult.alpha_deg} suffix="°" /></Col>
              <Col span={6}><Statistic title="Elevator" value={trimResult.elevator_deflection_deg} suffix="°" /></Col>
              <Col span={6}><Statistic title="Throttle" value={trimResult.throttle_pct} suffix="%" /></Col>
              <Col span={6}><Statistic title="Converged" value={trimResult.converged ? 'Yes' : 'No'} valueStyle={{color: trimResult.converged ? '#3f8600' : '#cf1322'}} /></Col>
            </Row>
          </Card>}
        </TabPane>

        <TabPane tab="6DOF Simulation" key="6dof">
          <Card title="6DOF Simulation">
            <Form layout="vertical" onFinish={handle6DOF}>
              <Row gutter={16}>
                <Col span={8}><Form.Item name="mtow_kg" label="MTOW (kg)" initialValue={25}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
                <Col span={8}><Form.Item name="cruise_speed_ms" label="Speed (m/s)" initialValue={30}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
                <Col span={8}><Form.Item name="duration_s" label="Duration (s)" initialValue={10}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
              </Row>
              <Button type="primary" htmlType="submit" icon={<ExperimentOutlined />}>Run 6DOF</Button>
            </Form>
          </Card>
          {simResult && <Card title="Simulation Results" style={{marginTop:16}}>
            {simResult.diverged && <Alert type="warning" message="Simulation diverged" style={{marginBottom:16}} />}
            <Table columns={simColumns} dataSource={simResult.states} rowKey="time_s" size="small" pagination={{pageSize:20}} />
          </Card>}
        </TabPane>

        <TabPane tab="Dynamic Response" key="dynamic">
          <Card title="Dynamic Response Analysis">
            <Form layout="vertical" onFinish={handleDynamic}>
              <Row gutter={16}>
                <Col span={8}><Form.Item name="natural_frequency_hz" label="Nat. Freq (Hz)" initialValue={1.5}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
                <Col span={8}><Form.Item name="damping_ratio" label="Damping Ratio" initialValue={0.5}><InputNumber min={0} max={1} step={0.1} style={{width:'100%'}} /></Form.Item></Col>
              </Row>
              <Button type="primary" htmlType="submit">Analyze Response</Button>
            </Form>
          </Card>
          {dynResult && <Card style={{marginTop:16}}>
            <Row gutter={16}>
              <Col span={6}><Statistic title="Settling Time" value={dynResult.settling_time_s} suffix="s" /></Col>
              <Col span={6}><Statistic title="Rise Time" value={dynResult.rise_time_s} suffix="s" /></Col>
              <Col span={6}><Statistic title="Overshoot" value={dynResult.overshoot_pct} suffix="%" /></Col>
              <Col span={6}><Statistic title="Damping" value={dynResult.damping_ratio} /></Col>
            </Row>
            {dynResult.modes && <Table style={{marginTop:16}} columns={[
              { title: 'Mode', dataIndex: 'name', key: 'name' },
              { title: 'Freq (Hz)', dataIndex: 'frequency_hz', key: 'freq' },
              { title: 'Damping', dataIndex: 'damping_ratio', key: 'damp' },
            ]} dataSource={dynResult.modes} rowKey="name" size="small" />}
          </Card>}
        </TabPane>
      </Tabs>
    </div>
  );
};

export default FlightDynamicsPage;