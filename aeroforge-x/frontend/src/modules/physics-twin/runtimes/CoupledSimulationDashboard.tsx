import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Modal, Form, Select, InputNumber, Statistic, Row, Col, Steps, Badge, message } from 'antd';
import { usePhysicsPluginStore } from '../../../stores/physicsPluginStore';

const CoupledSimulationDashboard: React.FC = () => {
  const { coupledSimulations, plugins, fetchPlugins, createCoupledSimulation, stepCoupledSimulation, switchFidelity } = usePhysicsPluginStore();
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [selectedSim, setSelectedSim] = useState<string | null>(null);

  useEffect(() => {
    fetchPlugins();
  }, []);

  const handleCreate = () => {
    form.validateFields().then(async (values) => {
      await createCoupledSimulation(values);
      message.success('Coupled simulation created');
      setCreateModalOpen(false);
      form.resetFields();
    });
  };

  const handleStep = async (simId: string) => {
    await stepCoupledSimulation(simId, 0.01);
    message.info('Step executed');
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id' },
    { title: 'Models', dataIndex: 'models', key: 'models', render: (models: string[]) => models?.map((m) => <Tag key={m}>{m}</Tag>) },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (s: string) => <Badge status={s === 'running' ? 'processing' : s === 'completed' ? 'success' : 'default'} text={s} /> },
    { title: 'Step', dataIndex: 'current_step', key: 'current_step' },
    { title: 'Fidelity', dataIndex: 'fidelity', key: 'fidelity', render: (f: Record<string, string>) => Object.entries(f || {}).map(([k, v]) => <Tag key={k} color={v === 'detail' ? 'red' : v === 'mid' ? 'orange' : 'green'}>{k}: {v}</Tag>) },
    {
      title: 'Actions', key: 'actions',
      render: (_: any, record: any) => (
        <Space>
          <Button size="small" type="primary" onClick={() => handleStep(record.id)} disabled={record.status === 'completed'}>Step</Button>
        </Space>
      ),
    },
  ];

  const runningCount = coupledSimulations.filter((s) => s.status === 'running').length;

  return (
    <div>
      <Card title="Coupled Simulation Dashboard" extra={<Button type="primary" onClick={() => setCreateModalOpen(true)}>New Coupled Simulation</Button>}>
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={8}><Statistic title="Total Simulations" value={coupledSimulations.length} /></Col>
          <Col span={8}><Statistic title="Running" value={runningCount} valueStyle={{ color: '#1890ff' }} /></Col>
          <Col span={8}><Statistic title="Completed" value={coupledSimulations.filter((s) => s.status === 'completed').length} valueStyle={{ color: '#3f8600' }} /></Col>
        </Row>

        <Card title="Data Exchange Flow" size="small" style={{ marginBottom: 16 }}>
          <Steps
            current={-1}
            items={[
              { title: '6DOF Model', description: 'Position, Velocity, Attitude' },
              { title: '→ Control Model', description: 'State → Control Output' },
              { title: '→ 6DOF Model', description: 'Control → Forces/Moments' },
              { title: '→ Battery Model', description: 'Power Draw → SOC Update' },
            ]}
          />
        </Card>

        <Table dataSource={coupledSimulations} columns={columns} rowKey="id" pagination={{ pageSize: 10 }} />
      </Card>

      <Modal title="Create Coupled Simulation" open={createModalOpen} onOk={handleCreate} onCancel={() => setCreateModalOpen(false)} width={560}>
        <Form form={form} layout="vertical">
          <Form.Item name="models" label="Models" rules={[{ required: true }]}>
            <Select mode="multiple" options={[
              { label: '6DOF Rigid Body', value: 'dof6' },
              { label: 'Battery', value: 'battery' },
              { label: 'Control', value: 'control' },
            ]} />
          </Form.Item>
          <Form.Item name="dof6_fidelity" label="6DOF Fidelity">
            <Select options={[{ label: 'Low', value: 'low' }, { label: 'Mid', value: 'mid' }, { label: 'Detail', value: 'detail' }]} />
          </Form.Item>
          <Form.Item name="battery_fidelity" label="Battery Fidelity">
            <Select options={[{ label: 'Low', value: 'low' }, { label: 'Mid', value: 'mid' }, { label: 'Detail', value: 'detail' }]} />
          </Form.Item>
          <Form.Item name="control_fidelity" label="Control Fidelity">
            <Select options={[{ label: 'Low', value: 'low' }, { label: 'Mid', value: 'mid' }, { label: 'Detail', value: 'detail' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default CoupledSimulationDashboard;