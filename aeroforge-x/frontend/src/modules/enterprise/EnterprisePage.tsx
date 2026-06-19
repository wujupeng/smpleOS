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
  Descriptions,
  Progress,
  message,
} from 'antd';
import {
  GlobalOutlined,
  DatabaseOutlined,
  RobotOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { TabPane } = Tabs;

const SITE_STATUS_COLORS: Record<string, string> = {
  online: 'green',
  offline: 'red',
  degraded: 'orange',
};

const JOB_STATUS_COLORS: Record<string, string> = {
  pending: 'default',
  running: 'processing',
  completed: 'success',
  failed: 'error',
};

const EnterprisePage: React.FC = () => {
  const { t } = useTranslation();
  const [sites, setSites] = useState<any[]>([]);
  const [syncResult, setSyncResult] = useState<any>(null);
  const [progress, setProgress] = useState<any>(null);
  const [lakeJobs, setLakeJobs] = useState<any[]>([]);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [trainingJobs, setTrainingJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [tenantId, setTenantId] = useState('default');

  const handleRegisterSite = async (values: any) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/open/platform/sites', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...values, tenant_id: tenantId }),
      });
      const result = await response.json();
      setSites(result.data?.sites || []);
      message.success('站点注册成功');
    } catch {
      message.error('注册失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/open/platform/sync', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId, data_type: 'all' }),
      });
      const result = await response.json();
      setSyncResult(result.data);
      message.success('数据同步完成');
    } catch {
      message.error('同步失败');
    } finally {
      setLoading(false);
    }
  };

  const handleGetProgress = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/open/platform/progress?tenant_id=${tenantId}`);
      const result = await response.json();
      setProgress(result.data);
      message.success('进度获取成功');
    } catch {
      message.error('获取失败');
    } finally {
      setLoading(false);
    }
  };

  const handleIngest = async (dataSource: string) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/datalake/ingest', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId, data_source: dataSource }),
      });
      const result = await response.json();
      message.success(`数据摄入完成: ${result.data?.records_processed?.toLocaleString()} 条记录`);
    } catch {
      message.error('摄入失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDataset = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/datalake/datasets', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId, name: 'Quality Prediction Dataset', dataset_type: 'quality_prediction' }),
      });
      const result = await response.json();
      message.success('数据集创建成功');
    } catch {
      message.error('创建失败');
    } finally {
      setLoading(false);
    }
  };

  const siteColumns = [
    { title: '站点ID', dataIndex: 'site_id', key: 'sid', width: 120 },
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '位置', dataIndex: 'location', key: 'loc' },
    { title: '产能', dataIndex: 'capacity', key: 'cap' },
    { title: '专业化', dataIndex: 'specialization', key: 'spec' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 80,
      render: (v: string) => <Tag color={SITE_STATUS_COLORS[v]}>{v}</Tag>,
    },
  ];

  const jobColumns = [
    { title: 'Job ID', dataIndex: 'id', key: 'id', width: 100, ellipsis: true },
    { title: '类型', dataIndex: 'job_type', key: 'type', width: 90 },
    { title: '数据源', dataIndex: 'data_source', key: 'source', width: 100 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (v: string) => <Tag color={JOB_STATUS_COLORS[v]}>{v}</Tag>,
    },
    { title: '记录数', dataIndex: 'records_processed', key: 'records', width: 100, render: (v: number) => v?.toLocaleString() },
  ];

  const datasetColumns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '类型', dataIndex: 'dataset_type', key: 'type' },
    { title: '记录数', dataIndex: 'record_count', key: 'records', render: (v: number) => v?.toLocaleString() },
    { title: '特征数', dataIndex: 'feature_count', key: 'features' },
    { title: '版本', dataIndex: 'version', key: 'version', width: 60 },
  ];

  const trainingColumns = [
    { title: '模型类型', dataIndex: 'model_type', key: 'model' },
    { title: '目标', dataIndex: 'objective', key: 'obj' },
    {
      title: '精度',
      dataIndex: 'metrics',
      key: 'acc',
      render: (v: any) => v?.accuracy ? `${(v.accuracy * 100).toFixed(1)}%` : '-',
    },
    {
      title: 'F1',
      dataIndex: 'metrics',
      key: 'f1',
      render: (v: any) => v?.f1_score ? `${(v.f1_score * 100).toFixed(1)}%` : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (v: string) => <Tag color={JOB_STATUS_COLORS[v]}>{v}</Tag>,
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2><GlobalOutlined /> 企业级管理</h2>

      <Card style={{ marginBottom: 16 }}>
        <Space>
          <span>租户ID:</span>
          <Input value={tenantId} onChange={e => setTenantId(e.target.value)} style={{ width: 200 }} />
        </Space>
      </Card>

      <Tabs defaultActiveKey="multisite">
        <TabPane tab="多站点协同" key="multisite">
          <Card title="注册站点" style={{ marginBottom: 16 }}>
            <Form layout="inline" onFinish={handleRegisterSite}>
              <Form.Item name="name" label="站点名称">
                <Input placeholder="北京工厂" />
              </Form.Item>
              <Form.Item name="location" label="位置">
                <Input placeholder="北京" />
              </Form.Item>
              <Form.Item name="capacity" label="产能">
                <Input type="number" placeholder="1000" />
              </Form.Item>
              <Form.Item name="specialization" label="专业化">
                <Select style={{ width: 150 }} defaultValue="forging">
                  <Select.Option value="forging">锻造</Select.Option>
                  <Select.Option value="machining">机加工</Select.Option>
                  <Select.Option value="heat_treatment">热处理</Select.Option>
                  <Select.Option value="assembly">装配</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading}>注册</Button>
              </Form.Item>
            </Form>
          </Card>

          <Card style={{ marginBottom: 16 }}>
            <Space>
              <Button icon={<GlobalOutlined />} onClick={handleSync} loading={loading}>触发数据同步</Button>
              <Button onClick={handleGetProgress} loading={loading}>查看进度</Button>
            </Space>
          </Card>

          {progress && (
            <Row gutter={16} style={{ marginBottom: 16 }}>
              <Col span={12}>
                <Card>
                  <Statistic
                    title="整体进度"
                    value={progress.overall_progress * 100}
                    precision={1}
                    suffix="%"
                  />
                  <Progress percent={progress.overall_progress * 100} style={{ marginTop: 8 }} />
                </Card>
              </Col>
              <Col span={12}>
                <Card title="各站点进度">
                  {progress.sites?.map((s: any) => (
                    <div key={s.site_id} style={{ marginBottom: 8 }}>
                      <span>{s.site_name}: </span>
                      <Progress percent={s.progress * 100} size="small" style={{ width: 200, display: 'inline-block' }} />
                      <Tag color={SITE_STATUS_COLORS[s.status]} style={{ marginLeft: 8 }}>{s.status}</Tag>
                    </div>
                  ))}
                </Card>
              </Col>
            </Row>
          )}

          {sites.length > 0 && (
            <Table dataSource={sites} columns={siteColumns} rowKey="site_id" pagination={false} />
          )}
        </TabPane>

        <TabPane tab="数据湖" key="datalake">
          <Card style={{ marginBottom: 16 }}>
            <Space>
              <Button icon={<CloudUploadOutlined />} onClick={() => handleIngest('mes')} loading={loading}>摄入MES数据</Button>
              <Button icon={<CloudUploadOutlined />} onClick={() => handleIngest('qms')} loading={loading}>摄入QMS数据</Button>
              <Button icon={<CloudUploadOutlined />} onClick={() => handleIngest('cae')} loading={loading}>摄入CAE数据</Button>
              <Button icon={<DatabaseOutlined />} onClick={handleCreateDataset} loading={loading}>创建训练数据集</Button>
            </Space>
          </Card>

          <Row gutter={16}>
            <Col span={12}>
              <Card title="数据任务">
                <Button size="small" onClick={async () => {
                  const r = await fetch(`/api/v1/datalake/jobs?tenant_id=${tenantId}`);
                  setLakeJobs((await r.json()).data || []);
                }}>刷新</Button>
                <Table dataSource={lakeJobs} columns={jobColumns} rowKey="id" pagination={{ pageSize: 5 }} size="small" />
              </Card>
            </Col>
            <Col span={12}>
              <Card title="数据集">
                <Button size="small" onClick={async () => {
                  const r = await fetch(`/api/v1/datalake/datasets?tenant_id=${tenantId}`);
                  setDatasets((await r.json()).data || []);
                }}>刷新</Button>
                <Table dataSource={datasets} columns={datasetColumns} rowKey="id" pagination={{ pageSize: 5 }} size="small" />
              </Card>
            </Col>
          </Row>
        </TabPane>

        <TabPane tab="AI训练" key="ai-training">
          <Card style={{ marginBottom: 16 }}>
            <Button icon={<RobotOutlined />} onClick={async () => {
              const r = await fetch(`/api/v1/datalake/training?tenant_id=${tenantId}`);
              setTrainingJobs((await r.json()).data || []);
            }} loading={loading}>刷新训练任务</Button>
          </Card>

          <Table dataSource={trainingJobs} columns={trainingColumns} rowKey="id" pagination={{ pageSize: 10 }} />
        </TabPane>
      </Tabs>
    </div>
  );
};

export default EnterprisePage;