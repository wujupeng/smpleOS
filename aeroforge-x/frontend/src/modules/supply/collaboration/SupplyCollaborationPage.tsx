import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Tag,
  Tabs,
  Table,
  Button,
  Form,
  Input,
  Space,
  Descriptions,
  Alert,
  message,
} from 'antd';
import {
  ApartmentOutlined,
  WarningOutlined,
  ShoppingCartOutlined,
  CheckCircleOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { TabPane } = Tabs;

const TIER_COLORS: Record<string, string> = {
  Tier1: 'blue',
  Tier2: 'green',
  Tier3: 'orange',
};

const RISK_COLORS: Record<string, string> = {
  low: 'green',
  medium: 'orange',
  high: 'red',
  critical: 'red',
};

const STATUS_COLORS: Record<string, string> = {
  active: 'green',
  suspended: 'orange',
  at_risk: 'red',
};

const SupplyCollaborationPage: React.FC = () => {
  const { t } = useTranslation();
  const [network, setNetwork] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [purchaseOrder, setPurchaseOrder] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const handleBuildNetwork = async (values: any) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/supply/networks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const result = await response.json();
      setNetwork(result.data);
      message.success('供应商网络构建完成');
    } catch {
      message.error('构建失败');
    } finally {
      setLoading(false);
    }
  };

  const handleShareForecast = async () => {
    if (!network) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/supply/networks/${network.id}/share-forecast`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ network_id: network.id }),
      });
      const result = await response.json();
      message.success('需求预测已共享');
    } catch {
      message.error('共享失败');
    } finally {
      setLoading(false);
    }
  };

  const handleMonitorRisks = async () => {
    if (!network) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/supply/risks/alerts?network_id=${network.id}`);
      const result = await response.json();
      setAlerts(result.data || []);
      message.success(`发现 ${result.data?.length || 0} 个风险预警`);
    } catch {
      message.error('监控失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSmartPurchase = async () => {
    if (!network) return;
    setLoading(true);
    try {
      const response = await fetch('/api/v1/supply/smart-purchase/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: network.tenant_id, project_id: network.project_id }),
      });
      const result = await response.json();
      setPurchaseOrder(result.data);
      message.success('智能采购订单已生成');
    } catch {
      message.error('生成失败');
    } finally {
      setLoading(false);
    }
  };

  const nodeColumns = [
    { title: '供应商ID', dataIndex: 'supplier_id', key: 'sid', width: 100 },
    { title: '供应商名称', dataIndex: 'supplier_name', key: 'sname' },
    {
      title: '层级',
      dataIndex: 'tier',
      key: 'tier',
      width: 80,
      render: (v: string) => <Tag color={TIER_COLORS[v]}>{v}</Tag>,
    },
    {
      title: '质量评级',
      dataIndex: 'quality_rating',
      key: 'qr',
      width: 100,
      render: (v: number) => `${(v * 100).toFixed(0)}%`,
    },
    {
      title: '交货周期(天)',
      dataIndex: 'lead_time_days',
      key: 'lt',
      width: 110,
      render: (v: number) => v.toFixed(0),
    },
    {
      title: '协同状态',
      dataIndex: 'collaboration_status',
      key: 'cs',
      width: 100,
      render: (v: string) => <Tag color={STATUS_COLORS[v]}>{v}</Tag>,
    },
  ];

  const alertColumns = [
    { title: '供应商', dataIndex: 'supplier_id', key: 'sid', width: 100 },
    {
      title: '风险类型',
      dataIndex: 'risk_type',
      key: 'rt',
      width: 130,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    {
      title: '风险等级',
      dataIndex: 'risk_level',
      key: 'rl',
      width: 100,
      render: (v: string) => <Tag color={RISK_COLORS[v]}>{v}</Tag>,
    },
    { title: '风险描述', dataIndex: 'risk_description', key: 'rd' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 's',
      width: 80,
      render: (v: string) => <Tag color={v === 'active' ? 'red' : 'green'}>{v}</Tag>,
    },
  ];

  const orderColumns = [
    { title: '物料', dataIndex: 'item_name', key: 'item' },
    { title: '数量', dataIndex: 'quantity', key: 'qty', width: 80 },
    { title: '单价', dataIndex: 'unit_price', key: 'price', width: 80 },
    { title: '折扣', dataIndex: 'discount', key: 'disc', width: 70 },
    { title: '小计', dataIndex: 'line_total', key: 'total', width: 100 },
    {
      title: '推荐供应商',
      key: 'supplier',
      render: (_: any, record: any) => record.recommended_supplier?.supplier_id || '-',
    },
    {
      title: '交货天数',
      key: 'lt',
      width: 90,
      render: (_: any, record: any) => record.recommended_supplier?.lead_time_days || '-',
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2><TeamOutlined /> 供应链协同网络</h2>

      <Card title="构建供应商网络" style={{ marginBottom: 16 }}>
        <Form form={form} layout="inline" onFinish={handleBuildNetwork}>
          <Form.Item name="project_id" label="项目ID">
            <Input placeholder="proj-001" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} icon={<ApartmentOutlined />}>
              构建网络
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {network && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card>
                <Statistic title="供应商总数" value={network.nodes_count} />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic title="供应关系" value={network.edges_count} />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="网络风险评分"
                  value={network.risk_score * 100}
                  precision={1}
                  suffix="%"
                  valueStyle={{ color: network.risk_score > 0.5 ? '#cf1322' : '#3f8600' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Space direction="vertical">
                  <Button icon={<TeamOutlined />} onClick={handleShareForecast} loading={loading} size="small">
                    共享需求预测
                  </Button>
                  <Button icon={<WarningOutlined />} onClick={handleMonitorRisks} loading={loading} size="small">
                    风险监控
                  </Button>
                  <Button icon={<ShoppingCartOutlined />} onClick={handleSmartPurchase} loading={loading} size="small">
                    智能采购
                  </Button>
                </Space>
              </Card>
            </Col>
          </Row>

          <Tabs defaultActiveKey="network">
            <TabPane tab="供应商网络" key="network">
              <Table
                dataSource={network.nodes || []}
                columns={nodeColumns}
                rowKey="node_id"
                pagination={false}
              />
            </TabPane>
            <TabPane tab="风险预警" key="risks">
              {alerts.length > 0 ? (
                <Table
                  dataSource={alerts}
                  columns={alertColumns}
                  rowKey="id"
                  pagination={false}
                />
              ) : (
                <Alert message="请先执行风险监控" type="info" />
              )}
            </TabPane>
            <TabPane tab="智能采购" key="purchase">
              {purchaseOrder ? (
                <>
                  <Descriptions bordered column={3} style={{ marginBottom: 16 }}>
                    <Descriptions.Item label="订单号">{purchaseOrder.order_id}</Descriptions.Item>
                    <Descriptions.Item label="总成本">¥{purchaseOrder.total_cost?.toLocaleString()}</Descriptions.Item>
                    <Descriptions.Item label="预计交货">{purchaseOrder.estimated_delivery_days}天</Descriptions.Item>
                  </Descriptions>
                  <Table
                    dataSource={purchaseOrder.order_lines || []}
                    columns={orderColumns}
                    rowKey="item_name"
                    pagination={false}
                  />
                </>
              ) : (
                <Alert message="请先生成智能采购订单" type="info" />
              )}
            </TabPane>
          </Tabs>
        </>
      )}
    </div>
  );
};

export default SupplyCollaborationPage;