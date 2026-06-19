import React, { useState } from 'react';
import {
  Card,
  Table,
  Button,
  Input,
  Space,
  Modal,
  Form,
  Tag,
  Statistic,
  Row,
  Col,
  message,
  DatePicker,
  List,
} from 'antd';
import {
  RocketOutlined,
  PlusOutlined,
  ToolOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

const API_BASE = '/api/v1';

const FleetManagementPage: React.FC = () => {
  const [aircraft, setAircraft] = useState<any[]>([]);
  const [fleetStatus, setFleetStatus] = useState<any>(null);
  const [registerModalVisible, setRegisterModalVisible] = useState(false);
  const [maintenanceModalVisible, setMaintenanceModalVisible] = useState(false);
  const [selectedAircraft, setSelectedAircraft] = useState<string>('');
  const [registerForm] = Form.useForm();
  const [maintenanceForm] = Form.useForm();

  const fetchFleetStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/operations/fleet/status`);
      const data = await res.json();
      setFleetStatus(data);
    } catch (e) {
      console.error(e);
    }
  };

  const registerAircraft = async (values: any) => {
    try {
      const res = await fetch(`${API_BASE}/operations/fleet/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          aircraft_sn: values.aircraft_sn,
          model: values.model,
          fleet_id: values.fleet_id || undefined,
        }),
      });
      if (res.ok) {
        message.success('Aircraft registered successfully');
        setRegisterModalVisible(false);
        registerForm.resetFields();
        fetchFleetStatus();
      } else {
        const err = await res.json();
        message.error(err.detail || 'Registration failed');
      }
    } catch (e) {
      message.error('Registration failed');
    }
  };

  const scheduleMaintenance = async (values: any) => {
    try {
      const res = await fetch(`${API_BASE}/operations/maintenance/schedules`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          aircraft_sn: selectedAircraft,
          maintenance_type: values.maintenance_type,
          scheduled_date: values.scheduled_date.toISOString(),
          estimated_duration_hours: values.estimated_duration_hours || 8,
        }),
      });
      if (res.ok) {
        message.success('Maintenance scheduled successfully');
        setMaintenanceModalVisible(false);
        maintenanceForm.resetFields();
      } else {
        const err = await res.json();
        message.error(err.detail || 'Scheduling failed');
      }
    } catch (e) {
      message.error('Scheduling failed');
    }
  };

  const columns = [
    { title: 'Serial Number', dataIndex: 'aircraft_serial_number', key: 'sn' },
    { title: 'Model', dataIndex: 'model', key: 'model' },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => (
        <Tag color={s === 'active' ? 'green' : s === 'under_maintenance' ? 'orange' : s === 'grounded' ? 'red' : 'default'}>
          {s}
        </Tag>
      ),
    },
    {
      title: 'Flight Hours',
      dataIndex: 'total_flight_hours',
      key: 'fh',
      render: (v: number) => v?.toFixed(1) || '0.0',
    },
    {
      title: 'Fleet',
      dataIndex: 'fleet_id',
      key: 'fleet',
      render: (v: string) => v || '-',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: any) => (
        <Button
          size="small"
          icon={<ToolOutlined />}
          onClick={() => {
            setSelectedAircraft(record.aircraft_serial_number);
            setMaintenanceModalVisible(true);
          }}
        >
          Schedule Maintenance
        </Button>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2>
        <RocketOutlined /> Fleet Management
      </h2>

      {fleetStatus && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card>
              <Statistic title="Total Aircraft" value={fleetStatus.total_aircraft} prefix={<RocketOutlined />} />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic title="Total Flight Hours" value={fleetStatus.total_flight_hours} precision={1} prefix={<ClockCircleOutlined />} />
            </Card>
          </Col>
          <Col span={12}>
            <Card title="Status Distribution">
              <Space>
                {Object.entries(fleetStatus.status_distribution || {}).map(([status, count]) => (
                  <Tag key={status} color={status === 'active' ? 'green' : status === 'under_maintenance' ? 'orange' : 'red'}>
                    {status}: {count as number}
                  </Tag>
                ))}
              </Space>
            </Card>
          </Col>
        </Row>
      )}

      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setRegisterModalVisible(true)}>
          Register Aircraft
        </Button>
        <Button onClick={fetchFleetStatus}>Refresh Status</Button>
      </Space>

      <Card title="Aircraft Registry">
        <Table
          dataSource={aircraft}
          columns={columns}
          rowKey="aircraft_serial_number"
          pagination={false}
          locale={{ emptyText: 'No aircraft registered. Click "Register Aircraft" to add.' }}
        />
      </Card>

      <Modal
        title="Register Aircraft"
        open={registerModalVisible}
        onCancel={() => setRegisterModalVisible(false)}
        onOk={() => registerForm.submit()}
      >
        <Form form={registerForm} onFinish={registerAircraft} layout="vertical">
          <Form.Item name="aircraft_sn" label="Aircraft Serial Number" rules={[{ required: true }]}>
            <Input placeholder="e.g., SN-2024-001" />
          </Form.Item>
          <Form.Item name="model" label="Model" rules={[{ required: true }]}>
            <Input placeholder="e.g., A320neo" />
          </Form.Item>
          <Form.Item name="fleet_id" label="Fleet ID">
            <Input placeholder="Optional" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`Schedule Maintenance - ${selectedAircraft}`}
        open={maintenanceModalVisible}
        onCancel={() => setMaintenanceModalVisible(false)}
        onOk={() => maintenanceForm.submit()}
      >
        <Form form={maintenanceForm} onFinish={scheduleMaintenance} layout="vertical">
          <Form.Item name="maintenance_type" label="Maintenance Type" rules={[{ required: true }]}>
            <Input placeholder="e.g., A-Check, C-Check" />
          </Form.Item>
          <Form.Item name="scheduled_date" label="Scheduled Date" rules={[{ required: true }]}>
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="estimated_duration_hours" label="Duration (hours)">
            <Input type="number" placeholder="8" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default FleetManagementPage;