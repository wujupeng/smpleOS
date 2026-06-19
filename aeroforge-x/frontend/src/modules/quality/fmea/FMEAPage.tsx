import React, { useState } from 'react';
import { Card, Form, Input, Select, Button, Table, Tag, Row, Col, Statistic } from 'antd';
import { ExperimentOutlined } from '@ant-design/icons';

const { Option } = Select;

const FMEAPage: React.FC = () => {
  const [form] = Form.useForm();
  const [analysis, setAnalysis] = useState<any>(null);
  const [modes, setModes] = useState<any[]>([]);

  const handleCreate = async (values: any) => {
    const res = await fetch('/api/v1/quality/fmea/analyses', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values),
    });
    setAnalysis(await res.json());
  };

  const handleAddMode = async (values: any) => {
    if (!analysis) return;
    const res = await fetch(`/api/v1/quality/fmea/analyses/${analysis.analysis_id}/failure-modes`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values),
    });
    const data = await res.json();
    setModes(prev => [...prev, data]);
  };

  const columns = [
    { title: 'Mode ID', dataIndex: 'mode_id', key: 'id', render: (v: string) => v?.slice(0,8) },
    { title: 'Description', dataIndex: 'description', key: 'desc' },
    { title: 'S', dataIndex: 's', key: 's' },
    { title: 'O', dataIndex: 'o', key: 'o' },
    { title: 'D', dataIndex: 'd', key: 'd' },
    { title: 'RPN', dataIndex: 'rpn', key: 'rpn', render: (v: number) => <Tag color={v>=200?'red':v>=100?'orange':'green'}>{v}</Tag> },
    { title: 'Safety Critical', dataIndex: 'is_safety_critical', key: 'sc', render: (v: boolean) => v ? <Tag color="red">YES</Tag> : 'No' },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card title="Create FMEA Analysis" style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="fmea_type" label="Type" initialValue="dfmea">
              <Select><Option value="dfmea">DFMEA</Option><Option value="pfmea">PFMEA</Option></Select>
            </Form.Item></Col>
            <Col span={8}><Form.Item name="component_name" label="Component"><Input /></Form.Item></Col>
          </Row>
          <Button type="primary" htmlType="submit">Create Analysis</Button>
        </Form>
      </Card>
      {analysis && <Card title="Add Failure Mode" style={{ marginBottom: 16 }}>
        <Form layout="inline" onFinish={handleAddMode}>
          <Form.Item name="failure_description" rules={[{required:true}]}><Input placeholder="Failure Description" style={{width:200}} /></Form.Item>
          <Form.Item name="severity" initialValue={5}><InputNumber min={1} max={10} /></Form.Item>
          <Form.Item name="occurrence" initialValue={5}><InputNumber min={1} max={10} /></Form.Item>
          <Form.Item name="detection" initialValue={5}><InputNumber min={1} max={10} /></Form.Item>
          <Button type="primary" htmlType="submit" icon={<ExperimentOutlined />}>Add</Button>
        </Form>
      </Card>}
      {modes.length > 0 && <Card title="Failure Modes & RPN Matrix">
        <Table columns={columns} dataSource={modes} rowKey="mode_id" size="small" />
      </Card>}
    </div>
  );
};

export default FMEAPage;