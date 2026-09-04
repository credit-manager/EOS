import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  base: '/ui/',
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@pages': path.resolve(__dirname, './src/pages'),
      '@services': path.resolve(__dirname, './src/services'),
      '@styles': path.resolve(__dirname, './src/styles'),
      '@utils': path.resolve(__dirname, './src/utils'),
      '@assets': path.resolve(__dirname, './src/assets'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': { target: 'http://localhost:8001', changeOrigin: true },
      '/docs': { target: 'http://localhost:8001', changeOrigin: true },
      '/openapi.json': { target: 'http://localhost:8001', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          ui: ['antd', '@ant-design/icons', 'framer-motion'],
          charts: ['recharts', '@ant-design/charts'],
          utils: ['axios', '@tanstack/react-query', 'zustand', 'dayjs', 'i18next', 'react-i18next'],
        },
      },
    },
  },
})
