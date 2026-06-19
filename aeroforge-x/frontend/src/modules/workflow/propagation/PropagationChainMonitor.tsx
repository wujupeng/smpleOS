import React, { useEffect, useRef, useState } from 'react';
import { Card, Table, Tag, Button, Space, Steps, Badge, Descriptions, Row, Col, Statistic, Progress } from 'antd';
import { usePropagationStore } from '../../../stores/propagationStore';

const PropagationChainMonitor: React.FC = () => {
  const { chains, executions, fetchChains, getChainStatus, executeChain } = usePropagationStore();
  const [selectedChainId, setSelectedChainId] = useState<string | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    fetchChains();
  }, []);

  useEffect(() => {
    if (selectedChainId) {
      getChainStatus(selectedChainId);
      intervalRef.current = setInterval(() => getChainStatus(selectedChainId), 5000);
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [selectedChainId]);

  const selectedExec = executions.find((e) => e.chain_id === selectedChainId);

  const chainColumns = [
    { title: 'Chain', dataIndex: 'name', key: 'name', render: (n: string, r: any) => <a onClick={() => setSelectedChainId(r.id)}>{n}</a> },
    { title: 'Trigger', dataIndex: 'trigger_event', key: 'trigger_event', render: (e: string) => <Tag>{e}</Tag> },
    { title: 'Handlers', dataIndex: 'handlers', key: 'handlers', render: (h: any[]) => h?.length || 0 },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (s: string) => <Badge status={s === 'active' ? 'success' : 'default'} text={s} /> },
    {
      title: 'Actions', key: 'actions',
      render: (_: any, record: any) => <Button size="small" type="primary" onClick={() => executeChain(record.id)}>Execute</Button>,
    },
  ];

  return (
    <div>
      <Card title="Propagation Chain Monitor">
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={8}><Statistic title="Total Chains" value={chains.length} /></Col>
          <Col span={8}><Statistic title="Active" value={chains.filter((c) => c.status === 'active').length} valueStyle={{ color: '#3f8600' }} /></Col>
          <Col span={8}><Statistic title="Executions" value={executions.length} /></Col>
        </Row>

        <Table dataSource={chains} columns={chainColumns} rowKey="id" pagination={{ pageSize: 10 }} />
      </Card>

      {selectedExec && (
        <Card title={`Execution: ${selectedExec.execution_id}`} style={{ marginTop: 16 }}>
          <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
            <Descriptions.Item label="Chain ID">{selectedExec.chain_id}</Descriptions.Item>
            <Descriptions.Item label="Status"><Badge status={selectedExec.status === 'running' ? 'processing' : selectedExec.status === 'completed' ? 'success' : 'error'} text={selectedExec.status} /></Descriptions.Item>
            <Descriptions.Item label="Progress">
              <Progress percent={selectedExec.total_steps ? Math.round((selectedExec.current_step / selectedExec.total_steps) * 100) : 0} />
            </Descriptions.Item>
            <Descriptions.Item label="Started">{selectedExec.started_at ? new Date(selectedExec.started_at).toLocaleString() : '-'}</Descriptions.Item>
          </Descriptions>

          <Steps
            current={selectedExec.current_step - 1}
            items={selectedExec.handler_results?.map((hr) => ({
              title: hr.handler,
              status: hr.status === 'completed' ? 'finish' : hr.status === 'running' ? 'process' : hr.status === 'failed' ? 'error' : 'wait',
              description: <Space><Tag color={hr.status === 'completed' ? 'green' : hr.status === 'failed' ? 'red' : 'blue'}>{hr.status}</Tag>{hr.duration_ms ? `${hr.duration_ms}ms` : ''}</Space>,
            })) || []}
          />
        </Card>
      )}
    </div>
  );
};

export default PropagationChainMonitor;