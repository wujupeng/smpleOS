import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Card, Typography, Space, Tag, Button, Select, InputNumber,
  message, Row, Col, Statistic, Table, Empty, Divider, Progress,
  Tabs, Spin, Descriptions, Alert,
} from 'antd'
import {
  AimOutlined, ApartmentOutlined, ThunderboltOutlined,
  CheckCircleOutlined, PlayCircleOutlined, ReloadOutlined,
  BarChartOutlined, FundOutlined,
} from '@ant-design/icons'
import apiClient from '../../services/apiClient'
import { useProjectStore } from '../../stores/projectStore'

const { Title, Text } = Typography

interface ParetoSolution {
  solution_id: string
  variable_values: Record<string, number>
  objective_values: Record<string, number>
  constraint_values: Record<string, number>
  is_feasible: boolean
  rank: number
}

interface OptimizationTaskInfo {
  id: string
  project_id: string
  status: string
  optimization_type: string
  objectives: Array<{ name: string; direction: string; weight: number }>
  constraints: Array<{ name: string; operator: string; value: number; description: string }>
  design_variables: Array<{ name: string; lower_bound: number; upper_bound: number; initial_value: number | null }>
  algorithm: string
  max_iterations: number
  population_size: number
  pareto_front: ParetoSolution[]
  optimal_solution: ParetoSolution | null
  iteration_count: number
  convergence_history: Array<Record<string, unknown>>
  error_message: string
  created_at: string
  completed_at: string
}

interface TopologyTaskInfo {
  id: string
  project_id: string
  status: string
  method: string
  design_regions: Array<{ name: string; volume_fraction: number; min_member_size: number; material_id: string }>
  load_cases: Array<{ name: string; load_case_type: string; force_z: number; description: string }>
  boundary_conditions: Array<{ name: string; constrained_dofs: string[]; region: string }>
  max_iterations: number
  convergence_tolerance: number
  penalty_factor: number
  filter_radius: number
  result: {
    iteration_count: number
    final_volume_fraction: number
    compliance: number
    max_stress: number
    mass_reduction_pct: number
    element_count: number
    converged: boolean
  } | null
  iteration_history: Array<Record<string, unknown>>
  error_message: string
  created_at: string
}

interface BuiltinItem {
  name: string
  [key: string]: unknown
}

interface BuiltinData {
  objectives?: Record<string, BuiltinItem>
  constraints?: Record<string, BuiltinItem>
  variables?: Record<string, BuiltinItem>
  load_cases?: Record<string, BuiltinItem>
  boundary_conditions?: Record<string, BuiltinItem>
  design_regions?: Record<string, BuiltinItem>
}

