import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Statistic, Row, Col, Badge, Steps, Progress } from 'antd';
import { usePropagationStore } from '../../../stores/propagationStore';

const PropagationDashboard: React.FC = () => {
  const { chains, executions, handlers, fetchChains, fetchHandlers } = usePropagationStore();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchChains(), fetchHandlers()]).finally(() => setLoading(false));
  }, []);

  const totalExecutions = executions.length;
  const successCount = executions.filter((e) => e.status === 'completed').length;
  const failedCount = executions.filter((e) => e.status === 'failed').length;
  const successRate = totalExecutions > 0 ? Math.round((successCount / totalExecutions) * 100) : 0;
  const avgDuration = executions.filter((e) => e.status === 'completed' && e.handler_results?.length > 0)
    .reduce((sum, e) => sum + e.handler_results.reduce((s, h) => s + (h.duration_ms || 0), 0), 0) / (successCount || 1);

  const chainStats = chains.map((chain) => {
    const chainExecs = executions.filter((e) => e.chain_id === chain.id);
    const completed = chainExecs.filter((e) => e.status === 'completed').length;
    const failed = chainExecs.filter((e) => e.status === 'failed').length;
    return { ...chain, total: chainExecs.length, completed, failed, successRate: chainExecs.length > 0 ? Math.round((completed / chainExecs.length) * 100) : 0 };
  });

  return (
    <Card title="Propagation Dashboard" loading={loading}>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={4}><Statistic title="Chains" value={chains.length} /></Col>
        <Col span={4}><Statistic title="Handlers" value={handlers.length} /></Col>
        <Col span={4}><Statistic title="Total Executions" value={totalExecutions} /></Col>
        <Col span={4}>
          <Statistic title="Success Rate" value={successRate} suffix="%" valueStyle={{ color: successRate >= 80 ? '#3f8600' : '#cf1322' }} />
        </Col>
        <Col span={4}><Statistic title="Failed" value={failedCount} valueStyle={{ color: failedCount > 0 ? '#cf1322' : '#3f8600' }} /></Col>
        <Col span={4}><Statistic title="Avg Duration" value={avgDuration.toFixed(0)} suffix="ms" /></Col>
      </Row>

      <Card title="Chain Definitions & Execution History" size="small" style={{ marginBottom: 16 }}>
        <Table
          dataSource={chainStats}
          columns={[
            { title: 'Chain', dataIndex: 'name', key: 'name' },
            { title: 'Trigger', dataIndex: 'trigger_event', key: 'trigger_event', render: (e: string) => <Tag>{e}</Tag> },
            { title: 'Handlers', dataIndex: 'handlers', key: 'handlers', render: (h: any[]) => h?.length || 0 },
            { title: 'Total Runs', dataIndex: 'total', key: 'total' },
            { title: 'Success', dataIndex: 'completed', key: 'completed', render: (v: number) => <Badge count={v} style={{ backgroundColor: '#52c41a' }} /> },
            { title: 'Failed', dataIndex: 'failed', key: 'failed', render: (v: number) => v > 0 ? <Badge count={v} style={{ backgroundColor: '#ff4d4f' }} /> : 0 },
            { title: 'Success Rate', dataIndex: 'successRate', key: 'successRate', render: (r: number) => <Progress percent={r} size="small" status={r >= 80 ? 'success' : 'exception'} /> },
          ]}
          rowKey="id"
          pagination={false}
        />
      </Card>

      <Card title="Registered Handlers" size="small">
        <Table
          dataSource={handlers}
          columns={[
            { title: 'Handler', dataIndex: 'name', key: 'name' },
            { title: 'Version', dataIndex: 'version', key: 'version' },
            { title: 'Status', dataIndex: 'loaded', key: 'loaded', render: (l: boolean) => l ? <Badge status="success" text="Loaded" /> : <Badge status="default" text="Unloaded" /> },
          ]}
          rowKey="name"
          pagination={false}
          size="small"
        />
      </Card>
    </Card>
  );
};

export default PropagationDashboard;