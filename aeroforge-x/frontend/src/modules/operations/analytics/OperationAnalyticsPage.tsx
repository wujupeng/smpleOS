import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Button,
  Input,
  Space,
  Divider,
  Progress,
  Typography,
} from 'antd';
import {
  DashboardOutlined,
  RiseOutlined,
  DollarOutlined,
  SafetyOutlined,
} from '@ant-design/icons';

const API_BASE = '/api/v1';

const { Title } = Typography;

const OperationAnalyticsPage: React.FC = () => {
  const [fleetId, setFleetId] = useState('');
  const [periodDays, setPeriodDays] = useState(30);
  const [utilization, setUtilization] = useState<any>(null);
  const [dispatchReliability, setDispatchReliability] = useState<any>(null);
  const [maintenanceCost, setMaintenanceCost] = useState<any>(null);

  const fetchUtilization = async () => {
    try {
      const params = new URLSearchParams();
      if (fleetId) params.set('fleet_id', fleetId);
      params.set('period_days', periodDays.toString());
      const res = await fetch(`${API_BASE}/operations/analytics/utilization?${params}`);
      const data = await res.json();
      setUtilization(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchDispatchReliability = async () => {
    try {
      const params = new URLSearchParams();
      if (fleetId) params.set('fleet_id', fleetId);
      params.set('period_days', periodDays.toString());
      const res = await fetch(`${API_BASE}/operations/analytics/dispatch-reliability?${params}`);
      const data = await res.json();
      setDispatchReliability(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchMaintenanceCost = async () => {
    try {
      const params = new URLSearchParams();
      if (fleetId) params.set('fleet_id', fleetId);
      params.set('period_days', periodDays.toString());
      const res = await fetch(`${API_BASE}/operations/analytics/maintenance-cost?${params}`);
      const data = await res.json();
      setMaintenanceCost(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchAll = async () => {
    await Promise.all([fetchUtilization(), fetchDispatchReliability(), fetchMaintenanceCost()]);
  };

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>
        <DashboardOutlined /> Operation Analytics
      </Title>

      <Space style={{ marginBottom: 16 }}>
        <Input
          placeholder="Fleet ID (optional)"
          value={fleetId}
          onChange={(e) => setFleetId(e.target.value)}
          style={{ width: 200 }}
        />
        <Input
          type="number"
          placeholder="Period (days)"
          value={periodDays}
          onChange={(e) => setPeriodDays(Number(e.target.value))}
          style={{ width: 120 }}
        />
        <Button type="primary" onClick={fetchAll}>
          Generate Report
        </Button>
      </Space>

      <Row gutter={16}>
        <Col span={8}>
          <Card title="Fleet Utilization" extra={<RiseOutlined />}>
            {utilization ? (
              <>
                <Statistic
                  title="Utilization Rate"
                  value={utilization.utilization_rate}
                  precision={2}
                  suffix="%"
                  valueStyle={{
                    color: utilization.utilization_rate >= 70 ? '#3f8600' : utilization.utilization_rate >= 40 ? '#faad14' : '#cf1322',
                  }}
                />
                <Progress
                  percent={utilization.utilization_rate}
                  status={utilization.utilization_rate >= 70 ? 'success' : utilization.utilization_rate >= 40 ? 'normal' : 'exception'}
                />
                <Divider />
                <Statistic title="Total Flight Hours" value={utilization.total_flight_hours} precision={1} />
                <Statistic title="Available Hours" value={utilization.total_available_hours} />
                <Statistic title="Aircraft Count" value={utilization.aircraft_count} />
              </>
            ) : (
              <div style={{ color: '#999', textAlign: 'center', padding: 40 }}>Click "Generate Report" to view</div>
            )}
          </Card>
        </Col>

        <Col span={8}>
          <Card title="Dispatch Reliability" extra={<SafetyOutlined />}>
            {dispatchReliability ? (
              <>
                <Statistic
                  title="Dispatch Reliability"
                  value={dispatchReliability.dispatch_reliability}
                  precision={2}
                  suffix="%"
                  valueStyle={{
                    color: dispatchReliability.dispatch_reliability >= 95 ? '#3f8600' : dispatchReliability.dispatch_reliability >= 80 ? '#faad14' : '#cf1322',
                  }}
                />
                <Progress
                  percent={dispatchReliability.dispatch_reliability}
                  status={dispatchReliability.dispatch_reliability >= 95 ? 'success' : dispatchReliability.dispatch_reliability >= 80 ? 'normal' : 'exception'}
                />
                <Divider />
                <Statistic title="Active Aircraft" value={dispatchReliability.active_aircraft} valueStyle={{ color: '#3f8600' }} />
                <Statistic title="Total Aircraft" value={dispatchReliability.total_aircraft} />
                <Statistic title="Period (days)" value={dispatchReliability.period_days} />
              </>
            ) : (
              <div style={{ color: '#999', textAlign: 'center', padding: 40 }}>Click "Generate Report" to view</div>
            )}
          </Card>
        </Col>

        <Col span={8}>
          <Card title="Maintenance Cost" extra={<DollarOutlined />}>
            {maintenanceCost ? (
              <>
                <Statistic
                  title="Total Cost"
                  value={maintenanceCost.total_cost}
                  precision={2}
                  prefix="$"
                />
                <Divider />
                <Statistic title="Scheduled Cost" value={maintenanceCost.scheduled_cost} precision={2} prefix="$" valueStyle={{ color: '#3f8600' }} />
                <Statistic title="Unscheduled Cost" value={maintenanceCost.unscheduled_cost} precision={2} prefix="$" valueStyle={{ color: '#cf1322' }} />
                <Divider />
                <Statistic title="Aircraft Under Maintenance" value={maintenanceCost.aircraft_under_maintenance} />
                <Statistic title="Period (days)" value={maintenanceCost.period_days} />
              </>
            ) : (
              <div style={{ color: '#999', textAlign: 'center', padding: 40 }}>Click "Generate Report" to view</div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default OperationAnalyticsPage;