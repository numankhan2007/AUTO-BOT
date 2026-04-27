import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// NOTE: Do NOT use @cloudflare/vite-plugin here.
// That plugin is for full-stack Vite+Workers setups. Our Worker (main.py)
// is deployed separately via pywrangler. Vite just builds static assets.
// [FIXED: L-4] Build optimizations with chunk splitting
export default defineConfig({
  plugins: [react()],
  build: {
    // [FIXED: L-4] Raise warning limit for canvas+animation bundles
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // [FIXED: L-4] Function-based manualChunks (required by Vite 8 / Rolldown)
        // Splits vendor (React) from effects (canvas/animation) for optimal caching
        manualChunks(id) {
          if (id.includes('node_modules/react-dom') || id.includes('node_modules/react/')) {
            return 'vendor';
          }
          if (id.includes('BackgroundEffects') || id.includes('BootScreen')) {
            return 'effects';
          }
        },
      },
    },
  },
})