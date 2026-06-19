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
  Alert,
  message,
} from 'antd';
import {
  BulbOutlined,
  NodeIndexOutlined,
  RobotOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { TabPane } = Tabs;

const ENTITY_COLORS: Record<string, string> = {
  Regulation: 'blue',
  Material: 'green',
  Process: 'purple',
  Component: 'cyan',
  FailureMode: 'red',
  DesignRule: 'orange',
  BestPractice: 'gold',
};

const KnowledgeCenterPage: React.FC = () => {
  const { t } = useTranslation();
  const [graphStats, setGraphStats] = useState<any>(null);
  const [queryResults, setQueryResults] = useState<any[]>([]);
  const [designRec, setDesignRec] = useState<any>(null);
  const [materialRec, setMaterialRec] = useState<any>(null);
  const [processRec, setProcessRec] = useState<any>(null);
  const [decisionResult, setDecisionResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [tenantId, setTenantId] = useState('default');

  const handleIngestAll = async () => {
    setLoading(true);
    try {
      await fetch('/api/v1/knowledge/ingest/regulation', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId }),
      });
      await fetch('/api/v1/knowledge/ingest/material', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId }),
      });
      await fetch('/api/v1/knowledge/ingest/process', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId }),
      });
      await fetch('/api/v1/knowledge/ingest/failure-mode', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId }),
      });
      message.success('知识导入完成');
    } catch {
      message.error('导入失败');
    } finally {
      setLoading(false);
    }
  };

  const handleBuildGraph = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/knowledge/graph/build', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId }),
      });
      const result = await response.json();
      setGraphStats(result.data);
      message.success('知识图谱构建完成');
    } catch {
      message.error('构建失败');
    } finally {
      setLoading(false);
    }
  };

  const handleQuery = async (values: any) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/knowledge/graph/query', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId, query: values.query || '', entity_type: values.entity_type || null }),
      });
      const result = await response.json();
      setQueryResults(result.data || []);
      message.success(`查询到 ${result.data?.length || 0} 条结果`);
    } catch {
      message.error('查询失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRecommendDesign = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/knowledge/recommend/design-parameters', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId, project_id: 'proj-001' }),
      });
      const result = await response.json();
      setDesignRec(result.data);
      message.success('设计参数推荐完成');
    } catch {
      message.error('推荐失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRecommendMaterial = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/knowledge/recommend/material', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId, project_id: 'proj-001' }),
      });
      const result = await response.json();
      setMaterialRec(result.data);
      message.success('材料选型推荐完成');
    } catch {
      message.error('推荐失败');
    } finally {
      setLoading(false);
    }
  };

  const handleRecommendProcess = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/knowledge/recommend/process', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId, project_id: 'proj-001', material: 'Ti-6Al-4V' }),
      });
      const result = await response.json();
      setProcessRec(result.data);
      message.success('工艺参数推荐完成');
    } catch {
      message.error('推荐失败');
    } finally {
      setLoading(false);
    }
  };

  const handleDesignDecision = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/knowledge/decision/design', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: tenantId, project_id: 'proj-001' }),
      });
      const result = await response.json();
      setDecisionResult(result.data);
      message.success('设计决策分析完成');
    } catch {
      message.error('分析失败');
    } finally {
      setLoading(false);
    }
  };

  const entityColumns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '描述', dataIndex: 'description', key: 'desc', ellipsis: true },
    {
      title: '类型',
      dataIndex: 'entity_type',
      key: 'type',
      width: 120,
      render: (v: string) => <Tag color={ENTITY_COLORS[v]}>{v}</Tag>,
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'conf',
      width: 80,
      render: (v: number) => `${(v * 100).toFixed(0)}%`,
    },
  ];

  const designRecColumns = [
    { title: '参数', dataIndex: 'parameter', key: 'param' },
    { title: '推荐值', dataIndex: 'recommended_value', key: 'val' },
    { title: '单位', dataIndex: 'unit', key: 'unit', width: 60 },
    { title: '推荐理由', dataIndex: 'reason', key: 'reason', ellipsis: true },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'conf',
      width: 80,
      render: (v: number) => `${(v * 100).toFixed(0)}%`,
    },
  ];

  const materialColumns = [
    { title: '材料', dataIndex: 'material', key: 'mat' },
    {
      title: '评分',
      dataIndex: 'score',
      key: 'score',
      width: 80,
      render: (v: number) => `${(v * 100).toFixed(0)}%`,
    },
    { title: '优点', dataIndex: 'pros', key: 'pros', render: (v: string[]) => v?.join('; ') },
    { title: '缺点', dataIndex: 'cons', key: 'cons', render: (v: string[]) => v?.join('; ') },
    {
      title: '认证',
      dataIndex: 'certification_status',
      key: 'cert',
      width: 80,
      render: (v: string) => <Tag color={v === 'certified' ? 'green' : 'orange'}>{v}</Tag>,
    },
  ];

  const decisionColumns = [
    { title: '方案', dataIndex: 'name', key: 'name' },
    { title: '性能', dataIndex: 'performance_score', key: 'perf', render: (v: number) => `${(v * 100).toFixed(0)}%` },
    { title: '成本', dataIndex: 'cost_score', key: 'cost', render: (v: number) => `${(v * 100).toFixed(0)}%` },
    { title: '风险', dataIndex: 'risk_score', key: 'risk', render: (v: number) => `${(v * 100).toFixed(0)}%` },
    { title: '认证', dataIndex: 'certification_ease', key: 'cert', render: (v: number) => `${(v * 100).toFixed(0)}%` },
    {
      title: '综合',
      dataIndex: 'overall_score',
      key: 'overall',
      render: (v: number) => <Tag color="blue">{(v * 100).toFixed(0)}%</Tag>,
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2><BulbOutlined /> 知识中心与智能决策</h2>

      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Input placeholder="租户ID" value={tenantId} onChange={e => setTenantId(e.target.value)} style={{ width: 150 }} />
          <Button type="primary" onClick={handleIngestAll} loading={loading} icon={<NodeIndexOutlined />}>
            导入全部知识
          </Button>
          <Button onClick={handleBuildGraph} loading={loading}>
            构建知识图谱
          </Button>
        </Space>
      </Card>

      {graphStats && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}><Card><Statistic title="实体总数" value={graphStats.total_entities} /></Card></Col>
          <Col span={6}><Card><Statistic title="关系总数" value={graphStats.total_relations} /></Card></Col>
          <Col span={6}><Card><Statistic title="法规" value={graphStats.entities_by_type?.Regulation || 0} /></Card></Col>
          <Col span={6}><Card><Statistic title="材料" value={graphStats.entities_by_type?.Material || 0} /></Card></Col>
        </Row>
      )}

      <Tabs defaultActiveKey="graph">
        <TabPane tab="知识图谱" key="graph">
          <Card style={{ marginBottom: 16 }}>
            <Form layout="inline" onFinish={handleQuery}>
              <Form.Item name="query" label="搜索">
                <Input placeholder="搜索知识..." style={{ width: 300 }} />
              </Form.Item>
              <Form.Item name="entity_type" label="类型">
                <Select style={{ width: 140 }} allowClear placeholder="全部类型">
                  <Select.Option value="Regulation">法规</Select.Option>
                  <Select.Option value="Material">材料</Select.Option>
                  <Select.Option value="Process">工艺</Select.Option>
                  <Select.Option value="FailureMode">故障模式</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading}>查询</Button>
              </Form.Item>
            </Form>
          </Card>

          <Table
            dataSource={queryResults}
            columns={entityColumns}
            rowKey="id"
            pagination={{ pageSize: 10 }}
          />
        </TabPane>

        <TabPane tab="智能推荐" key="recommend">
          <Card style={{ marginBottom: 16 }}>
            <Space>
              <Button icon={<BulbOutlined />} onClick={handleRecommendDesign} loading={loading}>推荐设计参数</Button>
              <Button icon={<BulbOutlined />} onClick={handleRecommendMaterial} loading={loading}>推荐材料选型</Button>
              <Button icon={<BulbOutlined />} onClick={handleRecommendProcess} loading={loading}>推荐工艺参数</Button>
            </Space>
          </Card>

          {designRec && (
            <Card title="设计参数推荐" style={{ marginBottom: 16 }}>
              <Table dataSource={designRec.recommendations || []} columns={designRecColumns} rowKey="parameter" pagination={false} />
            </Card>
          )}

          {materialRec && (
            <Card title="材料选型推荐" style={{ marginBottom: 16 }}>
              <Table dataSource={materialRec.materials || []} columns={materialColumns} rowKey="material" pagination={false} />
            </Card>
          )}

          {processRec && (
            <Card title="工艺参数推荐" style={{ marginBottom: 16 }}>
              <Descriptions bordered column={2}>
                <Descriptions.Item label="材料">{processRec.material}</Descriptions.Item>
                <Descriptions.Item label="推荐工艺">{processRec.recommended_process}</Descriptions.Item>
              </Descriptions>
              <Table
                dataSource={processRec.parameters || []}
                columns={[
                  { title: '参数', dataIndex: 'name', key: 'name' },
                  { title: '推荐值', dataIndex: 'value', key: 'val' },
                  { title: '单位', dataIndex: 'unit', key: 'unit' },
                  { title: '范围', dataIndex: 'range', key: 'range' },
                ]}
                rowKey="name"
                pagination={false}
              />
            </Card>
          )}
        </TabPane>

        <TabPane tab="决策支持" key="decision">
          <Card style={{ marginBottom: 16 }}>
            <Space>
              <Button icon={<RobotOutlined />} onClick={handleDesignDecision} loading={loading}>设计决策分析</Button>
            </Space>
          </Card>

          {decisionResult && (
            <Card title="设计决策分析">
              <Alert
                message={`推荐方案: ${decisionResult.recommended}`}
                description={decisionResult.recommendation_reason}
                type="success"
                style={{ marginBottom: 16 }}
              />
              <Table
                dataSource={decisionResult.alternatives_comparison || []}
                columns={decisionColumns}
                rowKey="name"
                pagination={false}
              />
            </Card>
          )}
        </TabPane>
      </Tabs>
    </div>
  );
};

export default KnowledgeCenterPage;