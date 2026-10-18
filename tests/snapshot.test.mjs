import { chromium } from 'playwright'
import { spawn } from 'child_process'
import { fileURLToPath } from 'url'
import path from 'path'
import fs from 'fs'
import { Jimp } from 'jimp'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(__dirname, '..')
const snapshotsDir = path.join(root, 'snapshots')
fs.mkdirSync(snapshotsDir, { recursive: true })

// 配置
const bodyColors = ['midnight-black', 'glacier-silver', 'mystic-rose', 'glimmer-gold', 'pearl-white']
const bandTypes = ['tpu', 'metal', 'leather', 'woven']
const presets = ['front', 'back', 'left', 'right', 'angle45', 'screenMacro', 'bandMacro']

// 启动静态服务器
function startServer() {
  return new Promise((resolve, reject) => {
    const proc = spawn('npm', ['run', 'preview', '--', '--port', '0'], {
      cwd: root,
      stdio: 'pipe',
      shell: true,
    })
    let url = null
    proc.stdout.on('data', (data) => {
      const text = data.toString()
      const m = text.match(/http:\/\/localhost:\d+\/[^\s]*/)
      if (m && !url) {
        url = m[0]
        resolve({ url, proc })
      }
    })
    proc.stderr.on('data', (data) => {
      // vite preview logs to stderr sometimes
      const text = data.toString()
      const m = text.match(/http:\/\/localhost:\d+\/[^\s]*/)
      if (m && !url) {
        url = m[0]
        resolve({ url, proc })
      }
    })
    setTimeout(() => reject(new Error('server start timeout')), 30000)
  })
}

async function analyzeImage(filePath) {
  const img = await Jimp.read(filePath)
  const { width, height } = img.bitmap
  let total = 0
  let dark = 0
  let bright = 0
  const step = 4
  for (let y = 0; y < height; y += step) {
    for (let x = 0; x < width; x += step) {
      const idx = (y * width + x) * 4
      const r = img.bitmap.data[idx]
      const g = img.bitmap.data[idx + 1]
      const b = img.bitmap.data[idx + 2]
      const lum = 0.299 * r + 0.587 * g + 0.114 * b
      total++
      if (lum < 25) dark++
      if (lum > 240) bright++
    }
  }
  return {
    width,
    height,
    darkRatio: dark / total,
    brightRatio: bright / total,
  }
}

async function main() {
  const { url, proc } = await startServer()
  console.log('server:', url)

  const browser = await chromium.launch({
    headless: true,
    executablePath: '/usr/bin/chromium',
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-gpu-sandbox',
      '--disable-dev-shm-usage',
      '--enable-unsafe-swiftshader',
      '--use-gl=swiftshader',
      '--use-angle=swiftshader',
    ],
  })

  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } })
  const pageErrors = []
  page.on('pageerror', (err) => pageErrors.push(err.message))
  page.on('console', (msg) => {
    if (msg.type() === 'error') pageErrors.push(msg.text())
  })

  await page.goto(url, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('canvas')
  await page.waitForTimeout(3000)

  const issues = []

  // 遍历配色 × 表带 × 机位
  for (const color of bodyColors) {
    await page.locator(`[data-testid="body-color-${color}"]`).click()
    await page.waitForTimeout(300)
    for (const band of bandTypes) {
      await page.locator(`[data-testid="band-type-${band}"]`).click()
      await page.waitForTimeout(300)
      for (const preset of presets) {
        await page.locator(`[data-testid="camera-preset-${preset}"]`).click()
        await page.waitForTimeout(800)
        const fileName = `${color}_${band}_${preset}.png`
        const filePath = path.join(snapshotsDir, fileName)
        await page.screenshot({ path: filePath })
        const stats = await analyzeImage(filePath)
        if (stats.darkRatio > 0.95) {
          issues.push(`${fileName}: too dark (${(stats.darkRatio * 100).toFixed(1)}% dark)`)
        }
        if (stats.brightRatio > 0.95) {
          issues.push(`${fileName}: too bright (${(stats.brightRatio * 100).toFixed(1)}% bright)`)
        }
        console.log('captured', fileName, `dark=${(stats.darkRatio * 100).toFixed(1)}% bright=${(stats.brightRatio * 100).toFixed(1)}%`)
      }
    }
  }

  // 8 个随机角度
  for (let i = 0; i < 8; i++) {
    const theta = Math.random() * Math.PI * 2
    const phi = Math.random() * Math.PI * 0.5 + 0.2
    const r = 0.12
    const x = r * Math.sin(phi) * Math.cos(theta)
    const y = r * Math.cos(phi) * 0.6
    const z = r * Math.sin(phi) * Math.sin(theta)
    await page.evaluate(({ x, y, z }) => {
      window.__r3f_camera?.position.set(x, y, z)
      window.__r3f_controls?.update()
    }, { x, y, z })
    await page.waitForTimeout(800)
    const fileName = `random_${i}.png`
    await page.screenshot({ path: path.join(snapshotsDir, fileName) })
    console.log('captured', fileName)
  }

  await browser.close()
  proc.kill()

  // 输出摘要
  console.log('\n--- Snapshot Test Summary ---')
  console.log('total screenshots:', bodyColors.length * bandTypes.length * presets.length + 8)
  console.log('issues found:', issues.length)
  issues.forEach((m) => console.log('  -', m))
  if (pageErrors.length) {
    console.log('page errors:', pageErrors.length)
    pageErrors.forEach((e) => console.log('  -', e))
  }

  // 写 CHANGELOG（追加本轮）
  const changelogPath = path.join(root, 'CHANGELOG.md')
  const roundArg = process.argv[2] || '1'
  const now = new Date().toISOString()
  const header = fs.existsSync(changelogPath) ? '' : `# 自动检测与迭代日志\n\n`
  const log = `${header}## [轮次 ${roundArg}] ${now}\n- 运行 Playwright 自动截图循环\n- 组合数: ${bodyColors.length} 配色 × ${bandTypes.length} 表带 × ${presets.length} 机位 + 8 随机角度\n- 截图总数: ${bodyColors.length * bandTypes.length * presets.length + 8}\n- 发现问题:\n${issues.length ? issues.map((m) => `  - ${m}`).join('\n') : '  - 无（亮度/加载检查通过）'}\n${pageErrors.length ? pageErrors.map((e) => `  - 页面错误: ${e}`).join('\n') : '  - 无页面错误'}\n`
  fs.appendFileSync(changelogPath, log)
  console.log('changelog appended to', changelogPath)
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})
