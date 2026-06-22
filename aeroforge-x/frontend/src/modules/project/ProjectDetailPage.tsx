import { useState, useEffect } from 'react'
import {
  Card, Typography, Space, Tag, Button, Table, Descriptions,
  message, Tabs, Form, Input, Select, Row, Col, Statistic,
  Empty, Modal,
} from 'antd'
import {
  RocketOutlined, TeamOutlined, SettingOutlined,
  CheckCircleOutlined, PauseCircleOutlined, InboxOutlined,
  PlusOutlined, DeleteOutlined,
} from '@ant-design/icons'
import { useParams } from 'react-router-dom'
import apiClient from '../../services/apiClient'

const { Title, Text } = Typography

interface ProjectInfo {
  id: string
  name: string
  code: string
  description: string
  aircraft_type: string
  status: string
  settings: Record<string, unknown>
  members: Array<{ user_id: string; role: string; joined_at: string }>
  created_by: string
  created_at: string
}

const aircraftTypeLabels: Record<string, string> = {
  fixed_wing: '固定翼',
  evtol: 'eVTOL',
  glider: '滑翔机',
  uav: '无人机',
}

const statusLabels: Record<string, { color: string; label: string }> = {
  planning: { color: 'default', label: '规划中' },
  active: { color: 'green', label: '进行中' },
  on_hold: { color: 'orange', label: '暂停' },
  completed: { color: 'blue', label: '已完成' },
  archived: { color: 'default', label: '已归档' },
}

