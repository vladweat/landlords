// frontend/src/main.tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './index.css';
import { App } from './app/App';
import { useAuthStore } from './features/auth/store';

// Восстановить браузерную сессию из HttpOnly-cookie.
void useAuthStore.getState().bootstrap();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
