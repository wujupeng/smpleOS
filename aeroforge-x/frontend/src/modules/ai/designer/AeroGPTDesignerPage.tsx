import React, { useState } from 'react';
import { Card, Input, Button, Space, Typography, Descriptions, Tag, List, Alert, Spin, Steps } from 'antd';
import { RobotOutlined, ThunderboltOutlined, CheckCircleOutlined } from '@ant-design/icons';

const { TextArea } = Input;
const { Title } = Typography;
const API_BASE = '/api/v1';

const AeroGPTDesignerPage: React.FC = () => {
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [proposal, setProposal] = useState<any>(null);
  const [model, setModel] = useState<any>(null);
  const [currentStep, setCurrentStep] = useState(0);

  const generateSpec = async () => {
    setLoading(true);
    setCurrentStep(1);
    try {
      const res = await fetch(`${API_BASE}/ai/designer/generate-spec`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description }),
      });
      const data = await res.json();
      setProposal(data);
      setCurrentStep(2);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const generateModel = async () => {
    if (!proposal) return;
    setLoading(true);
    setCurrentStep(3);
    try {
      const res = await fetch(`${API_BASE}/ai/designer/generate-model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proposal_id: proposal.id }),
      });
      const data = await res.json();
      setModel(data);
      setCurrentStep(4);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const reviewProposal = async (decision: string) => {
    if (!proposal) return;
    try {
      const res = await fetch(`${API_BASE}/ai/proposals/${proposal.id}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, reason: decision === 'reject' ? 'Needs revision' : '' }),
      });
      const data = await res.json();
      setProposal(data);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}><RobotOutlined /> AeroGPT Designer</Title>

      <Steps current={currentStep} items={[
        { title: 'Input' },
        { title: 'Generating Spec' },
        { title: 'Review Spec' },
        { title: 'Generating Model' },
        { title: 'Complete' },
      ]} style={{ marginBottom: 24 }} />

      <Card title="Natural Language Input" style={{ marginBottom: 16 }}>
        <TextArea
          rows={4}
          placeholder="Describe your aircraft design requirements in natural language... e.g., 'Design a narrow-body aircraft with wingspan of 35.8m, fuselage length of 40m, MTOW of 78000kg, cruise speed of 450kts'"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <Button type="primary" icon={<ThunderboltOutlined />} onClick={generateSpec} loading={loading} style={{ marginTop: 12 }}>
          Generate Aircraft Spec
        </Button>
      </Card>

      {proposal && (
        <>
          <Card title="Generated Specification" style={{ marginBottom: 16 }}>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="Status">
                <Tag color={proposal.status === 'pending_review' ? 'orange' : proposal.status === 'confirmed' ? 'green' : 'red'}>
                  {proposal.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Feasibility Score">
                <Tag color={proposal.feasibility_report?.overall_score >= 0.8 ? 'green' : proposal.feasibility_report?.overall_score >= 0.5 ? 'orange' : 'red'}>
                  {(proposal.feasibility_report?.overall_score * 100).toFixed(0)}%
                </Tag>
              </Descriptions.Item>
            </Descriptions>

            {proposal.feasibility_report?.summary && (
              <Alert
                message={proposal.feasibility_report.summary}
                type={proposal.feasibility_report.is_feasible ? 'success' : 'warning'}
                style={{ marginTop: 12 }}
                showIcon
              />
            )}

            {proposal.parsed_spec && Object.keys(proposal.parsed_spec).length > 0 && (
              <Descriptions bordered column={2} style={{ marginTop: 12 }} title="Parsed Parameters">
                {Object.entries(proposal.parsed_spec).map(([key, value]) => (
                  <Descriptions.Item key={key} label={key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}>
                    {String(value)}
                  </Descriptions.Item>
                ))}
              </Descriptions>
            )}

            {proposal.clarification_questions?.length > 0 && (
              <Card type="inner" title="Clarification Questions" style={{ marginTop: 12 }}>
                <List
                  dataSource={proposal.clarification_questions}
                  renderItem={(q: string) => <List.Item>{q}</List.Item>}
                />
              </Card>
            )}

            <Space style={{ marginTop: 16 }}>
              <Button type="primary" icon={<CheckCircleOutlined />} onClick={() => reviewProposal('confirm')}>
                Confirm Proposal
              </Button>
              <Button danger onClick={() => reviewProposal('reject')}>Reject</Button>
              <Button type="default" onClick={generateModel} disabled={proposal.status === 'rejected'}>
                Generate 3D Model
              </Button>
            </Space>
          </Card>

          {model && (
            <Card title="Generated 3D Model">
              <Descriptions bordered column={2}>
                <Descriptions.Item label="Model ID">{model.model_id}</Descriptions.Item>
                <Descriptions.Item label="Type">{model.model_type}</Descriptions.Item>
              </Descriptions>
              <Card type="inner" title="Geometry" style={{ marginTop: 8 }}>
                <Descriptions bordered column={2} size="small">
                  {Object.entries(model.geometry || {}).map(([k, v]) => (
                    <Descriptions.Item key={k} label={k.replace(/_/g, ' ')}>{String(v)}</Descriptions.Item>
                  ))}
                </Descriptions>
              </Card>
              <Card type="inner" title="Performance" style={{ marginTop: 8 }}>
                <Descriptions bordered column={2} size="small">
                  {Object.entries(model.performance || {}).map(([k, v]) => (
                    <Descriptions.Item key={k} label={k.replace(/_/g, ' ')}>{String(v)}</Descriptions.Item>
                  ))}
                </Descriptions>
              </Card>
            </Card>
          )}
        </>
      )}
    </div>
  );
};

export default AeroGPTDesignerPage;