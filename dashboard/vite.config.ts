/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/visitors': process.env.SIGIL_SERVER_URL ?? 'http://localhost:8000',
      '/accounts': process.env.SIGIL_SERVER_URL ?? 'http://localhost:8000',
      '/ip': process.env.SIGIL_SERVER_URL ?? 'http://localhost:8000',
    },
  },
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
  },
});
