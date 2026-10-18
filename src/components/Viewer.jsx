import { useRef, useMemo, useEffect, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Environment, Lightformer, OrbitControls, useGLTF } from '@react-three/drei'
import * as THREE from 'three'
import { useStore, BODY_COLORS, CAMERA_PRESETS } from '../store/useStore.js'

const MODEL_URL = 'models/mi_band10.glb'

function createDefaultScreenTexture() {
  const canvas = document.createElement('canvas')
  canvas.width = 512
  canvas.height = 1240
  const ctx = canvas.getContext('2d')
  // 黑色 AMOLED 背景
  const grad = ctx.createLinearGradient(0, 0, 0, canvas.height)
  grad.addColorStop(0, '#050505')
  grad.addColorStop(1, '#111')
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  // 时间
  const now = new Date()
  const hh = String(now.getHours()).padStart(2, '0')
  const mm = String(now.getMinutes()).padStart(2, '0')
  ctx.fillStyle = '#fff'
  ctx.textAlign = 'center'
  ctx.font = 'bold 220px sans-serif'
  ctx.fillText(`${hh}:${mm}`, canvas.width / 2, 520)
  // 日期
  ctx.font = '60px sans-serif'
  ctx.fillStyle = '#aaa'
  ctx.fillText(now.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric', weekday: 'short' }), canvas.width / 2, 640)
  // 健康图标占位
  ctx.font = '48px sans-serif'
  ctx.fillStyle = '#6cf'
  ctx.fillText('♥ 72  ·  2560 步', canvas.width / 2, 820)
  // 电量
  ctx.fillStyle = '#9f9'
  ctx.fillText('80%', canvas.width / 2, 940)
  const tex = new THREE.CanvasTexture(canvas)
  tex.colorSpace = THREE.SRGBColorSpace
  return tex
}

function BandModel({ scene }) {
  const { bodyColor, bandType, bandColor, customScreenImage, cameraPreset } = useStore()
  const frameRef = useRef()
  const bandsRef = useRef({})
  const displayRef = useRef()
  const controlsRef = useRef()
  const { camera, gl } = useThree()

  const defaultScreenTex = useMemo(() => createDefaultScreenTexture(), [])

  // 首次挂载时收集引用
  useEffect(() => {
    scene.traverse((obj) => {
      if (obj.isMesh) {
        if (obj.name === 'frame') frameRef.current = obj
        if (obj.name === 'display') displayRef.current = obj
        if (['band_tpu', 'band_metal', 'band_leather', 'band_woven'].includes(obj.name)) {
          bandsRef.current[obj.name] = obj
        }
      }
    })
    if (displayRef.current) {
      displayRef.current.material = displayRef.current.material.clone()
      displayRef.current.material.map = defaultScreenTex
      displayRef.current.material.emissive = new THREE.Color(0xffffff)
      displayRef.current.material.emissiveMap = defaultScreenTex
      displayRef.current.material.emissiveIntensity = 0.15
      displayRef.current.material.needsUpdate = true
    }
  }, [scene, defaultScreenTex])

  // 机身配色
  useEffect(() => {
    if (!frameRef.current) return
    const cfg = BODY_COLORS[bodyColor]
    const mat = frameRef.current.material
    mat.color.set(cfg.hex)
    mat.metalness = cfg.metalness
    mat.roughness = cfg.roughness
    mat.needsUpdate = true
  }, [bodyColor])

  // 表带切换 / 表带颜色
  useEffect(() => {
    Object.entries(bandsRef.current).forEach(([name, mesh]) => {
      mesh.visible = name === bandType
      if (mesh.visible) {
        mesh.material.color.set(bandColor)
        // 金属表带保留金属感
        if (bandType === 'metal') {
          mesh.material.metalness = 1.0
          mesh.material.roughness = 0.25
        } else {
          mesh.material.metalness = 0.0
          mesh.material.roughness = 0.7
        }
      }
    })
  }, [bandType, bandColor])

  // 自定义屏幕图片
  useEffect(() => {
    if (!displayRef.current) return
    const mat = displayRef.current.material
    if (customScreenImage) {
      const tex = new THREE.Texture(customScreenImage)
      tex.colorSpace = THREE.SRGBColorSpace
      tex.needsUpdate = true
      mat.map = tex
      mat.emissiveMap = tex
      mat.emissiveIntensity = 0.12
    } else {
      mat.map = defaultScreenTex
      mat.emissiveMap = defaultScreenTex
      mat.emissiveIntensity = 0.15
    }
    mat.needsUpdate = true
  }, [customScreenImage, defaultScreenTex])

  // 相机预设 + 暴露给测试
  useEffect(() => {
    window.__r3f_camera = camera
    if (controlsRef.current) {
      window.__r3f_controls = controlsRef.current
    }
  }, [camera])

  useEffect(() => {
    const preset = CAMERA_PRESETS[cameraPreset]
    if (!preset) return
    camera.fov = preset.fov
    camera.position.set(...preset.position)
    camera.updateProjectionMatrix()
    if (controlsRef.current) {
      controlsRef.current.target.set(...preset.target)
      controlsRef.current.update()
    }
  }, [cameraPreset, camera])

  // 截图方法挂到 window，供 Controls 调用
  useEffect(() => {
    window.takeModelScreenshot = () => {
      gl.render(camera, scene)
      return gl.domElement.toDataURL('image/png')
    }
  }, [gl, camera, scene])

  return (
    <>
      <primitive object={scene} />
      <OrbitControls
        ref={controlsRef}
        enablePan={false}
        minDistance={0.04}
        maxDistance={0.25}
        target={[0, 0, 0]}
      />
    </>
  )
}

function Scene() {
  const { scene } = useGLTF(MODEL_URL)
  return (
    <>
      <ambientLight intensity={0.8} />
      <hemisphereLight args={['#ffffff', '#404040', 0.7]} />
      <directionalLight position={[1, 1, 1]} intensity={1.4} />
      <directionalLight position={[-1, 0.5, 0.5]} intensity={0.9} />
      <directionalLight position={[0, -1, -1]} intensity={0.9} />
      <directionalLight position={[0, 1, -1]} intensity={0.6} />
      <pointLight position={[0, 0, 0.08]} intensity={0.25} />
      <Environment resolution={256} background={false}>
        <Lightformer form="rect" intensity={4} position={[0, 0, 5]} scale={[4, 4]} color="#ffffff" />
        <Lightformer form="rect" intensity={2} position={[5, 0, 2]} scale={[4, 4]} color="#d0e0ff" />
        <Lightformer form="rect" intensity={2} position={[-5, 0, 2]} scale={[4, 4]} color="#ffe0d0" />
        <Lightformer form="ring" intensity={1.5} position={[0, 5, 0]} scale={[3, 3]} color="#ffffff" />
      </Environment>
      <BandModel scene={scene} />
    </>
  )
}

export default function Viewer() {
  return (
    <div className="canvas-container">
      <Canvas
        camera={{ position: [0, 0, 0.12], fov: 35, near: 0.001, far: 10 }}
        gl={{ antialias: true, preserveDrawingBuffer: true, alpha: true }}
        shadows
      >
        <color attach="background" args={['#0f0f11']} />
        <Scene />
      </Canvas>
    </div>
  )
}