const roleLabels: Record<string, { label: string; color: string }> = {
  owner: { label: '负责人', color: 'red' },
  lead: { label: '主管', color: 'orange' },
  member: { label: '成员', color: 'blue' },
  observer: { label: '观察者', color: 'default' },
}

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [project, setProject] = useState<ProjectInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [addMemberOpen, setAddMemberOpen] = useState(false)
  const [memberForm] = Form.useForm()

  const fetchProject = async () => {
    if (!projectId) return
    setLoading(true)
    try {
      const resp = await apiClient.get(`/projects/${projectId}`)
      setProject(resp.data?.data ?? null)
    } catch {
      message.error('获取项目信息失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProject()
  }, [projectId])

  const handleAddMember = async (values: { user_id: string; role: string }) => {
    if (!projectId) return
    try {
      await apiClient.post(`/projects/${projectId}/members`, values)
      message.success('成员已添加')
      setAddMemberOpen(false)
      memberForm.resetFields()
      fetchProject()
    } catch {
      message.error('添加成员失败')
    }
  }

  const handleRemoveMember = async (userId: string) => {
    if (!projectId) return
    try {
      await apiClient.delete(`/projects/${projectId}/members/${userId}`)
      message.success('成员已移除')
      fetchProject()
    } catch {
      message.error('移除成员失败')
    }
  }

  const handleActivate = async () => {
    if (!projectId) return
    try {
      await apiClient.post(`/projects/${projectId}/activate`)
      message.success('项目已激活')
      fetchProject()
    } catch {
      message.error('激活失败')
    }
  }

  const handleArchive = async () => {
    if (!projectId) return
    try {
      await apiClient.post(`/projects/${projectId}/archive`)
      message.success('项目已归档')
      fetchProject()
    } catch {
      message.error('归档失败')
    }
  }

  const memberColumns = [
    { title: '用户ID', dataIndex: 'user_id', key: 'user_id' },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => {
        const cfg = roleLabels[role] || { label: role, color: 'default' }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: '加入时间',
      dataIndex: 'joined_at',
      key: 'joined_at',
      render: (t: string) => t ? new Date(t).toLocaleString() : '-',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: { user_id: string; role: string }) =>
        record.role !== 'owner' ? (
          <Button size="small" danger icon={<DeleteOutlined />} onClick={() => handleRemoveMember(record.user_id)}>
            移除
          </Button>
        ) : null,
    },
  ]

  if (!project) {
    return <Card loading={loading}><Empty description="项目不存在" /></Card>
  }

  const statusCfg = statusLabels[project.status] || statusLabels.planning

  return (
    <div>
      <Card>
        <Row gutter={16}>
          <Col span={6}>
            <Statistic title="项目名称" value={project.name} />
          </Col>
          <Col span={6}>
            <Statistic title="飞行器类型" value={aircraftTypeLabels[project.aircraft_type] || project.aircraft_type} />
          </Col>
          <Col span={6}>
            <Statistic
              title="状态"
              value={statusCfg.label}
              valueStyle={{ color: statusCfg.color === 'green' ? '#3f8600' : undefined }}
            />
          </Col>
          <Col span={6}>
            <Statistic title="成员数" value={project.members?.length || 0} suffix="人" />
          </Col>
        </Row>
      </Card>

      <Tabs
        defaultActiveKey="overview"
        style={{ marginTop: 16 }}
        items={[
          {
            key: 'overview',
            label: '项目概览',
            children: (
              <Card>
                <Descriptions bordered column={2} size="small">
                  <Descriptions.Item label="项目ID">{project.id}</Descriptions.Item>
                  <Descriptions.Item label="项目代码">{project.code}</Descriptions.Item>
                  <Descriptions.Item label="描述" span={2}>{project.description || '-'}</Descriptions.Item>
                  <Descriptions.Item label="创建者">{project.created_by || '-'}</Descriptions.Item>
                  <Descriptions.Item label="创建时间">{project.created_at ? new Date(project.created_at).toLocaleString() : '-'}</Descriptions.Item>
                  <Descriptions.Item label="设计规则集">{(project.settings as Record<string, unknown>)?.design_rule_set as string || 'default'}</Descriptions.Item>
                  <Descriptions.Item label="设计裕度">{(project.settings as Record<string, unknown>)?.design_margin as string || '1.5'}</Descriptions.Item>
                </Descriptions>
                <Space style={{ marginTop: 16 }}>
                  {project.status === 'planning' && (
                    <Button type="primary" icon={<CheckCircleOutlined />} onClick={handleActivate}>激活项目</Button>
                  )}
                  {project.status === 'active' && (
                    <Button icon={<ArchiveOutlined />} onClick={handleArchive}>归档项目</Button>
                  )}
                </Space>
              </Card>
            ),
          },
          {
            key: 'members',
            label: '成员管理',
            children: (
              <Card
                extra={
                  <Button icon={<PlusOutlined />} onClick={() => setAddMemberOpen(true)}>
                    添加成员
                  </Button>
                }
              >
                <Table
                  columns={memberColumns}
                  dataSource={project.members?.map((m, i) => ({ ...m, key: m.user_id || i })) || []}
                  size="small"
                  pagination={false}
                />
              </Card>
            ),
          },
          {
            key: 'settings',
            label: '项目设置',
            children: (
              <Card>
                <Descriptions bordered column={1} size="small">
                  <Descriptions.Item label="设计规则集">{(project.settings as Record<string, unknown>)?.design_rule_set as string || 'default'}</Descriptions.Item>
                  <Descriptions.Item label="材料范围">{JSON.stringify((project.settings as Record<string, unknown>)?.material_scope || [])}</Descriptions.Item>
                  <Descriptions.Item label="认证标准">{JSON.stringify((project.settings as Record<string, unknown>)?.certification_standards || [])}</Descriptions.Item>
                  <Descriptions.Item label="设计裕度">{(project.settings as Record<string, unknown>)?.design_margin as string || '1.5'}</Descriptions.Item>
                </Descriptions>
              </Card>
            ),
          },
        ]}
      />

      <Modal
        title="添加项目成员"
        open={addMemberOpen}
        onCancel={() => { setAddMemberOpen(false); memberForm.resetFields() }}
        onOk={() => memberForm.submit()}
      >
        <Form form={memberForm} onFinish={handleAddMember} layout="vertical">
          <Form.Item name="user_id" label="用户ID" rules={[{ required: true }]}>
            <Input placeholder="user-001" />
          </Form.Item>
          <Form.Item name="role" label="角色" initialValue="member">
            <Select options={[
              { value: 'lead', label: '主管' },
              { value: 'member', label: '成员' },
              { value: 'observer', label: '观察者' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}