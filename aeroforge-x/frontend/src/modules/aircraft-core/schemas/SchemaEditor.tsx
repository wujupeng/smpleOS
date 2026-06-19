import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Modal, Form, Input, Select, InputNumber, Switch, message, Descriptions, Badge } from 'antd';
import { PlusOutlined, EditOutlined } from '@ant-design/icons';
import { useSchemaStore } from '../../../stores/schemaStore';

const SCHEMA_TYPES = [
  'AircraftGeometry', 'AircraftStructure', 'AircraftPropulsion',
  'AircraftAvionics', 'AircraftFlightEnvelope', 'AircraftCertification',
];

const DATA_TYPES = ['float', 'int', 'str', 'bool', 'enum', 'SubSchema'];

const statusColorMap: Record<string, string> = {
  DRAFT: 'default', PUBLISHED: 'green', DEPRECATED: 'red',
};

const SchemaEditor: React.FC = () => {
  const { schemas, selectedSchema, loading, fetchSchemas, selectSchema, publishVersion, deprecateVersion, registerSchema } = useSchemaStore();
  const [modalOpen, setModalOpen] = useState(false);
  const [fieldModalOpen, setFieldModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [fieldForm] = Form.useForm();
  const [editingFields, setEditingFields] = useState<any[]>([]);

  useEffect(() => {
    fetchSchemas();
  }, []);

  const handlePublish = async (schemaType: string, version: number) => {
    await publishVersion(schemaType, version);
    message.success(`Schema ${schemaType} v${version} published`);
  };

  const handleDeprecate = async (schemaType: string, version: number) => {
    await deprecateVersion(schemaType, version);
    message.warning(`Schema ${schemaType} v${version} deprecated`);
  };

  const handleAddField = () => {
    fieldForm.validateFields().then((values) => {
      setEditingFields([...editingFields, { ...values, required: values.required || false }]);
      fieldForm.resetFields();
      setFieldModalOpen(false);
    });
  };

  const handleRegisterSchema = () => {
    form.validateFields().then(async (values) => {
      await registerSchema({ ...values, fields: editingFields });
      message.success('Schema registered');
      setModalOpen(false);
      form.resetFields();
      setEditingFields([]);
      fetchSchemas();
    });
  };

  const schemaColumns = [
    { title: 'Schema Type', dataIndex: 'schema_type', key: 'schema_type', render: (t: string) => <a onClick={() => selectSchema(t)}>{t}</a> },
    { title: 'Version', dataIndex: 'version', key: 'version' },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color={statusColorMap[s]}>{s}</Tag> },
    { title: 'Fields', dataIndex: 'fields', key: 'fields', render: (f: any[]) => f?.length || 0 },
    { title: 'Updated', dataIndex: 'updated_at', key: 'updated_at', render: (d: string) => d ? new Date(d).toLocaleString() : '-' },
    {
      title: 'Actions', key: 'actions',
      render: (_: any, record: any) => (
        <Space>
          {record.status === 'DRAFT' && <Button size="small" type="primary" onClick={() => handlePublish(record.schema_type, record.version)}>Publish</Button>}
          {record.status === 'PUBLISHED' && <Button size="small" danger onClick={() => handleDeprecate(record.schema_type, record.version)}>Deprecate</Button>}
        </Space>
      ),
    },
  ];

  const fieldColumns = [
    { title: 'Field Path', dataIndex: 'field_path', key: 'field_path' },
    { title: 'Data Type', dataIndex: 'data_type', key: 'data_type', render: (t: string) => <Tag>{t}</Tag> },
    { title: 'Unit', dataIndex: 'unit', key: 'unit' },
    { title: 'Required', dataIndex: 'required', key: 'required', render: (r: boolean) => r ? <Badge status="error" text="Required" /> : <Badge status="default" text="Optional" /> },
    { title: 'Default', dataIndex: 'default_value', key: 'default_value', render: (v: any) => v !== undefined ? String(v) : '-' },
  ];

  return (
    <div>
      <Card title="Schema Registry" extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>Register Schema</Button>}>
        <Table dataSource={schemas} columns={schemaColumns} rowKey="schema_type" loading={loading} pagination={{ pageSize: 10 }} />
      </Card>

      {selectedSchema && (
        <Card title={`Schema: ${selectedSchema.schema_type} v${selectedSchema.version}`} style={{ marginTop: 16 }}
          extra={<Tag color={statusColorMap[selectedSchema.status]}>{selectedSchema.status}</Tag>}>
          <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
            <Descriptions.Item label="Schema Type">{selectedSchema.schema_type}</Descriptions.Item>
            <Descriptions.Item label="Version">{selectedSchema.version}</Descriptions.Item>
            <Descriptions.Item label="Status"><Tag color={statusColorMap[selectedSchema.status]}>{selectedSchema.status}</Tag></Descriptions.Item>
            <Descriptions.Item label="Fields Count">{selectedSchema.fields?.length || 0}</Descriptions.Item>
          </Descriptions>
          <Table dataSource={selectedSchema.fields || []} columns={fieldColumns} rowKey="field_path" pagination={false} size="small" />
        </Card>
      )}

      <Modal title="Register New Schema" open={modalOpen} onOk={handleRegisterSchema} onCancel={() => { setModalOpen(false); setEditingFields([]); }} width={720}>
        <Form form={form} layout="vertical">
          <Form.Item name="schema_type" label="Schema Type" rules={[{ required: true }]}>
            <Select options={SCHEMA_TYPES.map((t) => ({ label: t, value: t }))} />
          </Form.Item>
        </Form>
        <Card title="Fields" size="small" extra={<Button size="small" icon={<PlusOutlined />} onClick={() => setFieldModalOpen(true)}>Add Field</Button>}>
          <Table dataSource={editingFields} columns={fieldColumns} rowKey="field_path" pagination={false} size="small" />
        </Card>
      </Modal>

      <Modal title="Add Field" open={fieldModalOpen} onOk={handleAddField} onCancel={() => setFieldModalOpen(false)}>
        <Form form={fieldForm} layout="vertical">
          <Form.Item name="field_path" label="Field Path" rules={[{ required: true }]}><Input placeholder="e.g. wingspan" /></Form.Item>
          <Form.Item name="data_type" label="Data Type" rules={[{ required: true }]}><Select options={DATA_TYPES.map((t) => ({ label: t, value: t }))} /></Form.Item>
          <Form.Item name="unit" label="Unit"><Input placeholder="e.g. m, kg, Pa" /></Form.Item>
          <Form.Item name="required" label="Required" valuePropName="checked"><Switch /></Form.Item>
          <Form.Item name="default_value" label="Default Value"><Input /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SchemaEditor;