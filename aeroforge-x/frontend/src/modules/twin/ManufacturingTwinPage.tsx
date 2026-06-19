import { useState } from 'react'
import {
  Card, Typography, Space, Tag, Table, Button, Input, Form,
  message, Descriptions, Alert, Row, Col, Statistic,
  Empty, Divider, Tooltip,
} from 'antd'
import {
  ToolOutlined, WarningOutlined, CheckCircleOutlined,
  SwapOutlined, BarChartOutlined,
} from '@ant-design/icons'
import apiClient from '../../services/apiClient'

const { Title, Text } = Typography

interface DeviationRecord {
  dimension_name: string
  design_value: number
  actual_value: number
  tolerance: number
  deviation: number
  is_out_of_tolerance: boolean
}

interface DeviationStats {
  total_dimensions: number
  out_of_tolerance: number
  in_tolerance: number
  avg_deviation: number
  max_deviation: number
}

export default function ManufacturingTwinPage() {
  const [searchSn, setSearchSn] = useState('')
  const [snapshot, setSnapshot] = useState<Record<string, unknown> | null>(null)
  const [deviationStats, setDeviationStats] = useState<DeviationStats | null>(null)
  const [comparison, setComparison] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchData = async (sn: string) => {
    if (!sn) return
    setLoading(true)
    try {
      const [snapResp, statsResp, compResp] = await Promise.all([
        apiClient.get(`/twin/manufacturing/${sn}/snapshot`).catch(() => null),
        apiClient.get(`/twin/manufacturing/${sn}/deviation-stats`).catch(() => null),
        apiClient.get(`/twin/manufacturing/${sn}/compare-design`).catch(() => null),
      ])
      setSnapshot(snapResp?.data?.data ?? null)
      setDeviationStats(statsResp?.data?.data?.statistics ?? null)
      setComparison(compResp?.data?.data ?? null)
    } catch {
      message.error('获取制造孪生数据失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSyncMeasurement = async (values: {
    aircraft_serial_number: string
    measurement_data: string
    design_data?: string
    tolerances?: string
  }) => {
    try {
      let measurementData: Record<string, number>
      let designData: Record<string, number> | undefined
      let tolerances: Record<string, number> | undefined

      try {
        measurementData = JSON.parse(values.measurement_data)
      } catch {
        message.error('实测数据必须是有效的JSON格式')
        return
      }

      if (values.design_data) {
        try {
          designData = JSON.parse(values.design_data)
        } catch {
          message.error('设计数据必须是有效的JSON格式')
          return
        }
      }

      if (values.tolerances) {
        try {
          tolerances = JSON.parse(values.tolerances)
        } catch {
          message.error('公差数据必须是有效的JSON格式')
          return
        }
      }

      await apiClient.post('/twin/manufacturing/sync', {
        aircraft_serial_number: values.aircraft_serial_number,
        measurement_data: measurementData,
        design_data: designData,
        tolerances,
      })
      message.success('制造孪生已同步')
      fetchData(values.aircraft_serial_number)
    } catch {
      message.error('同步失败')
    }
  }

  const deviations = (comparison?.deviations as DeviationRecord[]) || []

  const deviationColumns = [
    {
      title: '维度',
      dataIndex: 'dimension_name',
      key: 'dimension_name',
    },
    {
      title: '设计值',
      dataIndex: 'design_value',
      key: 'design_value',
      render: (v: number) => v.toFixed(4),
    },
    {
      title: '实测值',
      dataIndex: 'actual_value',
      key: 'actual_value',
      render: (v: number) => v.toFixed(4),
    },
    {
      title: '公差',
      dataIndex: 'tolerance',
      key: 'tolerance',
      render: (v: number) => `±${v.toFixed(4)}`,
    },
    {
      title: '偏差',
      dataIndex: 'deviation',
      key: 'deviation',
      render: (v: number) => (
        <span style={{ color: v > 0 ? '#f5222d' : '#1890ff' }}>
          {v > 0 ? '+' : ''}{v.toFixed(6)}
        </span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_out_of_tolerance',
      key: 'is_out_of_tolerance',
      render: (oot: boolean) => oot
        ? <Tag color="red" icon={<WarningOutlined />}>超差</Tag>
        : <Tag color="green" icon={<CheckCircleOutlined />}>合格</Tag>,
    },
  ]

  const inTolPercent = deviationStats && deviationStats.total_dimensions > 0
    ? Math.round((deviationStats.in_tolerance / deviationStats.total_dimensions) * 100)
    : 0

  return (
    <div>
      <Card title="制造孪生同步" style={{ marginBottom: 16 }}>
        <Form onFinish={handleSyncMeasurement} layout="inline" style={{ marginBottom: 16 }}>
          <Form.Item name="aircraft_serial_number" rules={[{ required: true }]}>
            <Input placeholder="飞行器SN" style={{ width: 140 }} />
          </Form.Item>
          <Form.Item name="measurement_data" rules={[{ required: true }]}>
            <Input.TextArea
              placeholder='实测: {"wing_span": 10.05}'
              rows={1}
              style={{ width: 200 }}
            />
          </Form.Item>
          <Form.Item name="design_data">
            <Input.TextArea
              placeholder='设计: {"wing_span": 10.0} (可选)'
              rows={1}
              style={{ width: 200 }}
            />
          </Form.Item>
          <Form.Item name="tolerances">
            <Input.TextArea
              placeholder='公差: {"wing_span": 0.1} (可选)'
              rows={1}
              style={{ width: 180 }}
            />
          </Form.Item>
          <Button type="primary" htmlType="submit" icon={<ToolOutlined />}>
            同步实测数据
          </Button>
        </Form>
      </Card>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总维度数"
              value={deviationStats?.total_dimensions ?? 0}
              prefix={<BarChartOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="合格项"
              value={deviationStats?.in_tolerance ?? 0}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="超差项"
              value={deviationStats?.out_of_tolerance ?? 0}
              valueStyle={{ color: '#cf1322' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="合格率"
              value={inTolPercent}
              suffix="%"
              valueStyle={{ color: inTolPercent >= 90 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={
          <Space>
            <SwapOutlined />
            <span>实测尺寸 vs 设计尺寸对比</span>
          </Space>
        }
        extra={
          <Input.Search
            placeholder="查询SN"
            value={searchSn}
            onChange={(e) => setSearchSn(e.target.value)}
            onSearch={fetchData}
            enterButton="查询"
            style={{ width: 250 }}
          />
        }
      >
        {deviations.length > 0 ? (
          <>
            {deviationStats && deviationStats.out_of_tolerance > 0 && (
              <Alert
                type="warning"
                message={`存在 ${deviationStats.out_of_tolerance} 项超差，建议触发设计反馈`}
                showIcon
                style={{ marginBottom: 12 }}
              />
            )}
            <Table
              columns={deviationColumns}
              dataSource={deviations.map((d, i) => ({ ...d, key: i }))}
              pagination={false}
              loading={loading}
              size="small"
              rowClassName={(record) => record.is_out_of_tolerance ? 'row-out-of-tolerance' : ''}
            />
          </>
        ) : (
          <Empty description="请输入飞行器SN查询制造偏差数据" />
        )}
      </Card>
    </div>
  )
}