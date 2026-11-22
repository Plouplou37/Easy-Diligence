import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '@/entities/viewer';
import { ConfirmProvider } from '@/shared/lib/confirm';
import { ThemeProvider } from '@/shared/lib/theme';
import { installEnglishValidity } from '@/shared/lib/validity';
import { AppToaster } from './providers/AppToaster';
import { AppRouter } from './router/AppRouter';

// The browser's form messages in English, whatever the system's language.
installEnglishValidity();

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
