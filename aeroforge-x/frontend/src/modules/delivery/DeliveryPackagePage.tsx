import React, { useState } from 'react';
import {
  Card,
  Table,
  Tabs,
  Tag,
  Button,
  Form,
  Select,
  Space,
  Progress,
  Statistic,
  Row,
  Col,
  Tree,
  Alert,
  List,
  Descriptions,
  Modal,
} from 'antd';
import {
  FileZipOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DownloadOutlined,
  FileSearchOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';

const { TabPane } = Tabs;

interface DeliveryDocument {
  doc_id: string;
  doc_type: string;
  name: string;
  version: string;
  status: string;
  pages: number;
  required: boolean;
  signatures: { signer: string; status: string }[];
}

interface DeliveryPackage {
  id: string;
  aircraft_model: string;
  package_type: string;
  documents: DeliveryDocument[];
  completeness_score: number;
  missing_items: { doc_type: string; reason: string; suggestion: string }[];
  status: string;
}

interface ValidationResult {
  completeness_score: number;
  total_required_types: number;
  covered_types: number;
  missing_items: { doc_type: string; reason: string; suggestion: string }[];
  is_complete: boolean;
}

interface PackageIndex {
  package_id: string;
  total_documents: number;
  documents_by_type: Record<string, DeliveryDocument[]>;
  signature_tracking: { document: string; signer: string; status: string }[];
  completeness_score: number;
}

const DOC_TYPE_LABELS: Record<string, string> = {
  aircraft_spec: '飞行器规格',
  design_review_report: '设计评审报告',
  cfd_report: 'CFD分析报告',
  fea_report: 'FEA分析报告',
  ebom: '工程BOM',
  mbom: '制造BOM',
  bom_conformance_report: 'BOM一致性报告',
  process_route: '工艺路线',
  work_order_records: '工单记录',
  manufacturing_deviation_report: '制造偏差报告',
  iqc_records: 'IQC记录',
  ipqc_records: 'IPQC记录',
  fqc_records: 'FQC记录',
  oqc_records: 'OQC记录',
  capa_records: 'CAPA记录',
  spc_report: 'SPC报告',
  traceability_report: '追溯报告',
  flight_test_plan: '试飞方案',
  compliance_report: '合规性报告',
  airworthiness_checklist: '适航检查单',
};

const DOC_TYPE_CATEGORY: Record<string, string> = {
  aircraft_spec: '设计文档',
  design_review_report: '设计文档',
  cfd_report: 'CAE报告',
  fea_report: 'CAE报告',
  ebom: 'BOM文档',
  mbom: 'BOM文档',
  bom_conformance_report: 'BOM文档',
  process_route: '制造文档',
  work_order_records: '制造文档',
  manufacturing_deviation_report: '制造文档',
  iqc_records: '质量文档',
  ipqc_records: '质量文档',
  fqc_records: '质量文档',
  oqc_records: '质量文档',
  capa_records: '质量文档',
  spc_report: '质量文档',
  traceability_report: '追溯文档',
  flight_test_plan: '试飞文档',
  compliance_report: '合规文档',
  airworthiness_checklist: '合规文档',
};

const STATUS_COLORS: Record<string, string> = {
  approved: 'green',
  final: 'green',
  pending: 'orange',
  draft: 'default',
  rejected: 'red',
};

const DeliveryPackagePage: React.FC = () => {
  const { t } = useTranslation();
  const [pkg, setPkg] = useState<DeliveryPackage | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [index, setIndex] = useState<PackageIndex | null>(null);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const generatePackage = async (values: any) => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/delivery/package/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...values, available_documents: [] }),
      });
      const result = await response.json();
      if (result.data) setPkg(result.data);
    } catch (error) {
      console.error('Failed to generate delivery package:', error);
    } finally {
      setLoading(false);
    }
  };

  const validatePackage = async () => {
    if (!pkg) return;
    try {
      const response = await fetch(`/api/v1/delivery/package/${pkg.id}/validate`);
      const result = await response.json();
      if (result.data) setValidation(result.data);
    } catch (error) {
      console.error('Failed to validate package:', error);
    }
  };

  const fetchIndex = async () => {
    if (!pkg) return;
    try {
      const response = await fetch(`/api/v1/delivery/package/${pkg.id}/index`);
      const result = await response.json();
      if (result.data) setIndex(result.data);
    } catch (error) {
      console.error('Failed to fetch index:', error);
    }
  };

  const buildDocumentTree = () => {
    if (!pkg) return [];

    const categoryMap: Record<string, DeliveryDocument[]> = {};
    pkg.documents.forEach((doc) => {
      const category = DOC_TYPE_CATEGORY[doc.doc_type] || '其他';
      if (!categoryMap[category]) categoryMap[category] = [];
      categoryMap[category].push(doc);
    });

    return Object.entries(categoryMap).map(([category, docs]) => ({
      title: `${category} (${docs.length})`,
      key: category,
      children: docs.map((doc) => ({
        title: (
          <Space>
            <span>{doc.name}</span>
            <Tag color={STATUS_COLORS[doc.status] || 'default'}>{doc.status}</Tag>
            <span style={{ color: '#999' }}>v{doc.version}</span>
            {doc.pages > 0 && <span style={{ color: '#999' }}>{doc.pages}页</span>}
          </Space>
        ),
        key: doc.doc_id,
        isLeaf: true,
      })),
    }));
  };

  const docColumns = [
    { title: '文档名称', dataIndex: 'name', key: 'name', width: 200 },
    {
      title: '类型',
      dataIndex: 'doc_type',
      key: 'doc_type',
      width: 150,
      render: (v: string) => DOC_TYPE_LABELS[v] || v,
    },
    { title: '版本', dataIndex: 'version', key: 'version', width: 80 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (v: string) => <Tag color={STATUS_COLORS[v] || 'default'}>{v}</Tag>,
    },
    { title: '页数', dataIndex: 'pages', key: 'pages', width: 80 },
    {
      title: '必需',
      dataIndex: 'required',
      key: 'required',
      width: 80,
      render: (v: boolean) => v ? <Tag color="red">必需</Tag> : <Tag>可选</Tag>,
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card title={<><FileZipOutlined /> 交付包管理</>} style={{ marginBottom: 16 }}>
        <Form form={form} layout="inline" onFinish={generatePackage}>
          <Form.Item name="aircraft_model" label="机型">
            <Select style={{ width: 160 }} placeholder="选择机型">
              <Select.Option value="AF-X100">AF-X100</Select.Option>
              <Select.Option value="AF-X200">AF-X200</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="package_type" label="类型">
            <Select style={{ width: 120 }} defaultValue="full">
              <Select.Option value="full">完整交付包</Select.Option>
              <Select.Option value="minimal">最小交付包</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<FileZipOutlined />} loading={loading}>
              生成交付包
            </Button>
          </Form.Item>
        </Form>
      </Card>

      {pkg && (
        <>
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card>
                <Statistic title="文档总数" value={pkg.documents.length} suffix="份" />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="完整性评分"
                  value={pkg.completeness_score}
                  suffix="%"
                  valueStyle={{ color: pkg.completeness_score >= 80 ? '#3f8600' : '#cf1322' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="缺失项"
                  value={pkg.missing_items.length}
                  suffix="项"
                  valueStyle={{ color: pkg.missing_items.length === 0 ? '#3f8600' : '#cf1322' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Button icon={<FileSearchOutlined />} onClick={validatePackage} block>校验完整性</Button>
                  <Button icon={<DownloadOutlined />} type="primary" block>下载交付包</Button>
                </Space>
              </Card>
            </Col>
          </Row>

          {validation && !validation.is_complete && (
            <Alert
              type="error"
              message={`交付包不完整，缺失 ${validation.missing_items.length} 项`}
              showIcon
              icon={<CloseCircleOutlined />}
              style={{ marginBottom: 16 }}
            />
          )}

          {validation && validation.is_complete && (
            <Alert
              type="success"
              message="交付包完整，所有必需文档齐全"
              showIcon
              icon={<CheckCircleOutlined />}
              style={{ marginBottom: 16 }}
            />
          )}

          <Card>
            <Tabs defaultActiveKey="documents">
              <TabPane tab="文档清单" key="documents">
                <Row gutter={16}>
                  <Col span={12}>
                    <Card title="文档树" size="small">
                      <Tree treeData={buildDocumentTree()} defaultExpandAll />
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Table
                      dataSource={pkg.documents}
                      columns={docColumns}
                      rowKey="doc_id"
                      size="small"
                      pagination={false}
                      scroll={{ y: 500 }}
                    />
                  </Col>
                </Row>
              </TabPane>

              <TabPane tab="完整性校验" key="validation">
                {validation ? (
                  <div>
                    <Progress
                      percent={validation.completeness_score}
                      status={validation.is_complete ? 'success' : 'exception'}
                      style={{ marginBottom: 16 }}
                    />
                    {validation.missing_items.length > 0 && (
                      <List
                        header="缺失项"
                        dataSource={validation.missing_items}
                        renderItem={(item) => (
                          <List.Item>
                            <List.Item.Meta
                              title={<Tag color="red">{item.doc_type}</Tag>}
                              description={`${item.reason} | 建议: ${item.suggestion}`}
                            />
                          </List.Item>
                        )}
                      />
                    )}
                  </div>
                ) : (
                  <Card>
                    <Button type="primary" onClick={validatePackage} icon={<SafetyCertificateOutlined />}>
                      执行完整性校验
                    </Button>
                  </Card>
                )}
              </TabPane>

              <TabPane tab="签名追踪" key="signatures">
                {index ? (
                  <Table
                    dataSource={index.signature_tracking}
                    columns={[
                      { title: '文档', dataIndex: 'document', key: 'document' },
                      { title: '签名人', dataIndex: 'signer', key: 'signer' },
                      {
                        title: '状态',
                        dataIndex: 'status',
                        key: 'status',
                        render: (v: string) => (
                          <Tag color={v === 'signed' ? 'green' : 'orange'}>{v === 'signed' ? '已签' : '待签'}</Tag>
                        ),
                      },
                    ]}
                    rowKey={(r) => `${r.document}-${r.signer}`}
                    size="small"
                  />
                ) : (
                  <Card>
                    <Button type="primary" onClick={fetchIndex}>加载签名状态</Button>
                  </Card>
                )}
              </TabPane>
            </Tabs>
          </Card>
        </>
      )}
    </div>
  );
};

export default DeliveryPackagePage;