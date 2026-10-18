import { useStore, BODY_COLORS, BAND_TYPES, BAND_COLORS, CAMERA_PRESETS } from '../store/useStore.js'

export default function Controls() {
  const {
    bodyColor, setBodyColor,
    bandType, setBandType,
    bandColor, setBandColor,
    setCustomScreenImage,
    cameraPreset, setCameraPreset,
  } = useStore()

  const handleScreenUpload = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const img = new Image()
    img.onload = () => setCustomScreenImage(img)
    img.src = URL.createObjectURL(file)
  }

  const handleScreenshot = () => {
    if (typeof window.takeModelScreenshot !== 'function') return
    const dataUrl = window.takeModelScreenshot()
    const link = document.createElement('a')
    link.href = dataUrl
    link.download = `mi-band10-${Date.now()}.png`
    link.click()
  }

  return (
    <div className="controls">
      <h1>小米手环 10 配置器</h1>

      <div className="control-group">
        <label>机身配色</label>
        <div className="color-row">
          {Object.entries(BODY_COLORS).map(([key, cfg]) => (
            <button
              key={key}
              data-testid={`body-color-${key}`}
              className={`color-btn ${bodyColor === key ? 'active' : ''}`}
              style={{ background: cfg.hex }}
              title={cfg.name}
              onClick={() => setBodyColor(key)}
            />
          ))}
        </div>
      </div>

      <div className="control-group">
        <label>表带材质</label>
        <div className="band-row">
          {Object.entries(BAND_TYPES).map(([key, cfg]) => (
            <button
              key={key}
              data-testid={`band-type-${key}`}
              className={`band-btn ${bandType === key ? 'active' : ''}`}
              onClick={() => setBandType(key)}
            >
              {cfg.name}
            </button>
          ))}
        </div>
      </div>

      <div className="control-group">
        <label>表带颜色</label>
        <div className="color-row">
          {Object.entries(BAND_COLORS).map(([name, hex]) => (
            <button
              key={name}
              className={`color-btn ${bandColor === hex ? 'active' : ''}`}
              style={{ background: hex }}
              title={name}
              onClick={() => setBandColor(hex)}
            />
          ))}
        </div>
      </div>

      <div className="control-group">
        <label>自定义屏幕表盘</label>
        <input type="file" accept="image/*" onChange={handleScreenUpload} />
      </div>

      <div className="control-group">
        <label>相机预设</label>
        <div className="preset-row">
          {Object.entries(CAMERA_PRESETS).map(([key, cfg]) => (
            <button
              key={key}
              data-testid={`camera-preset-${key}`}
              className={`preset-btn ${cameraPreset === key ? 'active' : ''}`}
              onClick={() => setCameraPreset(key)}
            >
              {cfg.name}
            </button>
          ))}
        </div>
      </div>

      <button className="action-btn" onClick={handleScreenshot}>
        截图保存 PNG
      </button>

      <div className="status">
        当前：{BODY_COLORS[bodyColor].name} · {BAND_TYPES[bandType].name}
      </div>
    </div>
  )
}
