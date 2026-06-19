import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Select, Descriptions, Typography } from 'antd';
import { usePropagationStore } from '../../../stores/propagationStore';

const { Text } = Typography;

const ChainAuditLog: React.FC = () => {
  const { chains, auditLogs, fetchChains, fetchAuditLogs } = usePropagationStore();
  const [selectedChainId, setSelectedChainId] = useState<string | null>(null);

  useEffect(() => {
    fetchChains();
  }, []);

  useEffect(() => {
    if (selectedChainId) fetchAuditLogs(selectedChainId);
  }, [selectedChainId]);

  const columns = [
    { title: 'Time', dataIndex: 'timestamp', key: 'timestamp', width: 180, render: (d: string) => d ? new Date(d).toLocaleString() : '-' },
    { title: 'Handler', dataIndex: 'handler_name', key: 'handler_name', render: (h: string) => <Tag color="blue">{h}</Tag> },
    { title: 'Action', dataIndex: 'action', key: 'action', render: (a: string) => <Tag>{a}</Tag> },
    { title: 'Actor', dataIndex: 'actor', key: 'actor' },
    {
      title: 'Input', dataIndex: 'input_snapshot', key: 'input_snapshot', width: 200,
      render: (s: any) => s ? <Text ellipsis style={{ maxWidth: 180 }}>{JSON.stringify(s)}</Text> : '-',
    },
    {
      title: 'Output', dataIndex: 'output_snapshot', key: 'output_snapshot', width: 200,
      render: (s: any) => s ? <Text ellipsis style={{ maxWidth: 180 }}>{JSON.stringify(s)}</Text> : '-',
    },
    {
      title: 'Decision', dataIndex: 'decision', key: 'decision',
      render: (d: string) => d ? <Tag color={d === 'approved' ? 'green' : d === 'rejected' ? 'red' : 'orange'}>{d}</Tag> : '-',
    },
  ];

  return (
    <Card title="Chain Audit Log">
      <Space style={{ marginBottom: 16 }}>
        <span>Select Chain: </span>
        <Select style={{ width: 240 }} value={selectedChainId || undefined} onChange={setSelectedChainId} placeholder="Select a chain">
          {chains.map((c) => <Select.Option key={c.id} value={c.id}>{c.name}</Select.Option>)}
        </Select>
        {selectedChainId && <Button onClick={() => fetchAuditLogs(selectedChainId)}>Refresh</Button>}
      </Space>

      <Table
        dataSource={auditLogs}
        columns={columns}
        rowKey="id"
        pagination={{ pageSize: 20 }}
        expandable={{
          expandedRowRender: (record) => (
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="Input Snapshot">
                <pre style={{ maxHeight: 200, overflow: 'auto', margin: 0 }}>{JSON.stringify(record.input_snapshot, null, 2)}</pre>
              </Descriptions.Item>
              <Descriptions.Item label="Output Snapshot">
                <pre style={{ maxHeight: 200, overflow: 'auto', margin: 0 }}>{JSON.stringify(record.output_snapshot, null, 2)}</pre>
              </Descriptions.Item>
            </Descriptions>
          ),
        }}
      />
    </Card>
  );
};

export default ChainAuditLog;