import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Card, Typography, Space, Tag, Button, Table, Form,
  Input, Select, InputNumber, message, Row, Col, Statistic,
  Descriptions, Tabs, Empty, Alert, Progress,
} from 'antd'
import {
  ExperimentOutlined, ThunderboltOutlined,
  BarChartOutlined, SafetyOutlined, CompressOutlined,
} from '@ant-design/icons'
import apiClient from '../../services/apiClient'
import { useProjectStore } from '../../stores/projectStore'

const { Text } = Typography

export default function AdvancedCAEPage() {
  const { t } = useTranslation()
  const { currentProjectId } = useProjectStore()

  const [parametricStudy, setParametricStudy] = useState<Record<string, unknown> | null>(null)
  const [adjointOpt, setAdjointOpt] = useState<Record<string, unknown> | null>(null)
  const [aeroDatabase, setAeroDatabase] = useState<Record<string, unknown> | null>(null)
  const [fatigueResult, setFatigueResult] = useState<Record<string, unknown> | null>(null)
  const [bucklingResult, setBucklingResult] = useState<Record<string, unknown> | null>(null)

  const [paramForm] = Form.useForm()
  const [adjointForm] = Form.useForm()
  const [aeroForm] = Form.useForm()
  const [fatigueForm] = Form.useForm()
  const [bucklingForm] = Form.useForm()

  const handleParametricStudy = async (values: Record<string, unknown>) => {
    try {
      const sweepRanges = []
      if (values.aoa_start !== undefined) {
        sweepRanges.push({ parameter: 'angle_of_attack', start: values.aoa_start, end: values.aoa_end, step: values.aoa_step, unit: 'deg' })
      }
      if (values.mach_start !== undefined) {
        sweepRanges.push({ parameter: 'mach_number', start: values.mach_start, end: values.mach_end, step: values.mach_step })
      }
      const resp = await apiClient.post('/cae/cfd/parametric-study', {
        ...values,
        project_id: currentProjectId || 'default',
        tenant_id: 'default',
        sweep_ranges: sweepRanges,
      })
      setParametricStudy(resp.data?.data)
      message.success(t('cae.parametricStudyComplete', 'Parametric study completed'))
    } catch {
      message.error(t('common.error'))
    }
  }

  const handleAdjointOpt = async (values: Record<string, unknown>) => {
    try {
      const resp = await apiClient.post('/cae/cfd/adjoint-optimization', {
        ...values,
        project_id: currentProjectId || 'default',
        tenant_id: 'default',
      })
      setAdjointOpt(resp.data?.data)
      message.success(t('cae.adjointOptComplete', 'Adjoint optimization completed'))
    } catch {
      message.error(t('common.error'))
    }
  }

  const handleAeroDatabase = async (values: Record<string, unknown>) => {
    try {
      const resp = await apiClient.post('/cae/cfd/aero-database', {
        ...values,
        project_id: currentProjectId || 'default',
        tenant_id: 'default',
        alpha_range: values.alpha_range ? { parameter: 'angle_of_attack', ...values.alpha_range } : undefined,
        mach_range: values.mach_range ? { parameter: 'mach_number', ...values.mach_range } : undefined,
      })
      setAeroDatabase(resp.data?.data)
      message.success(t('cae.aeroDatabaseComplete', 'Aero database generated'))
    } catch {
      message.error(t('common.error'))
    }
  }

  const handleFatigue = async (values: Record<string, unknown>) => {
    try {
      const spectrum = String(values.load_spectrum || '').split(',').map(Number).filter(n => !isNaN(n))
      const resp = await apiClient.post('/cae/fea/fatigue', {
        ...values,
        project_id: currentProjectId || 'default',
        tenant_id: 'default',
        load_spectrum: spectrum,
      })
      setFatigueResult(resp.data?.data)
      message.success(t('cae.fatigueComplete', 'Fatigue analysis completed'))
    } catch {
      message.error(t('common.error'))
    }
  }

  const handleBuckling = async (values: Record<string, unknown>) => {
    try {
      const resp = await apiClient.post('/cae/fea/buckling', {
        ...values,
        project_id: currentProjectId || 'default',
        tenant_id: 'default',
      })
      setBucklingResult(resp.data?.data)
      message.success(t('cae.bucklingComplete', 'Buckling analysis completed'))
    } catch {
      message.error(t('common.error'))
    }
  }

  const caseResultColumns = [
    { title: 'Case ID', dataIndex: 'case_id', key: 'case_id', width: 100 },
    {
      title: 'Parameters',
      key: 'params',
      width: 200,
      render: (_: unknown, r: Record<string, unknown>) => (
        <span>{Object.entries(r.parameters as Record<string, number> || {}).map(([k, v]) => `${k}=${v}`).join(', ')}</span>
      ),
    },
    { title: 'CL', dataIndex: 'lift_coefficient', key: 'cl', width: 80, render: (v: number) => v?.toFixed(4) },
    { title: 'CD', dataIndex: 'drag_coefficient', key: 'cd', width: 80, render: (v: number) => v?.toFixed(4) },
    { title: 'CM', dataIndex: 'moment_coefficient', key: 'cm', width: 80, render: (v: number) => v?.toFixed(4) },
    {
      title: t('common.status'),
      dataIndex: 'convergence_status',
      key: 'status',
      width: 100,
      render: (v: string) => v === 'converged' ? <Tag color="green">Converged</Tag> : <Tag color="red">Not Converged</Tag>,
    },
  ]

  const iterationColumns = [
    { title: t('optimization.iteration'), dataIndex: 'iteration', key: 'iter', width: 70 },
    { title: 'Objective', dataIndex: 'objective_value', key: 'obj', width: 100, render: (v: number) => v?.toExponential(4) },
    { title: 'Sensitivity', dataIndex: 'sensitivity_norm', key: 'sens', width: 100, render: (v: number) => v?.toExponential(4) },
    { title: 'Geom Update', dataIndex: 'geometry_update_norm', key: 'geom', width: 100, render: (v: number) => v?.toExponential(4) },
    {
      title: t('optimization.converged'),
      dataIndex: 'converged',
      key: 'conv',
      width: 80,
      render: (v: boolean) => v ? <Tag color="green">{t('common.yes')}</Tag> : <Tag>{t('common.no')}</Tag>,
    },
  ]

  const aeroDataColumns = [
    { title: 'Alpha (deg)', dataIndex: 'alpha', key: 'alpha', width: 90, render: (v: number) => v?.toFixed(1) },
    { title: 'Mach', dataIndex: 'mach', key: 'mach', width: 80, render: (v: number) => v?.toFixed(2) },
    { title: 'Beta (deg)', dataIndex: 'beta', key: 'beta', width: 80, render: (v: number) => v?.toFixed(1) },
    { title: 'CL', dataIndex: 'cl', key: 'cl', width: 80, render: (v: number) => v?.toFixed(4) },
    { title: 'CD', dataIndex: 'cd', key: 'cd', width: 80, render: (v: number) => v?.toFixed(4) },
    { title: 'CM', dataIndex: 'cm', key: 'cm', width: 80, render: (v: number) => v?.toFixed(4) },
  ]

  const damageColumns = [
    { title: 'Element', dataIndex: 'element_id', key: 'elem', width: 70 },
    { title: 'Damage', dataIndex: 'damage', key: 'damage', width: 100, render: (v: number) => v?.toExponential(4) },
    { title: 'Life (cycles)', dataIndex: 'life_cycles', key: 'life', width: 120, render: (v: number) => v === Infinity ? '∞' : v?.toFixed(0) },
    {
      title: 'Critical',
      dataIndex: 'critical',
      key: 'crit',
      width: 80,
      render: (v: boolean) => v ? <Tag color="red">Critical</Tag> : <Tag color="green">OK</Tag>,
    },
  ]

  const bucklingColumns = [
    { title: 'Mode', dataIndex: 'mode_number', key: 'mode', width: 70 },
    { title: 'Load Factor', dataIndex: 'critical_load_factor', key: 'lf', width: 120, render: (v: number) => v?.toFixed(4) },
    { title: t('common.description'), dataIndex: 'description', key: 'desc' },
  ]

  return (
    <div>
      <Tabs
        defaultActiveKey="parametric"
        items={[
          {
            key: 'parametric',
            label: <span><ExperimentOutlined /> Parametric Study</span>,
            children: (
              <Row gutter={16}>
                <Col span={8}>
                  <Card title="Configuration" size="small">
                    <Form form={paramForm} layout="vertical" onFinish={handleParametricStudy}>
                      <Form.Item name="model_id" label="Model ID" rules={[{ required: true }]} initialValue="wing-v1">
                        <Input />
                      </Form.Item>
                      <Form.Item label="AoA Sweep (deg)">
                        <Space>
                          <Form.Item name="aoa_start" noStyle initialValue={-5}><InputNumber placeholder="Start" style={{ width: 80 }} /></Form.Item>
                          <Form.Item name="aoa_end" noStyle initialValue={15}><InputNumber placeholder="End" style={{ width: 80 }} /></Form.Item>
                          <Form.Item name="aoa_step" noStyle initialValue={1}><InputNumber placeholder="Step" style={{ width: 80 }} /></Form.Item>
                        </Space>
                      </Form.Item>
                      <Form.Item label="Mach Sweep">
                        <Space>
                          <Form.Item name="mach_start" noStyle initialValue={0.1}><InputNumber placeholder="Start" step={0.1} style={{ width: 80 }} /></Form.Item>
                          <Form.Item name="mach_end" noStyle initialValue={0.8}><InputNumber placeholder="End" step={0.1} style={{ width: 80 }} /></Form.Item>
                          <Form.Item name="mach_step" noStyle initialValue={0.1}><InputNumber placeholder="Step" step={0.1} style={{ width: 80 }} /></Form.Item>
                        </Space>
                      </Form.Item>
                      <Button type="primary" icon={<ThunderboltOutlined />} htmlType="submit">Run Study</Button>
                    </Form>
                  </Card>
                </Col>
                <Col span={16}>
                  {parametricStudy ? (
                    <>
                      <Row gutter={16} style={{ marginBottom: 16 }}>
                        <Col span={8}><Card><Statistic title="Total Cases" value={parametricStudy.total_cases as number} /></Card></Col>
                        <Col span={8}><Card><Statistic title="Completed" value={parametricStudy.completed_cases as number} valueStyle={{ color: '#3f8600' }} /></Card></Col>
                        <Col span={8}><Card><Statistic title="Failed" value={parametricStudy.failed_cases as number} valueStyle={{ color: '#cf1322' }} /></Card></Col>
                      </Row>
                      <Card title="Case Results">
                        <Table
                          columns={caseResultColumns}
                          dataSource={((parametricStudy.case_results as Record<string, unknown>[]) || []).map((c, i) => ({ ...c, key: i }))}
                          size="small"
                          pagination={{ pageSize: 10 }}
                          scroll={{ x: 600 }}
                        />
                      </Card>
                    </>
                  ) : (
                    <Card><Empty description="Configure parameters and run a parametric study" /></Card>
                  )}
                </Col>
              </Row>
            ),
          },
          {
            key: 'adjoint',
            label: <span><CompressOutlined /> Adjoint Optimization</span>,
            children: (
              <Row gutter={16}>
                <Col span={8}>
                  <Card title="Configuration" size="small">
                    <Form form={adjointForm} layout="vertical" onFinish={handleAdjointOpt}>
                      <Form.Item name="model_id" label="Model ID" rules={[{ required: true }]} initialValue="wing-v1">
                        <Input />
                      </Form.Item>
                      <Form.Item name="objective_function" label="Objective" initialValue="minimize_drag">
                        <Select options={[
                          { value: 'minimize_drag', label: 'Minimize Drag' },
                          { value: 'maximize_lift', label: 'Maximize Lift' },
                          { value: 'maximize_ld', label: 'Maximize L/D' },
                        ]} />
                      </Form.Item>
                      <Form.Item name="max_iterations" label="Max Iterations" initialValue={20}>
                        <InputNumber min={1} max={100} style={{ width: '100%' }} />
                      </Form.Item>
                      <Form.Item name="convergence_tolerance" label="Convergence Tolerance" initialValue={0.0001}>
                        <InputNumber step={0.0001} style={{ width: '100%' }} />
                      </Form.Item>
                      <Button type="primary" icon={<ThunderboltOutlined />} htmlType="submit">Run Optimization</Button>
                    </Form>
                  </Card>
                </Col>
                <Col span={16}>
                  {adjointOpt ? (
                    <>
                      <Row gutter={16} style={{ marginBottom: 16 }}>
                        <Col span={8}><Card><Statistic title="Iterations" value={adjointOpt.current_iteration as number} /></Card></Col>
                        <Col span={8}><Card><Statistic title="Improvement" value={adjointOpt.improvement_pct as number} suffix="%" precision={2} valueStyle={{ color: '#3f8600' }} /></Card></Col>
                        <Col span={8}><Card><Statistic title="Status" value={adjointOpt.status as string} /></Card></Col>
                      </Row>
                      <Card title="Convergence History">
                        <Table
                          columns={iterationColumns}
                          dataSource={((adjointOpt.iterations as Record<string, unknown>[]) || []).map((it, i) => ({ ...it, key: i }))}
                          size="small"
                          pagination={false}
                        />
                      </Card>
                    </>
                  ) : (
                    <Card><Empty description="Configure and run adjoint shape optimization" /></Card>
                  )}
                </Col>
              </Row>
            ),
          },
          {
            key: 'aerodb',
            label: <span><BarChartOutlined /> Aero Database</span>,
            children: (
              <Row gutter={16}>
                <Col span={8}>
                  <Card title="Configuration" size="small">
                    <Form form={aeroForm} layout="vertical" onFinish={handleAeroDatabase}>
                      <Form.Item name="model_id" label="Model ID" rules={[{ required: true }]} initialValue="aircraft-v1">
                        <Input />
                      </Form.Item>
                      <Button type="primary" icon={<BarChartOutlined />} htmlType="submit">Generate Database</Button>
                    </Form>
                  </Card>
                </Col>
                <Col span={16}>
                  {aeroDatabase ? (
                    <>
                      <Row gutter={16} style={{ marginBottom: 16 }}>
                        <Col span={12}><Card><Statistic title="Total Points" value={aeroDatabase.total_points as number} /></Card></Col>
                        <Col span={12}><Card><Statistic title="Completed" value={aeroDatabase.completed_points as number} valueStyle={{ color: '#3f8600' }} /></Card></Col>
                      </Row>
                      <Card title="Aero Coefficients">
                        <Table
                          columns={aeroDataColumns}
                          dataSource={((aeroDatabase.data_points as Record<string, unknown>[]) || []).slice(0, 50).map((p, i) => ({ ...p, key: i }))}
                          size="small"
                          pagination={{ pageSize: 10 }}
                          scroll={{ x: 500 }}
                        />
                      </Card>
                    </>
                  ) : (
                    <Card><Empty description="Generate an aero database covering the full flight envelope" /></Card>
                  )}
                </Col>
              </Row>
            ),
          },
          {
            key: 'fatigue',
            label: <span><SafetyOutlined /> Fatigue Analysis</span>,
            children: (
              <Row gutter={16}>
                <Col span={8}>
                  <Card title="Configuration" size="small">
                    <Form form={fatigueForm} layout="vertical" onFinish={handleFatigue}>
                      <Form.Item name="model_id" label="Model ID" rules={[{ required: true }]} initialValue="wing-spar">
                        <Input />
                      </Form.Item>
                      <Form.Item name="load_spectrum" label="Load Spectrum (comma separated)" rules={[{ required: true }]}>
                        <Input placeholder="0, 100, -50, 80, -30, 60, 0" />
                      </Form.Item>
                      <Form.Item name="mean_stress_correction" label="Mean Stress Correction" initialValue="goodman">
                        <Select options={[
                          { value: 'goodman', label: 'Goodman' },
                          { value: 'gerber', label: 'Gerber' },
                          { value: 'none', label: 'None' },
                        ]} />
                      </Form.Item>
                      <Button type="primary" icon={<SafetyOutlined />} htmlType="submit">Run Fatigue Analysis</Button>
                    </Form>
                  </Card>
                </Col>
                <Col span={16}>
                  {fatigueResult ? (
                    <>
                      <Row gutter={16} style={{ marginBottom: 16 }}>
                        <Col span={8}><Card><Statistic title="Total Damage" value={fatigueResult.total_damage as number} precision={6} /></Card></Col>
                        <Col span={8}><Card><Statistic title="Min Life (cycles)" value={fatigueResult.min_life_cycles as number} /></Card></Col>
                        <Col span={8}><Card><Statistic title="Rainflow Cycles" value={(fatigueResult.rainflow_cycles as unknown[])?.length ?? 0} /></Card></Col>
                      </Row>
                      <Card title="Fatigue Damage per Element">
                        <Table
                          columns={damageColumns}
                          dataSource={((fatigueResult.damage_results as Record<string, unknown>[]) || []).map((d, i) => ({ ...d, key: i }))}
                          size="small"
                          pagination={false}
                        />
                      </Card>
                    </>
                  ) : (
                    <Card><Empty description="Configure load spectrum and run fatigue analysis" /></Card>
                  )}
                </Col>
              </Row>
            ),
          },
          {
            key: 'buckling',
            label: <span><CompressOutlined /> Buckling Analysis</span>,
            children: (
              <Row gutter={16}>
                <Col span={8}>
                  <Card title="Configuration" size="small">
                    <Form form={bucklingForm} layout="vertical" onFinish={handleBuckling}>
                      <Form.Item name="model_id" label="Model ID" rules={[{ required: true }]} initialValue="panel-v1">
                        <Input />
                      </Form.Item>
                      <Form.Item name="num_modes" label="Number of Modes" initialValue={5}>
                        <InputNumber min={1} max={50} style={{ width: '100%' }} />
                      </Form.Item>
                      <Button type="primary" icon={<CompressOutlined />} htmlType="submit">Run Buckling Analysis</Button>
                    </Form>
                  </Card>
                </Col>
                <Col span={16}>
                  {bucklingResult ? (
                    <>
                      <Row gutter={16} style={{ marginBottom: 16 }}>
                        <Col span={12}><Card><Statistic title="Critical Load Factor" value={bucklingResult.critical_load_factor as number} precision={4} valueStyle={{ color: (bucklingResult.critical_load_factor as number) < 1 ? '#cf1322' : '#3f8600' }} /></Card></Col>
                        <Col span={12}><Card><Statistic title="Modes" value={(bucklingResult.buckling_modes as unknown[])?.length ?? 0} /></Card></Col>
                      </Row>
                      <Card title="Buckling Modes">
                        <Table
                          columns={bucklingColumns}
                          dataSource={((bucklingResult.buckling_modes as Record<string, unknown>[]) || []).map((m, i) => ({ ...m, key: i }))}
                          size="small"
                          pagination={false}
                        />
                      </Card>
                    </>
                  ) : (
                    <Card><Empty description="Configure and run linear buckling analysis" /></Card>
                  )}
                </Col>
              </Row>
            ),
          },
        ]}
      />
    </div>
  )
}