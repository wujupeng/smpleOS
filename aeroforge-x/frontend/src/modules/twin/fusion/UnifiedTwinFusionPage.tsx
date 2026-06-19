import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Tag,
  Tabs,
  Table,
  Timeline,
  Button,
  Form,
  Input,
  Select,
  Space,
  Alert,
  Progress,
  Descriptions,
  List,
} from 'antd';
import {
  ApartmentOutlined,
  LinkOutlined,
  ThunderboltOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  ExperimentOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { TabPane } = Tabs;

interface TwinRef {
  twin_id: string;
  twin_type: string;
  status: string;
  last_sync: string | null;
  version: number;
}

interface UnifiedTwin {
  id: string;
  aircraft_serial_number: string;
  tenant_id: string;
  project_id: string;
  design_twin_ref: TwinRef | null;
  manufacturing_twin_ref: TwinRef | null;
  flight_twin_ref: TwinRef | null;
  maintenance_twin_ref: TwinRef | null;
  fusion_status: string;
  last_fusion_time: string | null;
  fusion_version: number;
  active_twin_count: number;
  insights_count: number;
  conflicts_count: number;
}

interface Insight {
  insight_id: string;
  category: string;
  severity: string;
  source_twin: string;
  target_twin: string;
  description: string;
  recommendation: string;
  acknowledged: boolean;
}

interface FeedbackItem {
  feedback_id: string;
  source_domain: string;
  target_domain: string;
  category: string;
  description: string;
  recommendation: string;
  priority: string;
  status: string;
}

const FUSION_STATUS_CONFIG: Record<string, { color: string; text: string; icon: React.ReactNode }> = {
  full_fusion: { color: 'green', text: '完全融合', icon: <CheckCircleOutlined /> },
  partial_fusion: { color: 'orange', text: '部分融合', icon: <SyncOutlined /> },
  sync_lost: { color: 'red', text: '同步丢失', icon: <WarningOutlined /> },
  not_fused: { color: 'default', text: '未融合', icon: <ApartmentOutlined /> },
};

const TWIN_TYPE_CONFIG: Record<string, { color: string; label: string; icon: React.ReactNode }> = {
  design: { color: 'blue', label: '设计孪生', icon: <ExperimentOutlined /> },
  manufacturing: { color: 'green', label: '制造孪生', icon: <ToolOutlined /> },
  flight: { color: 'purple', label: '飞行孪生', icon: <ThunderboltOutlined /> },
  maintenance: { color: 'orange', label: '维护孪生', icon: <SyncOutlined /> },
};

const LOOP_ARROW_MAP: Record<string, string> = {
  flight: '→',
  manufacturing: '→',
  maintenance: '→',
  design: '→',
};

const UnifiedTwinFusionPage: React.FC = () => {
  const { t } = useTranslation();
  const [twin, setTwin] = useState<UnifiedTwin | null>(null);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [feedbacks, setFeedbacks] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const createUnifiedTwin = async (values: any) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/twins/unified', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const result = await response.json();
      if (result.data) setTwin(result.data);
    } catch (error) {
      console.error('Failed to create unified twin:', error);
    } finally {
      setLoading(false);
    }
  };

  const triggerFusion = async () => {
    if (!twin) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/twins/unified/${twin.aircraft_serial_number}/fuse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          design_data: { parameters: { thickness: 5.0, span: 1200 }, limits: { limit_load_factor: 3.8 } },
          manufacturing_data: { deviations: { thickness: 5.12 } },
          flight_data: { loads: { max_load_factor: 3.2 }, measurements: { thickness: 5.15 } },
          maintenance_data: { health_indicators: { degradation_rate: 0.04 } },
        }),
      });
      const result = await response.json();
      if (result.data) {
        fetchInsights();
      }
    } catch (error) {
      console.error('Failed to fuse twin data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchInsights = async () => {
    if (!twin) return;
    try {
      const response = await fetch(`/api/v1/twins/unified/${twin.aircraft_serial_number}/insights`);
      const result = await response.json();
      if (result.data?.insights) setInsights(result.data.insights);
    } catch (error) {
      console.error('Failed to fetch insights:', error);
    }
  };

  const fetchFeedbacks = async () => {
    if (!twin) return;
    try {
      const response = await fetch(`/api/v1/twins/${twin.aircraft_serial_number}/loop/feedbacks`);
      const result = await response.json();
      if (result.data?.feedbacks) setFeedbacks(result.data.feedbacks);
    } catch (error) {
      console.error('Failed to fetch feedbacks:', error);
    }
  };

  const twinRefCards = twin ? [
    { type: 'design', ref: twin.design_twin_ref },
    { type: 'manufacturing', ref: twin.manufacturing_twin_ref },
    { type: 'flight', ref: twin.flight_twin_ref },
    { type: 'maintenance', ref: twin.maintenance_twin_ref },
  ] : [];

  const insightColumns = [
    { title: '严重程度', dataIndex: 'severity', key: 'severity', width: 100, render: (v: string) => <Tag color={v === 'critical' ? 'red' : v === 'warning' ? 'orange' : 'blue'}>{v}</Tag> },
    { title: '类别', dataIndex: 'category', key: 'category', width: 150 },
    { title: '来源', dataIndex: 'source_twin', key: 'source_twin', width: 100 },
    { title: '目标', dataIndex: 'target_twin', key: 'target_twin', width: 100 },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: '建议', dataIndex: 'recommendation', key: 'recommendation', ellipsis: true },
  ];

  const feedbackColumns = [
    { title: '优先级', dataIndex: 'priority', key: 'priority', width: 80, render: (v: string) => <Tag color={v === 'high' ? 'red' : 'orange'}>{v}</Tag> },
    { title: '链路', key: 'loop', width: 150, render: (_: any, r: FeedbackItem) => `${r.source_domain} → ${r.target_domain}` },
    { title: '类别', dataIndex: 'category', key: 'category', width: 150 },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: '建议', dataIndex: 'recommendation', key: 'recommendation', ellipsis: true },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card title={<><ApartmentOutlined /> 统一数字孪生融合</>} style={{ marginBottom: 16 }}>
        <Form form={form} layout="inline" onFinish={createUnifiedTwin}>
          <Form.Item name="aircraft_serial_number" label="机号">
            <Input placeholder="AF-X100-SN001" style={{ width: 160 }} />
          </Form.Item>
          <Form.Item name="tenant_id" label="租户ID">
            <Input placeholder="t1" style={{ width: 100 }} />
          </Form.Item>
          <Form.Item name="project_id" label="项目ID">
            <Input placeholder="p1" style={{ width: 100 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>创建统一孪生</Button>
          </Form.Item>
        </Form>
      </Card>

      {twin && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="融合状态"
                  value={FUSION_STATUS_CONFIG[twin.fusion_status]?.text || twin.fusion_status}
                  valueStyle={{ color: FUSION_STATUS_CONFIG[twin.fusion_status]?.color === 'green' ? '#3f8600' : FUSION_STATUS_CONFIG[twin.fusion_status]?.color === 'red' ? '#cf1322' : '#fa8c16' }}
                  prefix={FUSION_STATUS_CONFIG[twin.fusion_status]?.icon}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic title="活跃孪生" value={twin.active_twin_count} suffix="/ 4" />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic title="跨孪生洞察" value={twin.insights_count} />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic title="数据冲突" value={twin.conflicts_count} valueStyle={{ color: twin.conflicts_count > 0 ? '#cf1322' : '#3f8600' }} />
              </Card>
            </Col>
          </Row>

          <Row gutter={16} style={{ marginBottom: 16 }}>
            {twinRefCards.map(({ type, ref }) => {
              const config = TWIN_TYPE_CONFIG[type];
              return (
                <Col span={6} key={type}>
                  <Card
                    size="small"
                    title={<Space><config.icon /><span>{config.label}</span></Space>}
                    extra={<Tag color={ref?.status === 'active' ? 'green' : 'default'}>{ref?.status || '未关联'}</Tag>}
                  >
                    {ref ? (
                      <Descriptions size="small" column={1}>
                        <Descriptions.Item label="ID">{ref.twin_id.slice(0, 8)}...</Descriptions.Item>
                        <Descriptions.Item label="版本">v{ref.version}</Descriptions.Item>
                      </Descriptions>
                    ) : (
                      <Alert type="info" message="未关联" showIcon={false} />
                    )}
                  </Card>
                </Col>
              );
            })}
          </Row>

          <Card extra={<Button type="primary" icon={<LinkOutlined />} onClick={triggerFusion} loading={loading}>执行融合</Button>}>
            <Tabs defaultActiveKey="insights">
              <TabPane tab="跨孪生洞察" key="insights">
                <Table
                  dataSource={insights}
                  columns={insightColumns}
                  rowKey="insight_id"
                  size="small"
                  scroll={{ x: 900 }}
                />
              </TabPane>

              <TabPane tab="闭环反馈" key="loop">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Card title="飞行 → 设计" size="small">
                        <Timeline items={feedbacks
                          .filter(f => f.source_domain === 'flight' && f.target_domain === 'design')
                          .map(f => ({ children: <div><Tag color={f.priority === 'high' ? 'red' : 'orange'}>{f.priority}</Tag>{f.description}</div>, color: f.priority === 'high' ? 'red' : 'blue' }))
                        }/>
                      </Card>
                    </Col>
                    <Col span={12}>
                      <Card title="制造 → 设计" size="small">
                        <Timeline items={feedbacks
                          .filter(f => f.source_domain === 'manufacturing' && f.target_domain === 'design')
                          .map(f => ({ children: <div><Tag color={f.priority === 'high' ? 'red' : 'orange'}>{f.priority}</Tag>{f.description}</div>, color: f.priority === 'high' ? 'red' : 'blue' }))
                        }/>
                      </Card>
                    </Col>
                  </Row>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Card title="飞行 → 维护" size="small">
                        <Timeline items={feedbacks
                          .filter(f => f.source_domain === 'flight' && f.target_domain === 'maintenance')
                          .map(f => ({ children: <div><Tag color={f.priority === 'high' ? 'red' : 'orange'}>{f.priority}</Tag>{f.description}</div>, color: f.priority === 'high' ? 'red' : 'blue' }))
                        }/>
                      </Card>
                    </Col>
                    <Col span={12}>
                      <Card title="维护 → 制造" size="small">
                        <Timeline items={feedbacks
                          .filter(f => f.source_domain === 'maintenance' && f.target_domain === 'manufacturing')
                          .map(f => ({ children: <div><Tag color={f.priority === 'high' ? 'red' : 'orange'}>{f.priority}</Tag>{f.description}</div>, color: f.priority === 'high' ? 'red' : 'blue' }))
                        }/>
                      </Card>
                    </Col>
                  </Row>
                  <Button onClick={fetchFeedbacks} icon={<SyncOutlined />}>加载闭环反馈</Button>
                </Space>
              </TabPane>

              <TabPane tab="反馈列表" key="feedback-table">
                <Table
                  dataSource={feedbacks}
                  columns={feedbackColumns}
                  rowKey="feedback_id"
                  size="small"
                  scroll={{ x: 800 }}
                />
              </TabPane>
            </Tabs>
          </Card>
        </>
      )}
    </div>
  );
};

export default UnifiedTwinFusionPage;