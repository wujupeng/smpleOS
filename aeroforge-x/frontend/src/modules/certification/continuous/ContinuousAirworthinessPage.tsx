import React, { useState } from 'react';
import { Card, Button, Input, Space, Typography, Descriptions, Tag, Table, Statistic, Row, Col } from 'antd';
import { SyncOutlined } from '@ant-design/icons';

const { Title } = Typography;
const API_BASE = '/api/v1';

const ContinuousAirworthinessPage: React.FC = () => {
  const [aircraftSn, setAircraftSn] = useState('');
  const [loading, setLoading] = useState(false);
  const [adData, setAdData] = useState<any>(null);

  const fetchADCompliance = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/certification/continuous-airworthiness/ad?aircraft_sn=${aircraftSn}`);
      const data = await res.json();
      setAdData(data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}><SyncOutlined /> Continuous Airworthiness</Title>
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Input placeholder="Aircraft Serial Number" value={aircraftSn} onChange={(e) => setAircraftSn(e.target.value)} style={{ width: 250 }} />
          <Button type="primary" onClick={fetchADCompliance} loading={loading}>Check AD Compliance</Button>
        </Space>
      </Card>
      {adData && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={8}>
              <Card><Statistic title="Applicable ADs" value={adData.total_applicable_ads} /></Card>
            </Col>
            <Col span={8}>
              <Card><Statistic title="Compliant" value={adData.compliant_ads} valueStyle={{ color: '#3f8600' }} /></Card>
            </Col>
            <Col span={8}>
              <Card><Statistic title="Pending" value={adData.pending_ads} valueStyle={{ color: adData.pending_ads > 0 ? '#cf1322' : '#3f8600' }} /></Card>
            </Col>
          </Row>
          {adData.pending_ad_details?.length > 0 && (
            <Card title="Pending Airworthiness Directives">
              <Table
                dataSource={adData.pending_ad_details}
                columns={[
                  { title: 'AD Number', dataIndex: 'ad_number', key: 'num' },
                  { title: 'Title', dataIndex: 'title', key: 'title' },
                  { title: 'Effective Date', dataIndex: 'effective_date', key: 'eff' },
                  { title: 'Required By', dataIndex: 'compliance_required_by', key: 'req' },
                  { title: 'Status', dataIndex: 'status', key: 'status', render: (s: string) => <Tag color="red">{s}</Tag> },
                ]}
                rowKey="ad_number"
                size="small"
                pagination={false}
              />
            </Card>
          )}
        </>
      )}
    </div>
  );
};

export default ContinuousAirworthinessPage;