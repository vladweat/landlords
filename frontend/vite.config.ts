import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

const legalHtmlPaths: Record<string, string> = {
  '/privacy': '/privacy.html',
  '/terms': '/terms.html',
  '/offer': '/offer.html',
};

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'legal-html-aliases',
      configureServer(server) {
        server.middlewares.use((req, _res, next) => {
          const url = req.url?.split('?')[0] ?? '';
          if (url in legalHtmlPaths) {
            req.url = legalHtmlPaths[url] + (req.url?.includes('?') ? '?' + req.url.split('?')[1] : '');
          }
          next();
        });
      },
    },
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true,
    cors: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:80',
        changeOrigin: true,
      },
      '/documents': {
        target: 'http://127.0.0.1:80',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
