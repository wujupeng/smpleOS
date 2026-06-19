import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Statistic, Row, Col, Badge, Space, Button } from 'antd';
import { usePhysicsPluginStore } from '../../../stores/physicsPluginStore';

const ModelRegistryDashboard: React.FC = () => {
  const { plugins, coupledSimulations, fetchPlugins } = usePhysicsPluginStore();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchPlugins().finally(() => setLoading(false));
  }, []);

  const byType = plugins.reduce((acc, p) => {
    acc[p.model_type] = (acc[p.model_type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const byFidelity = plugins.reduce((acc, p) => {
    p.fidelity_levels?.forEach((l) => { acc[l] = (acc[l] || 0) + 1; });
    return acc;
  }, {} as Record<string, number>);

  const loadedCount = plugins.filter((p) => p.loaded).length;

  return (
    <Card title="Model Registry Dashboard">
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}><Statistic title="Registered Plugins" value={plugins.length} /></Col>
        <Col span={6}><Statistic title="Loaded" value={loadedCount} valueStyle={{ color: '#3f8600' }} /></Col>
        <Col span={6}><Statistic title="Active Simulations" value={coupledSimulations.filter((s) => s.status === 'running').length} valueStyle={{ color: '#1890ff' }} /></Col>
        <Col span={6}><Statistic title="Model Types" value={Object.keys(byType).length} /></Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card title="By Model Type" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              {Object.entries(byType).map(([type, count]) => (
                <div key={type}><Tag color={type === 'dof6' ? 'blue' : type === 'battery' ? 'green' : 'orange'}>{type}</Tag> {count} plugins</div>
              ))}
            </Space>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Fidelity Distribution" size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              {Object.entries(byFidelity).map(([level, count]) => (
                <div key={level}><Tag color={level === 'detail' ? 'red' : level === 'mid' ? 'orange' : 'green'}>{level}</Tag> {count} plugins</div>
              ))}
            </Space>
          </Card>
        </Col>
      </Row>

      <Table
        dataSource={plugins}
        columns={[
          { title: 'Plugin', dataIndex: 'name', key: 'name' },
          { title: 'Type', dataIndex: 'model_type', key: 'model_type', render: (t: string) => <Tag color={t === 'dof6' ? 'blue' : t === 'battery' ? 'green' : 'orange'}>{t}</Tag> },
          { title: 'Fidelity', dataIndex: 'fidelity_levels', key: 'fidelity_levels', render: (l: string[]) => l?.map((f) => <Tag key={f} color={f === 'detail' ? 'red' : f === 'mid' ? 'orange' : 'green'}>{f}</Tag>) },
          { title: 'Version', dataIndex: 'version', key: 'version' },
          { title: 'Status', dataIndex: 'loaded', key: 'loaded', render: (l: boolean) => l ? <Badge status="success" text="Loaded" /> : <Badge status="default" text="Unloaded" /> },
        ]}
        rowKey="name"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />
    </Card>
  );
};

export default ModelRegistryDashboard;