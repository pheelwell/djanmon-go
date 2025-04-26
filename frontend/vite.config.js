import { fileURLToPath, URL } from 'node:url'
import path from 'path' // Needed for alias

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// Import Sentry Vite plugin
import { sentryVitePlugin } from "@sentry/vite-plugin";

// https://vite.dev/config/
export default defineConfig({
  // Set the base path for assets to match Django's STATIC_URL
  base: '/static/',

  // alowed hosts
  server: {
    host: true,
    port: 5173,
    allowedHosts: ['lexmark-specialists-leone-legislation.trycloudflare.com'],
    proxy: {
      // Proxy requests starting with /api to the Django backend
      '/api': {
        target: 'http://localhost:8000/api', // Your Django backend URL
        changeOrigin: true, // Recommended for virtual hosts
        secure: false,      // Set to true if your backend uses HTTPS
        // Rewrite the path: remove /api prefix before forwarding
        // e.g., /api/users/login -> /users/login
        rewrite: (path) => path.replace(/^\/api/, '') 
      }
    }
  },
  // Enable sourcemaps for Sentry
  build: {
    sourcemap: true, 
  },
  plugins: [
    vue(),
    vueDevTools(),
    // Put the Sentry vite plugin after all other plugins
    sentryVitePlugin({
      org: "phemisto", // Replace with your Sentry organization slug
      project: "djanmongo-fe", // Replace with your Sentry project slug

      // Auth tokens can be obtained from https://sentry.io/settings/account/api/auth-tokens/
      // Preferably using environment variables
      // authToken: process.env.SENTRY_AUTH_TOKEN,

      // Optionally uncomment the line below to override automatic detection of repository structure
      // sourceMaps: {
      //   include: ["./dist/assets"],
      //   ignore: ["node_modules"],
      // },
    }),
    sentryVitePlugin({
      org: "wellm",
      project: "javascript-vue"
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'), // Setup @ alias for cleaner imports
    },
  },
})