import React, { useEffect, useRef, useState } from 'react';
import { Card, Select, Button, Space, Row, Col, Statistic, Tag, Progress } from 'antd';
import { usePhysicsPluginStore } from '../../../stores/physicsPluginStore';

const BatterySOCCurve: React.FC = () => {
  const { batteryData, executeModel, loading } = usePhysicsPluginStore();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [fidelity, setFidelity] = useState('mid');
  const [steps, setSteps] = useState(200);

  useEffect(() => {
    drawCurves();
  }, [batteryData]);

  const drawCurves = () => {
    const canvas = canvasRef.current;
    if (!canvas || batteryData.time.length === 0) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#0a0a2e';
    ctx.fillRect(0, 0, w, h);

    const charts = [
      { data: batteryData.soc, label: 'SOC', color: '#00ff88', yMin: 0, yMax: 1 },
      { data: batteryData.voltage, label: 'Voltage (V)', color: '#ffaa00', yMin: 0, yMax: Math.max(...batteryData.voltage, 5) * 1.1 },
      { data: batteryData.temperature, label: 'Temp (°C)', color: '#ff4444', yMin: 0, yMax: Math.max(...batteryData.temperature, 25) * 1.2 },
      { data: batteryData.soh, label: 'SOH', color: '#44aaff', yMin: 0, yMax: 1 },
    ];

    const chartH = (h - 20) / charts.length;
    const t = batteryData.time;
    const tMin = t[0]; const tMax = t[t.length - 1]; const tRange = tMax - tMin || 1;
    const padL = 80; const padR = 20;

    charts.forEach((chart, idx) => {
      const y0 = 10 + idx * chartH;
      const yRange = chart.yMax - chart.yMin || 1;

      ctx.fillStyle = '#1a2a3a';
      ctx.fillRect(padL, y0, w - padL - padR, chartH - 10);

      ctx.strokeStyle = chart.color;
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      chart.data.forEach((v, i) => {
        const x = padL + ((t[i] - tMin) / tRange) * (w - padL - padR);
        const y = y0 + chartH - 10 - ((v - chart.yMin) / yRange) * (chartH - 20);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.stroke();

      ctx.fillStyle = chart.color;
      ctx.font = '11px monospace';
      ctx.fillText(chart.label, 4, y0 + 14);
      if (chart.data.length > 0) {
        ctx.fillText(chart.data[chart.data.length - 1].toFixed(3), 4, y0 + 28);
      }
    });
  };

  const runSimulation = async () => {
    for (let i = 0; i < steps; i++) {
      await executeModel({
        model_type: 'battery',
        fidelity_level: fidelity,
        dt: 1.0,
        parameters: {},
      });
    }
  };

  const lastSoc = batteryData.soc.length > 0 ? batteryData.soc[batteryData.soc.length - 1] : 0;
  const lastSoh = batteryData.soh.length > 0 ? batteryData.soh[batteryData.soh.length - 1] : 1;
  const lastTemp = batteryData.temperature.length > 0 ? batteryData.temperature[batteryData.temperature.length - 1] : 25;
  const lastVoltage = batteryData.voltage.length > 0 ? batteryData.voltage[batteryData.voltage.length - 1] : 0;

  return (
    <Card title="Battery SOC / SOH / Temperature Curves">
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Progress type="circle" percent={Math.round(lastSoc * 100)} format={() => `${(lastSoc * 100).toFixed(1)}%`} strokeColor={lastSoc < 0.2 ? '#ff4444' : '#00ff88'} />
          <div style={{ textAlign: 'center', marginTop: 4 }}>SOC</div>
        </Col>
        <Col span={6}><Statistic title="SOH" value={(lastSoh * 100).toFixed(1)} suffix="%" valueStyle={{ color: lastSoh < 0.8 ? '#ff4444' : '#3f8600' }} /></Col>
        <Col span={6}><Statistic title="Temperature" value={lastTemp.toFixed(1)} suffix="°C" valueStyle={{ color: lastTemp > 60 ? '#cf1322' : '#3f8600' }} /></Col>
        <Col span={6}><Statistic title="Voltage" value={lastVoltage.toFixed(2)} suffix="V" /></Col>
      </Row>

      <canvas ref={canvasRef} width={800} height={400} style={{ width: '100%', border: '1px solid #333', borderRadius: 8, marginBottom: 16 }} />

      <Space>
        <Select value={fidelity} onChange={setFidelity} style={{ width: 120 }} options={[
          { label: 'Low', value: 'low' }, { label: 'Mid', value: 'mid' }, { label: 'Detail', value: 'detail' },
        ]} />
        <Tag>Steps: {batteryData.time.length}</Tag>
        <Button type="primary" onClick={runSimulation} loading={loading}>Run Battery Simulation</Button>
      </Space>
    </Card>
  );
};

export default BatterySOCCurve;