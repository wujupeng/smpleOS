import React, { useState } from 'react';
import { Card, Button, Input, Space, Typography, Table, Tag, Descriptions, Progress, Modal, Form, Select, Steps } from 'antd';
import { SafetyCertificateOutlined } from '@ant-design/icons';

const { Title } = Typography;
const API_BASE = '/api/v1';

const CertificationPlansPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [plan, setPlan] = useState<any>(null);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [form] = Form.useForm();

  const createPlan = async (values: any) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/certification/plans`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const data = await res.json();
      setPlan(data);
      setCreateModalVisible(false);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const fetchProgress = async () => {
    if (!plan) return;
    try {
      const res = await fetch(`${API_BASE}/certification/plans/${plan.plan_id}/progress`);
      const data = await res.json();
      setPlan({ ...plan, progress: data });
    } catch (e) { console.error(e); }
  };

  const columns = [
    { title: 'Clause', dataIndex: 'regulation_clause', key: 'clause', width: 100 },
    { title: 'Title', dataIndex: 'clause_title', key: 'title' },
    { title: 'Method', dataIndex: 'compliance_method', key: 'method', render: (m: string) => <Tag>{m || '-'}</Tag> },
    { title: 'Status', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color={s === 'compliant' ? 'green' : s === 'open' ? 'orange' : 'default'}>{s}</Tag> },
    { title: 'Gap', dataIndex: 'evidence_gap', key: 'gap', render: (g: boolean) => <Tag color={g ? 'red' : 'green'}>{g ? 'Gap' : 'Covered'}</Tag> },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}><SafetyCertificateOutlined /> Certification Plans</Title>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" onClick={() => setCreateModalVisible(true)}>Create Certification Plan</Button>
        {plan && <Button onClick={fetchProgress}>Refresh Progress</Button>}
      </Space>
      {plan && (
        <>
          <Card style={{ marginBottom: 16 }}>
            <Descriptions bordered column={3} size="small">
              <Descriptions.Item label="Plan ID">{plan.plan_id}</Descriptions.Item>
              <Descriptions.Item label="Aircraft Type">{plan.aircraft_type}</Descriptions.Item>
              <Descriptions.Item label="Standard">{plan.certification_standard}</Descriptions.Item>
              <Descriptions.Item label="Status"><Tag color="blue">{plan.status}</Tag></Descriptions.Item>
              <Descriptions.Item label="Items">{plan.compliance_items?.length}</Descriptions.Item>
              <Descriptions.Item label="Progress">
                <Progress percent={Math.round(plan.progress?.progress?.progress_percentage || 0)} size="small" />
              </Descriptions.Item>
            </Descriptions>
          </Card>
          <Card title="Compliance Items">
            <Table dataSource={plan.compliance_items || []} columns={columns} rowKey="item_id" size="small" pagination={{ pageSize: 15 }} />
          </Card>
        </>
      )}
      <Modal title="Create Certification Plan" open={createModalVisible} onCancel={() => setCreateModalVisible(false)} onOk={() => form.submit()}>
        <Form form={form} onFinish={createPlan} layout="vertical">
          <Form.Item name="project_id" label="Project ID" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="aircraft_type" label="Aircraft Type" rules={[{ required: true }]}><Input placeholder="e.g., narrow_body" /></Form.Item>
          <Form.Item name="standard" label="Standard" initialValue="FAR-25">
            <Select options={[{ value: 'FAR-25', label: 'FAR-25' }, { value: 'CS-25', label: 'CS-25' }]} />
          </Form.Item>
          <Form.Item name="authority" label="Authority" initialValue="FAA">
            <Select options={[{ value: 'FAA', label: 'FAA' }, { value: 'EASA', label: 'EASA' }, { value: 'CAAC', label: 'CAAC' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default CertificationPlansPage;