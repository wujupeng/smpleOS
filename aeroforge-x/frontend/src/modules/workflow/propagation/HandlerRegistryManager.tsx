import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Modal, Form, Input, Select, Badge, message, Statistic, Row, Col } from 'antd';
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import { usePropagationStore } from '../../../stores/propagationStore';

const HANDLER_TYPES = [
  'DesignRuleCheckHandler', 'CAETriggerHandler', 'CFDAnalysisHandler', 'FEAAnalysisHandler',
  'MBOMTransformHandler', 'WorkOrderGenerateHandler',
  'FRACASCreateHandler', 'RootCauseAnalysisHandler', 'ComplianceCheckHandler', 'ComplianceImpactHandler',
  'InspectionHandler',
];

const HandlerRegistryManager: React.FC = () => {
  const { handlers, fetchHandlers, registerHandler, hotReloadHandler } = usePropagationStore();
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchHandlers();
  }, []);

  const handleRegister = () => {
    form.validateFields().then(async (values) => {
      await registerHandler(values);
      message.success(`Handler ${values.name} registered`);
      setModalOpen(false);
      form.resetFields();
    });
  };

  const handleHotReload = async (name: string) => {
    await hotReloadHandler(name);
    message.success(`Handler ${name} hot-reloaded`);
  };

  const loadedCount = handlers.filter((h) => h.loaded).length;

  const columns = [
    { title: 'Handler Name', dataIndex: 'name', key: 'name' },
    { title: 'Version', dataIndex: 'version', key: 'version' },
    { title: 'Input Schema', dataIndex: 'input_schema', key: 'input_schema', render: (s: any) => s ? <Tag>{typeof s === 'string' ? s : 'defined'}</Tag> : '-' },
    { title: 'Output Schema', dataIndex: 'output_schema', key: 'output_schema', render: (s: any) => s ? <Tag color="green">{typeof s === 'string' ? s : 'defined'}</Tag> : '-' },
    { title: 'Status', dataIndex: 'loaded', key: 'loaded', render: (l: boolean) => l ? <Badge status="success" text="Loaded" /> : <Badge status="default" text="Unloaded" /> },
    {
      title: 'Actions', key: 'actions',
      render: (_: any, record: any) => (
        <Button size="small" icon={<ReloadOutlined />} onClick={() => handleHotReload(record.name)}>Hot Reload</Button>
      ),
    },
  ];

  return (
    <div>
      <Card title="Handler Registry Manager" extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>Register Handler</Button>}>
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={8}><Statistic title="Total Handlers" value={handlers.length} /></Col>
          <Col span={8}><Statistic title="Loaded" value={loadedCount} valueStyle={{ color: '#3f8600' }} /></Col>
          <Col span={8}><Statistic title="Unloaded" value={handlers.length - loadedCount} /></Col>
        </Row>
        <Table dataSource={handlers} columns={columns} rowKey="name" pagination={{ pageSize: 10 }} />
      </Card>

      <Modal title="Register Handler" open={modalOpen} onOk={handleRegister} onCancel={() => setModalOpen(false)}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Handler Name" rules={[{ required: true }]}>
            <Select options={HANDLER_TYPES.map((t) => ({ label: t, value: t }))} />
          </Form.Item>
          <Form.Item name="version" label="Version"><Input placeholder="1.0.0" /></Form.Item>
          <Form.Item name="module_path" label="Module Path"><Input placeholder="domain.handlers.v3_handlers" /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default HandlerRegistryManager;