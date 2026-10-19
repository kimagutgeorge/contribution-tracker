import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    // Local dev: forward API calls to Flask (`flask --app wsgi run`).
    proxy: { '/api': 'http://localhost:5000' },
  },
})
