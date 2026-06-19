import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Modal, InputNumber, message, Steps, Alert, Descriptions, Progress } from 'antd';
import { useSchemaStore } from '../../../stores/schemaStore';
import { schemaApi } from '../../../api/schemaApi';

const SchemaVersionManager: React.FC = () => {
  const { schemas, fetchSchemas, publishVersion, deprecateVersion } = useSchemaStore();
  const [compatResult, setCompatResult] = useState<any>(null);
  const [compatModalOpen, setCompatModalOpen] = useState(false);
  const [selectedSchemaType, setSelectedSchemaType] = useState('');
  const [fromVersion, setFromVersion] = useState(1);
  const [toVersion, setToVersion] = useState(2);

  useEffect(() => {
    fetchSchemas();
  }, []);

  const checkCompatibility = async () => {
    try {
      const result = await schemaApi.validateCompatibility(selectedSchemaType, fromVersion, toVersion);
      setCompatResult(result);
      setCompatModalOpen(true);
    } catch (e: any) {
      message.error(e.message);
    }
  };

  const handlePublish = async (schemaType: string, version: number) => {
    await publishVersion(schemaType, version);
    message.success(`Published ${schemaType} v${version}`);
  };

  const handleDeprecate = async (schemaType: string, version: number) => {
    await deprecateVersion(schemaType, version);
    message.warning(`Deprecated ${schemaType} v${version}`);
  };

  const columns = [
    { title: 'Schema Type', dataIndex: 'schema_type', key: 'schema_type' },
    { title: 'Version', dataIndex: 'version', key: 'version', render: (v: number) => `v${v}` },
    {
      title: 'Status', dataIndex: 'status', key: 'status',
      render: (s: string) => {
        const colorMap: Record<string, string> = { DRAFT: 'default', PUBLISHED: 'green', DEPRECATED: 'red' };
        return <Tag color={colorMap[s]}>{s}</Tag>;
      },
    },
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

  return (
    <div>
      <Card title="Schema Version Manager">
        <Space style={{ marginBottom: 16 }}>
          <select value={selectedSchemaType} onChange={(e) => setSelectedSchemaType(e.target.value)} style={{ padding: '4px 8px', borderRadius: 4 }}>
            <option value="">Select Schema</option>
            {[...new Set(schemas.map((s) => s.schema_type))].map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <span>From v</span><InputNumber min={1} value={fromVersion} onChange={(v) => setFromVersion(v || 1)} />
          <span>To v</span><InputNumber min={1} value={toVersion} onChange={(v) => setToVersion(v || 2)} />
          <Button type="primary" onClick={checkCompatibility} disabled={!selectedSchemaType}>Check Compatibility</Button>
        </Space>
        <Table dataSource={schemas} columns={columns} rowKey={(r) => `${r.schema_type}-${r.version}`} pagination={{ pageSize: 10 }} />
      </Card>

      <Modal title="Compatibility Check Result" open={compatModalOpen} onCancel={() => setCompatModalOpen(false)} footer={null} width={600}>
        {compatResult && (
          <div>
            <Alert
              type={compatResult.compatible ? 'success' : 'warning'}
              message={compatResult.compatible ? 'Versions are compatible' : 'Breaking changes detected'}
              style={{ marginBottom: 16 }}
            />
            {compatResult.breaking_changes?.length > 0 && (
              <Card title="Breaking Changes" size="small" style={{ marginBottom: 16 }}>
                {compatResult.breaking_changes.map((c: any, i: number) => (
                  <div key={i}><Tag color="red">{c.type}</Tag> {c.field_path}: {c.description}</div>
                ))}
              </Card>
            )}
            {compatResult.migration_path && (
              <Card title="Migration Path" size="small">
                <Steps current={-1} items={compatResult.migration_path.steps?.map((s: any) => ({
                  title: s.action,
                  description: s.description,
                })) || []} />
              </Card>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default SchemaVersionManager;