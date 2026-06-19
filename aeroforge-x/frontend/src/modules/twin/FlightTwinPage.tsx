import { useState } from 'react'
import {
  Card, Typography, Space, Tag, Table, Button, Input, Form,
  message, Descriptions, Row, Col, Statistic, Empty, Divider,
  Alert, Progress, Select, Tooltip,
} from 'antd'
import {
  ExperimentOutlined, ThunderboltOutlined, AlertOutlined,
  CheckCircleOutlined, WarningOutlined, LineChartOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons'
import apiClient from '../../services/apiClient'

const { Title, Text } = Typography

interface HealthAssessment {
  component_id: string
  component_name: string
  design_load: number
  actual_load: number
  load_ratio: number
  fatigue_damage_cumulative: number
  health_status: string
  remaining_life_estimate_fh: number
}

interface AnomalyEvent {
  anomaly_id: string
  aircraft_sn: string
  sensor_id: string
  metric_name: string
  actual_value: number
  expected_range: [number, number]
  anomaly_type: string
  severity: string
  detected_at: string
}

interface LoadTrendResult {
  aircraft_sn: string
  metric_name: string
  trend: string
  change_ratio: number
  first_half_avg: number
  second_half_avg: number
  data_points: number
}

const healthStatusConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  normal: { color: 'green', icon: <CheckCircleOutlined />, label: '正常' },
  warning: { color: 'orange', icon: <WarningOutlined />, label: '警告' },
  critical: { color: 'red', icon: <AlertOutlined />, label: '危险' },
}

const trendConfig: Record<string, { color: string; label: string }> = {
  increasing: { color: '#cf1322', label: '上升趋势' },
  stable: { color: '#3f8600', label: '稳定' },
  decreasing: { color: '#1890ff', label: '下降趋势' },
  unknown: { color: '#999', label: '未知' },
}

