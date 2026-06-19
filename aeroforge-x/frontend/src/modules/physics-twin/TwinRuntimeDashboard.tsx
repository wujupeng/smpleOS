import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Statistic, Row, Col } from 'antd';
import { physicsTwinApi } from '../../../api/physicsTwinApi';

const TwinRuntimeDashboard: React.FC = () => {
  const [runtimes, setRuntimes] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchRuntimes();
  }, []);

  const fetchRuntimes = async () => {
    setLoading(true);
    try {
      const data = await physicsTwinApi.listRuntimes();
      setRuntimes(data.runtimes || []);
    } catch (error) {
      console.error('Failed to fetch runtimes:', error);
    } finally {
      setLoading(false);
    }
  };

  const healthyCount = runtimes.filter((r: any) => !r.data_lagged).length;
  const laggedCount = runtimes.filter((r: any) => r.data_lagged).length;

  const columns = [
    { title: 'Runtime ID', dataIndex: 'runtime_id', key: 'runtime_id' },
    { title: 'Aircraft Object', dataIndex: 'aircraft_object_id', key: 'aircraft_object_id' },
    { title: 'Fidelity', dataIndex: 'active_fidelity', key: 'active_fidelity', render: (f: string) => <Tag color={f === 'High' ? 'red' : f === 'Mid' ? 'orange' : 'green'}>{f}</Tag> },
    { title: 'Data Status', dataIndex: 'data_lagged', key: 'data_lagged', render: (l: boolean) => l ? <Tag color="red">Lagged</Tag> : <Tag color="green">OK</Tag> },
    { title: 'Last Sensor', dataIndex: 'last_sensor_timestamp', key: 'last_sensor_timestamp', render: (d: string) => d ? new Date(d).toLocaleString() : '-' },
  ];

  return (
    <Card title="Digital Twin Runtime Dashboard">
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}><Statistic title="Total Runtimes" value={runtimes.length} /></Col>
        <Col span={8}><Statistic title="Healthy" value={healthyCount} valueStyle={{ color: '#3f8600' }} /></Col>
        <Col span={8}><Statistic title="Data Lagged" value={laggedCount} valueStyle={{ color: laggedCount > 0 ? '#cf1322' : '#3f8600' }} /></Col>
      </Row>
      <Table dataSource={runtimes} columns={columns} rowKey="runtime_id" loading={loading} />
    </Card>
  );
};

export default TwinRuntimeDashboard;