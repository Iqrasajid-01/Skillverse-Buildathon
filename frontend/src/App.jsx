// Main App - Routing between Home, Auth, and Dashboard
import { useState, useEffect } from 'react';
import Home from './components/Home';
import Auth from './components/Auth';
import Dashboard from './components/Dashboard';
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';

function App() {
  const [page, setPage] = useState('home'); // home, auth, dashboard
  const [authMode, setAuthMode] = useState('login'); // login, signup
  const [user, setUser] = useState(null);

  useEffect(() => {
    // Check for existing session
    const token = localStorage.getItem('coolshift_token');
    if (token) {
      // Verify token with backend
      fetch('http://localhost:8003/api/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
        .then(res => res.ok ? res.json() : null)
        .then(data => {
          if (data?.user) {
            setUser(data.user);
            setPage('dashboard');
          }
        })
        .catch(() => {});
    }
  }, []);

  const handleAuth = (mode) => {
    setAuthMode(mode);
    setPage('auth');
  };

  const handleGuest = () => {
    setUser({ name: 'Guest User', is_guest: true });
    setPage('dashboard');
  };

  const handleAuthComplete = (userData) => {
    setUser(userData);
    setPage('dashboard');
  };

  const handleLogout = () => {
    localStorage.removeItem('coolshift_token');
    setUser(null);
    setPage('home');
  };

  const handleBackToHome = () => {
    setPage('home');
  };

  return (
    <>
      {page === 'home' && (
        <Home onAuth={handleAuth} onGuest={handleGuest} />
      )}
      {page === 'auth' && (
        <AuthProvider>
          <ThemeProvider>
            <Auth
              mode={authMode}
              onComplete={handleAuthComplete}
              onBack={handleBackToHome}
              onSwitchMode={(mode) => setAuthMode(mode)}
            />
          </ThemeProvider>
        </AuthProvider>
      )}
      {page === 'dashboard' && (
        <Dashboard
          user={user}
          onLogout={handleLogout}
        />
      )}
    </>
  );
}

export default App;