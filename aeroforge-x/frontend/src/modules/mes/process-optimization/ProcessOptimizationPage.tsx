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
  Select,
  Space,
  Alert,
  Descriptions,
  Progress,
  message,
} from 'antd';
import {
  ThunderboltOutlined,
  AimOutlined,
  ExperimentOutlined,
  CheckCircleOutlined,
  RocketOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { TabPane } = Tabs;

const SEVERITY_COLORS: Record<string, string> = {
  high: 'red',
  medium: 'orange',
  low: 'green',
};

const VALIDATION_COLORS: Record<string, string> = {
  simulated: 'blue',
  validated: 'green',
  rejected: 'red',
};

const ProcessOptimizationPage: React.FC = () => {
  const { t } = useTranslation();
  const [optimization, setOptimization] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [bottleneckForm] = Form.useForm();

  const handleAnalyzeBottleneck = async (values: any) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/mes/process-optimizations/analyze-bottleneck', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tenant_id: values.tenant_id || 'default',
          project_id: values.project_id || 'proj-001',
          process_route_id: values.process_route_id || 'route-001',
        }),
      });
      const result = await response.json();
      setOptimization(result.data);
      message.success('瓶颈分析完成');
    } catch {
      message.error('分析失败');
    } finally {
      setLoading(false);
    }
  };

  const handleOptimize = async () => {
    if (!optimization) return;
    setLoading(true);
    try {
      const response = await fetch('/api/v1/mes/process-optimizations/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          optimization_id: optimization.id,
          optimization_type: 'quality',
        }),
      });
      const result = await response.json();
      setOptimization(result.data);
      message.success('工艺参数优化完成');
    } catch {
      message.error('优化失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSimulate = async () => {
    if (!optimization) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/mes/process-optimizations/${optimization.id}/simulate`, {
        method: 'POST',
      });
      const result = await response.json();
      setOptimization(result.data);
      message.success('变更仿真完成');
    } catch {
      message.error('仿真失败');
    } finally {
      setLoading(false);
    }
  };

  const handleValidate = async () => {
    if (!optimization) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/mes/process-optimizations/${optimization.id}/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ optimization_id: optimization.id, sample_size: 30 }),
      });
      const result = await response.json();
      setOptimization(result.data);
      message.success('验证完成');
    } catch {
      message.error('验证失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDeploy = async () => {
    if (!optimization) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/mes/process-optimizations/${optimization.id}/deploy`, {
        method: 'POST',
      });
      const result = await response.json();
      setOptimization(result.data);
      message.success('优化工艺已部署');
    } catch {
      message.error('部署失败');
    } finally {
      setLoading(false);
    }
  };

  const bottleneckColumns = [
    { title: '工位ID', dataIndex: 'station_id', key: 'sid' },
    { title: '工位名称', dataIndex: 'station_name', key: 'sname' },
    {
      title: '利用率',
      dataIndex: 'utilization_rate',
      key: 'util',
      render: (v: number) => <Progress percent={v * 100} size="small" status={v > 0.9 ? 'exception' : 'active'} />,
    },
    {
      title: '等待时间(min)',
      dataIndex: 'avg_wait_time_minutes',
      key: 'wait',
      render: (v: number) => v.toFixed(1),
    },
    {
      title: '加工时间(min)',
      dataIndex: 'avg_process_time_minutes',
      key: 'proc',
      render: (v: number) => v.toFixed(1),
    },
    {
      title: '关键路径',
      dataIndex: 'is_critical_path',
      key: 'critical',
      render: (v: boolean) => v ? <Tag color="red">是</Tag> : <Tag>否</Tag>,
    },
    {
      title: '瓶颈严重度',
      dataIndex: 'bottleneck_severity',
      key: 'severity',
      render: (v: string) => <Tag color={SEVERITY_COLORS[v]}>{v}</Tag>,
    },
  ];

  const paramCompareColumns = [
    { title: '参数名称', dataIndex: 'name', key: 'name' },
    { title: '单位', dataIndex: 'unit', key: 'unit' },
    {
      title: '当前值',
      dataIndex: 'current_value',
      key: 'current',
      render: (_: any, record: any) => {
        const current = optimization?.current_process_params?.find((p: any) => p.name === record.name);
        return current?.value?.toFixed(2) || '-';
      },
    },
    {
      title: '优化值',
      dataIndex: 'optimized_value',
      key: 'optimized',
      render: (_: any, record: any) => {
        const optimized = optimization?.optimized_process_params?.find((p: any) => p.name === record.name);
        return optimized ? (
          <span style={{ color: '#1890ff', fontWeight: 'bold' }}>{optimized.value?.toFixed(2)}</span>
        ) : '-';
      },
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2><ThunderboltOutlined /> 工艺优化</h2>

      <Card title="工艺路线选择" style={{ marginBottom: 16 }}>
        <Form form={bottleneckForm} layout="inline" onFinish={handleAnalyzeBottleneck}>
          <Form.Item name="project_id" label="项目ID">
            <Input placeholder="proj-001" />
          </Form.Item>
          <Form.Item name="process_route_id" label="工艺路线ID">
            <Input placeholder="route-001" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} icon={<BarChartOutlined />}>
              瓶颈分析
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {optimization && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="时间缩短"
                  value={optimization.improvement_metrics?.time_reduction_pct || 0}
                  precision={1}
                  suffix="%"
                  valueStyle={{ color: '#3f8600' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="质量提升"
                  value={optimization.improvement_metrics?.quality_improvement_pct || 0}
                  precision={1}
                  suffix="%"
                  valueStyle={{ color: '#3f8600' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="成本降低"
                  value={optimization.improvement_metrics?.cost_reduction_pct || 0}
                  precision={1}
                  suffix="%"
                  valueStyle={{ color: '#3f8600' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="验证状态"
                  value={optimization.validation_status || 'simulated'}
                  valueStyle={{ color: VALIDATION_COLORS[optimization.validation_status] || '#000' }}
                />
              </Card>
            </Col>
          </Row>

          <Card style={{ marginBottom: 16 }}>
            <Space>
              <Button icon={<AimOutlined />} onClick={handleOptimize} loading={loading}>
                参数优化
              </Button>
              <Button icon={<ExperimentOutlined />} onClick={handleSimulate} loading={loading}>
                变更仿真
              </Button>
              <Button icon={<CheckCircleOutlined />} onClick={handleValidate} loading={loading}>
                优化验证
              </Button>
              <Button
                icon={<RocketOutlined />}
                onClick={handleDeploy}
                loading={loading}
                disabled={optimization.validation_status !== 'validated'}
              >
                部署优化工艺
              </Button>
            </Space>
          </Card>

          <Tabs defaultActiveKey="bottleneck">
            <TabPane tab="瓶颈分析" key="bottleneck">
              <Table
                dataSource={optimization.bottleneck_analysis || []}
                columns={bottleneckColumns}
                rowKey="station_id"
                pagination={false}
              />
            </TabPane>
            <TabPane tab="参数对比" key="params">
              <Table
                dataSource={optimization.optimized_process_params || []}
                columns={paramCompareColumns}
                rowKey="name"
                pagination={false}
              />
            </TabPane>
            <TabPane tab="仿真结果" key="simulation">
              {optimization.simulation_result ? (
                <Descriptions bordered column={2}>
                  <Descriptions.Item label="产能变化">
                    {optimization.simulation_result.capacity_change_pct}%
                  </Descriptions.Item>
                  <Descriptions.Item label="交期影响">
                    {optimization.simulation_result.delivery_impact_days} 天
                  </Descriptions.Item>
                  <Descriptions.Item label="风险评估">
                    <Tag color={optimization.simulation_result.risk_assessment === 'high' ? 'red' : optimization.simulation_result.risk_assessment === 'medium' ? 'orange' : 'green'}>
                      {optimization.simulation_result.risk_assessment}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="可行性">
                    {optimization.simulation_result.feasible ? <Tag color="green">可行</Tag> : <Tag color="red">不可行</Tag>}
                  </Descriptions.Item>
                </Descriptions>
              ) : (
                <Alert message="请先执行变更仿真" type="info" />
              )}
            </TabPane>
            <TabPane tab="验证结果" key="validation">
              {optimization.validation_result ? (
                <Descriptions bordered column={2}>
                  <Descriptions.Item label="样本量">{optimization.validation_result.sample_size}</Descriptions.Item>
                  <Descriptions.Item label="优化前合格率">
                    {(optimization.validation_result.pass_rate_before * 100).toFixed(1)}%
                  </Descriptions.Item>
                  <Descriptions.Item label="优化后合格率">
                    {(optimization.validation_result.pass_rate_after * 100).toFixed(1)}%
                  </Descriptions.Item>
                  <Descriptions.Item label="统计显著性">
                    <Tag color={optimization.validation_result.is_significant ? 'green' : 'red'}>
                      p={optimization.validation_result.statistical_significance}
                    </Tag>
                  </Descriptions.Item>
                </Descriptions>
              ) : (
                <Alert message="请先执行优化验证" type="info" />
              )}
            </TabPane>
          </Tabs>
        </>
      )}
    </div>
  );
};

export default ProcessOptimizationPage;