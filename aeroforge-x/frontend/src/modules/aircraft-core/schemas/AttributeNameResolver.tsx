import React, { useState } from 'react';
import { Card, Input, Button, Space, Typography, Tag, Alert, Descriptions } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { schemaApi } from '../../../api/schemaApi';

const { Text } = Typography;

const COMMON_ALIASES: Record<string, string[]> = {
  wingspan: ['span', 'wing_span', 'Wingspan'],
  chord_length: ['chord', 'mean_chord', 'Chord Length'],
  sweep_angle: ['sweep', 'sweepback', 'Sweep Angle'],
  wing_area: ['S_wing', 'reference_area', 'Wing Area'],
  design_weight: ['MTOW', 'max_takeoff_weight', 'Design Weight'],
  yield_strength: ['sigma_y', 'yield', 'Yield Strength'],
  engine_thrust: ['thrust', 'max_thrust', 'Engine Thrust'],
};

const AttributeNameResolver: React.FC = () => {
  const [inputName, setInputName] = useState('');
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleResolve = async () => {
    if (!inputName.trim()) return;
    setError(null);
    try {
      const data = await schemaApi.resolveAttributeName(inputName.trim());
      setResult(data);
    } catch {
      const localMatch = Object.entries(COMMON_ALIASES).find(
        ([canonical, aliases]) => aliases.some((a) => a.toLowerCase() === inputName.trim().toLowerCase()) || canonical.toLowerCase() === inputName.trim().toLowerCase()
      );
      if (localMatch) {
        setResult({ canonical_name: localMatch[0], aliases: localMatch[1], resolved_from: inputName });
      } else {
        setResult(null);
        setError(`No canonical name found for "${inputName}"`);
      }
    }
  };

  return (
    <Card title="Attribute Name Resolver">
      <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
        <Input
          placeholder="Enter attribute name or alias (e.g. span, MTOW, sigma_y)"
          value={inputName}
          onChange={(e) => setInputName(e.target.value)}
          onPressEnter={handleResolve}
          prefix={<SearchOutlined />}
        />
        <Button type="primary" onClick={handleResolve}>Resolve</Button>
      </Space.Compact>

      {error && <Alert type="warning" message={error} style={{ marginBottom: 16 }} />}

      {result && (
        <Descriptions bordered column={1}>
          <Descriptions.Item label="Canonical Name">
            <Tag color="blue">{result.canonical_name}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="Known Aliases">
            <Space wrap>
              {result.aliases?.map((a: string) => (
                <Tag key={a} color={a === inputName ? 'green' : 'default'}>{a}</Tag>
              ))}
            </Space>
          </Descriptions.Item>
          {result.dimension && <Descriptions.Item label="Dimension">{result.dimension}</Descriptions.Item>}
          {result.canonical_unit && <Descriptions.Item label="Canonical Unit"><Tag>{result.canonical_unit}</Tag></Descriptions.Item>}
          {result.resolved_from && (
            <Descriptions.Item label="Resolved From">
              <Text code>{result.resolved_from}</Text> → <Tag color="green">{result.canonical_name}</Tag>
            </Descriptions.Item>
          )}
        </Descriptions>
      )}

      <Card title="Common Attribute Mappings" size="small" style={{ marginTop: 16 }}>
        {Object.entries(COMMON_ALIASES).map(([canonical, aliases]) => (
          <div key={canonical} style={{ marginBottom: 4 }}>
            <Tag color="blue">{canonical}</Tag>
            <Text type="secondary">←</Text>
            {' '}
            {aliases.map((a) => <Tag key={a} style={{ cursor: 'pointer' }} onClick={() => { setInputName(a); }}>{a}</Tag>)}
          </div>
        ))}
      </Card>
    </Card>
  );
};

export default AttributeNameResolver;