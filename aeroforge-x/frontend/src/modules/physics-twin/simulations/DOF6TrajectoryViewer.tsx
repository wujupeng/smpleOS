import React, { useEffect, useRef, useState } from 'react';
import { Card, Select, Button, Space, Row, Col, Statistic, Tag } from 'antd';
import { usePhysicsPluginStore } from '../../../stores/physicsPluginStore';

const DOF6TrajectoryViewer: React.FC = () => {
  const { trajectoryData, executeModel, loading } = usePhysicsPluginStore();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [fidelity, setFidelity] = useState('low');
  const [steps, setSteps] = useState(100);
  const [dt, setDt] = useState(0.01);

  useEffect(() => {
    drawTrajectory();
  }, [trajectoryData]);

  const drawTrajectory = () => {
    const canvas = canvasRef.current;
    if (!canvas || trajectoryData.time.length === 0) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    ctx.fillStyle = '#0a0a2e';
    ctx.fillRect(0, 0, w, h);

    ctx.strokeStyle = '#1a3a5c';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 10; i++) {
      ctx.beginPath(); ctx.moveTo((w / 10) * i, 0); ctx.lineTo((w / 10) * i, h); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(0, (h / 10) * i); ctx.lineTo(w, (h / 10) * i); ctx.stroke();
    }

    const positions = trajectoryData.position;
    if (positions.length < 2) return;

    const xs = positions.map((p) => p[0]);
    const ys = positions.map((p) => p[1]);
    const zs = positions.map((p) => p[2] || 0);

    const xMin = Math.min(...xs); const xMax = Math.max(...xs);
    const yMin = Math.min(...ys); const yMax = Math.max(...ys);
    const xRange = xMax - xMin || 1; const yRange = yMax - yMin || 1;
    const padding = 40;

    const toScreenX = (v: number) => padding + ((v - xMin) / xRange) * (w - 2 * padding);
    const toScreenY = (v: number) => h - padding - ((v - yMin) / yRange) * (h - 2 * padding);

    ctx.strokeStyle = '#00ff88';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(toScreenX(xs[0]), toScreenY(ys[0]));
    for (let i = 1; i < xs.length; i++) {
      ctx.lineTo(toScreenX(xs[i]), toScreenY(ys[i]));
    }
    ctx.stroke();

    ctx.fillStyle = '#ff4444';
    ctx.beginPath();
    ctx.arc(toScreenX(xs[xs.length - 1]), toScreenY(ys[ys.length - 1]), 5, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#00ff88';
    ctx.beginPath();
    ctx.arc(toScreenX(xs[0]), toScreenY(ys[0]), 4, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#aaa';
    ctx.font = '12px monospace';
    ctx.fillText('X-Y Trajectory (Top View)', 10, 20);
    ctx.fillText(`Points: ${positions.length}`, 10, 36);
  };

  const runSimulation = async () => {
    for (let i = 0; i < steps; i++) {
      await executeModel({
        model_type: 'dof6',
        fidelity_level: fidelity,
        dt,
        parameters: {},
      });
    }
  };

  const lastPos = trajectoryData.position.length > 0 ? trajectoryData.position[trajectoryData.position.length - 1] : [0, 0, 0];
  const lastAtt = trajectoryData.attitude.length > 0 ? trajectoryData.attitude[trajectoryData.attitude.length - 1] : [0, 0, 0];

  return (
    <Card title="6DOF Trajectory Viewer">
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={4}><Statistic title="X (m)" value={lastPos[0]?.toFixed(2)} /></Col>
        <Col span={4}><Statistic title="Y (m)" value={lastPos[1]?.toFixed(2)} /></Col>
        <Col span={4}><Statistic title="Z (m)" value={lastPos[2]?.toFixed(2)} /></Col>
        <Col span={4}><Statistic title="φ (deg)" value={lastAtt[0]?.toFixed(2)} /></Col>
        <Col span={4}><Statistic title="θ (deg)" value={lastAtt[1]?.toFixed(2)} /></Col>
        <Col span={4}><Statistic title="ψ (deg)" value={lastAtt[2]?.toFixed(2)} /></Col>
      </Row>

      <canvas ref={canvasRef} width={800} height={400} style={{ width: '100%', border: '1px solid #333', borderRadius: 8, marginBottom: 16 }} />

      <Space>
        <Select value={fidelity} onChange={setFidelity} style={{ width: 120 }} options={[
          { label: 'Low', value: 'low' }, { label: 'Mid', value: 'mid' }, { label: 'Detail', value: 'detail' },
        ]} />
        <Tag>Steps: {trajectoryData.time.length}</Tag>
        <Button type="primary" onClick={runSimulation} loading={loading}>Run Simulation</Button>
      </Space>
    </Card>
  );
};

export default DOF6TrajectoryViewer;