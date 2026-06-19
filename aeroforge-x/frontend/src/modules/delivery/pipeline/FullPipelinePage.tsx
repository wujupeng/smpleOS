import React, { useState } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Tag,
  Steps,
  Table,
  Button,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Descriptions,
  Progress,
  Alert,
  message,
} from 'antd';
import {
  RocketOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  FileZipOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const STAGE_NAMES: Record<string, string> = {
  requirements_to_design: '需求→设计',
  design_to_engineering: '设计→工程',
  engineering_to_cae: '工程→CAE',
  design_to_bom: '设计→BOM',
  bom_to_manufacturing: 'BOM→制造',
  certification: '认证',
  flight_test: '试飞',
  delivery_package: '交付包',
};

const STAGE_STATUS_COLORS: Record<string, string> = {
  pending: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
  skipped: 'warning',
};

const FullPipelinePage: React.FC = () => {
  const { t } = useTranslation();
  const [pipeline, setPipeline] = useState<any>(null);
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const handleGenerate = async (values: any) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/delivery/pipeline/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tenant_id: values.tenant_id || 'default',
          project_id: values.project_id || 'proj-001',
          aircraft_spec: {
            aircraft_type: values.aircraft_type || 'light_transport',
            mtow_kg: values.mtow || 5700,
            passengers: values.passengers || 9,
            range_nm: values.range || 1200,
            engine_type: values.engine_type || 'turboprop',
          },
        }),
      });
      const result = await response.json();
      setPipeline(result.data);
      message.success('全链路生成完成');
    } catch {
      message.error('生成失败');
    } finally {
      setLoading(false);
    }
  };

  const handleGetReport = async () => {
    if (!pipeline) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/delivery/pipeline/${pipeline.id}/report`);
      const result = await response.json();
      setReport(result.data);
      message.success('报告获取成功');
    } catch {
      message.error('获取失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = async () => {
    if (!pipeline) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/delivery/pipeline/${pipeline.id}/retry`, {
        method: 'POST',
      });
      const result = await response.json();
      setPipeline(result.data);
      message.success('重试成功');
    } catch {
      message.error('重试失败');
    } finally {
      setLoading(false);
    }
  };

  const getStepStatus = (stageStatus: string): 'wait' | 'process' | 'finish' | 'error' => {
    switch (stageStatus) {
      case 'completed': return 'finish';
      case 'running': return 'process';
      case 'failed': return 'error';
      case 'skipped': return 'wait';
      default: return 'wait';
    }
  };

  const stageColumns = [
    { title: '阶段', dataIndex: 'stage', key: 'stage', render: (v: string) => STAGE_NAMES[v] || v },
    { title: '描述', dataIndex: 'description', key: 'desc' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (v: string) => <Tag color={STAGE_STATUS_COLORS[v]}>{v}</Tag>,
    },
    { title: '耗时(s)', dataIndex: 'duration_seconds', key: 'dur', render: (v: number) => v?.toFixed(1) || '-' },
    {
      title: '输出',
      dataIndex: 'output_summary',
      key: 'output',
      render: (v: string[]) => v?.join(', ') || '-',
    },
    { title: '错误', dataIndex: 'error', key: 'error', render: (v: string) => v || '-' },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2><RocketOutlined /> 全链路自动生成</h2>

      <Card title="全链路生成配置" style={{ marginBottom: 16 }}>
        <Form form={form} layout="inline" onFinish={handleGenerate}>
          <Form.Item name="project_id" label="项目ID">
            <Input placeholder="proj-001" />
          </Form.Item>
          <Form.Item name="aircraft_type" label="飞行器类型">
            <Select style={{ width: 150 }} defaultValue="light_transport">
              <Select.Option value="light_transport">轻型运输机</Select.Option>
              <Select.Option value="regional_jet">支线喷气</Select.Option>
              <Select.Option value="business_jet">公务机</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="mtow" label="MTOW(kg)">
            <InputNumber placeholder="5700" min={500} max={100000} />
          </Form.Item>
          <Form.Item name="passengers" label="乘客数">
            <InputNumber placeholder="9" min={1} max={500} />
          </Form.Item>
          <Form.Item name="engine_type" label="发动机类型">
            <Select style={{ width: 120 }} defaultValue="turboprop">
              <Select.Option value="turboprop">涡桨</Select.Option>
              <Select.Option value="turbofan">涡扇</Select.Option>
              <Select.Option value="piston">活塞</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} icon={<RocketOutlined />}>
              触发全链路生成
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {pipeline && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card>
                <Statistic
                  title="整体进度"
                  value={pipeline.progress?.progress_pct || 0}
                  suffix="%"
                  valueStyle={{ color: pipeline.status === 'completed' ? '#3f8600' : pipeline.status === 'failed' ? '#cf1322' : '#1890ff' }}
                />
                <Progress percent={pipeline.progress?.progress_pct || 0} style={{ marginTop: 8 }} />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="状态"
                  value={pipeline.status}
                  valueStyle={{ color: pipeline.status === 'completed' ? '#3f8600' : pipeline.status === 'failed' ? '#cf1322' : '#1890ff' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="已完成阶段"
                  value={`${pipeline.progress?.completed_stages || 0}/${pipeline.progress?.total_stages || 8}`}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Space>
                  <Button icon={<FileZipOutlined />} onClick={handleGetReport} loading={loading}>
                    查看报告
                  </Button>
                  {pipeline.status === 'failed' && (
                    <Button icon={<SyncOutlined />} onClick={handleRetry} loading={loading}>
                      重试失败阶段
                    </Button>
                  )}
                </Space>
              </Card>
            </Col>
          </Row>

          <Card title="流水线阶段进度" style={{ marginBottom: 16 }}>
            {pipeline.stages && (
              <Steps
                current={Object.values(pipeline.stages).findIndex((s: any) => s.status === 'running' || s.status === 'failed')}
                status={pipeline.status === 'failed' ? 'error' : 'process'}
                items={Object.entries(pipeline.stages).map(([key, stage]: [string, any]) => ({
                  title: STAGE_NAMES[key] || key,
                  status: getStepStatus(stage.status),
                  description: stage.status === 'completed'
                    ? <CheckCircleOutlined style={{ color: '#52c41a' }} />
                    : stage.status === 'failed'
                    ? <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                    : stage.status === 'running'
                    ? <SyncOutlined spin style={{ color: '#1890ff' }} />
                    : null,
                }))}
              />
            )}
          </Card>

          {report && (
            <Card title="流水线报告">
              <Table
                dataSource={report.stages || []}
                columns={stageColumns}
                rowKey="stage"
                pagination={false}
              />
              {report.issues?.length > 0 && (
                <Alert
                  style={{ marginTop: 16 }}
                  message={`${report.issues.length} 个问题`}
                  description={report.issues.map((i: any) => `${i.stage}: ${i.issue}`).join('; ')}
                  type="warning"
                />
              )}
            </Card>
          )}
        </>
      )}
    </div>
  );
};

export default FullPipelinePage;