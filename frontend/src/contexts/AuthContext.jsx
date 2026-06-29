// Authentication Context - Email OTP based authentication
import { createContext, useContext, useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8003';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sessionToken, setSessionToken] = useState(null);

  useEffect(() => {
    const storedToken = localStorage.getItem('coolshift_token');
    if (storedToken) {
      setSessionToken(storedToken);
      fetchUser(storedToken);
    } else {
      setLoading(false);
    }
  }, []);

  const fetchUser = async (token) => {
    try {
      const response = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setUser(data.user);
      } else {
        localStorage.removeItem('coolshift_token');
        setSessionToken(null);
      }
    } catch (err) {
      console.error('Auth check failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const signup = async (userData) => {
    const response = await fetch(`${API_BASE}/api/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userData)
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Signup failed');
    }
    return data;
  };

  const verifyEmailOTP = async (email, otp) => {
    const response = await fetch(`${API_BASE}/api/auth/verify-email-otp`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, otp })
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'OTP verification failed');
    }
    
    localStorage.setItem('coolshift_token', data.session_token);
    setSessionToken(data.session_token);
    setUser(data.user);
    return data;
  };

  const resendOTP = async (email) => {
    const response = await fetch(`${API_BASE}/api/auth/resend-otp?email=${encodeURIComponent(email)}`, {
      method: 'POST'
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Failed to resend OTP');
    }
    return data;
  };

  const login = async (email, password) => {
    const response = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Login failed');
    }
    
    localStorage.setItem('coolshift_token', data.session_token);
    setSessionToken(data.session_token);
    setUser(data.user);
    return data;
  };

  const updateProfile = async (profileData) => {
    const response = await fetch(`${API_BASE}/api/auth/profile`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${sessionToken}`
      },
      body: JSON.stringify(profileData)
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Profile update failed');
    }
    setUser(data.user);
    return data;
  };

  const updatePassword = async (oldPassword, newPassword) => {
    const response = await fetch(`${API_BASE}/api/auth/password`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${sessionToken}`
      },
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Password update failed');
    }
    return data;
  };

  const logout = async () => {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${sessionToken}` }
      });
    } catch (err) {
      console.log('Logout error:', err);
    }
    localStorage.removeItem('coolshift_token');
    setUser(null);
    setSessionToken(null);
  };

  const value = {
    user,
    loading,
    isAuthenticated: !!user,
    sessionToken,
    signup,
    verifyEmailOTP,
    resendOTP,
    login,
    updateProfile,
    updatePassword,
    logout
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}