export default function FlightTwinPage() {
  const [searchSn, setSearchSn] = useState('')
  const [healthData, setHealthData] = useState<HealthAssessment[]>([])
  const [anomalies, setAnomalies] = useState<AnomalyEvent[]>([])
  const [loadTrend, setLoadTrend] = useState<LoadTrendResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [selectedMetric, setSelectedMetric] = useState('wing_lift')

  const fetchHealthData = async (sn: string) => {
    if (!sn) return
    setLoading(true)
    try {
      const [healthResp, anomalyResp, trendResp] = await Promise.all([
        apiClient.get(`/twin/flight/${sn}/health`),
        apiClient.post('/twin/flight/detect-anomaly', { aircraft_serial_number: sn, sensor_data: {} }),
        apiClient.get(`/twin/flight/${sn}/load-trend`, { params: { metric_name: selectedMetric } }),
      ])
      setHealthData(healthResp.data?.data?.assessments ?? [])
      setAnomalies(anomalyResp.data?.data?.anomalies ?? [])
      setLoadTrend(trendResp.data?.data ?? null)
    } catch {
      message.error('获取飞行孪生数据失败')
    } finally {
      setLoading(false)
    }
  }

  const handleIngestTelemetry = async (values: { aircraft_serial_number: string; telemetry_data: string }) => {
    try {
      let data: Array<Record<string, unknown>>
      try {
        data = JSON.parse(values.telemetry_data)
      } catch {
        message.error('遥测数据必须是有效的JSON数组格式')
        return
      }
      await apiClient.post('/twin/flight/ingest', {
        aircraft_serial_number: values.aircraft_serial_number,
        telemetry_data: data,
      })
      message.success('遥测数据已注入')
      fetchHealthData(values.aircraft_serial_number)
    } catch {
      message.error('遥测注入失败')
    }
  }

  const handleAssessHealth = async (values: { aircraft_serial_number: string; flight_hours: number }) => {
    try {
      const resp = await apiClient.post('/twin/flight/assess-health', {
        aircraft_serial_number: values.aircraft_serial_number,
        flight_hours: values.flight_hours,
      })
      setHealthData(resp.data?.data?.assessments ?? [])
      message.success('结构健康评估完成')
    } catch {
      message.error('健康评估失败')
    }
  }

  const handleAnalyzeTrend = async (sn: string, metric: string) => {
    try {
      const resp = await apiClient.get(`/twin/flight/${sn}/load-trend`, { params: { metric_name: metric } })
      setLoadTrend(resp.data?.data ?? null)
    } catch {
      message.error('载荷趋势分析失败')
    }
  }

  const healthColumns = [
    { title: '部件ID', dataIndex: 'component_id', key: 'component_id', width: 160 },
    { title: '部件名称', dataIndex: 'component_name', key: 'component_name', width: 140 },
    {
      title: '设计载荷',
      dataIndex: 'design_load',
      key: 'design_load',
      width: 100,
      render: (v: number) => v?.toLocaleString(),
    },
    {
      title: '实际载荷',
      dataIndex: 'actual_load',
      key: 'actual_load',
      width: 100,
      render: (v: number) => v?.toLocaleString(),
    },
    {
      title: '载荷比',
      dataIndex: 'load_ratio',
      key: 'load_ratio',
      width: 100,
      render: (v: number) => (
        <Progress
          percent={Math.min(v * 100, 100)}
          size="small"
          strokeColor={v > 1 ? '#cf1322' : v > 0.8 ? '#fa8c16' : '#52c41a'}
          format={() => `${(v * 100).toFixed(1)}%`}
        />
      ),
    },
    {
      title: '疲劳损伤',
      dataIndex: 'fatigue_damage_cumulative',
      key: 'fatigue_damage_cumulative',
      width: 100,
      render: (v: number) => (
        <Progress
          percent={Math.min(v * 100, 100)}
          size="small"
          strokeColor={v > 0.8 ? '#cf1322' : v > 0.6 ? '#fa8c16' : '#52c41a'}
          format={() => `${(v * 100).toFixed(2)}%`}
        />
      ),
    },
    {
      title: '健康状态',
      dataIndex: 'health_status',
      key: 'health_status',
      width: 100,
      render: (s: string) => {
        const cfg = healthStatusConfig[s] || healthStatusConfig.normal
        return <Tag color={cfg.color} icon={cfg.icon}>{cfg.label}</Tag>
      },
    },
    {
      title: '剩余寿命(FH)',
      dataIndex: 'remaining_life_estimate_fh',
      key: 'remaining_life_estimate_fh',
      width: 120,
      render: (v: number) => v?.toLocaleString(),
    },
  ]

  const anomalyColumns = [
    { title: '异常ID', dataIndex: 'anomaly_id', key: 'anomaly_id', width: 140 },
    { title: '传感器ID', dataIndex: 'sensor_id', key: 'sensor_id', width: 120 },
    { title: '指标', dataIndex: 'metric_name', key: 'metric_name', width: 120 },
    { title: '实际值', dataIndex: 'actual_value', key: 'actual_value', width: 100 },
    {
      title: '正常范围',
      key: 'expected_range',
      width: 140,
      render: (_: unknown, record: AnomalyEvent) => `[${record.expected_range[0]}, ${record.expected_range[1]}]`,
    },
    { title: '异常类型', dataIndex: 'anomaly_type', key: 'anomaly_type', width: 140 },
    {
      title: '严重度',
      dataIndex: 'severity',
      key: 'severity',
      width: 80,
      render: (s: string) => (
        <Tag color={s === 'critical' ? 'red' : 'orange'}>
          {s === 'critical' ? '严重' : '警告'}
        </Tag>
      ),
    },
    {
      title: '检测时间',
      dataIndex: 'detected_at',
      key: 'detected_at',
      width: 160,
      render: (t: string) => t ? new Date(t).toLocaleString() : '-',
    },
  ]

  const criticalCount = healthData.filter(h => h.health_status === 'critical').length
  const warningCount = healthData.filter(h => h.health_status === 'warning').length
  const normalCount = healthData.filter(h => h.health_status === 'normal').length

  return (
    <div>
      <Card title="遥测数据注入" style={{ marginBottom: 16 }}>
        <Form onFinish={handleIngestTelemetry} layout="inline" style={{ marginBottom: 16 }}>
          <Form.Item name="aircraft_serial_number" rules={[{ required: true }]}>
            <Input placeholder="飞行器SN" style={{ width: 160 }} />
          </Form.Item>
          <Form.Item name="telemetry_data" rules={[{ required: true }]} style={{ flex: 1 }}>
            <Input.TextArea
              placeholder='[{"metric_name": "wing_lift", "metric_value": 45000}]'
              rows={1}
              style={{ width: 500 }}
            />
          </Form.Item>
          <Button type="primary" htmlType="submit" icon={<ThunderboltOutlined />}>
            注入遥测
          </Button>
        </Form>
      </Card>

      <Card title="结构健康评估" style={{ marginBottom: 16 }}>
        <Form onFinish={handleAssessHealth} layout="inline" style={{ marginBottom: 16 }}>
          <Form.Item name="aircraft_serial_number" rules={[{ required: true }]}>
            <Input placeholder="飞行器SN" style={{ width: 160 }} />
          </Form.Item>
          <Form.Item name="flight_hours" initialValue={0}>
            <Input type="number" placeholder="飞行小时" style={{ width: 120 }} />
          </Form.Item>
          <Button type="primary" htmlType="submit" icon={<SafetyCertificateOutlined />}>
            评估健康
          </Button>
          <Button
            style={{ marginLeft: 8 }}
            onClick={() => { if (searchSn) fetchHealthData(searchSn) }}
            icon={<ExperimentOutlined />}
          >
            刷新数据
          </Button>
          <Input.Search
            placeholder="查询飞行器SN"
            value={searchSn}
            onChange={(e) => setSearchSn(e.target.value)}
            onSearch={fetchHealthData}
            enterButton="查询"
            style={{ width: 280, marginLeft: 16 }}
          />
        </Form>
      </Card>

      {criticalCount > 0 && (
        <Alert
          type="error"
          message={`检测到 ${criticalCount} 个部件处于危险状态，请立即检查！`}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="危险部件"
              value={criticalCount}
              valueStyle={{ color: '#cf1322' }}
              prefix={<AlertOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="警告部件"
              value={warningCount}
              valueStyle={{ color: '#fa8c16' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="正常部件"
              value={normalCount}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="异常事件"
              value={anomalies.length}
              valueStyle={{ color: anomalies.length > 0 ? '#cf1322' : '#3f8600' }}
              prefix={<AlertOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={
          <Space>
            <SafetyCertificateOutlined />
            <span>结构健康评估结果</span>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Table
          columns={healthColumns}
          dataSource={healthData.map((h, i) => ({ ...h, key: h.component_id || i }))}
          loading={loading}
          size="small"
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1000 }}
        />
      </Card>

      <Card
        title={
          <Space>
            <AlertOutlined />
            <span>异常事件</span>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Table
          columns={anomalyColumns}
          dataSource={anomalies.map((a, i) => ({ ...a, key: a.anomaly_id || i }))}
          loading={loading}
          size="small"
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1000 }}
        />
      </Card>

      <Card
        title={
          <Space>
            <LineChartOutlined />
            <span>载荷趋势分析</span>
          </Space>
        }
      >
        <Space style={{ marginBottom: 16 }}>
          <Select
            value={selectedMetric}
            onChange={(val) => { setSelectedMetric(val); if (searchSn) handleAnalyzeTrend(searchSn, val) }}
            style={{ width: 200 }}
            options={[
              { value: 'wing_lift', label: '机翼升力' },
              { value: 'wing_bending_moment', label: '机翼弯矩' },
              { value: 'fuselage_pressure', label: '机身压力' },
              { value: 'tail_lateral_load', label: '尾翼侧向载荷' },
              { value: 'engine_thrust', label: '发动机推力' },
              { value: 'landing_gear_load', label: '起落架载荷' },
            ]}
          />
          <Button onClick={() => { if (searchSn) handleAnalyzeTrend(searchSn, selectedMetric) }}>
            分析趋势
          </Button>
        </Space>

        {loadTrend ? (
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="飞行器SN">{loadTrend.aircraft_sn}</Descriptions.Item>
            <Descriptions.Item label="指标">{loadTrend.metric_name}</Descriptions.Item>
            <Descriptions.Item label="趋势">
              <Tag color={trendConfig[loadTrend.trend]?.color || '#999'}>
                {trendConfig[loadTrend.trend]?.label || loadTrend.trend}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="变化率">{(loadTrend.change_ratio * 100).toFixed(2)}%</Descriptions.Item>
            <Descriptions.Item label="前半段均值">{loadTrend.first_half_avg?.toFixed(2)}</Descriptions.Item>
            <Descriptions.Item label="后半段均值">{loadTrend.second_half_avg?.toFixed(2)}</Descriptions.Item>
            <Descriptions.Item label="数据点数">{loadTrend.data_points}</Descriptions.Item>
          </Descriptions>
        ) : (
          <Empty description="请选择指标并查询载荷趋势" />
        )}
      </Card>
    </div>
  )
}