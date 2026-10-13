import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'Finanzas',
        short_name: 'Finanzas',
        description: 'Mis finanzas personales',
        lang: 'es',
        start_url: '/',
        display: 'standalone',
        background_color: '#f8fafc',
        theme_color: '#059669',
        icons: [
          { src: 'pwa-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'pwa-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      // solo se cachea el "app shell"; las llamadas a /api siempre van a la red (datos reales, nunca viejos)
      workbox: { navigateFallbackDenylist: [/^\/api/] },
    }),
  ],
  server: { proxy: { '/api': 'http://localhost:8000' } },
  test: { environment: 'jsdom' },
})
