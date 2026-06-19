import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Descriptions, Tabs, Tag, Button, Space, Timeline } from 'antd';
import { aircraftCoreApi } from '../../../api/aircraftCoreApi';

const AircraftObjectDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [object, setObject] = useState<any>(null);
  const [versions, setVersions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      fetchObject();
      fetchVersions();
    }
  }, [id]);

  const fetchObject = async () => {
    setLoading(true);
    try {
      const data = await aircraftCoreApi.getObject(id!);
      setObject(data);
    } catch (error) {
      console.error('Failed to fetch object:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchVersions = async () => {
    try {
      const data = await aircraftCoreApi.getVersions(id!);
      setVersions(data.versions || []);
    } catch (error) {
      console.error('Failed to fetch versions:', error);
    }
  };

  const lifecycleColorMap: Record<string, string> = {
    Concept: 'default', Design: 'blue', Manufacturing: 'orange',
    Test: 'purple', Operation: 'green', Retirement: 'red',
  };

  if (!object) return <Card loading={loading}>Loading...</Card>;

  const domainTabs = [
    { key: 'design', label: 'Design Data', children: <pre>{JSON.stringify(object.design_data || {}, null, 2)}</pre> },
    { key: 'manufacturing', label: 'Manufacturing Data', children: <pre>{JSON.stringify(object.manufacturing_data || {}, null, 2)}</pre> },
    { key: 'operation', label: 'Operation Data', children: <pre>{JSON.stringify(object.operation_data || {}, null, 2)}</pre> },
    { key: 'certification', label: 'Certification Data', children: <pre>{JSON.stringify(object.certification_data || {}, null, 2)}</pre> },
  ];

  return (
    <Card title={`Aircraft Object: ${object.name || id}`} extra={<Space><Button onClick={() => navigate(`/aircraft-core/objects/${id}/impact`)}>Impact Analysis</Button><Button onClick={() => navigate(`/aircraft-core/objects/${id}/versions/diff`)}>Version Diff</Button></Space>}>
      <Descriptions bordered column={2} style={{ marginBottom: 24 }}>
        <Descriptions.Item label="ID">{object.id}</Descriptions.Item>
        <Descriptions.Item label="Name">{object.name}</Descriptions.Item>
        <Descriptions.Item label="Type"><Tag>{object.object_type}</Tag></Descriptions.Item>
        <Descriptions.Item label="Lifecycle"><Tag color={lifecycleColorMap[object.lifecycle_state] || 'default'}>{object.lifecycle_state}</Tag></Descriptions.Item>
        <Descriptions.Item label="Version">{object.optimistic_lock_version}</Descriptions.Item>
        <Descriptions.Item label="Updated">{object.updated_at ? new Date(object.updated_at).toLocaleString() : '-'}</Descriptions.Item>
      </Descriptions>
      <Tabs items={domainTabs} />
      <Card title="Version History" style={{ marginTop: 16 }}>
        <Timeline items={versions.map((v: any) => ({
          children: `V${v.version_number} - ${v.change_summary} (${v.author}) ${v.is_frozen ? '🔒 Frozen' : ''}`,
        }))} />
      </Card>
    </Card>
  );
};

export default AircraftObjectDetail;