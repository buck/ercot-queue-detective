// @ts-check
import { defineConfig } from 'astro/config';

// To enable SSR/chat endpoint tomorrow: import cloudflare from '@astrojs/cloudflare';
// then add: output: 'hybrid', adapter: cloudflare()

// https://astro.build/config
export default defineConfig({
  output: 'static',
});