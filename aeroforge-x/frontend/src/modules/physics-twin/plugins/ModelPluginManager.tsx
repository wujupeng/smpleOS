import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Modal, Form, Input, Select, Upload, message, Badge, Statistic, Row, Col } from 'antd';
import { PlusOutlined, ReloadOutlined, ApiOutlined } from '@ant-design/icons';
import { usePhysicsPluginStore } from '../../../stores/physicsPluginStore';

const MODEL_TYPES = ['dof6', 'battery', 'control'];
const FIDELITY_LEVELS = ['low', 'mid', 'detail'];

const ModelPluginManager: React.FC = () => {
  const { plugins, loading, fetchPlugins, registerPlugin, hotReloadPlugin, loadPlugin } = usePhysicsPluginStore();
  const [registerModalOpen, setRegisterModalOpen] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchPlugins();
  }, []);

  const handleRegister = () => {
    form.validateFields().then(async (values) => {
      await registerPlugin(values);
      message.success(`Plugin ${values.name} registered`);
      setRegisterModalOpen(false);
      form.resetFields();
    });
  };

  const handleHotReload = async (name: string) => {
    await hotReloadPlugin(name);
    message.success(`Plugin ${name} hot-reloaded`);
  };

  const handleLoad = async (name: string) => {
    await loadPlugin(name);
    message.success(`Plugin ${name} loaded`);
  };

  const loadedCount = plugins.filter((p) => p.loaded).length;

  const columns = [
    { title: 'Plugin Name', dataIndex: 'name', key: 'name', render: (n: string) => <Space><ApiOutlined />{n}</Space> },
    { title: 'Model Type', dataIndex: 'model_type', key: 'model_type', render: (t: string) => <Tag color={t === 'dof6' ? 'blue' : t === 'battery' ? 'green' : 'orange'}>{t}</Tag> },
    { title: 'Fidelity Levels', dataIndex: 'fidelity_levels', key: 'fidelity_levels', render: (levels: string[]) => levels?.map((l) => <Tag key={l} color={l === 'detail' ? 'red' : l === 'mid' ? 'orange' : 'green'}>{l}</Tag>) },
    { title: 'Version', dataIndex: 'version', key: 'version' },
    { title: 'Status', dataIndex: 'loaded', key: 'loaded', render: (l: boolean) => l ? <Badge status="success" text="Loaded" /> : <Badge status="default" text="Unloaded" /> },
    {
      title: 'Actions', key: 'actions',
      render: (_: any, record: any) => (
        <Space>
          {!record.loaded && <Button size="small" type="primary" onClick={() => handleLoad(record.name)}>Load</Button>}
          <Button size="small" icon={<ReloadOutlined />} onClick={() => handleHotReload(record.name)}>Hot Reload</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card title="Model Plugin Manager" extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setRegisterModalOpen(true)}>Register Plugin</Button>}>
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={8}><Statistic title="Total Plugins" value={plugins.length} /></Col>
          <Col span={8}><Statistic title="Loaded" value={loadedCount} valueStyle={{ color: '#3f8600' }} /></Col>
          <Col span={8}><Statistic title="Unloaded" value={plugins.length - loadedCount} /></Col>
        </Row>
        <Table dataSource={plugins} columns={columns} rowKey="name" loading={loading} pagination={{ pageSize: 10 }} />
      </Card>

      <Modal title="Register Plugin" open={registerModalOpen} onOk={handleRegister} onCancel={() => setRegisterModalOpen(false)} width={560}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Plugin Name" rules={[{ required: true }]}><Input placeholder="e.g. dof6_linear" /></Form.Item>
          <Form.Item name="model_type" label="Model Type" rules={[{ required: true }]}>
            <Select options={MODEL_TYPES.map((t) => ({ label: t, value: t }))} />
          </Form.Item>
          <Form.Item name="fidelity_levels" label="Fidelity Levels" rules={[{ required: true }]}>
            <Select mode="multiple" options={FIDELITY_LEVELS.map((l) => ({ label: l, value: l }))} />
          </Form.Item>
          <Form.Item name="version" label="Version"><Input placeholder="1.0.0" /></Form.Item>
          <Form.Item name="module_path" label="Module Path" rules={[{ required: true }]}><Input placeholder="domain.plugins.dof6_model" /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ModelPluginManager;