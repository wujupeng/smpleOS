import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Tabs,
  Tag,
  Button,
  Form,
  Select,
  InputNumber,
  Space,
  Progress,
  Statistic,
  Row,
  Col,
  Descriptions,
  Timeline,
  Alert,
  Spin,
} from 'antd';
import {
  RocketOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  ExperimentOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { TabPane } = Tabs;

interface TestSubject {
  subject_id: string;
  category: string;
  objective: string;
  method: string;
  test_points: TestPoint[];
  certification_clauses: string[];
  priority: number;
}

interface TestPoint {
  point_id: string;
  name: string;
  flight_condition: string;
  altitude_ft: number;
  speed_ktas: number;
  estimated_duration_minutes: number;
  certification_clause: string;
}

interface FlightTestPlan {
  id: string;
  aircraft_model: string;
  certification_standard: string;
  subjects: TestSubject[];
  total_flights: number;
  total_flight_hours: number;
  coverage_percentage: number;
  status: string;
}

interface CoverageResult {
  total_required: number;
  covered: number;
  uncovered: number;
  coverage_percentage: number;
  uncovered_clauses: string[];
}

interface FlightSequence {
  flight_number: number;
  test_points: { point_id: string; name: string; flight_condition: string }[];
  estimated_duration_minutes: number;
}

const CATEGORY_COLORS: Record<string, string> = {
  performance: 'blue',
  stability: 'green',
  controllability: 'orange',
  structural: 'red',
  systems: 'purple',
  flutter: 'magenta',
  stall: 'volcano',
  engine: 'gold',
  avionics: 'cyan',
  environmental: 'lime',
};

const CATEGORY_LABELS: Record<string, string> = {
  performance: '性能试飞',
  stability: '稳定性试飞',
  controllability: '操纵性试飞',
  structural: '结构试飞',
  systems: '系统试飞',
  flutter: '颤振试飞',
  stall: '失速试飞',
  engine: '发动机试飞',
  avionics: '航电试飞',
  environmental: '环境试飞',
};

const FlightTestPage: React.FC = () => {
  const { t } = useTranslation();
  const [plan, setPlan] = useState<FlightTestPlan | null>(null);
  const [coverage, setCoverage] = useState<CoverageResult | null>(null);
  const [sequence, setSequence] = useState<FlightSequence[]>([]);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const generatePlan = async (values: any) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/delivery/flight-test/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const result = await response.json();
      if (result.data) {
        setPlan(result.data);
        fetchCoverage(result.data.id);
        fetchSequence(result.data.id);
      }
    } catch (error) {
      console.error('Failed to generate flight test plan:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCoverage = async (planId: string) => {
    try {
      const response = await fetch(`/api/v1/delivery/flight-test/${planId}/coverage`);
      const result = await response.json();
      if (result.data) setCoverage(result.data);
    } catch (error) {
      console.error('Failed to fetch coverage:', error);
    }
  };

  const fetchSequence = async (planId: string) => {
    try {
      const response = await fetch(`/api/v1/delivery/flight-test/${planId}/sequence`);
      const result = await response.json();
      if (result.data?.sequence) setSequence(result.data.sequence);
    } catch (error) {
      console.error('Failed to fetch sequence:', error);
    }
  };

  const testPointColumns = [
    { title: '测试点ID', dataIndex: 'point_id', key: 'point_id', width: 120 },
    { title: '名称', dataIndex: 'name', key: 'name', width: 200 },
    {
      title: '飞行条件',
      dataIndex: 'flight_condition',
      key: 'flight_condition',
      width: 120,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    { title: '高度(ft)', dataIndex: 'altitude_ft', key: 'altitude_ft', width: 100 },
    { title: '速度(ktas)', dataIndex: 'speed_ktas', key: 'speed_ktas', width: 100 },
    { title: '认证条款', dataIndex: 'certification_clause', key: 'certification_clause', width: 120 },
    { title: '预计时长(min)', dataIndex: 'estimated_duration_minutes', key: 'estimated_duration_minutes', width: 120 },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card title={<><RocketOutlined /> 试飞方案管理</>} style={{ marginBottom: 16 }}>
        <Form form={form} layout="inline" onFinish={generatePlan}>
          <Form.Item name="aircraft_model" label="机型">
            <Select style={{ width: 160 }} placeholder="选择机型">
              <Select.Option value="AF-X100">AF-X100</Select.Option>
              <Select.Option value="AF-X200">AF-X200</Select.Option>
              <Select.Option value="AF-X300">AF-X300</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="certification_standard" label="认证标准">
            <Select style={{ width: 120 }} defaultValue="FAR-23">
              <Select.Option value="FAR-23">FAR-23</Select.Option>
              <Select.Option value="FAR-25">FAR-25</Select.Option>
              <Select.Option value="CCAR-23">CCAR-23</Select.Option>
              <Select.Option value="CCAR-25">CCAR-25</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<ExperimentOutlined />} loading={loading}>
              生成试飞方案
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {plan && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card>
                <Statistic title="试飞科目" value={plan.subjects.length} suffix="个" />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic title="试飞架次" value={plan.total_flights} suffix="架次" />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic title="试飞时长" value={plan.total_flight_hours} suffix="小时" />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="认证覆盖度"
                  value={plan.coverage_percentage}
                  suffix="%"
                  valueStyle={{ color: plan.coverage_percentage >= 90 ? '#3f8600' : '#cf1322' }}
                />
              </Card>
            </Col>
          </Row>

          {coverage && coverage.uncovered_clauses.length > 0 && (
            <Alert
              type="warning"
              message={`未覆盖认证条款: ${coverage.uncovered_clauses.length} 项`}
              description={coverage.uncovered_clauses.slice(0, 10).join(', ') + (coverage.uncovered_clauses.length > 10 ? '...' : '')}
              showIcon
              icon={<WarningOutlined />}
              style={{ marginBottom: 16 }}
            />
          )}

          <Card>
            <Tabs defaultActiveKey="subjects">
              <TabPane tab="试飞科目" key="subjects">
                {plan.subjects.map((subject) => (
                  <Card
                    key={subject.subject_id}
                    title={
                      <Space>
                        <Tag color={CATEGORY_COLORS[subject.category] || 'default'}>
                          {CATEGORY_LABELS[subject.category] || subject.category}
                        </Tag>
                        <span>{subject.objective}</span>
                      </Space>
                    }
                    size="small"
                    style={{ marginBottom: 12 }}
                  >
                    <Descriptions size="small" column={3}>
                      <Descriptions.Item label="方法">{subject.method}</Descriptions.Item>
                      <Descriptions.Item label="优先级">{subject.priority}</Descriptions.Item>
                      <Descriptions.Item label="测试点数">{subject.test_points.length}</Descriptions.Item>
                    </Descriptions>
                    <Table
                      dataSource={subject.test_points}
                      columns={testPointColumns}
                      rowKey="point_id"
                      size="small"
                      pagination={false}
                      scroll={{ x: 900 }}
                    />
                  </Card>
                ))}
              </TabPane>

              <TabPane tab="覆盖度矩阵" key="coverage">
                {coverage && (
                  <div>
                    <Progress
                      percent={coverage.coverage_percentage}
                      status={coverage.coverage_percentage >= 90 ? 'success' : 'active'}
                      style={{ marginBottom: 16 }}
                    />
                    <Row gutter={16}>
                      <Col span={8}>
                        <Statistic title="总要求" value={coverage.total_required} />
                      </Col>
                      <Col span={8}>
                        <Statistic title="已覆盖" value={coverage.covered} valueStyle={{ color: '#3f8600' }} />
                      </Col>
                      <Col span={8}>
                        <Statistic title="未覆盖" value={coverage.uncovered} valueStyle={{ color: '#cf1322' }} />
                      </Col>
                    </Row>
                    {coverage.uncovered_clauses.length > 0 && (
                      <Card title="未覆盖条款" size="small" style={{ marginTop: 16 }}>
                        <Space wrap>
                          {coverage.uncovered_clauses.map((clause) => (
                            <Tag key={clause} color="red">{clause}</Tag>
                          ))}
                        </Space>
                      </Card>
                    )}
                  </div>
                )}
              </TabPane>

              <TabPane tab="试飞顺序" key="sequence">
                <Timeline>
                  {sequence.map((flight) => (
                    <Timeline.Item key={flight.flight_number} color="blue">
                      <Card size="small" title={`第 ${flight.flight_number} 架次`} style={{ marginBottom: 8 }}>
                        <p>预计时长: {flight.estimated_duration_minutes} 分钟</p>
                        <Space wrap>
                          {flight.test_points.map((tp) => (
                            <Tag key={tp.point_id} color={CATEGORY_COLORS[tp.flight_condition] || 'default'}>
                              {tp.name}
                            </Tag>
                          ))}
                        </Space>
                      </Card>
                    </Timeline.Item>
                  ))}
                </Timeline>
              </TabPane>
            </Tabs>
          </Card>
        </>
      )}
    </div>
  );
};

export default FlightTestPage;