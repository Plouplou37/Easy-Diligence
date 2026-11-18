import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import ProtectedRoute from './components/ProtectedRoute';

// Pages
import Dashboard from './pages/Dashboard';
import SessionCreate from './pages/SessionCreate';
import AnswerReview from './features/answers/AnswerReview';
import QuestionManagement from './features/questions/QuestionManagement';
import DDTypeManagement from './pages/DDTypeManagement';
import VectorStoreManagement from './features/vector-stores/VectorStoreManagement';
import UserManagement from './pages/UserManagement';
import SessionDetail from './pages/SessionDetail';
import Login from './pages/Login';
import Register from './pages/Register';
import Profile from './pages/Profile';

function App() {
  return (
    <Router>
      <ThemeProvider>
        <AuthProvider>
          <div className="App min-h-screen">
          <Routes>
            {/* Public routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            
            {/* Protected routes */}
            <Route path="/" element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } />
            <Route path="/session/create" element={
              <ProtectedRoute>
                <SessionCreate />
              </ProtectedRoute>
            } />
            <Route path="/session/:sessionId/answers" element={
              <ProtectedRoute>
                <AnswerReview />
              </ProtectedRoute>
            } />
            <Route path="/session/:sessionId" element={
              <ProtectedRoute>
                <SessionDetail />
              </ProtectedRoute>
            } />
            <Route path="/profile" element={
              <ProtectedRoute>
                <Profile />
              </ProtectedRoute>
            } />
            
            {/* Admin only routes */}
            <Route path="/admin/users" element={
              <ProtectedRoute adminOnly>
                <UserManagement />
              </ProtectedRoute>
            } />
            <Route path="/questions" element={
              <ProtectedRoute>
                <QuestionManagement />
              </ProtectedRoute>
            } />
            <Route path="/dd-types" element={
              <ProtectedRoute>
                <DDTypeManagement />
              </ProtectedRoute>
            } />
            <Route path="/vector-stores" element={
              <ProtectedRoute>
                <VectorStoreManagement />
              </ProtectedRoute>
            } />
            
            {/* Redirect old routes */}
            <Route path="/dashboard" element={<Navigate to="/" replace />} />
            <Route path="/sessions" element={<Navigate to="/" replace />} />
            {/* Answer Management was merged into the Dashboard. */}
            <Route path="/answers" element={<Navigate to="/" replace />} />
          </Routes>
        
        {/* Toast notifications */}
        <Toaster
          position="bottom-right"
          toastOptions={{
            duration: 4000,
            // Theme tokens (src/index.css), so toasts follow light/dark mode.
            style: {
              background: 'color-mix(in srgb, var(--color-primary-dark) 92%, transparent)',
              color: '#ffffff',
              borderRadius: '0.5rem',
              fontSize: '0.875rem',
            },
            success: {
              duration: 3000,
              style: {
                background: 'var(--color-success)',
                color: 'var(--color-text-inverse)',
              },
              iconTheme: {
                primary: 'var(--color-text-inverse)',
                secondary: 'var(--color-success)',
              },
            },
            error: {
              duration: 5000,
              style: {
                background: 'var(--color-error)',
                color: 'var(--color-text-inverse)',
              },
              iconTheme: {
                primary: 'var(--color-text-inverse)',
                secondary: 'var(--color-error)',
              },
            },
          }}
        />
      </div>
        </AuthProvider>
      </ThemeProvider>
    </Router>
  );
}

export default App;