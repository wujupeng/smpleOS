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
  Rate,
  message,
} from 'antd';
import {
  AppstoreOutlined,
  ApiOutlined,
  ShopOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { TabPane } = Tabs;

const APP_TYPE_COLORS: Record<string, string> = {
  integration: 'blue',
  visualization: 'purple',
  analysis: 'green',
  automation: 'orange',
  custom_widget: 'cyan',
};

const PLUGIN_TYPE_COLORS: Record<string, string> = {
  data_source: 'blue',
  visualization: 'purple',
  analysis: 'green',
  workflow: 'orange',
  custom_panel: 'cyan',
};

const PRICE_COLORS: Record<string, string> = {
  free: 'green',
  freemium: 'blue',
  paid: 'orange',
  subscription: 'purple',
};

const EcosystemPage: React.FC = () => {
  const { t } = useTranslation();
  const [developer, setDeveloper] = useState<any>(null);
  const [apiKey, setApiKey] = useState<any>(null);
  const [apps, setApps] = useState<any[]>([]);
  const [plugins, setPlugins] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [devForm] = Form.useForm();
  const [appForm] = Form.useForm();
  const [pluginForm] = Form.useForm();

  const handleRegister = async (values: any) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/open/developers/register', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const result = await response.json();
      setDeveloper(result.data);
      message.success('开发者注册成功');
    } catch {
      message.error('注册失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateApiKey = async () => {
    if (!developer) return;
    setLoading(true);
    try {
      const response = await fetch('/api/v1/open/developers/api-keys', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ developer_id: developer.developer_id, scopes: ['read', 'write'] }),
      });
      const result = await response.json();
      setApiKey(result.data);
      message.success('API Key已创建');
    } catch {
      message.error('创建失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitApp = async (values: any) => {
    if (!developer) return;
    setLoading(true);
    try {
      const response = await fetch('/api/v1/open/apps', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...values, developer_id: developer.developer_id }),
      });
      const result = await response.json();
      setApps(prev => [...prev, result.data]);
      message.success('应用已提交');
    } catch {
      message.error('提交失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitPlugin = async (values: any) => {
    if (!developer) return;
    setLoading(true);
    try {
      const response = await fetch('/api/v1/open/plugins', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...values, developer_id: developer.developer_id }),
      });
      const result = await response.json();
      message.success('插件已提交，待审核');
    } catch {
      message.error('提交失败');
    } finally {
      setLoading(false);
    }
  };

  const handleListPlugins = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/open/plugins');
      const result = await response.json();
      setPlugins(result.data || []);
      message.success(`共 ${result.data?.length || 0} 个插件`);
    } catch {
      message.error('查询失败');
    } finally {
      setLoading(false);
    }
  };

  const handleInstallPlugin = async (pluginId: string) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/open/plugins/${pluginId}/install?tenant_id=default`, {
        method: 'POST',
      });
      const result = await response.json();
      message.success('插件已安装');
      handleListPlugins();
    } catch {
      message.error('安装失败');
    } finally {
      setLoading(false);
    }
  };

  const appColumns = [
    { title: '应用名称', dataIndex: 'name', key: 'name' },
    { title: '类型', dataIndex: 'app_type', key: 'type', render: (v: string) => <Tag color={APP_TYPE_COLORS[v]}>{v}</Tag> },
    { title: '状态', dataIndex: 'status', key: 'status', render: (v: string) => <Tag color={v === 'published' ? 'green' : 'orange'}>{v}</Tag> },
    { title: '版本', dataIndex: 'version', key: 'version', width: 80 },
  ];

  const pluginColumns = [
    { title: '插件名称', dataIndex: 'name', key: 'name' },
    { title: '类型', dataIndex: 'plugin_type', key: 'type', render: (v: string) => <Tag color={PLUGIN_TYPE_COLORS[v]}>{v}</Tag> },
    { title: '价格', dataIndex: 'price_model', key: 'price', render: (v: string) => <Tag color={PRICE_COLORS[v]}>{v}</Tag> },
    { title: '安装数', dataIndex: 'install_count', key: 'installs', width: 80 },
    {
      title: '评分',
      dataIndex: 'rating',
      key: 'rating',
      width: 120,
      render: (v: number) => v > 0 ? <Rate disabled value={v} allowHalf /> : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_: any, record: any) => (
        <Button size="small" type="link" onClick={() => handleInstallPlugin(record.id)}>安装</Button>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2><AppstoreOutlined /> 平台生态</h2>

      <Tabs defaultActiveKey="developer">
        <TabPane tab="开发者门户" key="developer">
          <Card title="注册开发者" style={{ marginBottom: 16 }}>
            <Form form={devForm} layout="inline" onFinish={handleRegister}>
              <Form.Item name="developer_name" label="开发者名称">
                <Input placeholder="My Company" />
              </Form.Item>
              <Form.Item name="email" label="邮箱">
                <Input placeholder="dev@example.com" />
              </Form.Item>
              <Form.Item name="tier" label="等级">
                <Select style={{ width: 120 }} defaultValue="free">
                  <Select.Option value="free">Free</Select.Option>
                  <Select.Option value="pro">Pro</Select.Option>
                  <Select.Option value="enterprise">Enterprise</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} icon={<UserOutlined />}>
                  注册
                </Button>
              </Form.Item>
            </Form>
          </Card>

          {developer && (
            <>
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={8}>
                  <Card>
                    <Descriptions column={1} size="small">
                      <Descriptions.Item label="开发者ID">{developer.developer_id}</Descriptions.Item>
                      <Descriptions.Item label="名称">{developer.developer_name}</Descriptions.Item>
                      <Descriptions.Item label="等级"><Tag color="blue">{developer.tier}</Tag></Descriptions.Item>
                    </Descriptions>
                  </Card>
                </Col>
                <Col span={8}>
                  <Card>
                    {apiKey ? (
                      <Descriptions column={1} size="small">
                        <Descriptions.Item label="Key前缀"><code>{apiKey.key_prefix}***</code></Descriptions.Item>
                        <Descriptions.Item label="权限">{apiKey.scopes?.join(', ')}</Descriptions.Item>
                        <Descriptions.Item label="速率限制">{apiKey.rate_limit}/min</Descriptions.Item>
                      </Descriptions>
                    ) : (
                      <Button type="primary" onClick={handleCreateApiKey} icon={<ApiOutlined />}>创建API Key</Button>
                    )}
                  </Card>
                </Col>
                <Col span={8}>
                  <Card>
                    <Statistic title="已提交应用" value={apps.length} />
                  </Card>
                </Col>
              </Row>

              <Card title="提交应用" style={{ marginBottom: 16 }}>
                <Form form={appForm} layout="inline" onFinish={handleSubmitApp}>
                  <Form.Item name="name" label="应用名称">
                    <Input placeholder="My App" />
                  </Form.Item>
                  <Form.Item name="app_type" label="类型">
                    <Select style={{ width: 140 }} defaultValue="integration">
                      <Select.Option value="integration">集成</Select.Option>
                      <Select.Option value="visualization">可视化</Select.Option>
                      <Select.Option value="analysis">分析</Select.Option>
                      <Select.Option value="automation">自动化</Select.Option>
                    </Select>
                  </Form.Item>
                  <Form.Item name="description" label="描述">
                    <Input placeholder="应用描述" />
                  </Form.Item>
                  <Form.Item>
                    <Button type="primary" htmlType="submit" loading={loading}>提交</Button>
                  </Form.Item>
                </Form>
              </Card>

              {apps.length > 0 && (
                <Table dataSource={apps} columns={appColumns} rowKey="id" pagination={false} />
              )}
            </>
          )}
        </TabPane>

        <TabPane tab="插件市场" key="marketplace">
          <Card style={{ marginBottom: 16 }}>
            <Space>
              <Button type="primary" onClick={handleListPlugins} loading={loading} icon={<ShopOutlined />}>
                浏览插件市场
              </Button>
            </Space>
          </Card>

          {developer && (
            <Card title="提交插件" style={{ marginBottom: 16 }}>
              <Form form={pluginForm} layout="inline" onFinish={handleSubmitPlugin}>
                <Form.Item name="name" label="插件名称">
                  <Input placeholder="My Plugin" />
                </Form.Item>
                <Form.Item name="plugin_type" label="类型">
                  <Select style={{ width: 140 }} defaultValue="visualization">
                    <Select.Option value="data_source">数据源</Select.Option>
                    <Select.Option value="visualization">可视化</Select.Option>
                    <Select.Option value="analysis">分析</Select.Option>
                    <Select.Option value="workflow">工作流</Select.Option>
                  </Select>
                </Form.Item>
                <Form.Item name="description" label="描述">
                  <Input placeholder="插件描述" />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit" loading={loading}>提交</Button>
                </Form.Item>
              </Form>
            </Card>
          )}

          <Table
            dataSource={plugins}
            columns={pluginColumns}
            rowKey="id"
            pagination={{ pageSize: 10 }}
          />
        </TabPane>
      </Tabs>
    </div>
  );
};

export default EcosystemPage;