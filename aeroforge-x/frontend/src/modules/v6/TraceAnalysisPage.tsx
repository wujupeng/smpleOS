import React, { useEffect, useState, useCallback } from 'react'
import { Card, Button, Space, Statistic, Row, Col, Spin, Empty, message } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { dtHardeningApi } from '../../api/v6Api'
import type { TraceNode, TraceEdge, TraceQueryResult, TraceStatistics, ConfigurationIdentity, IdentityMapping } from '../../api/types'
import TraceGraphCanvas from './trace/TraceGraphCanvas'
import TraceNodeDetailPanel from './trace/TraceNodeDetailPanel'
import ImpactAnalysisView from './trace/ImpactAnalysisView'
import TraceSearchBar from './trace/TraceSearchBar'
import DigitalThreadDashboard from './trace/DigitalThreadDashboard'

const TraceAnalysisPage: React.FC = () => {
  const [nodes, setNodes] = useState<TraceNode[]>([])
  const [edges, setEdges] = useState<TraceEdge[]>([])
  const [stats, setStats] = useState<TraceStatistics | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [highlightedNodeIds, setHighlightedNodeIds] = useState<Set<string>>(new Set())
  const [upstreamNodeIds, setUpstreamNodeIds] = useState<Set<string>>(new Set())
  const [downstreamNodeIds, setDownstreamNodeIds] = useState<Set<string>>(new Set())
  const [selectedIdentity, setSelectedIdentity] = useState<ConfigurationIdentity | null>(null)
  const [identityMappings, setIdentityMappings] = useState<IdentityMapping[]>([])
  const [loading, setLoading] = useState(false)
  const [impactCollapsed, setImpactCollapsed] = useState(false)

  const selectedNode = nodes.find(n => n.node_id === selectedNodeId) || null

  const loadStatistics = useCallback(async () => {
    try {
      const data = await dtHardeningApi.getTraceStatistics() as any
      setStats(data)
    } catch {}
  }, [])

  const loadGraphFromRoot = useCallback(async () => {
    setLoading(true)
    try {
      const statData = await dtHardeningApi.getTraceStatistics() as any as TraceStatistics
      setStats(statData)
      if (statData.node_count === 0) {
        setNodes([])
        setEdges([])
        setLoading(false)
        return
      }

      const allNodes: TraceNode[] = await dtHardeningApi.listTraceNodes() as any
      if (!allNodes || allNodes.length === 0) {
        setNodes([])
        setEdges([])
        setLoading(false)
        return
      }

      const startId = allNodes[0].node_id
      const result = await dtHardeningApi.traceQuery(startId, 'both', 10, 500) as any as TraceQueryResult
      setNodes(result.nodes || allNodes)
      setEdges(result.edges || [])
    } catch (e) {
      console.error('Failed to load graph:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  const loadFullGraph = useCallback(async () => {
    setLoading(true)
    try {
      const rebuildResult = await dtHardeningApi.rebuildGraph() as any
      const statData = await dtHardeningApi.getTraceStatistics() as any as TraceStatistics
      setStats(statData)
      if (statData.node_count > 0) {
        const allNodes: TraceNode[] = await dtHardeningApi.listTraceNodes() as any
        if (allNodes && allNodes.length > 0) {
          const startId = allNodes[0].node_id
          const result = await dtHardeningApi.traceQuery(startId, 'both', 10, 500) as any as TraceQueryResult
          setNodes(result.nodes || allNodes)
          setEdges(result.edges || [])
        }
      }
      message.success(`Graph rebuilt: ${rebuildResult.nodes} nodes, ${rebuildResult.edges} edges`)
    } catch (e: any) {
      message.error('Failed to rebuild graph')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadGraphFromRoot()
  }, [])

  const handleNodeClick = useCallback(async (nodeId: string) => {
    setSelectedNodeId(nodeId)
    setHighlightedNodeIds(new Set())
    setUpstreamNodeIds(new Set())
    setDownstreamNodeIds(new Set())
    setSelectedIdentity(null)
    setIdentityMappings([])

    const node = nodes.find(n => n.node_id === nodeId)
    if (!node) return

    const props = node.properties || {}
    const domain = String(props.domain || '')
    const domainId = String(props.domain_id || '')

    if (domain && domainId) {
      try {
        const idResult = await dtHardeningApi.getIdentityByDomain(domain, domainId) as any
        if (idResult.identity_id) {
          setSelectedIdentity(idResult)
          if (idResult.mappings) {
            setIdentityMappings(idResult.mappings)
          }
        }
      } catch {}
    }

    try {
      const [impact, deps] = await Promise.all([
        dtHardeningApi.impactAnalysis(nodeId) as any,
        dtHardeningApi.dependencyQuery(nodeId) as any,
      ])

      const downIds = new Set<string>()
      const upIds = new Set<string>()
      const allHighlighted = new Set<string>([nodeId])

      if (impact.direct) {
        impact.direct.forEach((e: any) => { downIds.add(e.node.node_id); allHighlighted.add(e.node.node_id) })
      }
      if (impact.indirect) {
        impact.indirect.forEach((e: any) => { downIds.add(e.node.node_id); allHighlighted.add(e.node.node_id) })
      }
      if (deps.dependencies) {
        deps.dependencies.forEach((e: any) => { upIds.add(e.node.node_id); allHighlighted.add(e.node.node_id) })
      }

      setHighlightedNodeIds(allHighlighted)
      setUpstreamNodeIds(upIds)
      setDownstreamNodeIds(downIds)
    } catch {}
  }, [nodes])

  const handleSearchNodeSelect = useCallback((nodeId: string) => {
    handleNodeClick(nodeId)
  }, [handleNodeClick])

  return (
    <div style={{ padding: 16, height: 'calc(100vh - 100px)', display: 'flex', flexDirection: 'column' }}>
      <DigitalThreadDashboard />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <TraceSearchBar allNodes={nodes} onNodeSelect={handleSearchNodeSelect} />
        <Space>
          {stats && (
            <Space size={16}>
              <Statistic title="Nodes" value={stats.node_count} valueStyle={{ fontSize: 14 }} />
              <Statistic title="Edges" value={stats.edge_count} valueStyle={{ fontSize: 14 }} />
            </Space>
          )}
          <Button icon={<ReloadOutlined />} onClick={loadFullGraph} loading={loading}>
            Rebuild Graph
          </Button>
        </Space>
      </div>

      <div style={{ flex: 1, display: 'flex', gap: 12, minHeight: 0 }}>
        <Card
          title="Trace Graph"
          size="small"
          style={{ flex: 1, overflow: 'hidden' }}
          bodyStyle={{ padding: 0, height: 'calc(100% - 40px)' }}
        >
          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
              <Spin size="large" />
            </div>
          ) : nodes.length > 0 ? (
            <TraceGraphCanvas
              nodes={nodes}
              edges={edges}
              selectedNodeId={selectedNodeId}
              highlightedNodeIds={highlightedNodeIds}
              upstreamNodeIds={upstreamNodeIds}
              downstreamNodeIds={downstreamNodeIds}
              onNodeClick={handleNodeClick}
            />
          ) : (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
              <Empty description="No trace data. Click Rebuild Graph to generate." />
            </div>
          )}
        </Card>

        <Card
          title="Node Details"
          size="small"
          style={{ width: 320, overflow: 'auto' }}
          bodyStyle={{ padding: 0 }}
        >
          <TraceNodeDetailPanel
            node={selectedNode}
            identity={selectedIdentity}
            identityMappings={identityMappings}
          />
        </Card>
      </div>

      <div style={{ marginTop: 8 }}>
        <ImpactAnalysisView node={selectedNode} onNodeClick={handleNodeClick} />
      </div>
    </div>
  )
}

export default TraceAnalysisPage