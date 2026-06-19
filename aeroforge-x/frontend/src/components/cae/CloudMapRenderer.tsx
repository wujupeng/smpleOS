import { useRef, useEffect } from 'react'
import * as THREE from 'three'

interface CloudMapProps {
  data?: Float32Array
  width?: number
  height?: number
  fieldRange?: [number, number]
  colorMap?: string
}

export default function CloudMapRenderer({
  width = 400,
  height = 300,
  fieldRange = [0, 1],
}: CloudMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000)
    camera.position.set(0, 0, 5)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(width, height)
    containerRef.current.appendChild(renderer.domElement)

    const geometry = new THREE.PlaneGeometry(3, 3, 64, 64)
    const material = new THREE.MeshBasicMaterial({
      color: 0x3498db,
      wireframe: true,
      transparent: true,
      opacity: 0.6,
    })
    const plane = new THREE.Mesh(geometry, material)
    scene.add(plane)

    const axesHelper = new THREE.AxesHelper(2)
    scene.add(axesHelper)

    renderer.render(scene, camera)

    return () => {
      renderer.dispose()
      if (containerRef.current) {
        containerRef.current.removeChild(renderer.domElement)
      }
    }
  }, [width, height, fieldRange])

  return <div ref={containerRef} style={{ width, height }} />
}