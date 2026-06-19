import React, { useState } from 'react';
import { Card, Form, InputNumber, Button, Row, Col, Statistic, Descriptions, Tag, Alert, Table } from 'antd';
import { DashboardOutlined } from '@ant-design/icons';

const FlightEnvelopePage: React.FC = () => {
  const [result, setResult] = useState<any>(null);

  const handleAnalyze = async (values: any) => {
    const res = await fetch('/api/v1/verification/flight-envelope/analyze', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values),
    });
    setResult(await res.json());
  };

  return (
    <div style={{ padding: 24 }}>
      <Card title="Flight Envelope Analysis" style={{ marginBottom: 16 }}>
        <Form layout="vertical" onFinish={handleAnalyze}>
          <Row gutter={16}>
            <Col span={6}><Form.Item name="mtow_kg" label="MTOW (kg)" initialValue={25}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
            <Col span={6}><Form.Item name="wing_area_m2" label="Wing Area (m²)" initialValue={0.5}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
            <Col span={6}><Form.Item name="cruise_speed_kmh" label="Cruise Speed (km/h)" initialValue={100}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
            <Col span={6}><Form.Item name="cl_max" label="CL Max" initialValue={1.5}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
          </Row>
          <Button type="primary" htmlType="submit" icon={<DashboardOutlined />}>Analyze Envelope</Button>
        </Form>
      </Card>

      {result && <>
        {!result.is_airworthy && <Alert type="error" message="AIRWORTHINESS VIOLATION" description="Flight envelope does not meet airworthiness standards." style={{marginBottom:16}} />}
        <Card title="Limit Speeds" style={{marginBottom:16}}>
          <Row gutter={16}>
            <Col span={4}><Statistic title="VS1" value={result.limit_speeds.vs1_ms} suffix="m/s" /></Col>
            <Col span={4}><Statistic title="VS0" value={result.limit_speeds.vs0_ms} suffix="m/s" /></Col>
            <Col span={4}><Statistic title="VA" value={result.limit_speeds.va_ms} suffix="m/s" /></Col>
            <Col span={4}><Statistic title="VC" value={result.limit_speeds.vc_ms} suffix="m/s" /></Col>
            <Col span={4}><Statistic title="VD" value={result.limit_speeds.vd_ms} suffix="m/s" /></Col>
            <Col span={4}><Statistic title="VNE" value={result.limit_speeds.vne_ms} suffix="m/s" /></Col>
          </Row>
        </Card>
        <Card title="Load Factors" style={{marginBottom:16}}>
          <Row gutter={16}>
            <Col span={8}><Statistic title="Max Positive" value={result.limit_load_factors.n_max_positive} prefix="n=" /></Col>
            <Col span={8}><Statistic title="Max Negative" value={result.limit_load_factors.n_max_negative} prefix="n=" /></Col>
            <Col span={8}><Statistic title="Airworthy" value={result.is_airworthy ? 'YES' : 'NO'} valueStyle={{color: result.is_airworthy ? '#3f8600' : '#cf1322'}} /></Col>
          </Row>
        </Card>
        <Card title="V-n Diagram" style={{marginBottom:16}}>
          <Table columns={[
            { title: 'Speed (m/s)', dataIndex: 'speed_ms', key: 'speed' },
            { title: 'Load Factor', dataIndex: 'load_factor', key: 'n' },
            { title: 'Label', dataIndex: 'label', key: 'label' },
          ]} dataSource={result.vn_diagram} rowKey="label" size="small" pagination={false} />
        </Card>
        {result.violations?.length > 0 && <Card title="Violations">
          <Table columns={[
            { title: 'Type', dataIndex: 'type', key: 'type' },
            { title: 'Speed (m/s)', dataIndex: 'speed_ms', key: 'speed' },
            { title: 'Load Factor', dataIndex: 'load_factor', key: 'n' },
            { title: 'Description', dataIndex: 'description', key: 'desc' },
            { title: 'Severity', dataIndex: 'severity', key: 'sev', render: (v: string) => <Tag color={v==='critical'?'red':'orange'}>{v}</Tag> },
          ]} dataSource={result.violations} rowKey="description" size="small" />
        </Card>}
      </>}
    </div>
  );
};

export default FlightEnvelopePage;