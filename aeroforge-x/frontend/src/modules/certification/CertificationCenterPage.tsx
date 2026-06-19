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
  Progress,
  Descriptions,
  Alert,
  message,
} from 'antd';
import {
  SafetyCertificateOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  FileProtectOutlined,
  AuditOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { TabPane } = Tabs;

const STATUS_COLORS: Record<string, string> = {
  not_started: 'default',
  in_progress: 'processing',
  compliant: 'success',
  non_compliant: 'error',
  not_applicable: 'default',
};

const VERIFICATION_COLORS: Record<string, string> = {
  compliant: 'green',
  non_compliant: 'red',
  needs_review: 'orange',
};

const AIRWORTHINESS_COLORS: Record<string, string> = {
  airworthy: 'green',
  conditionally_airworthy: 'orange',
  unairworthy: 'red',
};

const CertificationCenterPage: React.FC = () => {
  const { t } = useTranslation();
  const [plan, setPlan] = useState<any>(null);
  const [verificationReports, setVerificationReports] = useState<any[]>([]);
  const [approval, setApproval] = useState<any>(null);
  const [airworthinessRecord, setAirworthinessRecord] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [planForm] = Form.useForm();
  const [approvalForm] = Form.useForm();
  const [aircraftSn, setAircraftSn] = useState('');

  const handleCreatePlan = async (values: any) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/certification/plans', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values),
      });
      const result = await response.json();
      setPlan(result.data);
      message.success('认证计划创建成功');
    } catch {
      message.error('创建失败');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyDesign = async () => {
    if (!plan) return;
    setLoading(true);
    try {
      const response = await fetch('/api/v1/certification/verify/design', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_id: plan.id }),
      });
      const result = await response.json();
      setVerificationReports(prev => [...prev, result.data]);
      message.success('设计符合性验证完成');
    } catch {
      message.error('验证失败');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyManufacturing = async () => {
    if (!plan) return;
    setLoading(true);
    try {
      const response = await fetch('/api/v1/certification/verify/manufacturing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_id: plan.id }),
      });
      const result = await response.json();
      setVerificationReports(prev => [...prev, result.data]);
      message.success('制造符合性验证完成');
    } catch {
      message.error('验证失败');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyTest = async () => {
    if (!plan) return;
    setLoading(true);
    try {
      const response = await fetch('/api/v1/certification/verify/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan_id: plan.id }),
      });
      const result = await response.json();
      setVerificationReports(prev => [...prev, result.data]);
      message.success('试验符合性验证完成');
    } catch {
      message.error('验证失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitApproval = async (values: any) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/certification/approvals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...values, certification_plan_id: plan?.id || 'default' }),
      });
      const result = await response.json();
      setApproval(result.data);
      message.success('审定申请已提交');
    } catch {
      message.error('提交失败');
    } finally {
      setLoading(false);
    }
  };

  const handleIssueCertificate = async () => {
    if (!approval) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/certification/approvals/${approval.id}/issue-certificate`, {
        method: 'POST',
      });
      const result = await response.json();
      setApproval(result.data);
      message.success('证书已颁发');
    } catch {
      message.error('颁发失败');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAirworthinessRecord = async () => {
    if (!aircraftSn) return;
    setLoading(true);
    try {
      const response = await fetch('/api/v1/certification/continuous-airworthiness', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tenant_id: 'default', aircraft_serial_number: aircraftSn }),
      });
      const result = await response.json();
      setAirworthinessRecord(result.data);
      message.success('持续适航记录已创建');
    } catch {
      message.error('创建失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAssessAirworthiness = async () => {
    if (!aircraftSn) return;
    setLoading(true);
    try {
      const response = await fetch(`/api/v1/certification/continuous-airworthiness/${aircraftSn}/assessment`);
      const result = await response.json();
      message.success(`适航状态: ${result.data.overall_status}`);
    } catch {
      message.error('评估失败');
    } finally {
      setLoading(false);
    }
  };

  const complianceColumns = [
    { title: '法规条款', dataIndex: 'regulation_clause', key: 'clause', width: 120 },
    { title: '条款标题', dataIndex: 'clause_title', key: 'title' },
    { title: '符合性方法', dataIndex: 'compliance_method', key: 'moc', width: 100 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (v: string) => <Tag color={STATUS_COLORS[v]}>{v}</Tag>,
    },
    {
      title: '证据数',
      key: 'evidence',
      width: 80,
      render: (_: any, record: any) => record.evidence_refs?.length || 0,
    },
    { title: '责任人', dataIndex: 'responsible_person', key: 'person', width: 100 },
  ];

  const verificationColumns = [
    { title: '条款', dataIndex: 'regulation_clause', key: 'clause', width: 100 },
    { title: '检查描述', dataIndex: 'check_description', key: 'desc' },
    { title: '期望值', dataIndex: 'expected_value', key: 'expected', width: 100 },
    { title: '实际值', dataIndex: 'actual_value', key: 'actual', width: 100 },
    {
      title: '结果',
      dataIndex: 'result',
      key: 'result',
      width: 120,
      render: (v: string) => <Tag color={VERIFICATION_COLORS[v]}>{v}</Tag>,
    },
  ];

  const findingColumns = [
    { title: 'ID', dataIndex: 'finding_id', key: 'id', width: 100, ellipsis: true },
    {
      title: '类型',
      dataIndex: 'finding_type',
      key: 'type',
      width: 100,
      render: (v: string) => <Tag color={v === 'major_finding' ? 'red' : v === 'finding' ? 'orange' : 'blue'}>{v}</Tag>,
    },
    { title: '描述', dataIndex: 'description', key: 'desc' },
    { title: '纠正措施', dataIndex: 'corrective_action', key: 'action' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (v: string) => <Tag color={v === 'closed' ? 'green' : v === 'verified' ? 'blue' : 'orange'}>{v}</Tag>,
    },
  ];

  const adColumns = [
    { title: 'AD编号', dataIndex: 'ad_number', key: 'ad_num', width: 120 },
    { title: '标题', dataIndex: 'ad_title', key: 'ad_title' },
    { title: '截止日期', dataIndex: 'compliance_deadline', key: 'deadline', width: 120 },
    {
      title: '合规状态',
      dataIndex: 'compliance_status',
      key: 'status',
      width: 120,
      render: (v: string) => <Tag color={v === 'compliant' ? 'green' : v === 'overdue' ? 'red' : 'orange'}>{v}</Tag>,
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <h2><SafetyCertificateOutlined /> 航空认证中心</h2>

      <Tabs defaultActiveKey="plan">
        <TabPane tab="认证计划" key="plan">
          <Card title="创建认证计划" style={{ marginBottom: 16 }}>
            <Form form={planForm} layout="inline" onFinish={handleCreatePlan}>
              <Form.Item name="project_id" label="项目ID">
                <Input placeholder="proj-001" />
              </Form.Item>
              <Form.Item name="aircraft_type" label="飞行器型号">
                <Input placeholder="AF-X100" />
              </Form.Item>
              <Form.Item name="certification_standard" label="认证标准">
                <Select style={{ width: 120 }} defaultValue="FAR-25">
                  <Select.Option value="FAR-23">FAR-23</Select.Option>
                  <Select.Option value="FAR-25">FAR-25</Select.Option>
                  <Select.Option value="CCAR-23">CCAR-23</Select.Option>
                  <Select.Option value="CCAR-25">CCAR-25</Select.Option>
                  <Select.Option value="CS-23">CS-23</Select.Option>
                  <Select.Option value="CS-25">CS-25</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item name="certification_authority" label="认证当局">
                <Select style={{ width: 100 }} defaultValue="FAA">
                  <Select.Option value="FAA">FAA</Select.Option>
                  <Select.Option value="EASA">EASA</Select.Option>
                  <Select.Option value="CAAC">CAAC</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} icon={<FileProtectOutlined />}>
                  创建计划
                </Button>
              </Form.Item>
            </Form>
          </Card>

          {plan && (
            <>
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="符合性完成率"
                      value={(plan.compliance_progress?.completion_rate || 0) * 100}
                      precision={1}
                      suffix="%"
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic title="总条款数" value={plan.compliance_progress?.total || 0} />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="逾期项"
                      value={plan.compliance_progress?.overdue_count || 0}
                      valueStyle={{ color: (plan.compliance_progress?.overdue_count || 0) > 0 ? '#cf1322' : '#3f8600' }}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic title="计划状态" value={plan.plan_status} />
                  </Card>
                </Col>
              </Row>

              <Card title="符合性验证项">
                <Table
                  dataSource={plan.compliance_items || []}
                  columns={complianceColumns}
                  rowKey="item_id"
                  pagination={{ pageSize: 10 }}
                />
              </Card>
            </>
          )}
        </TabPane>

        <TabPane tab="符合性验证" key="verification">
          <Card style={{ marginBottom: 16 }}>
            <Space>
              <Button icon={<CheckCircleOutlined />} onClick={handleVerifyDesign} loading={loading}>
                设计符合性验证
              </Button>
              <Button icon={<AuditOutlined />} onClick={handleVerifyManufacturing} loading={loading}>
                制造符合性验证
              </Button>
              <Button icon={<ExclamationCircleOutlined />} onClick={handleVerifyTest} loading={loading}>
                试验符合性验证
              </Button>
            </Space>
          </Card>

          {verificationReports.length > 0 ? (
            verificationReports.map((report, idx) => (
              <Card key={idx} title={`${report.verification_type} 验证报告`} style={{ marginBottom: 16 }}>
                <Row gutter={16} style={{ marginBottom: 12 }}>
                  <Col span={8}>
                    <Statistic title="合规" value={report.compliant_count} valueStyle={{ color: '#3f8600' }} />
                  </Col>
                  <Col span={8}>
                    <Statistic title="不合规" value={report.non_compliant_count} valueStyle={{ color: '#cf1322' }} />
                  </Col>
                  <Col span={8}>
                    <Statistic title="需审查" value={report.needs_review_count} valueStyle={{ color: '#fa8c16' }} />
                  </Col>
                </Row>
                <Table
                  dataSource={report.checks || []}
                  columns={verificationColumns}
                  rowKey="check_id"
                  pagination={false}
                />
              </Card>
            ))
          ) : (
            <Alert message="请先创建认证计划并执行验证" type="info" />
          )}
        </TabPane>

        <TabPane tab="适航审定" key="approval">
          <Card title="提交审定申请" style={{ marginBottom: 16 }}>
            <Form form={approvalForm} layout="inline" onFinish={handleSubmitApproval}>
              <Form.Item name="approval_type" label="审定类型">
                <Select style={{ width: 200 }} defaultValue="Type_Certificate">
                  <Select.Option value="Type_Certificate">型号合格证 (TC)</Select.Option>
                  <Select.Option value="Supplemental_Type_Certificate">补充型号合格证 (STC)</Select.Option>
                  <Select.Option value="Production_Certificate">生产许可证 (PC)</Select.Option>
                  <Select.Option value="Airworthiness_Certificate">适航证 (AC)</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading}>
                  提交申请
                </Button>
              </Form.Item>
            </Form>
          </Card>

          {approval && (
            <>
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={6}>
                  <Card>
                    <Statistic title="审查状态" value={approval.review_status} />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic title="审查发现" value={approval.review_findings?.length || 0} />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="证书编号"
                      value={approval.certificate_number || '未颁发'}
                      valueStyle={{ fontSize: 14 }}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Button
                      type="primary"
                      icon={<SafetyCertificateOutlined />}
                      onClick={handleIssueCertificate}
                      loading={loading}
                      disabled={approval.review_status === 'approved'}
                    >
                      颁发证书
                    </Button>
                  </Card>
                </Col>
              </Row>

              <Card title="审查发现">
                <Table
                  dataSource={approval.review_findings || []}
                  columns={findingColumns}
                  rowKey="finding_id"
                  pagination={false}
                />
              </Card>
            </>
          )}
        </TabPane>

        <TabPane tab="持续适航" key="continuous">
          <Card title="持续适航管理" style={{ marginBottom: 16 }}>
            <Space>
              <Input
                placeholder="飞行器序列号"
                value={aircraftSn}
                onChange={e => setAircraftSn(e.target.value)}
                style={{ width: 200 }}
              />
              <Button type="primary" onClick={handleCreateAirworthinessRecord} loading={loading}>
                创建适航记录
              </Button>
              <Button onClick={handleAssessAirworthiness} loading={loading}>
                评估适航状态
              </Button>
            </Space>
          </Card>

          {airworthinessRecord && (
            <>
              <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="适航状态"
                      value={airworthinessRecord.overall_status}
                      valueStyle={{ color: AIRWORTHINESS_COLORS[airworthinessRecord.overall_status] || '#000' }}
                    />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic title="适航指令" value={airworthinessRecord.summary?.ads_total || 0} />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic title="服务通告" value={airworthinessRecord.summary?.sbs_total || 0} />
                  </Card>
                </Col>
                <Col span={6}>
                  <Card>
                    <Statistic title="重复检查" value={airworthinessRecord.summary?.inspections_total || 0} />
                  </Card>
                </Col>
              </Row>

              <Card title="适航指令合规状态">
                <Table
                  dataSource={airworthinessRecord.airworthiness_directives || []}
                  columns={adColumns}
                  rowKey="ad_number"
                  pagination={false}
                />
              </Card>
            </>
          )}
        </TabPane>
      </Tabs>
    </div>
  );
};

export default CertificationCenterPage;