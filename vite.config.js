import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// GitHub Pages 部署时使用仓库名作为 base
export default defineConfig({
  base: '/mi-band10-configurator/',
  plugins: [react()],
})
