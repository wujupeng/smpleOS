import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Modal, Form, Input, Select, InputNumber, message, Steps } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { usePropagationStore } from '../../../stores/propagationStore';

const TRIGGER_EVENTS = [
  'aeroforge.aircraft.object.updated',
  'aeroforge.aircraft.object.created',
  'aeroforge.twin.anomaly.detected',
  'aeroforge.ebom.generated',
];

const HANDLER_NAMES = [
  'DesignRuleCheckHandler', 'CAETriggerHandler', 'CFDAnalysisHandler', 'FEAAnalysisHandler',
  'MBOMTransformHandler', 'WorkOrderGenerateHandler',
  'FRACASCreateHandler', 'RootCauseAnalysisHandler', 'ComplianceCheckHandler', 'ComplianceImpactHandler',
];

const GATE_TYPES = ['HumanTask', 'DualApproval', 'AutoApproval'];

const CHAIN_TEMPLATES = [
  {
    name: 'DesignToCAE',
    trigger_event: 'aeroforge.aircraft.object.updated',
    handlers: ['DesignRuleCheckHandler', 'CAETriggerHandler', 'CFDAnalysisHandler', 'FEAAnalysisHandler'],
    gates: [{ type: 'HumanTask', timeout_hours: 24, approvers: ['cae_engineer'] }],
  },
  {
    name: 'EBOMToMBOM',
    trigger_event: 'aeroforge.ebom.generated',
    handlers: ['MBOMTransformHandler', 'WorkOrderGenerateHandler'],
    gates: [{ type: 'HumanTask', timeout_hours: 48, approvers: ['manufacturing_engineer'] }],
  },
  {
    name: 'TwinToFRACAS',
    trigger_event: 'aeroforge.twin.anomaly.detected',
    handlers: ['FRACASCreateHandler', 'RootCauseAnalysisHandler', 'ComplianceImpactHandler'],
    gates: [{ type: 'HumanTask', timeout_hours: 12, approvers: ['safety_engineer'] }, { type: 'DualApproval', timeout_hours: 24, approvers: ['safety_engineer', 'cert_manager'] }],
  },
];

const PropagationChainConfig: React.FC = () => {
  const { chains, handlers, fetchChains, fetchHandlers, configureChain } = usePropagationStore();
  const [modalOpen, setModalOpenOpen] = useState(false);
  const [form] = Form.useForm();
  const [handlerSteps, setHandlerSteps] = useState<string[]>([]);
  const [gateConfigs, setGateConfigs] = useState<any[]>([]);

  useEffect(() => {
    fetchChains();
    fetchHandlers();
  }, []);

  const handleAddHandler = (name: string) => {
    setHandlerSteps([...handlerSteps, name]);
  };

  const handleRemoveHandler = (index: number) => {
    setHandlerSteps(handlerSteps.filter((_, i) => i !== index));
  };

  const handleAddGate = () => {
    setGateConfigs([...gateConfigs, { type: 'HumanTask', timeout_hours: 24, approvers: [] }]);
  };

  const handleCreate = () => {
    form.validateFields().then(async (values) => {
      await configureChain({
        name: values.name,
        trigger_event: values.trigger_event,
        handlers: handlerSteps.map((name) => ({ name, config: {} })),
        gates: gateConfigs,
      });
      message.success('Chain configured');
      setModalOpenOpen(false);
      form.resetFields();
      setHandlerSteps([]);
      setGateConfigs([]);
    });
  };

  const handleTemplate = (template: typeof CHAIN_TEMPLATES[0]) => {
    form.setFieldsValue({ name: template.name, trigger_event: template.trigger_event });
    setHandlerSteps(template.handlers);
    setGateConfigs(template.gates);
    setModalOpenOpen(true);
  };

  const columns = [
    { title: 'Chain Name', dataIndex: 'name', key: 'name' },
    { title: 'Trigger Event', dataIndex: 'trigger_event', key: 'trigger_event', render: (e: string) => <Tag>{e}</Tag> },
    { title: 'Handlers', dataIndex: 'handlers', key: 'handlers', render: (h: any[]) => h?.map((hi, i) => <Tag key={i} color="blue">{hi.name}</Tag>) },
    { title: 'Gates', dataIndex: 'gates', key: 'gates', render: (g: any[]) => g?.map((gi, i) => <Tag key={i} color="orange">{gi.type} ({gi.timeout_hours}h)</Tag>) },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color={s === 'active' ? 'green' : 'default'}>{s}</Tag> },
  ];

  return (
    <div>
      <Card title="Propagation Chain Configuration" extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpenOpen(true)}>New Chain</Button>}>
        <Card title="Quick Templates" size="small" style={{ marginBottom: 16 }}>
          <Space>
            {CHAIN_TEMPLATES.map((t) => (
              <Button key={t.name} onClick={() => handleTemplate(t)}>{t.name}</Button>
            ))}
          </Space>
        </Card>

        <Table dataSource={chains} columns={columns} rowKey="id" pagination={{ pageSize: 10 }} />
      </Card>

      <Modal title="Configure Propagation Chain" open={modalOpen} onOk={handleCreate} onCancel={() => { setModalOpenOpen(false); setHandlerSteps([]); setGateConfigs([]); }} width={720}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="Chain Name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="trigger_event" label="Trigger Event" rules={[{ required: true }]}>
            <Select options={TRIGGER_EVENTS.map((e) => ({ label: e, value: e }))} />
          </Form.Item>
        </Form>

        <Card title="Handler Pipeline" size="small" style={{ marginBottom: 16 }}>
          <Steps current={-1} direction="vertical" size="small" items={handlerSteps.map((h, i) => ({
            title: h,
            status: 'wait' as const,
            description: <Button size="small" danger onClick={() => handleRemoveHandler(i)}>Remove</Button>,
          }))} />
          <Select style={{ width: '100%', marginTop: 8 }} placeholder="Add handler..." onChange={handleAddHandler}
            options={HANDLER_NAMES.filter((h) => !handlerSteps.includes(h)).map((h) => ({ label: h, value: h }))} />
        </Card>

        <Card title="Approval Gates" size="small" extra={<Button size="small" onClick={handleAddGate}>Add Gate</Button>}>
          {gateConfigs.map((gate, i) => (
            <Space key={i} style={{ display: 'flex', marginBottom: 8 }}>
              <Select value={gate.type} onChange={(v) => { const g = [...gateConfigs]; g[i] = { ...g[i], type: v }; setGateConfigs(g); }}
                style={{ width: 140 }} options={GATE_TYPES.map((t) => ({ label: t, value: t }))} />
              <InputNumber value={gate.timeout_hours} onChange={(v) => { const g = [...gateConfigs]; g[i] = { ...g[i], timeout_hours: v || 24 }; setGateConfigs(g); }}
                addonBefore="Timeout" addonAfter="h" />
              <Button size="small" danger onClick={() => setGateConfigs(gateConfigs.filter((_, j) => j !== i))}>Remove</Button>
            </Space>
          ))}
        </Card>
      </Modal>
    </div>
  );
};

export default PropagationChainConfig;