import path from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const localCacheRoot = process.env.LOCALAPPDATA || process.cwd();

export default defineConfig({
  plugins: [react()],
  cacheDir: path.join(localCacheRoot, 'scalerai-vite-cache'),
  server: {
    watch: {
      usePolling: true,
      interval: 300,
    },
  },
});
