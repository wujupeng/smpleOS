import React, { useEffect, useState } from 'react';
import { Card, Descriptions, Tag, Table, Alert, Badge, Space, Select, Button } from 'antd';
import { useParams } from 'react-router-dom';
import { schemaApi } from '../../../api/schemaApi';

const SCHEMA_LABELS: Record<string, string> = {
  AircraftGeometry: 'Geometry',
  AircraftStructure: 'Structure',
  AircraftPropulsion: 'Propulsion',
  AircraftAvionics: 'Avionics',
  AircraftFlightEnvelope: 'Flight Envelope',
  AircraftCertification: 'Certification',
};

const SchemaInstanceViewer: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [instance, setInstance] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedSchema, setSelectedSchema] = useState<string | null>(null);

  useEffect(() => {
    if (id) fetchInstance();
  }, [id]);

  const fetchInstance = async () => {
    setLoading(true);
    try {
      const data = await schemaApi.getSchemaInstance(id!);
      setInstance(data);
      const schemas = Object.keys(data.schema_instances || {});
      if (schemas.length > 0) setSelectedSchema(schemas[0]);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  if (!instance) return <Card loading={loading}>Loading schema instance...</Card>;

  const schemaInstances = instance.schema_instances || {};
  const schemaTypes = Object.keys(schemaInstances);

  const currentData = selectedSchema ? schemaInstances[selectedSchema] : null;
  const validation = currentData?._validation || {};
  const derived = currentData?._derived_params || {};

  const dataFields = currentData
    ? Object.entries(currentData).filter(([k]) => !k.startsWith('_')).map(([key, value]) => ({ key, value }))
    : [];

  return (
    <Card title={`Schema Instance: ${instance.object_name || id}`} loading={loading}>
      <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
        <Descriptions.Item label="Object ID">{instance.object_id}</Descriptions.Item>
        <Descriptions.Item label="Object Type"><Tag>{instance.object_type}</Tag></Descriptions.Item>
      </Descriptions>

      <Space style={{ marginBottom: 16 }}>
        {schemaTypes.map((st) => (
          <Button key={st} type={selectedSchema === st ? 'primary' : 'default'} onClick={() => setSelectedSchema(st)}>
            {SCHEMA_LABELS[st] || st}
          </Button>
        ))}
      </Space>

      {validation && (
        <Alert
          type={validation.valid ? 'success' : 'error'}
          message={validation.valid ? 'All validations passed' : `${validation.errors?.length || 0} validation errors`}
          style={{ marginBottom: 16 }}
          description={validation.errors?.length > 0 && (
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {validation.errors.map((e: any, i: number) => <li key={i}>{e.field}: {e.message}</li>)}
            </ul>
          )}
        />
      )}

      {validation?.warnings?.length > 0 && (
        <Alert type="warning" message="Warnings" style={{ marginBottom: 16 }}
          description={
            <ul style={{ margin: 0, paddingLeft: 20 }}>
              {validation.warnings.map((w: any, i: number) => <li key={i}>{w.field}: {w.message}</li>)}
            </ul>
          }
        />
      )}

      {currentData && (
        <Table
          dataSource={dataFields}
          columns={[
            { title: 'Field', dataIndex: 'key', key: 'key', render: (k: string) => <Text strong>{k}</Text> },
            {
              title: 'Value', dataIndex: 'value', key: 'value',
              render: (v: any) => typeof v === 'object' ? <pre style={{ margin: 0 }}>{JSON.stringify(v, null, 2)}</pre> : String(v),
            },
          ]}
          rowKey="key"
          pagination={false}
          size="small"
        />
      )}

      {Object.keys(derived).length > 0 && (
        <Card title="Derived Parameters" size="small" style={{ marginTop: 16 }}>
          <Table
            dataSource={Object.entries(derived).map(([k, v]) => ({ key: k, value: v }))}
            columns={[
              { title: 'Parameter', dataIndex: 'key', key: 'key' },
              { title: 'Value', dataIndex: 'value', key: 'value', render: (v: any) => String(v) },
            ]}
            rowKey="key"
            pagination={false}
            size="small"
          />
        </Card>
      )}
    </Card>
  );
};

const Text: React.FC<{ strong?: boolean; children: React.ReactNode }> = ({ strong, children }) => (
  <span style={{ fontWeight: strong ? 600 : 400 }}>{children}</span>
);

export default SchemaInstanceViewer;