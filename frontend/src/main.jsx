import React from 'react';
import ReactDOM from 'react-dom/client';
import App from '@/app/App';
// Inter, served with the application: no request to a font service.
import '@fontsource-variable/inter';
import '@/app/styles/index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
