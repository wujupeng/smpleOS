import React, { useEffect, useState } from 'react';
import { Card, InputNumber, Select, Button, Space, Typography, Divider, Alert, Row, Col, Statistic } from 'antd';
import { SwapOutlined } from '@ant-design/icons';
import { schemaApi } from '../../../api/schemaApi';

const { Text } = Typography;

const DIMENSIONS = [
  'length', 'mass', 'time', 'temperature', 'velocity', 'force', 'pressure', 'energy', 'power', 'angle',
];

const UNIT_MAP: Record<string, string[]> = {
  length: ['m', 'mm', 'cm', 'km', 'in', 'ft', 'yd'],
  mass: ['kg', 'g', 'mg', 'lb', 'oz', 'slug'],
  time: ['s', 'ms', 'min', 'h'],
  temperature: ['K', 'degC', 'degF'],
  velocity: ['m/s', 'km/h', 'ft/s', 'knot', 'mph'],
  force: ['N', 'kN', 'lbf', 'kgf'],
  pressure: ['Pa', 'kPa', 'MPa', 'bar', 'psi', 'atm'],
  energy: ['J', 'kJ', 'MJ', 'BTU', 'kWh', 'ft_lbf'],
  power: ['W', 'kW', 'MW', 'hp'],
  angle: ['rad', 'deg'],
};

const UnitConverter: React.FC = () => {
  const [dimension, setDimension] = useState('length');
  const [fromUnit, setFromUnit] = useState('m');
  const [toUnit, setToUnit] = useState('ft');
  const [value, setValue] = useState(1);
  const [result, setResult] = useState<number | null>(null);
  const [compatible, setCompatible] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const units = UNIT_MAP[dimension] || [];
    setFromUnit(units[0] || '');
    setToUnit(units[1] || '');
    setResult(null);
    setCompatible(null);
  }, [dimension]);

  const handleConvert = async () => {
    setError(null);
    try {
      const compatData = await schemaApi.validateDimensionalCompatibility(fromUnit, toUnit);
      setCompatible(compatData.compatible);
      if (!compatData.compatible) {
        setResult(null);
        return;
      }
      const data = await schemaApi.convertUnit(value, fromUnit, toUnit);
      setResult(data.converted_value);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleSwap = () => {
    setFromUnit(toUnit);
    setToUnit(fromUnit);
    setResult(null);
  };

  const units = UNIT_MAP[dimension] || [];

  return (
    <Card title="Unit Converter">
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <div>
          <Text strong>Dimension: </Text>
          <Select value={dimension} onChange={setDimension} style={{ width: 200 }}>
            {DIMENSIONS.map((d) => <Select.Option key={d} value={d}>{d}</Select.Option>)}
          </Select>
        </div>

        <Row gutter={16} align="middle">
          <Col span={10}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text type="secondary">From</Text>
              <Select value={fromUnit} onChange={setFromUnit} style={{ width: '100%' }}>
                {units.map((u) => <Select.Option key={u} value={u}>{u}</Select.Option>)}
              </Select>
              <InputNumber value={value} onChange={(v) => { setValue(v || 0); setResult(null); }} style={{ width: '100%' }} min={0} />
            </Space>
          </Col>
          <Col span={4} style={{ textAlign: 'center' }}>
            <Button icon={<SwapOutlined />} onClick={handleSwap} type="text" />
          </Col>
          <Col span={10}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text type="secondary">To</Text>
              <Select value={toUnit} onChange={setToUnit} style={{ width: '100%' }}>
                {units.map((u) => <Select.Option key={u} value={u}>{u}</Select.Option>)}
              </Select>
              <Statistic value={result !== null ? result : '-'} suffix={toUnit} />
            </Space>
          </Col>
        </Row>

        <Button type="primary" onClick={handleConvert} block>Convert</Button>

        {compatible === false && <Alert type="error" message="Incompatible dimensions" />}
        {error && <Alert type="error" message={error} />}
      </Space>
    </Card>
  );
};

export default UnitConverter;