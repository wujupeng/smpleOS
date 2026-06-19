import React, { useState } from 'react';
import { Card, Form, Input, InputNumber, Button, Table, Tag, Alert, Row, Col, Statistic, Descriptions } from 'antd';
import { FileTextOutlined, CheckCircleOutlined } from '@ant-design/icons';

const TravelerPage: React.FC = () => {
  const [form] = Form.useForm();
  const [travelers, setTravelers] = useState<any[]>([]);
  const [current, setCurrent] = useState<any>(null);

  const handleCreate = async (values: any) => {
    const res = await fetch('/api/v1/mes/travelers', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values),
    });
    const data = await res.json();
    setCurrent(data);
    setTravelers(prev => [data, ...prev]);
  };

  return (
    <div style={{ padding: 24 }}>
      <Card title="Create Traveler" style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Row gutter={16}>
            <Col span={8}><Form.Item name="work_order_id" label="Work Order ID" rules={[{required:true}]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="serial_number" label="Serial Number" rules={[{required:true}]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item name="process_step" label="Process Step" rules={[{required:true}]}><Input /></Form.Item></Col>
          </Row>
          <Button type="primary" htmlType="submit" icon={<FileTextOutlined />}>Create Traveler</Button>
        </Form>
      </Card>
      {current && <Card title={`Traveler: ${current.traveler_id?.slice(0,8)}...`}>
        <Descriptions bordered column={2}>
          <Descriptions.Item label="Status"><Tag color={current.status==='finalized'?'green':current.status==='non_conforming'?'red':'blue'}>{current.status}</Descriptions.Item></Descriptions.Item>
          <Descriptions.Item label="Serial Number">{current.serial_number}</Descriptions.Item>
        </Descriptions>
      </Card>}
    </div>
  );
};

export default TravelerPage;