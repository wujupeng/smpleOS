import React, { useState } from 'react';
import { Card, Form, InputNumber, Button, Row, Col, Statistic, Descriptions, Tag, Alert, Table, Space } from 'antd';
import { SafetyCertificateOutlined, WarningOutlined } from '@ant-design/icons';

const StabilityPage: React.FC = () => {
  const [form] = Form.useForm();
  const [result, setResult] = useState<any>(null);

  const handleAnalyze = async (values: any) => {
    try {
      const res = await fetch('/api/v1/verification/stability/analyze', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values),
      });
      setResult(await res.json());
    } catch { /* ignore */ }
  };

  return (
    <div style={{ padding: 24 }}>
      <Card title="Stability Analysis" style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical" onFinish={handleAnalyze}>
          <Row gutter={16}>
            <Col span={6}><Form.Item name="wing_area_m2" label="Wing Area (m²)" initialValue={0.5}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
            <Col span={6}><Form.Item name="wing_span_m" label="Wing Span (m)" initialValue={2.0}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
            <Col span={6}><Form.Item name="h_tail_area_m2" label="H-Tail Area (m²)" initialValue={0.05}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
            <Col span={6}><Form.Item name="h_tail_arm_m" label="H-Tail Arm (m)" initialValue={0.6}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
          </Row>
          <Row gutter={16}>
            <Col span={6}><Form.Item name="v_tail_area_m2" label="V-Tail Area (m²)" initialValue={0.03}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
            <Col span={6}><Form.Item name="cg_position_pct_mac" label="CG (%MAC)" initialValue={25}><InputNumber style={{width:'100%'}} /></Form.Item></Col>
            <Col span={6}><Form.Item name="dihedral_angle_deg" label="Dihedral (°)" initialValue={3}><InputNumber style={{width:'100%'}} /></Form.Item></Col>
            <Col span={6}><Form.Item name="sweep_angle_deg" label="Sweep (°)" initialValue={2}><InputNumber style={{width:'100%'}} /></Form.Item></Col>
          </Row>
          <Button type="primary" htmlType="submit" icon={<SafetyCertificateOutlined />}>Analyze Stability</Button>
        </Form>
      </Card>

      {result && <>
        {result.is_statically_unstable && <Alert type="error" message="STATIC INSTABILITY DETECTED" description="Aircraft is statically unstable. See suggestions below." showIcon icon={<WarningOutlined />} style={{ marginBottom: 16 }} />}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={8}><Card><Statistic title="Longitudinal" value={result.longitudinal.is_stable ? 'STABLE' : 'UNSTABLE'} valueStyle={{ color: result.longitudinal.is_stable ? '#3f8600' : '#cf1322' }} /><div style={{fontSize:12,marginTop:8}}>SM: {result.longitudinal.static_margin_pct_mac}% MAC</div></Card></Col>
          <Col span={8}><Card><Statistic title="Lateral" value={result.lateral.is_stable ? 'STABLE' : 'UNSTABLE'} valueStyle={{ color: result.lateral.is_stable ? '#3f8600' : '#cf1322' }} /><div style={{fontSize:12,marginTop:8}}>Dutch Roll ζ: {result.lateral.dutch_roll_damping_ratio}</div></Card></Col>
          <Col span={8}><Card><Statistic title="Directional" value={result.directional.is_stable ? 'STABLE' : 'UNSTABLE'} valueStyle={{ color: result.directional.is_stable ? '#3f8600' : '#cf1322' }} /><div style={{fontSize:12,marginTop:8}}>Cnβ: {result.directional.yaw_stiffness_derivative}</div></Card></Col>
        </Row>
        {result.suggestions?.length > 0 && <Card title="Parameter Adjustment Suggestions">
          <Table columns={[
            { title: 'Parameter', dataIndex: 'parameter', key: 'param' },
            { title: 'Current', dataIndex: 'current_value', key: 'current' },
            { title: 'Suggested', dataIndex: 'suggested_value', key: 'suggested', render: (v: number) => <Tag color="blue">{v}</Tag> },
            { title: 'Reason', dataIndex: 'reason', key: 'reason' },
          ]} dataSource={result.suggestions} rowKey="parameter" size="small" />
        </Card>}
      </>}
    </div>
  );
};

export default StabilityPage;