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
  InputNumber,
  Select,
  Space,
  Alert,
  Progress,
  Descriptions,
  Modal,
  message,
} from 'antd';
import {
  SafetyCertificateOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ExperimentOutlined,
  AimOutlined,
  LineChartOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { TabPane } = Tabs;

const RISK_COLORS: Record<string, string> = {
  low: 'green',
  medium: 'orange',
  high: 'red',
};

const DRIFT_COLORS: Record<string, string> = {
  stable: 'green',
  warning: 'orange',
  drifted: 'red',
};

const QualityPredictionPage: React.FC = () => {
  const { t } = useTranslation();
  const [prediction, setPrediction] = useState<any>(null);
  const [shapValues, setShapValues] = useState<any[]>([]);
  const [driftRecord, setDriftRecord] = useState<any>(null);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [predictForm] = Form.useForm();

  const handlePredict = async (values: any) => {
    setLoading(true);
    try {
      const features = values.features || [
        { name: 'forging_temperature', value: 1150, feature_type: 'process_parameter', unit: '°C' },
        { name: 'press_speed', value: 50, feature_type: 'process_parameter', unit: 'mm/s' },
        { name: 'holding_time', value: 30, feature_type: 'process_parameter', unit: 'min' },
        { name: 'cooling_rate', value: 5, feature_type: 'process_parameter', unit: '°C/min' },
      ];
      const response = await fetch('/api/v1/mes/quality-predictions/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tenant_id: values.tenant_id || 'default',
          project_id: values.project_id || 'proj-001',
          work_order_id: values.work_order_id || 'wo-001',
          prediction_type: values.prediction_type || 'operation_quality',
          input_features: features,
          model_version: values.model_version || '1.0.0',
        }),
      });
      const result = await response.json();
      setPrediction(result.data);
      message.success('质量预测完成');
    } catch {
      message.error('预测失败');
    } finally {
      setLoading(false);
    }
  };

  const handleIdentifyDrivers = async () => {
    if (!prediction) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/mes/quality-predictions/${prediction.id}/drivers`);
      const result = await response.json();
      setShapValues(result.data || []);
      message.success('质量关键因素分析完成');
    } catch {
      message.error('分析失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDetectDrift = async () => {
    if (!prediction) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/mes/quality-predictions/${prediction.id}/detect-drift`, {
        method: 'POST',
      });
      const result = await response.json();
      setDriftRecord(result.data);
      message.success('漂移检测完成');
    } catch {
      message.error('检测失败');
    } finally {
      setLoading(false);
    }
  };

  const handleOptimizeProcess = async () => {
    if (!prediction) return;
    setLoading(true);
    try {
      const response = await fetch('/api/v1/mes/quality-predictions/optimize-process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prediction_id: prediction.id }),
      });
      const result = await response.json();
      setRecommendations(result.data || []);
      message.success('工艺参数优化完成');
    } catch {
      message.error('优化失败');
    } finally {
      setLoading(false);
    }
  };

  const shapColumns = [
    { title: '排名', dataIndex: 'importance_rank', key: 'rank', width: 60 },
    { title: '特征名称', dataIndex: 'feature_name', key: 'name' },
    {
      title: 'SHAP值',
      dataIndex: 'shap_value',
      key: 'shap',
      render: (v: number) => (
        <span style={{ color: v > 0 ? '#52c41a' : '#ff4d4f', fontWeight: 'bold' }}>
          {v > 0 ? '+' : ''}{v.toFixed(4)}
        </span>
      ),
    },
    {
      title: '方向',
      dataIndex: 'contribution_direction',
      key: 'dir',
      render: (v: string) => (
        <Tag color={v === 'positive' ? 'green' : 'red'}>
          {v === 'positive' ? '正向贡献' : '负向贡献'}
        </Tag>
      ),
    },
  ];

  const defectColumns = [
    { title: '缺陷类型', dataIndex: 'defect_type', key: 'type' },
    {
      title: '概率',
      dataIndex: 'probability',
      key: 'prob',
      render: (v: number) => <Progress percent={v * 100} size="small" />,
    },
    {
      title: '严重度',
      dataIndex: 'severity',
      key: 'sev',
      render: (v: string) => <Tag color={v === 'high' ? 'red' : v === 'medium' ? 'orange' : 'green'}>{v}</Tag>,
    },
  ];

  const recColumns = [
    { title: '参数名称', dataIndex: 'parameter_name', key: 'name' },
    { title: '当前值', dataIndex: 'current_value', key: 'current' },
    { title: '推荐值', dataIndex: 'recommended_value', key: 'recommended' },
    {
      title: '预期改善',
      dataIndex: 'expected_improvement',
      key: 'improvement',
      render: (v: number) => <Tag color="blue">{(v * 100).toFixed(1)}%</Tag>,
    },
    {
      title: '约束满足',
      dataIndex: 'constraint_satisfied',
      key: 'constraint',
      render: (v: boolean) => v ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <WarningOutlined style={{ color: '#ff4d4f' }} />,
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2><SafetyCertificateOutlined /> 质量预测</h2>

      <Card title="质量预测输入" style={{ marginBottom: 16 }}>
        <Form form={predictForm} layout="inline" onFinish={handlePredict}>
          <Form.Item name="project_id" label="项目ID">
            <Input placeholder="proj-001" />
          </Form.Item>
          <Form.Item name="work_order_id" label="工单ID">
            <Input placeholder="wo-001" />
          </Form.Item>
          <Form.Item name="prediction_type" label="预测类型">
            <Select style={{ width: 150 }} defaultValue="operation_quality">
              <Select.Option value="operation_quality">工序质量</Select.Option>
              <Select.Option value="part_quality">零件质量</Select.Option>
              <Select.Option value="batch_quality">批次质量</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} icon={<ExperimentOutlined />}>
              执行预测
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {prediction && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="合格概率"
                  value={prediction.predicted_result?.pass_probability * 100 || 0}
                  precision={1}
                  suffix="%"
                  valueStyle={{ color: prediction.predicted_result?.pass_probability > 0.9 ? '#3f8600' : '#cf1322' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="置信度"
                  value={prediction.confidence * 100 || 0}
                  precision={1}
                  suffix="%"
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="风险等级"
                  value={prediction.predicted_result?.risk_level || 'N/A'}
                  valueStyle={{ color: RISK_COLORS[prediction.predicted_result?.risk_level] || '#000' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="漂移状态"
                  value={prediction.drift_status || 'stable'}
                  valueStyle={{ color: DRIFT_COLORS[prediction.drift_status] || '#000' }}
                />
              </Card>
            </Col>
          </Row>

          <Card style={{ marginBottom: 16 }}>
            <Space>
              <Button icon={<AimOutlined />} onClick={handleIdentifyDrivers} loading={loading}>
                识别质量关键因素
              </Button>
              <Button icon={<LineChartOutlined />} onClick={handleDetectDrift} loading={loading}>
                检测质量漂移
              </Button>
              <Button icon={<ExperimentOutlined />} onClick={handleOptimizeProcess} loading={loading}>
                优化工艺参数
              </Button>
            </Space>
          </Card>

          <Tabs defaultActiveKey="defects">
            <TabPane tab="缺陷概率分布" key="defects">
              <Table
                dataSource={prediction.predicted_result?.defect_probabilities || []}
                columns={defectColumns}
                rowKey="defect_type"
                pagination={false}
              />
            </TabPane>
            <TabPane tab="SHAP关键因素" key="shap">
              <Table
                dataSource={shapValues}
                columns={shapColumns}
                rowKey="feature_name"
                pagination={false}
              />
            </TabPane>
            <TabPane tab="质量漂移" key="drift">
              {driftRecord ? (
                <Descriptions bordered column={2}>
                  <Descriptions.Item label="漂移类型">{driftRecord.drift_type}</Descriptions.Item>
                  <Descriptions.Item label="指标名称">{driftRecord.metric_name}</Descriptions.Item>
                  <Descriptions.Item label="之前值">{driftRecord.previous_value}</Descriptions.Item>
                  <Descriptions.Item label="当前值">{driftRecord.current_value}</Descriptions.Item>
                  <Descriptions.Item label="漂移幅度">
                    <Tag color={driftRecord.drift_magnitude > 0.15 ? 'red' : driftRecord.drift_magnitude > 0.08 ? 'orange' : 'green'}>
                      {driftRecord.drift_magnitude}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="采取措施">{driftRecord.action_taken}</Descriptions.Item>
                </Descriptions>
              ) : (
                <Alert message="请先执行漂移检测" type="info" />
              )}
            </TabPane>
            <TabPane tab="工艺参数优化" key="recommendations">
              <Table
                dataSource={recommendations}
                columns={recColumns}
                rowKey="parameter_name"
                pagination={false}
              />
            </TabPane>
          </Tabs>
        </>
      )}
    </div>
  );
};

export default QualityPredictionPage;