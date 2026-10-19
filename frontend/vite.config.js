import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 1404,
    // Local dev: forward API calls to Flask (`flask --app wsgi run --port 5003`).
    proxy: { '/api': 'http://localhost:5003' },
  },
})
