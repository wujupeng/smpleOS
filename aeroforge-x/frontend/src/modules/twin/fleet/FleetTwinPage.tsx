import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Button,
  Input,
  Space,
  Alert,
  Tabs,
  Progress,
  Spin,
} from 'antd';
import {
  RocketOutlined,
  WarningOutlined,
  ToolOutlined,
  BarChartOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';

const API_BASE = '/api/v1';

const FleetTwinPage: React.FC = () => {
  const [fleetId, setFleetId] = useState('fleet-001');
  const [loading, setLoading] = useState(false);
  const [fleetData, setFleetData] = useState<any>(null);
  const [anomalies, setAnomalies] = useState<any[]>([]);
  const [reliability, setReliability] = useState<any>(null);

  const aggregateFleet = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/twins/fleet/aggregate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fleet_id: fleetId }),
      });
      const data = await res.json();
      setFleetData(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const fetchAnomalies = async () => {
    try {
      const res = await fetch(`${API_BASE}/twins/fleet/${fleetId}/anomalies`);
      const data = await res.json();
      setAnomalies(data.anomalies || []);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchReliability = async () => {
    try {
      const res = await fetch(`${API_BASE}/twins/fleet/${fleetId}/reliability`);
      const data = await res.json();
      setReliability(data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    if (fleetData) {
      fetchAnomalies();
      fetchReliability();
    }
  }, [fleetData]);

  const faultColumns = [
    { title: 'System', dataIndex: 'key', key: 'key' },
    { title: 'Fault Count', dataIndex: 'value', key: 'value' },
  ];

  const anomalyColumns = [
    { title: 'Type', dataIndex: 'type', key: 'type' },
    { title: 'Description', dataIndex: 'description', key: 'description' },
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      render: (s: string) => (
        <Tag color={s === 'high' ? 'red' : s === 'medium' ? 'orange' : 'green'}>{s}</Tag>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2>
        <RocketOutlined /> Fleet Twin Dashboard
      </h2>

      <Space style={{ marginBottom: 16 }}>
        <Input
          placeholder="Fleet ID"
          value={fleetId}
          onChange={(e) => setFleetId(e.target.value)}
          style={{ width: 200 }}
        />
        <Button type="primary" onClick={aggregateFleet} loading={loading}>
          Aggregate Fleet Data
        </Button>
      </Space>

      {anomalies.length > 0 && (
        <Alert
          message="Fleet Anomalies Detected"
          description={`${anomalies.length} anomaly(ies) detected in fleet ${fleetId}`}
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          style={{ marginBottom: 16 }}
        />
      )}

      {fleetData && (
        <Tabs
          items={[
            {
              key: 'overview',
              label: 'Fleet Overview',
              children: (
                <Row gutter={16}>
                  <Col span={6}>
                    <Card>
                      <Statistic title="Aircraft Count" value={fleetData.aircraft_count} prefix={<RocketOutlined />} />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="Total Faults"
                        value={fleetData.fault_statistics?.total_faults || 0}
                        prefix={<WarningOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="Components Due"
                        value={fleetData.life_statistics?.components_due_replacement || 0}
                        prefix={<ToolOutlined />}
                      />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic
                        title="MTBF (hrs)"
                        value={fleetData.fault_statistics?.mtbf_hours || 0}
                        precision={1}
                        prefix={<BarChartOutlined />}
                      />
                    </Card>
                  </Col>
                </Row>
              ),
            },
            {
              key: 'faults',
              label: 'Fault Statistics',
              children: (
                <Card title="Faults by System">
                  <Table
                    dataSource={Object.entries(fleetData.fault_statistics?.faults_by_system || {}).map(
                      ([k, v]) => ({ key: k, value: v as number })
                    )}
                    columns={faultColumns}
                    pagination={false}
                    size="small"
                  />
                </Card>
              ),
            },
            {
              key: 'life',
              label: 'Life Statistics',
              children: (
                <Card title="Component Remaining Life Distribution">
                  <Row gutter={16}>
                    {Object.entries(fleetData.life_statistics?.components_by_remaining_life || {}).map(
                      ([range, count]) => (
                        <Col span={4} key={range}>
                          <Statistic title={range} value={count as number} />
                        </Col>
                      )
                    )}
                  </Row>
                  <div style={{ marginTop: 16 }}>
                    <Progress
                      percent={Math.round(fleetData.life_statistics?.average_remaining_life_percentage || 0)}
                      status={
                        (fleetData.life_statistics?.average_remaining_life_percentage || 0) < 30
                          ? 'exception'
                          : 'active'
                      }
                    />
                  </div>
                </Card>
              ),
            },
            {
              key: 'maintenance',
              label: 'Maintenance Statistics',
              children: (
                <Row gutter={16}>
                  <Col span={8}>
                    <Card>
                      <Statistic
                        title="Total Events"
                        value={fleetData.maintenance_statistics?.total_maintenance_events || 0}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card>
                      <Statistic
                        title="Scheduled"
                        value={fleetData.maintenance_statistics?.scheduled_events || 0}
                        valueStyle={{ color: '#3f8600' }}
                      />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card>
                      <Statistic
                        title="Unscheduled"
                        value={fleetData.maintenance_statistics?.unscheduled_events || 0}
                        valueStyle={{
                          color:
                            (fleetData.maintenance_statistics?.unscheduled_events || 0) >
                            (fleetData.maintenance_statistics?.scheduled_events || 0)
                              ? '#cf1322'
                              : '#3f8600',
                        }}
                      />
                    </Card>
                  </Col>
                </Row>
              ),
            },
            {
              key: 'anomalies',
              label: 'Anomalies',
              children: (
                <Card title="Fleet Anomaly Detection">
                  <Table
                    dataSource={anomalies}
                    columns={anomalyColumns}
                    rowKey="type"
                    pagination={false}
                    locale={{ emptyText: 'No anomalies detected' }}
                  />
                </Card>
              ),
            },
            {
              key: 'reliability',
              label: 'Reliability',
              children: reliability ? (
                <Card title="Fleet Reliability Analysis">
                  <Row gutter={16}>
                    <Col span={6}>
                      <Statistic title="MTBF (hrs)" value={reliability.mtbf_hours} precision={1} />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="Scheduled Ratio"
                        value={reliability.scheduled_maintenance_ratio * 100}
                        precision={1}
                        suffix="%"
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="Avg Remaining Life"
                        value={reliability.average_remaining_life_percentage}
                        precision={1}
                        suffix="%"
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title="Reliability Score"
                        value={reliability.reliability_score}
                        precision={1}
                        prefix={<ThunderboltOutlined />}
                        valueStyle={{
                          color:
                            reliability.reliability_score >= 80
                              ? '#3f8600'
                              : reliability.reliability_score >= 60
                              ? '#faad14'
                              : '#cf1322',
                        }}
                      />
                      <Tag
                        color={
                          reliability.assessment === 'excellent'
                            ? 'green'
                            : reliability.assessment === 'good'
                            ? 'blue'
                            : reliability.assessment === 'needs_attention'
                            ? 'orange'
                            : 'red'
                        }
                      >
                        {reliability.assessment}
                      </Tag>
                    </Col>
                  </Row>
                </Card>
              ) : (
                <Spin />
              ),
            },
          ]}
        />
      )}
    </div>
  );
};

export default FleetTwinPage;