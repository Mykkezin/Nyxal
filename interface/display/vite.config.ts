import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  // A Nyxal API can serve this static bundle under /display/.
  base: '/display/',
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 3000,
    strictPort: true,
  },
  preview: {
    host: '127.0.0.1',
  },
});
