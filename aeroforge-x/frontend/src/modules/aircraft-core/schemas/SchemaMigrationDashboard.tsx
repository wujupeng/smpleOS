import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Modal, Select, InputNumber, Progress, Statistic, Row, Col, Alert, message } from 'antd';
import { useSchemaStore } from '../../../stores/schemaStore';

const SchemaMigrationDashboard: React.FC = () => {
  const { schemas, migrationResult, loading, fetchSchemas, executeMigration, batchMigrate } = useSchemaStore();
  const [migrateModalOpen, setMigrateModalOpen] = useState(false);
  const [selectedSchema, setSelectedSchema] = useState('');
  const [fromVersion, setFromVersion] = useState(1);
  const [toVersion, setToVersion] = useState(2);

  useEffect(() => {
    fetchSchemas();
  }, []);

  const handleMigrate = async () => {
    if (!selectedSchema) return;
    await executeMigration(selectedSchema, { from_version: fromVersion, to_version: toVersion });
    message.info('Migration completed');
  };

  const handleBatchMigrate = async () => {
    await batchMigrate({ schema_type: selectedSchema, from_version: fromVersion, to_version: toVersion });
    message.info('Batch migration completed');
  };

  const schemaTypes = [...new Set(schemas.map((s) => s.schema_type))];

  return (
    <div>
      <Card title="Schema Migration Dashboard" extra={
        <Button type="primary" onClick={() => setMigrateModalOpen(true)}>Start Migration</Button>
      }>
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}><Statistic title="Total Schemas" value={schemas.length} /></Col>
          <Col span={6}><Statistic title="Published" value={schemas.filter((s) => s.status === 'PUBLISHED').length} valueStyle={{ color: '#3f8600' }} /></Col>
          <Col span={6}><Statistic title="Draft" value={schemas.filter((s) => s.status === 'DRAFT').length} /></Col>
          <Col span={6}><Statistic title="Deprecated" value={schemas.filter((s) => s.status === 'DEPRECATED').length} valueStyle={{ color: '#cf1322' }} /></Col>
        </Row>

        {migrationResult && (
          <Card title="Last Migration Result" size="small" style={{ marginBottom: 16 }}>
            <Row gutter={16}>
              <Col span={8}><Progress type="circle" percent={migrationResult.total ? Math.round((migrationResult.succeeded / migrationResult.total) * 100) : 0} /></Col>
              <Col span={16}>
                <Space direction="vertical">
                  <Statistic title="Total" value={migrationResult.total} />
                  <Statistic title="Succeeded" value={migrationResult.succeeded} valueStyle={{ color: '#3f8600' }} />
                  <Statistic title="Failed" value={migrationResult.failed} valueStyle={{ color: migrationResult.failed > 0 ? '#cf1322' : '#3f8600' }} />
                </Space>
              </Col>
            </Row>
            {migrationResult.failures?.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <Alert type="error" message={`${migrationResult.failures.length} objects failed migration`} style={{ marginBottom: 8 }} />
                <Table
                  dataSource={migrationResult.failures}
                  columns={[
                    { title: 'Object ID', dataIndex: 'object_id', key: 'object_id' },
                    { title: 'Error', dataIndex: 'error', key: 'error', render: (e: string) => <Tag color="red">{e}</Tag> },
                  ]}
                  rowKey="object_id"
                  pagination={{ pageSize: 5 }}
                  size="small"
                />
              </div>
            )}
          </Card>
        )}

        <Table
          dataSource={schemas}
          columns={[
            { title: 'Schema Type', dataIndex: 'schema_type', key: 'schema_type' },
            { title: 'Version', dataIndex: 'version', key: 'version', render: (v: number) => `v${v}` },
            { title: 'Status', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color={s === 'PUBLISHED' ? 'green' : s === 'DEPRECATED' ? 'red' : 'default'}>{s}</Tag> },
            { title: 'Fields', dataIndex: 'fields', key: 'fields', render: (f: any[]) => f?.length || 0 },
          ]}
          rowKey={(r) => `${r.schema_type}-${r.version}`}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      <Modal title="Execute Migration" open={migrateModalOpen} onOk={handleMigrate} onCancel={() => setMigrateModalOpen(false)} width={480}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <span>Schema Type: </span>
            <Select style={{ width: 240 }} value={selectedSchema || undefined} onChange={setSelectedSchema} placeholder="Select Schema">
              {schemaTypes.map((t) => <Select.Option key={t} value={t}>{t}</Select.Option>)}
            </Select>
          </div>
          <div>
            <span>From Version: </span><InputNumber min={1} value={fromVersion} onChange={(v) => setFromVersion(v || 1)} />
          </div>
          <div>
            <span>To Version: </span><InputNumber min={1} value={toVersion} onChange={(v) => setToVersion(v || 2)} />
          </div>
          <Button block onClick={handleBatchMigrate} disabled={!selectedSchema}>Batch Migrate All Objects</Button>
        </Space>
      </Modal>
    </div>
  );
};

export default SchemaMigrationDashboard;