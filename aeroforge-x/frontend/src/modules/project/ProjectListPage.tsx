import { useState, useEffect } from 'react'
import {
  Card, Typography, Space, Tag, Button, Input, Form, Modal,
  Row, Col, Statistic, Empty, Select, Steps, Table, Descriptions,
  message, Badge, Dropdown, Avatar, List,
} from 'antd'
import {
  RocketOutlined, PlusOutlined, SettingOutlined,
  TeamOutlined, ProjectOutlined, SwapOutlined,
  CheckCircleOutlined, ClockCircleOutlined, PauseCircleOutlined,
  ArchiveOutlined, ExperimentOutlined,
} from '@ant-design/icons'
import apiClient from '../../services/apiClient'
import { useProjectStore } from '../../stores/projectStore'

const { Title, Text } = Typography

const statusConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  planning: { color: 'default', icon: <ClockCircleOutlined />, label: '规划中' },
  active: { color: 'green', icon: <CheckCircleOutlined />, label: '进行中' },
  on_hold: { color: 'orange', icon: <PauseCircleOutlined />, label: '暂停' },
  completed: { color: 'blue', icon: <CheckCircleOutlined />, label: '已完成' },
  archived: { color: 'default', icon: <ArchiveOutlined />, label: '已归档' },
}

const aircraftTypeLabels: Record<string, string> = {
  fixed_wing: '固定翼',
  evtol: 'eVTOL',
  glider: '滑翔机',
  uav: '无人机',
}

interface TemplateInfo {
  id: string
  name: string
  aircraft_type: string
  layout_type: string
  description: string
}

