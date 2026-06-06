import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],

  // GitHub Pages: el repo se sirve desde /lynx-fact-checker/
  base: '/lynx-fact-checker/',
})
