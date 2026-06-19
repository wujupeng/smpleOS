import React, { useState } from 'react';
import { Card, Form, InputNumber, Select, Button, Space, Divider, Row, Col, Statistic, Tag, message } from 'antd';
import { usePhysicsPluginStore } from '../../../stores/physicsPluginStore';

const FIDELITY_LEVELS = [
  { label: 'Low — Linearized / Simplified', value: 'low' },
  { label: 'Mid — Nonlinear / Thevenin / Gain-Scheduled', value: 'mid' },
  { label: 'Detail — Quaternion / EKF / LQR', value: 'detail' },
];

const ModelParameterConfig: React.FC = () => {
  const { setModelParameters, switchFidelity } = usePhysicsPluginStore();
  const [modelType, setModelType] = useState<string>('dof6');
  const [fidelity, setFidelity] = useState<string>('low');
  const [runtimeId, setRuntimeId] = useState('');
  const [form] = Form.useForm();

  const handleApply = async () => {
    const values = form.getFieldsValue();
    const params = Object.fromEntries(Object.entries(values).filter(([_, v]) => v !== undefined && v !== null));
    if (runtimeId) {
      await setModelParameters(runtimeId, { model_type: modelType, fidelity_level: fidelity, parameters: params });
      message.success('Parameters applied');
    } else {
      message.warning('Enter a runtime ID');
    }
  };

  const handleFidelitySwitch = async () => {
    if (runtimeId) {
      await switchFidelity(runtimeId, fidelity);
      message.info(`Switched to ${fidelity} fidelity`);
    }
  };

  const dof6Fields = (
    <>
      <Form.Item name="mass" label="Mass (kg)"><InputNumber style={{ width: '100%' }} /></Form.Item>
      <Form.Item name="ixx" label="Ixx (kg·m²)"><InputNumber style={{ width: '100%' }} /></Form.Item>
      <Form.Item name="iyy" label="Iyy (kg·m²)"><InputNumber style={{ width: '100%' }} /></Form.Item>
      <Form.Item name="izz" label="Izz (kg·m²)"><InputNumber style={{ width: '100%' }} /></Form.Item>
      <Form.Item name="cl_alpha" label="CLα (1/rad)"><InputNumber style={{ width: '100%' }} /></Form.Item>
      <Form.Item name="cd0" label="CD0"><InputNumber style={{ width: '100%' }} /></Form.Item>
      <Form.Item name="s_wing" label="Wing Area (m²)"><InputNumber style={{ width: '100%' }} /></Form.Item>
    </>
  );

  const batteryFields = (
    <>
      <Form.Item name="capacity" label="Capacity (Ah)"><InputNumber style={{ width: '100%' }} /></Form.Item>
      <Form.Item name="r0" label="R₀ (Ω)"><InputNumber style={{ width: '100%' }} step={0.001} /></Form.Item>
      <Form.Item name="rc1" label="RC1 (Ω)"><InputNumber style={{ width: '100%' }} step={0.001} /></Form.Item>
      <Form.Item name="c1" label="C1 (F)"><InputNumber style={{ width: '100%' }} /></Form.Item>
      <Form.Item name="nominal_voltage" label="Nominal Voltage (V)"><InputNumber style={{ width: '100%' }} /></Form.Item>
      <Form.Item name="initial_soc" label="Initial SOC"><InputNumber style={{ width: '100%' }} min={0} max={1} step={0.01} /></Form.Item>
    </>
  );

  const controlFields = (
    <>
      <Form.Item name="kp" label="Kp"><InputNumber style={{ width: '100%' }} step={0.1} /></Form.Item>
      <Form.Item name="ki" label="Ki"><InputNumber style={{ width: '100%' }} step={0.01} /></Form.Item>
      <Form.Item name="kd" label="Kd"><InputNumber style={{ width: '100%' }} step={0.01} /></Form.Item>
      <Form.Item name="dt" label="Timestep (s)"><InputNumber style={{ width: '100%' }} step={0.001} /></Form.Item>
      <Form.Item name="output_min" label="Output Min"><InputNumber style={{ width: '100%' }} /></Form.Item>
      <Form.Item name="output_max" label="Output Max"><InputNumber style={{ width: '100%' }} /></Form.Item>
    </>
  );

  const fieldMap: Record<string, React.ReactNode> = {
    dof6: dof6Fields,
    battery: batteryFields,
    control: controlFields,
  };

  return (
    <Card title="Model Parameter Configuration">
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Row gutter={16}>
          <Col span={8}>
            <div style={{ marginBottom: 8 }}>Runtime ID</div>
            <InputNumber style={{ width: '100%' }} value={runtimeId || undefined} onChange={(v) => setRuntimeId(String(v || ''))} placeholder="Enter runtime ID" />
          </Col>
          <Col span={8}>
            <div style={{ marginBottom: 8 }}>Model Type</div>
            <Select value={modelType} onChange={setModelType} style={{ width: '100%' }} options={[
              { label: '6DOF Rigid Body', value: 'dof6' },
              { label: 'Battery', value: 'battery' },
              { label: 'Control', value: 'control' },
            ]} />
          </Col>
          <Col span={8}>
            <div style={{ marginBottom: 8 }}>Fidelity Level</div>
            <Select value={fidelity} onChange={setFidelity} style={{ width: '100%' }} options={FIDELITY_LEVELS} />
          </Col>
        </Row>

        <Button onClick={handleFidelitySwitch} disabled={!runtimeId}>Switch Fidelity</Button>

        <Divider>Parameters</Divider>

        <Form form={form} layout="vertical">
          {fieldMap[modelType]}
          <Button type="primary" onClick={handleApply} block>Apply Parameters</Button>
        </Form>
      </Space>
    </Card>
  );
};

export default ModelParameterConfig;