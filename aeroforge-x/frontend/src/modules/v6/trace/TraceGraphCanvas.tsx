import React, { useRef, useEffect, useState, useCallback } from 'react'
import type { TraceNode, TraceEdge } from '../../../api/types'

const NODE_TYPE_COLORS: Record<string, string> = {
  block: '#1890ff',
  material_lot: '#52c41a',
  ndt_record: '#faad14',
  car: '#ff4d4f',
  evidence: '#722ed1',
  compliance: '#13c2c2',
}

const NODE_WIDTH = 180
const NODE_HEIGHT = 48
const LAYER_GAP = 100
const NODE_GAP = 20
const LAYER_ORDER = ['block', 'material_lot', 'ndt_record', 'car', 'evidence', 'compliance']

interface Props {
  nodes: TraceNode[]
  edges: TraceEdge[]
  selectedNodeId: string | null
  highlightedNodeIds: Set<string>
  upstreamNodeIds: Set<string>
  downstreamNodeIds: Set<string>
  onNodeClick: (nodeId: string) => void
}

interface NodeLayout {
  node: TraceNode
  x: number
  y: number
  layer: number
}

const TraceGraphCanvas: React.FC<Props> = ({
  nodes,
  edges,
  selectedNodeId,
  highlightedNodeIds,
  upstreamNodeIds,
  downstreamNodeIds,
  onNodeClick,
}) => {
  const svgRef = useRef<SVGSVGElement>(null)
  const [viewBox, setViewBox] = useState({ x: 0, y: 0, w: 1200, h: 800 })
  const [dragging, setDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [scale, setScale] = useState(1)

  const layout = useCallback((): NodeLayout[] => {
    const layerMap = new Map<string, number>()
    LAYER_ORDER.forEach((t, i) => layerMap.set(t, i))

    const layerGroups: Map<number, TraceNode[]> = new Map()
    for (const n of nodes) {
      const layer = layerMap.get(n.node_type) ?? 3
      if (!layerGroups.has(layer)) layerGroups.set(layer, [])
      layerGroups.get(layer)!.push(n)
    }

    const result: NodeLayout[] = []
    for (const [layer, group] of layerGroups) {
      const totalHeight = group.length * (NODE_HEIGHT + NODE_GAP) - NODE_GAP
      const startY = -totalHeight / 2
      group.forEach((node, i) => {
        result.push({
          node,
          x: layer * (NODE_WIDTH + LAYER_GAP) + 80,
          y: startY + i * (NODE_HEIGHT + NODE_GAP) + 300,
          layer,
        })
      })
    }
    return result
  }, [nodes])

  const layouts = layout()
  const layoutMap = new Map(layouts.map(l => [l.node.node_id, l]))

  const maxW = layouts.length > 0 ? Math.max(...layouts.map(l => l.x)) + NODE_WIDTH + 80 : 1200
  const maxH = layouts.length > 0 ? Math.max(...layouts.map(l => l.y)) + NODE_HEIGHT + 80 : 800

  useEffect(() => {
    setViewBox({ x: 0, y: 0, w: maxW, h: maxH })
    setScale(1)
  }, [maxW, maxH])

  const onWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    const factor = e.deltaY > 0 ? 0.9 : 1.1
    const newScale = Math.max(0.2, Math.min(3, scale * factor))
    const svg = svgRef.current
    if (!svg) return
    const rect = svg.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    const newX = viewBox.x + mx * (1 - 1 / factor)
    const newY = viewBox.y + my * (1 - 1 / factor)
    setScale(newScale)
    setViewBox({ x: newX, y: newY, w: viewBox.w / factor, h: viewBox.h / factor })
  }, [scale, viewBox])

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return
    setDragging(true)
    setDragStart({ x: e.clientX, y: e.clientY })
  }, [])

  const onMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging) return
    const dx = (e.clientX - dragStart.x) * (viewBox.w / (svgRef.current?.clientWidth || 1))
    const dy = (e.clientY - dragStart.y) * (viewBox.h / (svgRef.current?.clientHeight || 1))
    setViewBox({ ...viewBox, x: viewBox.x - dx, y: viewBox.y - dy })
    setDragStart({ x: e.clientX, y: e.clientY })
  }, [dragging, dragStart, viewBox])

  const onMouseUp = useCallback(() => setDragging(false), [])

  const getNodeOpacity = (nodeId: string): number => {
    if (highlightedNodeIds.size === 0) return 1
    if (highlightedNodeIds.has(nodeId)) return 1
    return 0.25
  }

  const getNodeStroke = (nodeId: string): string => {
    if (selectedNodeId === nodeId) return '#fff'
    if (upstreamNodeIds.has(nodeId)) return '#1890ff'
    if (downstreamNodeIds.has(nodeId)) return '#fa8c16'
    return 'transparent'
  }

  const getEdgeOpacity = (edge: TraceEdge): number => {
    if (highlightedNodeIds.size === 0) return 0.6
    if (highlightedNodeIds.has(edge.source_node_id) && highlightedNodeIds.has(edge.target_node_id)) return 1
    return 0.1
  }

  const renderEdge = (edge: TraceEdge) => {
    const src = layoutMap.get(edge.source_node_id)
    const tgt = layoutMap.get(edge.target_node_id)
    if (!src || !tgt) return null
    const x1 = src.x + NODE_WIDTH
    const y1 = src.y + NODE_HEIGHT / 2
    const x2 = tgt.x
    const y2 = tgt.y + NODE_HEIGHT / 2
    const midX = (x1 + x2) / 2
    const opacity = getEdgeOpacity(edge)
    const isHighlighted = highlightedNodeIds.has(edge.source_node_id) && highlightedNodeIds.has(edge.target_node_id)
    return (
      <g key={edge.edge_id}>
        <path
          d={`M${x1},${y1} C${midX},${y1} ${midX},${y2} ${x2},${y2}`}
          fill="none"
          stroke={isHighlighted ? '#faad14' : '#555'}
          strokeWidth={isHighlighted ? 2.5 : 1.5}
          opacity={opacity}
          markerEnd="url(#arrowhead)"
        />
        <text
          x={midX}
          y={(y1 + y2) / 2 - 6}
          textAnchor="middle"
          fontSize={10}
          fill="#999"
          opacity={opacity}
        >
          {edge.edge_type}
        </text>
      </g>
    )
  }

  const renderNode = (l: NodeLayout) => {
    const { node, x, y } = l
    const color = NODE_TYPE_COLORS[node.node_type] || '#666'
    const opacity = getNodeOpacity(node.node_id)
    const stroke = getNodeStroke(node.node_id)
    const isSelected = selectedNodeId === node.node_id
    return (
      <g
        key={node.node_id}
        transform={`translate(${x},${y})`}
        onClick={() => onNodeClick(node.node_id)}
        style={{ cursor: 'pointer' }}
        opacity={opacity}
      >
        <rect
          x={0}
          y={0}
          width={NODE_WIDTH}
          height={NODE_HEIGHT}
          rx={8}
          fill={color}
          stroke={stroke}
          strokeWidth={isSelected ? 3 : stroke !== 'transparent' ? 2 : 0}
        />
        <text
          x={NODE_WIDTH / 2}
          y={20}
          textAnchor="middle"
          fill="#fff"
          fontSize={12}
          fontWeight={600}
        >
          {node.label.length > 20 ? node.label.slice(0, 18) + '...' : node.label}
        </text>
        <text
          x={NODE_WIDTH / 2}
          y={36}
          textAnchor="middle"
          fill="rgba(255,255,255,0.7)"
          fontSize={9}
        >
          {node.node_type}
        </text>
      </g>
    )
  }

  return (
    <svg
      ref={svgRef}
      width="100%"
      height="100%"
      viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`}
      onWheel={onWheel}
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
      style={{ background: '#1a1a2e', borderRadius: 8 }}
    >
      <defs>
        <marker
          id="arrowhead"
          markerWidth="10"
          markerHeight="7"
          refX="10"
          refY="3.5"
          orient="auto"
        >
          <polygon points="0 0, 10 3.5, 0 7" fill="#999" />
        </marker>
      </defs>
      {edges.map(renderEdge)}
      {layouts.map(renderNode)}
    </svg>
  )
}

export default TraceGraphCanvas