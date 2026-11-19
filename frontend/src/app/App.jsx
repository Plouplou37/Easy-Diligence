import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '@/entities/viewer';
import { ConfirmProvider } from '@/shared/lib/confirm';
import { ThemeProvider } from '@/shared/lib/theme';
import { AppToaster } from './providers/AppToaster';
import { AppRouter } from './router/AppRouter';

const App = () => (
  <BrowserRouter>
    <ThemeProvider>
      <AuthProvider>
        <ConfirmProvider>
          <div className="App min-h-screen">
            <AppRouter />
            <AppToaster />
          </div>
        </ConfirmProvider>
      </AuthProvider>
    </ThemeProvider>
  </BrowserRouter>
);

export default App;
