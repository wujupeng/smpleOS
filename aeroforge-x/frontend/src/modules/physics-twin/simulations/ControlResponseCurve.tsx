import React, { useEffect, useRef, useState } from 'react';
import { Card, Select, Button, Space, Row, Col, Statistic, Tag } from 'antd';
import { usePhysicsPluginStore } from '../../../stores/physicsPluginStore';

const ControlResponseCurve: React.FC = () => {
  const { controlData, executeModel, loading } = usePhysicsPluginStore();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [fidelity, setFidelity] = useState('mid');
  const [steps, setSteps] = useState(200);

  useEffect(() => {
    drawCurves();
  }, [controlData]);

  const drawCurves = () => {
    const canvas = canvasRef.current;
    if (!canvas || controlData.time.length === 0) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#0a0a2e';
    ctx.fillRect(0, 0, w, h);

    const t = controlData.time;
    const tMin = t[0]; const tMax = t[t.length - 1]; const tRange = tMax - tMin || 1;
    const padL = 60; const padR = 20; const padT = 30; const padB = 20;

    const outputs = controlData.output;
    if (outputs.length === 0) return;

    const numAxes = outputs[0]?.length || 1;
    const axisLabels = ['Aileron δa', 'Elevator δe', 'Rudder δr'];
    const axisColors = ['#ff4444', '#00ff88', '#44aaff'];

    const chartH = (h - padT - padB) / numAxes;

    for (let ax = 0; ax < numAxes; ax++) {
      const y0 = padT + ax * chartH;
      const vals = outputs.map((o) => o[ax] || 0);
      const vMin = Math.min(...vals); const vMax = Math.max(...vals);
      const vRange = vMax - vMin || 1;

      ctx.fillStyle = '#1a2a3a';
      ctx.fillRect(padL, y0, w - padL - padR, chartH - 4);

      ctx.strokeStyle = axisColors[ax] || '#aaa';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      vals.forEach((v, i) => {
        const x = padL + ((t[i] - tMin) / tRange) * (w - padL - padR);
        const y = y0 + chartH - 4 - ((v - vMin) / vRange) * (chartH - 8);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.stroke();

      ctx.fillStyle = axisColors[ax] || '#aaa';
      ctx.font = '11px monospace';
      ctx.fillText(axisLabels[ax] || `Axis ${ax}`, 4, y0 + 14);
      if (vals.length > 0) ctx.fillText(vals[vals.length - 1].toFixed(3), 4, y0 + 28);
    }

    if (controlData.mode.length > 0) {
      ctx.fillStyle = '#aaa';
      ctx.font = '11px monospace';
      ctx.fillText(`Mode: ${controlData.mode[controlData.mode.length - 1]}`, w - 200, 16);
    }
  };

  const runSimulation = async () => {
    for (let i = 0; i < steps; i++) {
      await executeModel({
        model_type: 'control',
        fidelity_level: fidelity,
        dt: 0.01,
        parameters: {},
      });
    }
  };

  const lastOutput = controlData.output.length > 0 ? controlData.output[controlData.output.length - 1] : [0, 0, 0];
  const lastMode = controlData.mode.length > 0 ? controlData.mode[controlData.mode.length - 1] : '-';

  return (
    <Card title="Control Response Curves">
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Statistic title="Aileron" value={lastOutput[0]?.toFixed(3)} suffix="deg" /></Col>
        <Col span={6}><Statistic title="Elevator" value={lastOutput[1]?.toFixed(3)} suffix="deg" /></Col>
        <Col span={6}><Statistic title="Rudder" value={lastOutput[2]?.toFixed(3)} suffix="deg" /></Col>
        <Col span={6}><Statistic title="Autopilot Mode" value={lastMode} /></Col>
      </Row>

      <canvas ref={canvasRef} width={800} height={400} style={{ width: '100%', border: '1px solid #333', borderRadius: 8, marginBottom: 16 }} />

      <Space>
        <Select value={fidelity} onChange={setFidelity} style={{ width: 120 }} options={[
          { label: 'Low (PID)', value: 'low' }, { label: 'Mid (Gain-Sched)', value: 'mid' }, { label: 'Detail (LQR)', value: 'detail' },
        ]} />
        <Tag>Steps: {controlData.time.length}</Tag>
        <Button type="primary" onClick={runSimulation} loading={loading}>Run Control Simulation</Button>
      </Space>
    </Card>
  );
};

export default ControlResponseCurve;