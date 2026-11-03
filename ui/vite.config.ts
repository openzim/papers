import { fileURLToPath, URL } from 'node:url'
import { cp } from 'node:fs/promises'
import { join } from 'node:path'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vuetify from 'vite-plugin-vuetify'
import legacy from '@vitejs/plugin-legacy'

function copyPdfJsAssets() {
  let outputDir = ''
  let copied = false
  const pdfjsDir = fileURLToPath(new URL('./node_modules/pdfjs-dist/', import.meta.url))

  return {
    name: 'copy-pdfjs-assets',
    configResolved(config: { build: { outDir: string } }) {
      outputDir = config.build.outDir
    },
    async writeBundle() {
      if (copied) return
      copied = true
      await Promise.all(
        ['cmaps', 'standard_fonts'].map((directory) =>
          cp(join(pdfjsDir, directory), join(outputDir, 'pdfjs', directory), {
            recursive: true
          })
        )
      )
    }
  }
}

// https://vitejs.dev/config/
export default defineConfig({
  base: './',
  plugins: [
    vue({
      template: {
        compilerOptions: {
          isCustomElement: (tag) => tag === 'foliate-view'
        }
      }
    }),
    vuetify({ autoImport: true }),
    copyPdfJsAssets(),
    legacy({
      targets: ['fully supports es6'],
      modernPolyfills: true
    })
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  // Vuetify 4 derives overlay z-index from a shared useStack singleton. In dev, Vite's
  // dependency pre-bundler can serve some Vuetify modules from its optimized cache and
  // others as raw ESM, creating two useStack instances; overlays opened inside a dialog
  // (menus, selects, tooltips) then stay at the default z-index and render behind it.
  // Pre-bundling the components that take part in stacking keeps a single instance.
  // This is the workaround documented in the Vuetify 4 upgrade guide and only affects
  // dev mode: production builds bundle a single module graph and are not concerned.
  // https://vuetifyjs.com/getting-started/upgrade-guide/#vite-overlay-z-index-in-dev-mode
  optimizeDeps: {
    include: [
      'vuetify/components/VOverlay',
      'vuetify/components/VDialog',
      'vuetify/components/VMenu',
      'vuetify/components/VSelect',
      'vuetify/components/VTooltip'
    ]
  },
  build: {
    outDir: '../scraper/src/papers2zim/zimui',
    emptyOutDir: true,
    chunkSizeWarningLimit: 1000
  },
  server: {
    port: 5173,
    allowedHosts: ['hetwork1b.tail035625.ts.net']
  },
  preview: {
    port: 5173
  }
})
