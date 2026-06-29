// Login/Signup Component with Email OTP
import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import {
  Smartphone,
  Lock,
  Loader2,
  CheckCircle,
  ArrowLeft,
  Sun,
  Moon,
  Zap,
  User,
  MapPin,
  ChevronRight,
  Shield,
  Mail,
  Eye,
  EyeOff,
  Globe,
  Home,
  AlertCircle
} from 'lucide-react';

const COUNTRIES = [
  "Pakistan", "India", "Bangladesh", "Sri Lanka", "Nepal",
  "United Arab Emirates", "Saudi Arabia", "Qatar", "Oman", "Kuwait",
  "United States", "United Kingdom", "Canada", "Australia"
];

export default function Auth({ mode = 'login', onComplete, onBack, onSwitchMode }) {
  const { login, signup, verifyEmailOTP, resendOTP } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  
  // Views: landing, signup-form, otp-verify, login-form
  const [view, setView] = useState(mode === 'signup' ? 'signup-form' : 'login-form');
  
  // Form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [country, setCountry] = useState('Pakistan');
  const [city, setCity] = useState('');
  const [address, setAddress] = useState('');
  
  // UI state
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [devOTP, setDevOTP] = useState(null);
  const [pendingEmail, setPendingEmail] = useState('');

  useEffect(() => {
    setView(mode === 'signup' ? 'signup-form' : 'login-form');
    setError('');
  }, [mode]);

  const validateForm = () => {
    if (!email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
      setError('Please enter a valid email address');
      return false;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return false;
    }
    if (mode === 'signup' && password !== confirmPassword) {
      setError('Passwords do not match');
      return false;
    }
    if (mode === 'signup' && !firstName.trim()) {
      setError('Please enter your first name');
      return false;
    }
    if (mode === 'signup' && !city.trim()) {
      setError('Please enter your city');
      return false;
    }
    return true;
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!validateForm()) return;
    
    setLoading(true);
    try {
      const result = await signup({
        email: email.toLowerCase().trim(),
        password,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        country,
        city: city.trim(),
        address: address.trim()
      });
      
      if (result.status === 'sent') {
        setPendingEmail(result.email);
        setDevOTP(result.otp_for_testing);
        setView('otp-verify');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
      setError('Please enter a valid email address');
      return;
    }
    if (!password) {
      setError('Please enter your password');
      return;
    }
    
    setLoading(true);
    try {
      await login(email.toLowerCase().trim(), password);
      onComplete();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleOTPVerify = async (e) => {
    e.preventDefault();
    setError('');
    
    if (otp.length < 6) {
      setError('Please enter the 6-digit code');
      return;
    }
    
    setLoading(true);
    try {
      await verifyEmailOTP(pendingEmail, otp);
      onComplete();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResendOTP = async () => {
    setLoading(true);
    setError('');
    try {
      const result = await resendOTP(pendingEmail);
      setDevOTP(result.otp_for_testing);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const inputClass = `w-full px-4 py-3.5 rounded-xl border-2 transition-all duration-200 outline-none ${
    isDark 
      ? 'bg-gray-700/50 border-gray-600 text-white placeholder-gray-400 focus:border-blue-500' 
      : 'bg-gray-50 border-gray-200 text-gray-900 placeholder-gray-400 focus:border-blue-500'
  }`;

  const labelClass = `block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`;

  return (
    <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50'}`}>
      {/* Header */}
      <header className={`${isDark ? 'bg-gray-800/80 backdrop-blur-sm border-gray-700' : 'bg-white/80 backdrop-blur-sm border-gray-200'} border-b sticky top-0 z-10`}>
        <div className="max-w-md mx-auto px-4 py-4 flex items-center justify-between">
          <button onClick={onBack} className={`flex items-center gap-2 font-medium transition-colors ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-700'}`}>
            <ArrowLeft className="w-5 h-5" />
            Back
          </button>
          <button onClick={toggleTheme} className={`p-2 rounded-xl transition-all ${isDark ? 'bg-gray-700 hover:bg-gray-600 text-yellow-400' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'}`}>
            {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
        </div>
      </header>

      <div className="flex items-center justify-center px-4 py-8 min-h-[calc(100vh-80px)]">
        <div className={`w-full max-w-md ${isDark ? 'bg-gray-800/90 backdrop-blur-sm' : 'bg-white/90 backdrop-blur-sm'} rounded-3xl shadow-2xl p-8 border ${isDark ? 'border-gray-700' : 'border-gray-100'}`}>
          
          {/* Logo */}
          <div className="text-center mb-6">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 via-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-xl shadow-blue-500/25">
              <Zap className="w-8 h-8 text-white" />
            </div>
            <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>CoolShift</h1>
            <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Smart Energy Optimization</p>
          </div>

          {/* Toggle */}
          <div className={`flex rounded-2xl p-1.5 mb-6 ${isDark ? 'bg-gray-700/50' : 'bg-gray-100'}`}>
            <button 
              onClick={() => onSwitchMode && onSwitchMode('login')}
              className={`flex-1 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 ${
                mode === 'login' 
                  ? 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white shadow-lg' 
                  : `${isDark ? 'text-gray-400' : 'text-gray-500'}`
              }`}>
              Sign In
            </button>
            <button 
              onClick={() => onSwitchMode && onSwitchMode('signup')}
              className={`flex-1 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 ${
                mode === 'signup' 
                  ? 'bg-gradient-to-r from-blue-500 to-indigo-500 text-white shadow-lg' 
                  : `${isDark ? 'text-gray-400' : 'text-gray-500'}`
              }`}>
              Sign Up
            </button>
          </div>

          {/* LOGIN FORM */}
          {view === 'login-form' && (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className={labelClass}>Email</label>
                <div className={`flex items-center gap-3 ${inputClass}`}>
                  <Mail className={`w-5 h-5 ${isDark ? 'text-gray-400' : 'text-gray-400'}`} />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="your@email.com"
                    className="flex-1 bg-transparent outline-none"
                  />
                </div>
              </div>

              <div>
                <label className={labelClass}>Password</label>
                <div className={`flex items-center gap-3 ${inputClass}`}>
                  <Lock className={`w-5 h-5 ${isDark ? 'text-gray-400' : 'text-gray-400'}`} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter password"
                    className="flex-1 bg-transparent outline-none"
                  />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="text-gray-400 hover:text-gray-600">
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              {error && (
                <div className={`p-3 rounded-xl text-sm flex items-center gap-2 ${isDark ? 'bg-red-900/30 text-red-400' : 'bg-red-50 text-red-600'}`}>
                  <AlertCircle className="w-4 h-4" />
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 px-4 py-4 rounded-2xl font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 disabled:opacity-50 shadow-lg shadow-blue-500/25"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : null}
                {loading ? 'Signing in...' : 'Sign In'}
                {!loading && <ChevronRight className="w-5 h-5" />}
              </button>
            </form>
          )}

          {/* SIGNUP FORM */}
          {view === 'signup-form' && (
            <form onSubmit={handleSignup} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>First Name *</label>
                  <div className={`flex items-center gap-2 ${inputClass}`}>
                    <User className={`w-4 h-4 ${isDark ? 'text-gray-400' : 'text-gray-400'}`} />
                    <input
                      type="text"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      placeholder="First name"
                      className="flex-1 bg-transparent outline-none text-sm"
                      required
                    />
                  </div>
                </div>
                <div>
                  <label className={labelClass}>Last Name</label>
                  <div className={`flex items-center gap-2 ${inputClass}`}>
                    <User className={`w-4 h-4 ${isDark ? 'text-gray-400' : 'text-gray-400'}`} />
                    <input
                      type="text"
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                      placeholder="Last name"
                      className="flex-1 bg-transparent outline-none text-sm"
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className={labelClass}>Email *</label>
                <div className={`flex items-center gap-3 ${inputClass}`}>
                  <Mail className={`w-5 h-5 ${isDark ? 'text-gray-400' : 'text-gray-400'}`} />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="your@email.com"
                    className="flex-1 bg-transparent outline-none"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>Country</label>
                  <div className={`flex items-center gap-2 ${inputClass}`}>
                    <Globe className={`w-4 h-4 ${isDark ? 'text-gray-400' : 'text-gray-400'}`} />
                    <select
                      value={country}
                      onChange={(e) => setCountry(e.target.value)}
                      className="flex-1 bg-transparent outline-none text-sm cursor-pointer"
                    >
                      {COUNTRIES.map(c => (
                        <option key={c} value={c} className={isDark ? 'bg-gray-800' : 'bg-white'}>{c}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div>
                  <label className={labelClass}>City *</label>
                  <div className={`flex items-center gap-2 ${inputClass}`}>
                    <MapPin className={`w-4 h-4 ${isDark ? 'text-gray-400' : 'text-gray-400'}`} />
                    <input
                      type="text"
                      value={city}
                      onChange={(e) => setCity(e.target.value)}
                      placeholder="City"
                      className="flex-1 bg-transparent outline-none text-sm"
                      required
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className={labelClass}>Address</label>
                <div className={`flex items-center gap-3 ${inputClass}`}>
                  <Home className={`w-5 h-5 ${isDark ? 'text-gray-400' : 'text-gray-400'}`} />
                  <input
                    type="text"
                    value={address}
                    onChange={(e) => setAddress(e.target.value)}
                    placeholder="Street address (optional)"
                    className="flex-1 bg-transparent outline-none"
                  />
                </div>
              </div>

              <div>
                <label className={labelClass}>Password *</label>
                <div className={`flex items-center gap-3 ${inputClass}`}>
                  <Lock className={`w-5 h-5 ${isDark ? 'text-gray-400' : 'text-gray-400'}`} />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Min 6 characters"
                    className="flex-1 bg-transparent outline-none"
                    required
                  />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="text-gray-400 hover:text-gray-600">
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              <div>
                <label className={labelClass}>Confirm Password *</label>
                <div className={`flex items-center gap-3 ${inputClass}`}>
                  <Lock className={`w-5 h-5 ${isDark ? 'text-gray-400' : 'text-gray-400'}`} />
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter password"
                    className="flex-1 bg-transparent outline-none"
                    required
                  />
                  <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)} className="text-gray-400 hover:text-gray-600">
                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
              </div>

              {error && (
                <div className={`p-3 rounded-xl text-sm flex items-center gap-2 ${isDark ? 'bg-red-900/30 text-red-400' : 'bg-red-50 text-red-600'}`}>
                  <AlertCircle className="w-4 h-4" />
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 px-4 py-4 rounded-2xl font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 disabled:opacity-50 shadow-lg shadow-blue-500/25"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : null}
                {loading ? 'Creating Account...' : 'Create Account'}
                {!loading && <ChevronRight className="w-5 h-5" />}
              </button>
            </form>
          )}

          {/* OTP VERIFICATION */}
          {view === 'otp-verify' && (
            <div className="space-y-6">
              <button
                onClick={() => setView(mode === 'signup' ? 'signup-form' : 'login-form')}
                className={`flex items-center gap-2 text-sm font-medium transition-colors ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-700'}`}
              >
                <ArrowLeft className="w-4 h-4" />
                Back
              </button>

              <div className="text-center">
                <div className="w-14 h-14 bg-green-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Mail className="w-7 h-7 text-green-600" />
                </div>
                <h2 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  Verify Email
                </h2>
                <p className={`text-sm mt-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  Code sent to {pendingEmail}
                </p>
                {devOTP && (
                  <div className={`mt-3 p-3 rounded-xl text-sm ${isDark ? 'bg-yellow-900/30 text-yellow-400' : 'bg-yellow-50 text-yellow-700'} border ${isDark ? 'border-yellow-700' : 'border-yellow-200'}`}>
                    <span className="font-semibold">DEV:</span> OTP is <span className="font-mono font-bold text-lg">{devOTP}</span>
                  </div>
                )}
              </div>

              <form onSubmit={handleOTPVerify} className="space-y-4">
                <div>
                  <label className={labelClass}>Enter 6-digit code</label>
                  <div className={`flex items-center gap-3 ${inputClass}`}>
                    <Lock className={`w-5 h-5 ${isDark ? 'text-gray-400' : 'text-gray-400'}`} />
                    <input
                      type="text"
                      value={otp}
                      onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                      placeholder="• • • • • •"
                      className="flex-1 bg-transparent outline-none text-lg tracking-[0.5em] text-center font-mono"
                      maxLength={6}
                      required
                      autoFocus
                    />
                  </div>
                </div>

                {error && (
                  <div className={`p-3 rounded-xl text-sm flex items-center gap-2 ${isDark ? 'bg-red-900/30 text-red-400' : 'bg-red-50 text-red-600'}`}>
                    <AlertCircle className="w-4 h-4" />
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading || otp.length < 6}
                  className="w-full flex items-center justify-center gap-2 px-4 py-4 rounded-2xl font-semibold bg-gradient-to-r from-green-600 to-emerald-600 text-white hover:from-green-700 hover:to-emerald-700 transition-all duration-200 disabled:opacity-50 shadow-lg shadow-green-500/25"
                >
                  {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : null}
                  {loading ? 'Verifying...' : 'Verify & Create Account'}
                  {!loading && <ChevronRight className="w-5 h-5" />}
                </button>

                <button
                  type="button"
                  onClick={handleResendOTP}
                  disabled={loading}
                  className={`w-full text-sm font-medium py-2 ${isDark ? 'text-blue-400 hover:text-blue-300' : 'text-blue-600 hover:text-blue-700'}`}
                >
                  Didn't receive code? Resend
                </button>
              </form>
            </div>
          )}

          <div className={`flex items-center gap-2 justify-center text-xs mt-6 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
            <Shield className="w-3.5 h-3.5" />
            <span>Your data is encrypted and secure</span>
          </div>
        </div>
      </div>
    </div>
  );
}