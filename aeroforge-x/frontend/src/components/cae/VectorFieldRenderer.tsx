import { useRef, useEffect } from 'react'
import * as THREE from 'three'

interface VectorFieldProps {
  width?: number
  height?: number
  gridX?: number
  gridY?: number
}

export default function VectorFieldRenderer({
  width = 400,
  height = 300,
  gridX = 8,
  gridY = 6,
}: VectorFieldProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
    camera.position.set(0, 0, 8)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(width, height)
    containerRef.current.appendChild(renderer.domElement)

    const arrowGroup = new THREE.Group()
    for (let i = 0; i < gridX; i++) {
      for (let j = 0; j < gridY; j++) {
        const x = (i / (gridX - 1) - 0.5) * 5
        const y = (j / (gridY - 1) - 0.5) * 3.5
        const dir = new THREE.Vector3(1, 0.2 * Math.sin(i + j), 0).normalize()
        const origin = new THREE.Vector3(x, y, 0)
        const arrowHelper = new THREE.ArrowHelper(dir, origin, 0.4, 0x3498db, 0.1, 0.08)
        arrowGroup.add(arrowHelper)
      }
    }
    scene.add(arrowGroup)

    renderer.render(scene, camera)

    return () => {
      renderer.dispose()
      if (containerRef.current) {
        containerRef.current.removeChild(renderer.domElement)
      }
    }
  }, [width, height, gridX, gridY])

  return <div ref={containerRef} style={{ width, height }} />
}