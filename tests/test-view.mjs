import { chromium } from 'playwright'
import { spawn } from 'child_process'
import { fileURLToPath } from 'url'
import path from 'path'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const root = path.resolve(__dirname, '..')

// 启动 vite preview 静态服务器
const preview = spawn('npm', ['run', 'preview', '--', '--port', '4173'], {
  cwd: root,
  stdio: 'pipe',
  shell: true,
})

let serverUrl = null
for await (const line of preview.stdout) {
  const text = line.toString()
  const m = text.match(/http:\/\/localhost:\d+\/[^\s]*/)
  if (m) {
    serverUrl = m[0]
    break
  }
}

console.log('preview server:', serverUrl)
if (!serverUrl) {
  preview.kill()
  process.exit(1)
}

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
page.on('console', (msg) => console.log('[page]', msg.type(), msg.text()))
page.on('pageerror', (err) => console.error('[pageerror]', err))

await page.goto(serverUrl, { waitUntil: 'domcontentloaded' })
await page.waitForTimeout(5000)

const hasCanvas = await page.locator('canvas').count()
console.log('canvas count:', hasCanvas)

await page.screenshot({ path: path.join(root, 'snapshots', 'test-front.png') })
console.log('screenshot saved to snapshots/test-front.png')

await browser.close()
preview.kill()
