import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '@/entities/viewer';
import { ThemeProvider } from '@/shared/lib/theme';
import { AppToaster } from './providers/AppToaster';
import { AppRouter } from './router/AppRouter';

const App = () => (
  <BrowserRouter>
    <ThemeProvider>
      <AuthProvider>
        <div className="App min-h-screen">
          <AppRouter />
          <AppToaster />
        </div>
      </AuthProvider>
    </ThemeProvider>
  </BrowserRouter>
);

export default App;
