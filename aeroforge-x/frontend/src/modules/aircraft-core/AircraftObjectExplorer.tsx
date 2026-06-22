import React, { useEffect, useState } from 'react';
import { Table, Input, Select, Space, Card, Tag, Button } from 'antd';
import { useNavigate } from 'react-router-dom';
import { aircraftCoreApi } from '../../api/aircraftCoreApi';

const { Search } = Input;

const AircraftObjectExplorer: React.FC = () => {
  const navigate = useNavigate();
  const [objects, setObjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [objectType, setObjectType] = useState<string | undefined>(undefined);

  const fetchObjects = async () => {
    setLoading(true);
    try {
      const data = await aircraftCoreApi.listObjects(objectType);
      setObjects(data.objects || []);
    } catch (error) {
      console.error('Failed to fetch objects:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchObjects();
  }, [objectType]);

  const lifecycleColorMap: Record<string, string> = {
    Concept: 'default',
    Design: 'blue',
    Manufacturing: 'orange',
    Test: 'purple',
    Operation: 'green',
    Retirement: 'red',
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', render: (id: string) => <a onClick={() => navigate(`/aircraft-core/objects/${id}`)}>{id}</a> },
    { title: 'Name', dataIndex: 'name', key: 'name' },
    { title: 'Type', dataIndex: 'object_type', key: 'object_type', render: (t: string) => <Tag>{t}</Tag> },
    { title: 'Lifecycle', dataIndex: 'lifecycle_state', key: 'lifecycle_state', render: (s: string) => <Tag color={lifecycleColorMap[s] || 'default'}>{s}</Tag> },
    { title: 'Updated', dataIndex: 'updated_at', key: 'updated_at', render: (d: string) => d ? new Date(d).toLocaleString() : '-' },
  ];

  return (
    <Card title="Aircraft Object Explorer" extra={<Button type="primary" onClick={() => navigate('/aircraft-core/objects/new')}>Create Object</Button>}>
      <Space style={{ marginBottom: 16 }}>
        <Select placeholder="Object Type" allowClear style={{ width: 200 }} onChange={setObjectType} value={objectType}>
          <Select.Option value="Aircraft">Aircraft</Select.Option>
          <Select.Option value="System">System</Select.Option>
          <Select.Option value="Subsystem">Subsystem</Select.Option>
          <Select.Option value="Component">Component</Select.Option>
          <Select.Option value="Part">Part</Select.Option>
        </Select>
        <Search placeholder="Search by name" style={{ width: 300 }} onSearch={() => fetchObjects()} />
      </Space>
      <Table dataSource={objects} columns={columns} rowKey="id" loading={loading} pagination={{ pageSize: 20 }} />
    </Card>
  );
};

export default AircraftObjectExplorer;