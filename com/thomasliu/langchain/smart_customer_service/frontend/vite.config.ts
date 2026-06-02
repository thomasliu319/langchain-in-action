import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'

export default defineConfig({
  plugins: [vue(), vueJsx()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8005',
        changeOrigin: true
      }
    }
  }
})
