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
  Descriptions,
  Modal,
  message,
} from 'antd';
import {
  ThunderboltOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  ScheduleOutlined,
  ExperimentOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { TabPane } = Tabs;

const TRIGGER_TYPE_CONFIG: Record<string, { color: string; label: string }> = {
  station_failure: { color: 'red', label: '工位故障' },
  station_recovery: { color: 'green', label: '工位恢复' },
  material_delay: { color: 'orange', label: '物料延迟' },
  urgent_insert: { color: 'purple', label: '紧急插单' },
  quality_anomaly: { color: 'volcano', label: '质量异常' },
  personnel_absence: { color: 'gold', label: '人员缺勤' },
  deadline_change: { color: 'blue', label: '交期变更' },
};

const AdaptiveSchedulingPage: React.FC = () => {
  const { t } = useTranslation();
  const [scheduleId, setScheduleId] = useState<string | null>(null);
  const [schedule, setSchedule] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const [triggerForm] = Form.useForm();

  const createSchedule = async (values: any) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/mes/adaptive-schedules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const result = await response.json();
      if (result.data) {
        setScheduleId(result.data.id);
        setSchedule(result.data);
        message.success('自适应排程创建成功');
      }
    } catch (error) {
      message.error('创建失败');
    } finally {
      setLoading(false);
    }
  };

  const detectAndAdapt = async (values: any) => {
    if (!scheduleId) return;
    setLoading(true);
    try {
      const triggerRes = await fetch(`/api/v1/mes/adaptive-schedules/${scheduleId}/detect-trigger`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const triggerResult = await triggerRes.json();
      if (triggerResult.data?.trigger_id) {
        const adaptRes = await fetch(`/api/v1/mes/adaptive-schedules/${scheduleId}/adapt`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ trigger_id: triggerResult.data.trigger_id }),
        });
        const adaptResult = await adaptRes.json();
        if (adaptResult.data) {
          message.success(`排程已调整，影响: ${adaptResult.data.delay_impact_hours}h延迟，¥${adaptResult.data.cost_impact}额外成本`);
          fetchHistory();
        }
      }
    } catch (error) {
      message.error('调整失败');
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    if (!scheduleId) return;
    try {
      const response = await fetch(`/api/v1/mes/adaptive-schedules/${scheduleId}/history`);
      const result = await response.json();
      if (result.data?.history) setHistory(result.data.history);
    } catch (error) {
      console.error('Failed to fetch history:', error);
    }
  };

  const fetchLearnings = async () => {
    if (!scheduleId) return;
    try {
      const response = await fetch(`/api/v1/mes/adaptive-schedules/${scheduleId}/learn`);
      const result = await response.json();
      if (result.data?.recommendations) {
        Modal.info({
          title: '学习建议',
          content: (
            <div>
              {result.data.recommendations.length > 0 ? (
                <ul>
                  {result.data.recommendations.map((r: string, i: number) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              ) : (
                <p>暂无学习建议</p>
              )}
              <p>总调整次数: {result.data.total_adaptations}</p>
              <p>总延迟: {result.data.total_delay_hours}h</p>
              <p>总成本影响: ¥{result.data.total_cost_impact}</p>
            </div>
          ),
        });
      }
    } catch (error) {
      console.error('Failed to fetch learnings:', error);
    }
  };

  const historyColumns = [
    { title: '记录ID', dataIndex: 'record_id', key: 'record_id', width: 120 },
    {
      title: '触发类型',
      key: 'trigger_type',
      width: 120,
      render: (_: any, r: any) => {
        const tt = r.trigger?.trigger_type;
        const config = TRIGGER_TYPE_CONFIG[tt] || { color: 'default', label: tt };
        return <Tag color={config.color}>{config.label}</Tag>;
      },
    },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: (v: string) => <Tag color={v === 'applied' ? 'green' : 'orange'}>{v}</Tag> },
    { title: '延迟(h)', dataIndex: 'delay_impact_hours', key: 'delay', width: 90 },
    { title: '成本(¥)', dataIndex: 'cost_impact', key: 'cost', width: 100 },
    { title: '审批人', dataIndex: 'approved_by', key: 'approved_by', width: 100 },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card title={<><ScheduleOutlined /> 自适应排程管理</>} style={{ marginBottom: 16 }}>
        <Form form={form} layout="inline" onFinish={createSchedule}>
          <Form.Item name="tenant_id" label="租户ID">
            <Input placeholder="t1" style={{ width: 100 }} />
          </Form.Item>
          <Form.Item name="project_id" label="项目ID">
            <Input placeholder="p1" style={{ width: 100 }} />
          </Form.Item>
          <Form.Item name="name" label="排程名称">
            <Input placeholder="自适应排程-001" style={{ width: 160 }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading}>创建排程</Button>
          </Form.Item>
        </Form>
      </Card>

      {schedule && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card>
                <Statistic title="状态" value={schedule.status === 'active' ? '运行中' : schedule.status} valueStyle={{ color: schedule.status === 'active' ? '#3f8600' : '#fa8c16' }} />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic title="准时率" value={schedule.performance_metrics?.on_time_rate * 100 || 0} suffix="%" />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic title="利用率" value={schedule.performance_metrics?.utilization_rate * 100 || 0} suffix="%" />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic title="调整次数" value={schedule.performance_metrics?.adaptation_count || 0} />
              </Card>
            </Col>
          </Row>

          <Card style={{ marginBottom: 16 }}>
            <Form form={triggerForm} layout="inline" onFinish={detectAndAdapt}>
              <Form.Item name="event_type" label="事件类型">
                <Select style={{ width: 140 }}>
                  {Object.entries(TRIGGER_TYPE_CONFIG).map(([key, config]) => (
                    <Select.Option key={key} value={key}>{config.label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
              <Form.Item name="event_data" label="事件数据">
                <Input placeholder='{"affected_operations":["OP-001"]}' style={{ width: 250 }} />
              </Form.Item>
              <Form.Item>
                <Button type="primary" icon={<ThunderboltOutlined />} htmlType="submit" loading={loading}>
                  检测并调整
                </Button>
              </Form.Item>
            </Form>
          </Card>

          <Card>
            <Tabs defaultActiveKey="history">
              <TabPane tab="调整历史" key="history">
                <Space style={{ marginBottom: 16 }}>
                  <Button icon={<SyncOutlined />} onClick={fetchHistory}>刷新历史</Button>
                  <Button icon={<ExperimentOutlined />} onClick={fetchLearnings}>学习建议</Button>
                </Space>
                <Table
                  dataSource={history}
                  columns={historyColumns}
                  rowKey="record_id"
                  size="small"
                  scroll={{ x: 700 }}
                />
              </TabPane>

              <TabPane tab="调整时间线" key="timeline">
                <Timeline>
                  {history.map((record) => (
                    <Timeline.Item
                      key={record.record_id}
                      color={record.status === 'applied' ? 'green' : 'orange'}
                    >
                      <Space>
                        <Tag color={TRIGGER_TYPE_CONFIG[record.trigger?.trigger_type]?.color || 'default'}>
                          {TRIGGER_TYPE_CONFIG[record.trigger?.trigger_type]?.label || record.trigger?.trigger_type}
                        </Tag>
                        <span>延迟: {record.delay_impact_hours}h</span>
                        <span>成本: ¥{record.cost_impact}</span>
                        <Tag color={record.status === 'applied' ? 'green' : 'orange'}>{record.status}</Tag>
                      </Space>
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

export default AdaptiveSchedulingPage;