export default function OptimizationPage() {
  const { t } = useTranslation()
  const { currentProjectId } = useProjectStore()

  const optStatusConfig: Record<string, { color: string; label: string }> = {
    queued: { color: 'default', label: t('status.queued') },
    running: { color: 'processing', label: t('status.running') },
    completed: { color: 'success', label: t('status.completed') },
    failed: { color: 'error', label: t('status.failed') },
  }

  const topoStatusConfig: Record<string, { color: string; label: string }> = {
    queued: { color: 'default', label: t('status.queued') },
    meshing: { color: 'processing', label: t('status.meshing') },
    optimizing: { color: 'processing', label: t('status.optimizing') },
    post_processing: { color: 'processing', label: t('status.postProcessing') },
    completed: { color: 'success', label: t('status.completed') },
    failed: { color: 'error', label: t('status.failed') },
  }

  const methodLabels: Record<string, string> = {
    simp: t('optimization.methodSimp'),
    level_set: t('optimization.methodLevelSet'),
    beso: t('optimization.methodBeso'),
    homogenization: t('optimization.methodHomogenization'),
  }

  const algorithmLabels: Record<string, string> = {
    nsga2: t('optimization.algorithmNsga2'),
    moead: t('optimization.algorithmMoead'),
    pso: t('optimization.algorithmPso'),
  }

  const [builtins, setBuiltins] = useState<BuiltinData>({})
  const [loadingBuiltins, setLoadingBuiltins] = useState(true)

  const [optTask, setOptTask] = useState<OptimizationTaskInfo | null>(null)
  const [optLoading, setOptLoading] = useState(false)
  const [selectedObjectives, setSelectedObjectives] = useState<string[]>(['minimize_weight', 'maximize_lift_drag_ratio'])
  const [selectedConstraints, setSelectedConstraints] = useState<string[]>(['safety_factor'])
  const [selectedVariables, setSelectedVariables] = useState<string[]>(['wing_span', 'aspect_ratio'])
  const [optAlgorithm, setOptAlgorithm] = useState('nsga2')
  const [optMaxIter, setOptMaxIter] = useState(50)
  const [optPopSize, setOptPopSize] = useState(50)

  const [topoTask, setTopoTask] = useState<TopologyTaskInfo | null>(null)
  const [topoLoading, setTopoLoading] = useState(false)
  const [selectedRegions, setSelectedRegions] = useState<string[]>(['wing_box'])
  const [selectedLoadCases, setSelectedLoadCases] = useState<string[]>(['wing_bending'])
  const [selectedBCs, setSelectedBCs] = useState<string[]>(['wing_root_fixed'])
  const [topoMethod, setTopoMethod] = useState('simp')
  const [topoMaxIter, setTopoMaxIter] = useState(50)
  const [topoPenalty, setTopoPenalty] = useState(3.0)
  const [topoFilterRadius, setTopoFilterRadius] = useState(1.5)

  const loadBuiltins = useCallback(async () => {
    setLoadingBuiltins(true)
    try {
      const [objResp, conResp, varResp, lcResp, bcResp, drResp] = await Promise.all([
        apiClient.get('/ai/optimization/builtins/objectives'),
        apiClient.get('/ai/optimization/builtins/constraints'),
        apiClient.get('/ai/optimization/builtins/variables'),
        apiClient.get('/ai/topology/builtins/load-cases'),
        apiClient.get('/ai/topology/builtins/boundary-conditions'),
        apiClient.get('/ai/topology/builtins/design-regions'),
      ])
      setBuiltins({
        objectives: objResp.data?.data?.objectives ?? {},
        constraints: conResp.data?.data?.constraints ?? {},
        variables: varResp.data?.data?.variables ?? {},
        load_cases: lcResp.data?.data?.load_cases ?? {},
        boundary_conditions: bcResp.data?.data?.boundary_conditions ?? {},
        design_regions: drResp.data?.data?.design_regions ?? {},
      })
    } catch {
      message.warning(t('optimization.loadBuiltinsFailed'))
    } finally {
      setLoadingBuiltins(false)
    }
  }, [t])

  useEffect(() => {
    loadBuiltins()
  }, [loadBuiltins])

  const handleCreateAndRunOptimization = async () => {
    if (selectedObjectives.length === 0) {
      message.warning(t('optimization.selectAtLeastObjective'))
      return
    }
    setOptLoading(true)
    try {
      const createResp = await apiClient.post('/ai/optimization/create', {
        project_id: currentProjectId || 'default',
        tenant_id: 'default',
        objective_names: selectedObjectives,
        constraint_names: selectedConstraints,
        variable_names: selectedVariables,
        algorithm: optAlgorithm,
        max_iterations: optMaxIter,
        population_size: optPopSize,
      })
      const taskId = createResp.data?.data?.id
      if (!taskId) {
        message.error(t('optimization.createOptFailed'))
        return
      }
      const runResp = await apiClient.post('/ai/optimization/run', { task_id: taskId })
      setOptTask(runResp.data?.data ?? null)
      message.success(t('optimization.optComplete'))
    } catch {
      message.error(t('optimization.optExecFailed'))
    } finally {
      setOptLoading(false)
    }
  }

  const handleCreateAndRunTopology = async () => {
    if (selectedRegions.length === 0) {
      message.warning(t('optimization.selectAtLeastRegion'))
      return
    }
    setTopoLoading(true)
    try {
      const createResp = await apiClient.post('/ai/topology/create', {
        project_id: currentProjectId || 'default',
        tenant_id: 'default',
        design_region_names: selectedRegions,
        load_case_names: selectedLoadCases,
        boundary_condition_names: selectedBCs,
        method: topoMethod,
        max_iterations: topoMaxIter,
        penalty_factor: topoPenalty,
        filter_radius: topoFilterRadius,
      })
      const taskId = createResp.data?.data?.id
      if (!taskId) {
        message.error(t('optimization.createTopoFailed'))
        return
      }
      const runResp = await apiClient.post('/ai/topology/run', { task_id: taskId })
      setTopoTask(runResp.data?.data ?? null)
      message.success(t('optimization.topoComplete'))
    } catch {
      message.error(t('optimization.topoExecFailed'))
    } finally {
      setTopoLoading(false)
    }
  }

  const objectiveOptions = Object.keys(builtins.objectives || {}).map(k => ({
    value: k,
    label: k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
  }))

  const constraintOptions = Object.keys(builtins.constraints || {}).map(k => ({
    value: k,
    label: k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
  }))

  const variableOptions = Object.keys(builtins.variables || {}).map(k => ({
    value: k,
    label: k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
  }))

  const loadCaseOptions = Object.keys(builtins.load_cases || {}).map(k => ({
    value: k,
    label: k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
  }))

  const bcOptions = Object.keys(builtins.boundary_conditions || {}).map(k => ({
    value: k,
    label: k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
  }))

  const regionOptions = Object.keys(builtins.design_regions || {}).map(k => ({
    value: k,
    label: k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
  }))

  const paretoColumns = [
    { title: t('optimization.solutionId'), dataIndex: 'solution_id', key: 'solution_id', width: 100 },
    {
      title: t('optimization.feasible'),
      dataIndex: 'is_feasible',
      key: 'is_feasible',
      width: 70,
      render: (v: boolean) => v ? <Tag color="green">{t('common.yes')}</Tag> : <Tag color="red">{t('common.no')}</Tag>,
    },
    { title: t('optimization.rank'), dataIndex: 'rank', key: 'rank', width: 60 },
    {
      title: t('optimization.designVars'),
      key: 'variables',
      render: (_: unknown, record: ParetoSolution) => (
        <span>{Object.entries(record.variable_values).map(([k, v]) => `${k}=${v.toFixed(2)}`).join(', ')}</span>
      ),
    },
    {
      title: t('optimization.objectiveValues'),
      key: 'objectives',
      render: (_: unknown, record: ParetoSolution) => (
        <span>{Object.entries(record.objective_values).map(([k, v]) => `${k}=${v.toFixed(2)}`).join(', ')}</span>
      ),
    },
  ]

  const convergenceColumns = [
    { title: t('optimization.iteration'), dataIndex: 'iteration', key: 'iteration', width: 70 },
    {
      title: t('optimization.feasibleCount'),
      dataIndex: 'feasible_count',
      key: 'feasible_count',
      width: 100,
    },
    {
      title: t('optimization.bestObjectives'),
      dataIndex: 'best_objectives',
      key: 'best_objectives',
      render: (v: Record<string, number>) => (
        <span>{Object.entries(v || {}).map(([k, val]) => `${k}=${Number(val).toFixed(2)}`).join(', ')}</span>
      ),
    },
  ]

  const topoHistoryColumns = [
    { title: t('optimization.iteration'), dataIndex: 'iteration', key: 'iteration', width: 70 },
    { title: t('optimization.compliance'), dataIndex: 'compliance', key: 'compliance', width: 100 },
    { title: t('optimization.volumeFraction'), dataIndex: 'volume_fraction', key: 'volume_fraction', width: 100 },
    { title: t('optimization.maxStress'), dataIndex: 'max_stress', key: 'max_stress', width: 100 },
    {
      title: t('optimization.converged'),
      dataIndex: 'converged',
      key: 'converged',
      width: 70,
      render: (v: boolean) => v ? <Tag color="green">{t('common.yes')}</Tag> : <Tag color="default">{t('common.no')}</Tag>,
    },
  ]

  return (
    <div>
      <Tabs
        defaultActiveKey="multi-objective"
        items={[
          {
            key: 'multi-objective',
            label: (
              <span>
                <AimOutlined /> {t('optimization.multiObjective')}
              </span>
            ),
            children: (
              <div>
                <Card
                  title={
                    <Space>
                      <AimOutlined style={{ fontSize: 18 }} />
                      <span>{t('optimization.config')}</span>
                    </Space>
                  }
                  style={{ marginBottom: 16 }}
                >
                  <Spin spinning={loadingBuiltins}>
                    <Space direction="vertical" style={{ width: '100%' }} size="middle">
                      <Row gutter={16}>
                        <Col span={12}>
                          <div style={{ marginBottom: 8 }}><Text strong>{t('optimization.objectives')}</Text></div>
                          <Select
                            mode="multiple"
                            value={selectedObjectives}
                            onChange={setSelectedObjectives}
                            options={objectiveOptions}
                            style={{ width: '100%' }}
                            placeholder={t('optimization.selectObjectives')}
                          />
                        </Col>
                        <Col span={12}>
                          <div style={{ marginBottom: 8 }}><Text strong>{t('optimization.constraints')}</Text></div>
                          <Select
                            mode="multiple"
                            value={selectedConstraints}
                            onChange={setSelectedConstraints}
                            options={constraintOptions}
                            style={{ width: '100%' }}
                            placeholder={t('optimization.selectConstraints')}
                          />
                        </Col>
                      </Row>
                      <Row gutter={16}>
                        <Col span={12}>
                          <div style={{ marginBottom: 8 }}><Text strong>{t('optimization.variables')}</Text></div>
                          <Select
                            mode="multiple"
                            value={selectedVariables}
                            onChange={setSelectedVariables}
                            options={variableOptions}
                            style={{ width: '100%' }}
                            placeholder={t('optimization.selectVariables')}
                          />
                        </Col>
                        <Col span={12}>
                          <div style={{ marginBottom: 8 }}><Text strong>{t('optimization.algorithm')}</Text></div>
                          <Select
                            value={optAlgorithm}
                            onChange={setOptAlgorithm}
                            options={Object.entries(algorithmLabels).map(([k, v]) => ({ value: k, label: v }))}
                            style={{ width: '100%' }}
                          />
                        </Col>
                      </Row>
                      <Row gutter={16}>
                        <Col span={6}>
                          <div style={{ marginBottom: 8 }}><Text strong>{t('optimization.maxIterations')}</Text></div>
                          <InputNumber
                            value={optMaxIter}
                            onChange={(v) => setOptMaxIter(v || 50)}
                            min={1}
                            max={1000}
                            style={{ width: '100%' }}
                          />
                        </Col>
                        <Col span={6}>
                          <div style={{ marginBottom: 8 }}><Text strong>{t('optimization.populationSize')}</Text></div>
                          <InputNumber
                            value={optPopSize}
                            onChange={(v) => setOptPopSize(v || 50)}
                            min={10}
                            max={500}
                            style={{ width: '100%' }}
                          />
                        </Col>
                        <Col span={12}>
                          <div style={{ marginBottom: 8 }}>&nbsp;</div>
                          <Button
                            type="primary"
                            icon={<PlayCircleOutlined />}
                            onClick={handleCreateAndRunOptimization}
                            loading={optLoading}
                            size="large"
                          >
                            {t('optimization.createAndRun')}
                          </Button>
                        </Col>
                      </Row>
                    </Space>
                  </Spin>
                </Card>

                {optTask && (
                  <>
                    {optTask.status === 'failed' && (
                      <Alert
                        type="error"
                        message={t('optimization.optimizationFailed')}
                        description={optTask.error_message}
                        showIcon
                        style={{ marginBottom: 16 }}
                      />
                    )}

                    <Row gutter={16} style={{ marginBottom: 16 }}>
                      <Col span={6}>
                        <Card>
                          <Statistic
                            title={t('common.status')}
                            value={optStatusConfig[optTask.status]?.label || optTask.status}
                            valueStyle={{ color: optStatusConfig[optTask.status]?.color === 'success' ? '#3f8600' : undefined }}
                            prefix={optTask.status === 'running' ? <ReloadOutlined spin /> : <CheckCircleOutlined />}
                          />
                        </Card>
                      </Col>
                      <Col span={6}>
                        <Card>
                          <Statistic
                            title={t('optimization.paretoCount')}
                            value={optTask.pareto_front?.length ?? 0}
                            prefix={<FundOutlined />}
                          />
                        </Card>
                      </Col>
                      <Col span={6}>
                        <Card>
                          <Statistic
                            title={t('optimization.iterationCount')}
                            value={optTask.iteration_count}
                            prefix={<BarChartOutlined />}
                          />
                        </Card>
                      </Col>
                      <Col span={6}>
                        <Card>
                          <Statistic
                            title={t('optimization.algorithm')}
                            value={algorithmLabels[optTask.algorithm] || optTask.algorithm}
                          />
                        </Card>
                      </Col>
                    </Row>

                    {optTask.optimal_solution && (
                      <Card title={t('optimization.optimalSolution')} style={{ marginBottom: 16 }}>
                        <Descriptions bordered column={2} size="small">
                          <Descriptions.Item label={t('optimization.solutionId')}>{optTask.optimal_solution.solution_id}</Descriptions.Item>
                          <Descriptions.Item label={t('optimization.feasible')}>
                            {optTask.optimal_solution.is_feasible ? <Tag color="green">{t('common.yes')}</Tag> : <Tag color="red">{t('common.no')}</Tag>}
                          </Descriptions.Item>
                          {Object.entries(optTask.optimal_solution.variable_values).map(([k, v]) => (
                            <Descriptions.Item key={k} label={k}>{Number(v).toFixed(4)}</Descriptions.Item>
                          ))}
                          {Object.entries(optTask.optimal_solution.objective_values).map(([k, v]) => (
                            <Descriptions.Item key={k} label={`${t('optimization.objectivePrefix')}: ${k}`}>{Number(v).toFixed(4)}</Descriptions.Item>
                          ))}
                        </Descriptions>
                      </Card>
                    )}

                    <Card title={t('optimization.paretoFront')} style={{ marginBottom: 16 }}>
                      <Table
                        columns={paretoColumns}
                        dataSource={optTask.pareto_front?.map(s => ({ ...s, key: s.solution_id })) || []}
                        size="small"
                        pagination={{ pageSize: 10 }}
                        scroll={{ x: 600 }}
                      />
                    </Card>

                    {optTask.convergence_history?.length > 0 && (
                      <Card title={t('optimization.convergenceHistory')}>
                        <Table
                          columns={convergenceColumns}
                          dataSource={optTask.convergence_history.map((h, i) => ({ ...h, key: i }))}
                          size="small"
                          pagination={false}
                        />
                      </Card>
                    )}
                  </>
                )}

                {!optTask && !optLoading && (
                  <Card>
                    <Empty
                      image={<AimOutlined style={{ fontSize: 64, color: '#1890ff' }} />}
                      description={t('optimization.configureAndRun')}
                    />
                  </Card>
                )}
              </div>
            ),
          },
          {
            key: 'topology',
            label: (
              <span>
                <ApartmentOutlined /> {t('optimization.topology')}
              </span>
            ),
            children: (
              <div>
                <Card
                  title={
                    <Space>
                      <ApartmentOutlined style={{ fontSize: 18 }} />
                      <span>{t('optimization.topoConfig')}</span>
                    </Space>
                  }
                  style={{ marginBottom: 16 }}
                >
                  <Spin spinning={loadingBuiltins}>
                    <Space direction="vertical" style={{ width: '100%' }} size="middle">
                      <Row gutter={16}>
                        <Col span={8}>
                          <div style={{ marginBottom: 8 }}><Text strong>{t('optimization.designRegions')}</Text></div>
                          <Select
                            mode="multiple"
                            value={selectedRegions}
                            onChange={setSelectedRegions}
                            options={regionOptions}
                            style={{ width: '100%' }}
                            placeholder={t('optimization.selectRegions')}
                          />
                        </Col>
                        <Col span={8}>
                          <div style={{ marginBottom: 8 }}><Text strong>{t('optimization.loadCases')}</Text></div>
                          <Select
                            mode="multiple"
                            value={selectedLoadCases}
                            onChange={setSelectedLoadCases}
                            options={loadCaseOptions}
                            style={{ width: '100%' }}
                            placeholder={t('optimization.selectLoadCases')}
                          />
                        </Col>
                        <Col span={8}>
                          <div style={{ marginBottom: 8 }}><Text strong>{t('optimization.boundaryConditions')}</Text></div>
                          <Select
                            mode="multiple"
                            value={selectedBCs}
                            onChange={setSelectedBCs}
                            options={bcOptions}
                            style={{ width: '100%' }}
                            placeholder={t('optimization.selectBCs')}
                          />
                        </Col>
                      </Row>
                      <Row gutter={16}>
                        <Col span={6}>
                          <div style={{ marginBottom: 8 }}><Text strong>{t('optimization.method')}</Text></div>
                          <Select
                            value={topoMethod}
                            onChange={setTopoMethod}
                            options={Object.entries(methodLabels).map(([k, v]) => ({ value: k, label: v }))}
                            style={{ width: '100%' }}
                          />
                        </Col>
                        <Col span={6}>
                          <div style={{ marginBottom: 8 }}><Text strong>{t('optimization.maxIterations')}</Text></div>
                          <InputNumber
                            value={topoMaxIter}
                            onChange={(v) => setTopoMaxIter(v || 50)}
                            min={1}
                            max={500}
                            style={{ width: '100%' }}
                          />
                        </Col>
                        <Col span={6}>
                          <div style={{ marginBottom: 8 }}><Text strong>{t('optimization.penaltyFactor')}</Text></div>
                          <InputNumber
                            value={topoPenalty}
                            onChange={(v) => setTopoPenalty(v || 3.0)}
                            min={1}
                            max={10}
                            step={0.5}
                            style={{ width: '100%' }}
                          />
                        </Col>
                        <Col span={6}>
                          <div style={{ marginBottom: 8 }}><Text strong>{t('optimization.filterRadius')}</Text></div>
                          <InputNumber
                            value={topoFilterRadius}
                            onChange={(v) => setTopoFilterRadius(v || 1.5)}
                            min={0.5}
                            max={10}
                            step={0.5}
                            style={{ width: '100%' }}
                          />
                        </Col>
                      </Row>
                      <Row>
                        <Col span={24}>
                          <Button
                            type="primary"
                            icon={<ThunderboltOutlined />}
                            onClick={handleCreateAndRunTopology}
                            loading={topoLoading}
                            size="large"
                          >
                            {t('optimization.createAndRunTopo')}
                          </Button>
                        </Col>
                      </Row>
                    </Space>
                  </Spin>
                </Card>

                {topoTask && (
                  <>
                    {topoTask.status === 'failed' && (
                      <Alert
                        type="error"
                        message={t('optimization.topoFailed')}
                        description={topoTask.error_message}
                        showIcon
                        style={{ marginBottom: 16 }}
                      />
                    )}

                    <Row gutter={16} style={{ marginBottom: 16 }}>
                      <Col span={6}>
                        <Card>
                          <Statistic
                            title={t('common.status')}
                            value={topoStatusConfig[topoTask.status]?.label || topoTask.status}
                            valueStyle={{ color: topoStatusConfig[topoTask.status]?.color === 'success' ? '#3f8600' : undefined }}
                          />
                        </Card>
                      </Col>
                      <Col span={6}>
                        <Card>
                          <Statistic
                            title={t('optimization.massReduction')}
                            value={topoTask.result?.mass_reduction_pct ?? 0}
                            suffix="%"
                            prefix={<ThunderboltOutlined />}
                            valueStyle={{ color: '#3f8600' }}
                          />
                        </Card>
                      </Col>
                      <Col span={6}>
                        <Card>
                          <Statistic
                            title={t('optimization.finalVolumeFraction')}
                            value={topoTask.result?.final_volume_fraction ?? 0}
                            precision={4}
                          />
                        </Card>
                      </Col>
                      <Col span={6}>
                        <Card>
                          <Statistic
                            title={t('optimization.method')}
                            value={methodLabels[topoTask.method] || topoTask.method}
                          />
                        </Card>
                      </Col>
                    </Row>

                    {topoTask.result && (
                      <Card title={t('optimization.result')} style={{ marginBottom: 16 }}>
                        <Descriptions bordered column={2} size="small">
                          <Descriptions.Item label={t('optimization.iterationCount')}>{topoTask.result.iteration_count}</Descriptions.Item>
                          <Descriptions.Item label={t('optimization.converged')}>
                            {topoTask.result.converged ? <Tag color="green">{t('status.converged')}</Tag> : <Tag color="orange">{t('status.notConverged')}</Tag>}
                          </Descriptions.Item>
                          <Descriptions.Item label={t('optimization.compliance')}>{topoTask.result.compliance}</Descriptions.Item>
                          <Descriptions.Item label={t('optimization.maxStress')}>{topoTask.result.max_stress} MPa</Descriptions.Item>
                          <Descriptions.Item label={t('optimization.elementCount')}>{topoTask.result.element_count}</Descriptions.Item>
                          <Descriptions.Item label={t('optimization.massReduction')}>
                            <Progress
                              percent={topoTask.result.mass_reduction_pct}
                              strokeColor="#52c41a"
                              format={(p) => `${p?.toFixed(1)}%`}
                            />
                          </Descriptions.Item>
                        </Descriptions>
                      </Card>
                    )}

                    {topoTask.iteration_history?.length > 0 && (
                      <Card title={t('optimization.iterationHistory')}>
                        <Table
                          columns={topoHistoryColumns}
                          dataSource={topoTask.iteration_history.map((h, i) => ({ ...h, key: i }))}
                          size="small"
                          pagination={false}
                        />
                      </Card>
                    )}
                  </>
                )}

                {!topoTask && !topoLoading && (
                  <Card>
                    <Empty
                      image={<ApartmentOutlined style={{ fontSize: 64, color: '#1890ff' }} />}
                      description={t('optimization.configureTopoAndRun')}
                    />
                  </Card>
                )}
              </div>
            ),
          },
        ]}
      />
    </div>
  )
}
