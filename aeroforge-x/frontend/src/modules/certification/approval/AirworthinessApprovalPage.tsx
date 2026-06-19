import React, { useState } from 'react';
import { Card, Button, Input, Space, Typography, Descriptions, Tag, Steps } from 'antd';
import { AuditOutlined } from '@ant-design/icons';

const { Title } = Typography;
const API_BASE = '/api/v1';

const AirworthinessApprovalPage: React.FC = () => {
  const [planId, setPlanId] = useState('');
  const [approval, setApproval] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const submitApplication = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/certification/approvals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ certification_plan_id: planId, approval_type: 'type_certificate', submitted_by: 'current_user' }),
      });
      const data = await res.json();
      setApproval(data);
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const refreshStatus = async () => {
    if (!approval) return;
    try {
      const res = await fetch(`${API_BASE}/certification/approvals/${approval.approval_id}`);
      const data = await res.json();
      setApproval({ ...approval, review_status: data.review_status, findings_count: data.findings_count });
    } catch (e) { console.error(e); }
  };

  const statusSteps = ['submitted', 'under_review', 'findings_issued', 'approved'];
  const currentStep = approval ? statusSteps.indexOf(approval.review_status) : -1;

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}><AuditOutlined /> Airworthiness Approval</Title>
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Input placeholder="Certification Plan ID" value={planId} onChange={(e) => setPlanId(e.target.value)} style={{ width: 250 }} />
          <Button type="primary" onClick={submitApplication} loading={loading}>Submit Approval Application</Button>
          {approval && <Button onClick={refreshStatus}>Refresh Status</Button>}
        </Space>
      </Card>
      {approval && (
        <>
          <Steps current={currentStep} items={[
            { title: 'Submitted' },
            { title: 'Under Review' },
            { title: 'Findings Issued' },
            { title: 'Approved' },
          ]} style={{ marginBottom: 16 }} />
          <Card title="Approval Details">
            <Descriptions bordered column={2} size="small">
              <Descriptions.Item label="Approval ID">{approval.approval_id}</Descriptions.Item>
              <Descriptions.Item label="Type">{approval.approval_type}</Descriptions.Item>
              <Descriptions.Item label="Status">
                <Tag color={approval.review_status === 'approved' ? 'green' : approval.review_status === 'rejected' ? 'red' : 'blue'}>
                  {approval.review_status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Certificate">{approval.certificate_number || 'Pending'}</Descriptions.Item>
              <Descriptions.Item label="Findings">{approval.review_findings?.length || 0}</Descriptions.Item>
              <Descriptions.Item label="Conditions">{approval.conditions?.length || 0}</Descriptions.Item>
            </Descriptions>
          </Card>
        </>
      )}
    </div>
  );
};

export default AirworthinessApprovalPage;