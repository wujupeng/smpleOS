import React, { useState } from 'react';
import { Card, Button, Input, Select, Space, Typography, Table, Tag, Descriptions, Tabs, InputNumber } from 'antd';
import { ExperimentOutlined } from '@ant-design/icons';

const { Title } = Typography;
const API_BASE = '/api/v1';

const OptimizationPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('multi');
  const [loading, setLoading] = useState(false);
  const [multiResult, setMultiResult] = useState<any>(null);
  const [topoResult, setTopoResult] = useState<any>(null);

  const runMultiObjective = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ai/optimization/multi-objective`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: `OPT-${Date.now()}`,
          objectives: [
            { name: 'weight', direction: 'minimize', weight: 0.4 },
            { name: 'cost', direction: 'minimize', weight: 0.3 },
            { name: 'lift_drag_ratio', direction: 'maximize', weight: 0.3 },
          ],
          constraints: [
            { name: 'min_wingspan', type: 'greater_than', bound: 20.0, variable: 'wingspan_m' },
            { name: 'max_mtow', type: 'less_than', bound: 200000.0, variable: 'mtow_kg' },
          ],
          design_variables: {
            wingspan_m: { min: 20.0, max: 65.0 },
            fuselage_length_m: { min: 25.0, max: 70.0 },
            mtow_kg: { min: 30000.0, max: 300000.0 },
            aspect_ratio: { min: 7.0, max: 12.0 },
            sweep_angle_deg: { min: 15.0, max: 35.0 },
          },
          max_iterations: 50,
        }),
      });
      const data = await res.json();
      setMultiResult(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const runTopology = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ai/optimization/topology`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          component_type: 'wing_spar',
          load_conditions: { loads: [{ type: 'bending', magnitude: 150.0, unit: 'kN' }] },
          material_constraints: { yield_stress_mpa: 600.0, density_kg_m3: 1600.0 },
          volume_fraction: 0.3,
          max_iterations: 30,
        }),
      });
      const data = await res.json();
      setTopoResult(data);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const paretoColumns = [
    { title: 'Point ID', dataIndex: 'point_id', key: 'id' },
    {
      title: 'Feasible',
      dataIndex: 'is_feasible',
      key: 'feasible',
      render: (f: boolean) => <Tag color={f ? 'green' : 'red'}>{f ? 'Yes' : 'No'}</Tag>,
    },
    {
      title: 'Weight (kg)',
      key: 'weight',
      render: (_: any, r: any) => r.objectives?.weight?.toFixed(0) || '-',
    },
    {
      title: 'Cost ($)',
      key: 'cost',
      render: (_: any, r: any) => r.objectives?.cost?.toFixed(0) || '-',
    },
    {
      title: 'L/D',
      key: 'ld',
      render: (_: any, r: any) => r.objectives?.lift_drag_ratio?.toFixed(1) || '-',
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}><ExperimentOutlined /> Optimization</Title>
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={[
        {
          key: 'multi',
          label: 'Multi-Objective Optimization',
          children: (
            <>
              <Card style={{ marginBottom: 16 }}>
                <Space>
                  <Button type="primary" onClick={runMultiObjective} loading={loading}>
                    Run Multi-Objective Optimization
                  </Button>
                  <span>Objectives: Minimize Weight & Cost, Maximize L/D</span>
                </Space>
              </Card>
              {multiResult && (
                <Card title="Optimization Results">
                  <Descriptions bordered column={3} size="small">
                    <Descriptions.Item label="Result ID">{multiResult.result_id}</Descriptions.Item>
                    <Descriptions.Item label="Iterations">{multiResult.iteration_count}</Descriptions.Item>
                    <Descriptions.Item label="Converged">
                      <Tag color={multiResult.convergence_achieved ? 'green' : 'orange'}>
                        {multiResult.convergence_achieved ? 'Yes' : 'No'}
                      </Tag>
                    </Descriptions.Item>
                  </Descriptions>
                  {multiResult.best_compromise && (
                    <Card type="inner" title="Best Compromise" style={{ marginTop: 12 }}>
                      <Descriptions bordered column={2} size="small">
                        {Object.entries(multiResult.best_compromise.design_variables || {}).map(([k, v]) => (
                          <Descriptions.Item key={k} label={k.replace(/_/g, ' ')}>{String(Number(v).toFixed(2))}</Descriptions.Item>
                        ))}
                        {Object.entries(multiResult.best_compromise.objectives || {}).map(([k, v]) => (
                          <Descriptions.Item key={k} label={k.replace(/_/g, ' ')}>{String(Number(v).toFixed(2))}</Descriptions.Item>
                        ))}
                      </Descriptions>
                    </Card>
                  )}
                  <Card type="inner" title="Pareto Front" style={{ marginTop: 12 }}>
                    <Table
                      dataSource={multiResult.pareto_front?.slice(0, 20) || []}
                      columns={paretoColumns}
                      rowKey="point_id"
                      size="small"
                      pagination={{ pageSize: 10 }}
                    />
                  </Card>
                </Card>
              )}
            </>
          ),
        },
        {
          key: 'topology',
          label: 'Topology Optimization',
          children: (
            <>
              <Card style={{ marginBottom: 16 }}>
                <Space>
                  <Button type="primary" onClick={runTopology} loading={loading}>
                    Run Topology Optimization (Wing Spar)
                  </Button>
                </Space>
              </Card>
              {topoResult && (
                <Card title="Topology Optimization Results">
                  <Descriptions bordered column={2} size="small">
                    <Descriptions.Item label="Result ID">{topoResult.result_id}</Descriptions.Item>
                    <Descriptions.Item label="Component">{topoResult.component_type}</Descriptions.Item>
                    <Descriptions.Item label="Weight Reduction">
                      <Tag color={topoResult.weight_reduction_percentage > 20 ? 'green' : 'orange'}>
                        {topoResult.weight_reduction_percentage?.toFixed(1)}%
                      </Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="Converged">
                      <Tag color={topoResult.convergence_achieved ? 'green' : 'orange'}>
                        {topoResult.convergence_achieved ? 'Yes' : 'No'}
                      </Tag>
                    </Descriptions.Item>
                    <Descriptions.Item label="Max Stress">{topoResult.stress_distribution?.max_stress_mpa?.toFixed(1)} MPa</Descriptions.Item>
                    <Descriptions.Item label="Safety Factor">{topoResult.stress_distribution?.safety_factor?.toFixed(2)}</Descriptions.Item>
                  </Descriptions>
                </Card>
              )}
            </>
          ),
        },
      ]} />
    </div>
  );
};

export default OptimizationPage;