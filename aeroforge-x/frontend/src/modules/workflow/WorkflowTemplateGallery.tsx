import React, { useEffect, useState } from 'react';
import { Card, Table, Tag, Button, Space, Select, Input } from 'antd';
import { useNavigate } from 'react-router-dom';
import { workflowApi } from '../../api/workflowApi';

const WorkflowTemplateGallery: React.FC = () => {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    setLoading(true);
    try {
      const data = await workflowApi.listTemplates();
      setTemplates(data || []);
    } catch (error) {
      console.error('Failed to fetch templates:', error);
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    { title: 'Template Name', dataIndex: 'name', key: 'name' },
    { title: 'Nodes', key: 'nodes', render: (_: any, r: any) => (r.nodes || []).length },
    { title: 'Trigger Event', dataIndex: 'trigger_event', key: 'trigger_event', render: (t: string) => t ? <Tag color="blue">{t}</Tag> : '-' },
    {
      title: 'Action', key: 'action', render: (_: any, r: any) => (
        <Button type="link" onClick={() => navigate(`/workflow/definitions/new?template=${r.name}`)}>Use Template</Button>
      ),
    },
  ];

  return (
    <Card title="Workflow Template Gallery">
      <Table dataSource={templates} columns={columns} rowKey="name" loading={loading} pagination={false} />
    </Card>
  );
};

export default WorkflowTemplateGallery;