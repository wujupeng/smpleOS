import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Tabs,
  Tag,
  Button,
  Form,
  Select,
  Input,
  Space,
  Statistic,
  Row,
  Col,
  Descriptions,
  Alert,
  Timeline,
  Modal,
  message,
} from 'antd';
import {
  ApiOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SettingOutlined,
  CloudSyncOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { TabPane } = Tabs;

interface SyncRecord {
  sync_id: string;
  data_type: string;
  direction: string;
  status: string;
  records_total: number;
  records_success: number;
  records_failed: number;
  error_message: string;
  started_at: string;
  completed_at: string;
}

interface SyncStatus {
  connected: boolean;
  erp_type: string;
  total_syncs: number;
  recent_syncs: SyncRecord[];
}

const DATA_TYPE_LABELS: Record<string, string> = {
  material_master: '物料主数据',
  bom: 'BOM数据',
  work_order: '工单数据',
  cost: '成本数据',
  inventory: '库存数据',
};

const DIRECTION_LABELS: Record<string, string> = {
  erp_to_aeroforge: 'ERP → AeroForge',
  aeroforge_to_erp: 'AeroForge → ERP',
  bidirectional: '双向',
};

const STATUS_CONFIG: Record<string, { color: string; icon: React.ReactNode }> = {
  completed: { color: 'green', icon: <CheckCircleOutlined /> },
  failed: { color: 'red', icon: <CloseCircleOutlined /> },
  in_progress: { color: 'blue', icon: <SyncOutlined spin /> },
  pending: { color: 'orange', icon: <SyncOutlined /> },
  partial: { color: 'gold', icon: <WarningOutlined /> },
};

const WarningOutlined = require('@ant-design/icons').WarningOutlined;

const ERPIntegrationPage: React.FC = () => {
  const { t } = useTranslation();
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [configVisible, setConfigVisible] = useState(false);
  const [configForm] = Form.useForm();

  const fetchSyncStatus = async () => {
    try {
      const response = await fetch('/api/v1/integrations/erp/sync-status');
      const result = await response.json();
      if (result.data) setSyncStatus(result.data);
    } catch (error) {
      console.error('Failed to fetch sync status:', error);
    }
  };

  const configureERP = async (values: any) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/integrations/erp/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const result = await response.json();
      if (result.data?.connected) {
        message.success('ERP连接配置成功');
        setConfigVisible(false);
        fetchSyncStatus();
      } else {
        message.error('ERP连接配置失败');
      }
    } catch (error) {
      message.error('配置请求失败');
    } finally {
      setLoading(false);
    }
  };

  const triggerSync = async (dataType: string) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/integrations/erp/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data_type: dataType }),
      });
      const result = await response.json();
      if (result.data?.status === 'completed') {
        message.success(`${DATA_TYPE_LABELS[dataType]}同步成功`);
      } else {
        message.error(`${DATA_TYPE_LABELS[dataType]}同步失败: ${result.data?.error_message || '未知错误'}`);
      }
      fetchSyncStatus();
    } catch (error) {
      message.error('同步请求失败');
    } finally {
      setLoading(false);
    }
  };

  const syncColumns = [
    { title: '同步ID', dataIndex: 'sync_id', key: 'sync_id', width: 150 },
    {
      title: '数据类型',
      dataIndex: 'data_type',
      key: 'data_type',
      width: 120,
      render: (v: string) => DATA_TYPE_LABELS[v] || v,
    },
    {
      title: '方向',
      dataIndex: 'direction',
      key: 'direction',
      width: 150,
      render: (v: string) => DIRECTION_LABELS[v] || v,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (v: string) => {
        const config = STATUS_CONFIG[v] || { color: 'default', icon: null };
        return <Tag color={config.color} icon={config.icon}>{v}</Tag>;
      },
    },
    { title: '总数', dataIndex: 'records_total', key: 'records_total', width: 80 },
    { title: '成功', dataIndex: 'records_success', key: 'records_success', width: 80 },
    { title: '失败', dataIndex: 'records_failed', key: 'records_failed', width: 80 },
    { title: '错误信息', dataIndex: 'error_message', key: 'error_message', ellipsis: true },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      key: 'started_at',
      width: 180,
      render: (v: string) => v ? new Date(v).toLocaleString() : '-',
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={<><ApiOutlined /> ERP集成管理</>}
        extra={
          <Button icon={<SettingOutlined />} onClick={() => setConfigVisible(true)}>
            连接配置
          </Button>
        }
        style={{ marginBottom: 16 }}
      >
        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title="连接状态"
              value={syncStatus?.connected ? '已连接' : '未连接'}
              valueStyle={{ color: syncStatus?.connected ? '#3f8600' : '#cf1322' }}
              prefix={syncStatus?.connected ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic title="ERP类型" value={syncStatus?.erp_type || '-'} />
          </Col>
          <Col span={6}>
            <Statistic title="总同步次数" value={syncStatus?.total_syncs || 0} />
          </Col>
          <Col span={6}>
            <Statistic
              title="最近同步"
              value={syncStatus?.recent_syncs?.[0]?.started_at
                ? new Date(syncStatus.recent_syncs[0].started_at).toLocaleString()
                : '-'}
            />
          </Col>
        </Row>
      </Card>

      <Card>
        <Tabs defaultActiveKey="sync">
          <TabPane tab="数据同步" key="sync">
            <Row gutter={[16, 16]}>
              {Object.entries(DATA_TYPE_LABELS).map(([type, label]) => {
                const direction = ['bom', 'work_order'].includes(type) ? 'aeroforge_to_erp' : 'erp_to_aeroforge';
                return (
                  <Col span={8} key={type}>
                    <Card
                      size="small"
                      title={label}
                      extra={
                        <Tag color={direction === 'erp_to_aeroforge' ? 'blue' : 'green'}>
                          {DIRECTION_LABELS[direction]}
                        </Tag>
                      }
                    >
                      <Button
                        type="primary"
                        icon={<CloudSyncOutlined />}
                        onClick={() => triggerSync(type)}
                        loading={loading}
                        block
                      >
                        执行同步
                      </Button>
                    </Card>
                  </Col>
                );
              })}
            </Row>
          </TabPane>

          <TabPane tab="同步记录" key="history">
            <Table
              dataSource={syncStatus?.recent_syncs || []}
              columns={syncColumns}
              rowKey="sync_id"
              size="small"
              scroll={{ x: 1100 }}
            />
          </TabPane>

          <TabPane tab="同步时间线" key="timeline">
            <Timeline>
              {(syncStatus?.recent_syncs || []).map((record) => (
                <Timeline.Item
                  key={record.sync_id}
                  color={record.status === 'completed' ? 'green' : record.status === 'failed' ? 'red' : 'blue'}
                >
                  <Space>
                    <Tag>{DATA_TYPE_LABELS[record.data_type] || record.data_type}</Tag>
                    <Tag color={STATUS_CONFIG[record.status]?.color}>{record.status}</Tag>
                    <span>{record.records_success}/{record.records_total} 成功</span>
                    <span style={{ color: '#999' }}>
                      {record.started_at ? new Date(record.started_at).toLocaleString() : ''}
                    </span>
                  </Space>
                  {record.error_message && (
                    <div style={{ color: 'red', marginTop: 4 }}>{record.error_message}</div>
                  )}
                </Timeline.Item>
              ))}
            </Timeline>
          </TabPane>
        </Tabs>
      </Card>

      <Modal
        title="ERP连接配置"
        open={configVisible}
        onCancel={() => setConfigVisible(false)}
        footer={null}
      >
        <Form form={configForm} layout="vertical" onFinish={configureERP}>
          <Form.Item name="erp_type" label="ERP类型" rules={[{ required: true }]}>
            <Select placeholder="选择ERP类型">
              <Select.Option value="sap">SAP ERP</Select.Option>
              <Select.Option value="oracle">Oracle ERP</Select.Option>
              <Select.Option value="generic">通用ERP</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="base_url" label="服务地址" rules={[{ required: true }]}>
            <Input placeholder="https://erp.example.com/api" />
          </Form.Item>
          <Form.Item name="username" label="用户名">
            <Input placeholder="ERP登录用户名" />
          </Form.Item>
          <Form.Item name="password" label="密码">
            <Input.Password placeholder="ERP登录密码" />
          </Form.Item>
          <Form.Item name="api_key" label="API密钥">
            <Input.Password placeholder="API Key（可选）" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              保存并测试连接
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ERPIntegrationPage;