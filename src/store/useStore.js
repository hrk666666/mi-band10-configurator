import { create } from 'zustand'

export const BODY_COLORS = {
  'midnight-black': { name: '午夜黑', hex: '#1a1a1a', metalness: 1.0, roughness: 0.35 },
  'glacier-silver': { name: '冰川银', hex: '#d0d2d6', metalness: 1.0, roughness: 0.30 },
  'mystic-rose':    { name: '神秘玫瑰', hex: '#e6b6b6', metalness: 1.0, roughness: 0.32 },
  'glimmer-gold':   { name: '璀璨金', hex: '#e6c88a', metalness: 1.0, roughness: 0.28 },
  'pearl-white':    { name: '珍珠白', hex: '#f5f5f5', metalness: 0.05, roughness: 0.12 },
}

export const BAND_TYPES = {
  tpu:   { name: 'TPU 运动', defaultColor: '#2a2a2e' },
  metal: { name: '不锈钢链式', defaultColor: '#d0d2d6' },
  leather: { name: '科纳皮', defaultColor: '#b8b0a8' },
  woven: { name: '编织', defaultColor: '#6a6a72' },
}

export const BAND_COLORS = {
  black: '#1a1a1a',
  silver: '#d0d2d6',
  white: '#f5f5f5',
  pink: '#e6b6b6',
  gold: '#e6c88a',
  brown: '#8b7e6a',
  gray: '#6a6a72',
}

export const CAMERA_PRESETS = {
  front:       { name: '正面', position: [0, 0, 0.12], target: [0, 0, 0], fov: 35 },
  back:        { name: '背面', position: [0, 0, -0.13], target: [0, 0, 0], fov: 35 },
  left:        { name: '左侧', position: [-0.10, 0, 0], target: [0, 0, 0], fov: 35 },
  right:       { name: '右侧', position: [0.10, 0, 0], target: [0, 0, 0], fov: 35 },
  angle45:     { name: '45°', position: [0.09, 0.05, 0.09], target: [0, 0, 0], fov: 35 },
  screenMacro: { name: '屏幕微距', position: [0, 0, 0.055], target: [0, 0, 0], fov: 18 },
  bandMacro:   { name: '表带微距', position: [0, -0.045, 0.03], target: [0, -0.04, 0], fov: 22 },
}

export const useStore = create((set) => ({
  bodyColor: 'glacier-silver',
  bandType: 'tpu',
  bandColor: '#2a2a2e',
  customScreenImage: null,
  cameraPreset: 'front',

  setBodyColor: (key) => set({ bodyColor: key }),
  setBandType: (type) => set({ bandType: type, bandColor: BAND_TYPES[type].defaultColor }),
  setBandColor: (color) => set({ bandColor: color }),
  setCustomScreenImage: (img) => set({ customScreenImage: img }),
  setCameraPreset: (preset) => set({ cameraPreset: preset }),
}))
