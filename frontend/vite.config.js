import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
export default defineConfig({
  base: '/satdash/',
  plugins: [vue()],
  server: { port: 5173, proxy: { '/api': 'http://127.0.0.1:47237', '/ws': { target: 'ws://127.0.0.1:47237', ws: true } } },
  build: { chunkSizeWarningLimit: 1200 }
})
