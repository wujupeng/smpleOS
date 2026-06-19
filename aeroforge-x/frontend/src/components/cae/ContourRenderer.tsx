import { useRef, useEffect } from 'react'
import * as THREE from 'three'

interface ContourProps {
  width?: number
  height?: number
  levels?: number[]
}

export default function ContourRenderer({
  width = 400,
  height = 300,
  levels = [0.2, 0.4, 0.6, 0.8],
}: ContourProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
    camera.position.set(0, 0, 5)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(width, height)
    containerRef.current.appendChild(renderer.domElement)

    const colors = [0x3498db, 0x2ecc71, 0xe74c3c, 0xf39c12, 0x9b59b6]
    levels.forEach((_, idx) => {
      const radius = 0.5 + idx * 0.3
      const curve = new THREE.EllipseCurve(0, 0, radius, radius, 0, 2 * Math.PI, false, 0)
      const points = curve.getPoints(64)
      const geometry = new THREE.BufferGeometry().setFromPoints(
        points.map(p => new THREE.Vector3(p.x, p.y, 0))
      )
      const material = new THREE.LineBasicMaterial({ color: colors[idx % colors.length] })
      const line = new THREE.Line(geometry, material)
      scene.add(line)
    })

    renderer.render(scene, camera)

    return () => {
      renderer.dispose()
      if (containerRef.current) {
        containerRef.current.removeChild(renderer.domElement)
      }
    }
  }, [width, height, levels])

  return <div ref={containerRef} style={{ width, height }} />
}