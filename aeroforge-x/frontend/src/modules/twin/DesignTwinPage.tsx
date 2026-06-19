import { useState } from 'react'
import {
  Card, Typography, Space, Tag, Table, Button, Input, Form,
  message, Descriptions, Timeline, Alert, Row, Col, Statistic,
  Empty, Divider,
} from 'antd'
import {
  RocketOutlined, HistoryOutlined, CompareOutlined,
  CheckCircleOutlined, WarningOutlined,
} from '@ant-design/icons'
import apiClient from '../../services/apiClient'

const { Title, Text } = Typography

interface ParamChangeRecord {
  param_name: string
  old_value: unknown
  new_value: unknown
  reason: string
  changed_by: string
  changed_at: string
}

export default function DesignTwinPage() {
  const [searchSn, setSearchSn] = useState('')
  const [snapshot, setSnapshot] = useState<Record<string, unknown> | null>(null)
  const [paramHistory, setParamHistory] = useState<ParamChangeRecord[]>([])
  const [loading, setLoading] = useState(false)

  const fetchSnapshot = async (sn: string) => {
    if (!sn) return
    setLoading(true)
    try {
      const resp = await apiClient.get(`/twin/design/${sn}/snapshot`)
      setSnapshot(resp.data?.data ?? null)
    } catch {
      setSnapshot(null)
    }
    try {
      const resp = await apiClient.get(`/twin/design/${sn}/param-history`)
      setParamHistory(resp.data?.data?.param_history ?? [])
    } catch {
      setParamHistory([])
    } finally {
      setLoading(false)
    }
  }

  const handleSyncDesign = async (values: { aircraft_serial_number: string; design_params: string }) => {
    try {
      let params: Record<string, unknown>
      try {
        params = JSON.parse(values.design_params)
      } catch {
        message.error('设计参数必须是有效的JSON格式')
        return
      }
      await apiClient.post('/twin/design/sync', {
        aircraft_serial_number: values.aircraft_serial_number,
        design_params: params,
      })
      message.success('设计孪生已同步')
      fetchSnapshot(values.aircraft_serial_number)
    } catch {
      message.error('同步失败')
    }
  }

  const timelineItems = paramHistory.map((record, idx) => ({
    key: idx,
    color: 'blue' as const,
    children: (
      <div>
        <Text strong>{record.param_name}</Text>
        <br />
        <Text type="secondary">
          {String(record.old_value)} → {String(record.new_value)}
        </Text>
        <br />
        <Text type="secondary" style={{ fontSize: 12 }}>
          {record.changed_by} | {record.reason} | {record.changed_at ? new Date(record.changed_at).toLocaleString() : '-'}
        </Text>
      </div>
    ),
  }))

  const currentParams = snapshot?.snapshot as Record<string, unknown> | undefined

  return (
    <div>
      <Card title="设计孪生同步" style={{ marginBottom: 16 }}>
        <Form onFinish={handleSyncDesign} layout="inline" style={{ marginBottom: 16 }}>
          <Form.Item name="aircraft_serial_number" rules={[{ required: true }]}>
            <Input placeholder="飞行器SN" style={{ width: 160 }} />
          </Form.Item>
          <Form.Item name="design_params" rules={[{ required: true }]}>
            <Input.TextArea
              placeholder='{"wing_span": 10.0, "fuselage_length": 20.0}'
              rows={1}
              style={{ width: 400 }}
            />
          </Form.Item>
          <Button type="primary" htmlType="submit" icon={<RocketOutlined />}>
            同步设计参数
          </Button>
        </Form>
      </Card>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card
            title={
              <Space>
                <RocketOutlined />
                <span>当前设计参数</span>
              </Space>
            }
            extra={
              <Space>
                <Input.Search
                  placeholder="查询SN"
                  value={searchSn}
                  onChange={(e) => setSearchSn(e.target.value)}
                  onSearch={fetchSnapshot}
                  enterButton="查询"
                  style={{ width: 250 }}
                />
              </Space>
            }
          >
            {snapshot ? (
              <>
                <Descriptions column={2} size="small" bordered>
                  <Descriptions.Item label="飞行器SN">{snapshot.aircraft_sn as string}</Descriptions.Item>
                  <Descriptions.Item label="数据版本">v{snapshot.data_version as number}</Descriptions.Item>
                </Descriptions>
                <Divider style={{ margin: '12px 0' }} />
                {currentParams && Object.keys(currentParams).length > 0 ? (
                  <Table
                    dataSource={Object.entries(currentParams).map(([key, val]) => ({
                      key,
                      param_name: key,
                      value: String(val),
                    }))}
                    columns={[
                      { title: '参数名', dataIndex: 'param_name', key: 'param_name' },
                      { title: '当前值', dataIndex: 'value', key: 'value' },
                    ]}
                    pagination={false}
                    size="small"
                  />
                ) : (
                  <Empty description="暂无设计参数" />
                )}
              </>
            ) : (
              <Empty description="请输入飞行器SN查询设计快照" />
            )}
          </Card>
        </Col>

        <Col span={12}>
          <Card
            title={
              <Space>
                <HistoryOutlined />
                <span>参数变更历史</span>
              </Space>
            }
          >
            {paramHistory.length > 0 ? (
              <Timeline items={timelineItems} />
            ) : (
              <Empty description="暂无参数变更记录" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}