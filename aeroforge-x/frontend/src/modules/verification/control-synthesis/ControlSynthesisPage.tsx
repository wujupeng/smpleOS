import React, { useState } from 'react';
import { Card, Form, InputNumber, Button, Row, Col, Statistic, Table, Tabs, Tag, Descriptions } from 'antd';
import { ControlOutlined } from '@ant-design/icons';

const { TabPane } = Tabs;

const ControlSynthesisPage: React.FC = () => {
  const [pidResult, setPidResult] = useState<any>(null);
  const [lqrResult, setLqrResult] = useState<any>(null);
  const [comparison, setComparison] = useState<any>(null);

  const handlePID = async (values: any) => {
    const res = await fetch('/api/v1/verification/control-synthesis/pid', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values),
    });
    setPidResult(await res.json());
  };

  const handleLQR = async (values: any) => {
    const res = await fetch('/api/v1/verification/control-synthesis/lqr', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values),
    });
    setLqrResult(await res.json());
  };

  const handleCompare = async () => {
    const res = await fetch('/api/v1/verification/control-synthesis/compare', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}),
    });
    setComparison(await res.json());
  };

  return (
    <div style={{ padding: 24 }}>
      <Tabs defaultActiveKey="pid">
        <TabPane tab="PID" key="pid">
          <Card title="PID Control Law Synthesis">
            <Form layout="vertical" onFinish={handlePID}>
              <Row gutter={16}>
                <Col span={8}><Form.Item name="natural_frequency_hz" label="Nat. Freq (Hz)" initialValue={1.5}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
                <Col span={8}><Form.Item name="damping_ratio" label="Damping Ratio" initialValue={0.5}><InputNumber min={0} max={1} step={0.1} style={{width:'100%'}} /></Form.Item></Col>
                <Col span={8}><Form.Item name="time_constant_s" label="Time Const (s)" initialValue={0.1}><InputNumber min={0} style={{width:'100%'}} /></Form.Item></Col>
              </Row>
              <Button type="primary" htmlType="submit" icon={<ControlOutlined />}>Generate PID</Button>
            </Form>
          </Card>
          {pidResult && <Card style={{marginTop:16}}>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="Kp">{pidResult.pid_params.kp}</Descriptions.Item>
              <Descriptions.Item label="Ki">{pidResult.pid_params.ki}</Descriptions.Item>
              <Descriptions.Item label="Kd">{pidResult.pid_params.kd}</Descriptions.Item>
              <Descriptions.Item label="Gain Margin">{pidResult.stability_margins.gain_margin_db} dB</Descriptions.Item>
              <Descriptions.Item label="Phase Margin">{pidResult.stability_margins.phase_margin_deg}°</Descriptions.Item>
              <Descriptions.Item label="Sufficient">{pidResult.stability_margins.is_sufficient ? <Tag color="green">Yes</Tag> : <Tag color="red">No</Tag>}</Descriptions.Item>
            </Descriptions>
          </Card>}
        </TabPane>

        <TabPane tab="LQR" key="lqr">
          <Card title="LQR Control Law Synthesis">
            <Form layout="vertical" onFinish={handleLQR}>
              <Row gutter={16}>
                <Col span={8}><Form.Item name="state_dimension" label="State Dim" initialValue={4}><InputNumber min={1} style={{width:'100%'}} /></Form.Item></Col>
                <Col span={8}><Form.Item name="input_dimension" label="Input Dim" initialValue={1}><InputNumber min={1} style={{width:'100%'}} /></Form.Item></Col>
              </Row>
              <Button type="primary" htmlType="submit">Generate LQR</Button>
            </Form>
          </Card>
          {lqrResult && <Card style={{marginTop:16}}>
            <Row gutter={16}>
              <Col span={8}><Statistic title="Gain Margin" value={lqrResult.stability_margins.gain_margin_db} suffix="dB" /></Col>
              <Col span={8}><Statistic title="Phase Margin" value={lqrResult.stability_margins.phase_margin_deg} suffix="°" /></Col>
              <Col span={8}><Statistic title="Sufficient" value={lqrResult.stability_margins.is_sufficient ? 'Yes' : 'No'} valueStyle={{color: lqrResult.stability_margins.is_sufficient ? '#3f8600' : '#cf1322'}} /></Col>
            </Row>
          </Card>}
        </TabPane>

        <TabPane tab="Compare" key="compare">
          <Card title="Compare Control Law Alternatives" extra={<Button type="primary" onClick={handleCompare}>Compare All</Button>}>
            {comparison && <Table columns={[
              { title: 'Type', dataIndex: 'type', key: 'type' },
              { title: 'Gain Margin (dB)', key: 'gm' },
              { title: 'Phase Margin (°)', key: 'pm' },
              { title: 'Satisfied', key: 'sat' },
            ]} dataSource={[
              { type: 'PID', key: 'pid', ...comparison.pid },
              { type: 'LQR', key: 'lqr', ...comparison.lqr },
              { type: 'MPC', key: 'mpc', ...comparison.mpc },
            ]} size="small" />}
            {comparison && <Alert type="info" message={`Recommended: ${comparison.recommendation?.toUpperCase()}`} style={{marginTop:16}} />}
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default ControlSynthesisPage;