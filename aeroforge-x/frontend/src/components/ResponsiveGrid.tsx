import { Row, Col } from 'antd'
import { useIsMobile } from '../hooks/useBreakpoint'
import React from 'react'

interface ResponsiveRowProps {
  children: React.ReactNode
  gutter?: number | [number, number]
  style?: React.CSSProperties
}

export function ResponsiveRow({ children, gutter = 16, style }: ResponsiveRowProps) {
  const isMobile = useIsMobile()
  return (
    <Row gutter={isMobile ? [8, 8] : gutter} style={style}>
      {children}
    </Row>
  )
}

interface ResponsiveColProps {
  children: React.ReactNode
  span: number
  mobileSpan?: number
  tabletSpan?: number
  style?: React.CSSProperties
}

export function ResponsiveCol({ children, span, mobileSpan, tabletSpan, style }: ResponsiveColProps) {
  const isMobile = useIsMobile()
  const actualSpan = isMobile ? (mobileSpan || 24) : span
  return (
    <Col span={actualSpan} style={style}>
      {children}
    </Col>
  )
}

interface ResponsiveCardGridProps {
  children: React.ReactNode
  desktopSpan?: number
  tabletSpan?: number
  mobileSpan?: number
}

export function ResponsiveCardGrid({ children, desktopSpan = 6, tabletSpan = 12, mobileSpan = 24 }: ResponsiveCardGridProps) {
  const isMobile = useIsMobile()
  const span = isMobile ? mobileSpan : desktopSpan
  return (
    <Row gutter={[16, 16]}>
      {React.Children.map(children, child => (
        <Col span={span}>{child}</Col>
      ))}
    </Row>
  )
}