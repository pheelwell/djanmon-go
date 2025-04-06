import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// Import Sentry Vite plugin
import { sentryVitePlugin } from "@sentry/vite-plugin";

// https://vite.dev/config/
export default defineConfig({
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
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
})