export default function ProjectListPage() {
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [templates, setTemplates] = useState<TemplateInfo[]>([])
  const [createStep, setCreateStep] = useState(0)
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [form] = Form.useForm()
  const { projects, loading, fetchProjects, setCurrentProject } = useProjectStore()
  const tenantId = 'default'

  useEffect(() => {
    fetchProjects(tenantId)
  }, [])

  const handleOpenCreate = async () => {
    setCreateModalOpen(true)
    setCreateStep(0)
    try {
      const resp = await apiClient.get('/projects/templates/list')
      setTemplates(resp.data?.data?.templates ?? [])
    } catch {
      setTemplates([])
    }
  }

  const handleCreate = async () => {
    try {
      const values = await form.validateFields()
      const resp = await apiClient.post('/projects', {
        name: values.name,
        code: values.code,
        tenant_id: tenantId,
        aircraft_type: values.aircraft_type || 'fixed_wing',
        description: values.description || '',
        created_by: 'current-user',
      })
      const projectId = resp.data?.data?.id
      if (selectedTemplate && projectId) {
        await apiClient.post(`/projects/${projectId}/apply-template`, { template_id: selectedTemplate })
      }
      message.success('项目创建成功')
      setCreateModalOpen(false)
      form.resetFields()
      setSelectedTemplate('')
      fetchProjects(tenantId)
    } catch {
      message.error('项目创建失败')
    }
  }

  const handleActivate = async (projectId: string) => {
    try {
      await apiClient.post(`/projects/${projectId}/activate`)
      message.success('项目已激活')
      fetchProjects(tenantId)
    } catch {
      message.error('激活失败')
    }
  }

  const handleArchive = async (projectId: string) => {
    try {
      await apiClient.post(`/projects/${projectId}/archive`)
      message.success('项目已归档')
      fetchProjects(tenantId)
    } catch {
      message.error('归档失败')
    }
  }

  const handleSwitchProject = (projectId: string) => {
    setCurrentProject(projectId)
    message.success('已切换项目')
  }

  const templateGroups = templates.reduce((acc, t) => {
    const type = t.aircraft_type
    if (!acc[type]) acc[type] = []
    acc[type].push(t)
    return acc
  }, {} as Record<string, TemplateInfo[]>)

  return (
    <div>
      <Card
        title={
          <Space>
            <ProjectOutlined />
            <span>项目管理</span>
          </Space>
        }
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleOpenCreate}>
            新建项目
          </Button>
        }
      >
        <Row gutter={[16, 16]}>
          {projects.length > 0 ? projects.map((project) => {
            const cfg = statusConfig[project.status] || statusConfig.planning
            return (
              <Col span={8} key={project.id}>
                <Card
                  hoverable
                  size="small"
                  onClick={() => handleSwitchProject(project.id)}
                  actions={[
                    <SwapOutlined key="switch" onClick={(e) => { e.stopPropagation(); handleSwitchProject(project.id) }} />,
                    <SettingOutlined key="settings" />,
                  ]}
                >
                  <Card.Meta
                    avatar={<Avatar icon={<RocketOutlined />} style={{ backgroundColor: '#1890ff' }} />}
                    title={
                      <Space>
                        <span>{project.name}</span>
                        <Tag color={cfg.color} icon={cfg.icon}>{cfg.label}</Tag>
                      </Space>
                    }
                    description={
                      <div>
                        <Text type="secondary">{project.code}</Text>
                        <br />
                        <Tag>{aircraftTypeLabels[project.aircraft_type] || project.aircraft_type}</Tag>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {project.members?.length || 0} 成员
                        </Text>
                      </div>
                    }
                  />
                </Card>
              </Col>
            )
          }) : (
            <Col span={24}>
              <Empty description="暂无项目，点击"新建项目"开始" />
            </Col>
          )}
        </Row>
      </Card>

      <Modal
        title="新建项目"
        open={createModalOpen}
        onCancel={() => { setCreateModalOpen(false); form.resetFields(); setSelectedTemplate('') }}
        onOk={handleCreate}
        width={700}
        okText="创建"
      >
        <Steps
          current={createStep}
          onChange={setCreateStep}
          items={[
            { title: '基本信息' },
            { title: '选择模板' },
            { title: '确认创建' },
          ]}
          style={{ marginBottom: 24 }}
        />

        {createStep === 0 && (
          <Form form={form} layout="vertical">
            <Form.Item name="name" label="项目名称" rules={[{ required: true }]}>
              <Input placeholder="AAF-001 项目" />
            </Form.Item>
            <Form.Item name="code" label="项目代码" rules={[{ required: true, pattern: /^[a-z0-9_-]+$/ }]}>
              <Input placeholder="aaf-001" />
            </Form.Item>
            <Form.Item name="aircraft_type" label="飞行器类型" initialValue="fixed_wing">
              <Select options={[
                { value: 'fixed_wing', label: '固定翼' },
                { value: 'evtol', label: 'eVTOL' },
                { value: 'glider', label: '滑翔机' },
                { value: 'uav', label: '无人机' },
              ]} />
            </Form.Item>
            <Form.Item name="description" label="描述">
              <Input.TextArea rows={3} />
            </Form.Item>
          </Form>
        )}

        {createStep === 1 && (
          <div>
            <Text type="secondary" style={{ marginBottom: 16, display: 'block' }}>
              选择机型模板（可选，跳过使用默认配置）
            </Text>
            <List
              grid={{ gutter: 12, column: 2 }}
              dataSource={templates}
              renderItem={(template) => (
                <List.Item>
                  <Card
                    size="small"
                    hoverable
                    onClick={() => setSelectedTemplate(template.id)}
                    style={selectedTemplate === template.id ? { border: '2px solid #1890ff' } : {}}
                  >
                    <Card.Meta
                      title={template.name}
                      description={
                        <Text type="secondary" style={{ fontSize: 12 }}>{template.description}</Text>
                      }
                    />
                  </Card>
                </List.Item>
              )}
            />
          </div>
        )}

        {createStep === 2 && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="项目名称">{form.getFieldValue('name') || '-'}</Descriptions.Item>
            <Descriptions.Item label="项目代码">{form.getFieldValue('code') || '-'}</Descriptions.Item>
            <Descriptions.Item label="飞行器类型">
              {aircraftTypeLabels[form.getFieldValue('aircraft_type')] || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="模板">
              {selectedTemplate ? templates.find(t => t.id === selectedTemplate)?.name || '自定义' : '无（默认配置）'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  )
}