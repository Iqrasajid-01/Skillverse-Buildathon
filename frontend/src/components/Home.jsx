// Home Page - Landing page with Sign In / Sign Up
import { useState } from 'react';
import { Zap, Sun, Thermometer, TrendingDown, Leaf, Shield, ChevronRight, ArrowRight, Play, BarChart3 } from 'lucide-react';

const features = [
  { icon: Thermometer, title: 'Real Weather Data', desc: 'Live weather integration for accurate predictions' },
  { icon: TrendingDown, title: 'Smart Optimization', desc: 'AI-powered cooling schedule optimization' },
  { icon: Leaf, title: 'Cost Savings', desc: 'Reduce energy bills by up to 40%' },
  { icon: Shield, title: 'Comfort Guaranteed', desc: 'Stay within your preferred temperature range' }
];

export default function Home({ onAuth, onGuest }) {
  const [isDark, setIsDark] = useState(() => localStorage.getItem('coolshift_theme') === 'dark');

  const toggleDark = () => {
    const newDark = !isDark;
    setIsDark(newDark);
    document.documentElement.classList.toggle('dark', newDark);
    localStorage.setItem('coolshift_theme', newDark ? 'dark' : 'light');
  };

  return (
    <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50'}`}>
      {/* Header */}
      <header className={`${isDark ? 'bg-gray-800/80' : 'bg-white/80'} backdrop-blur-md border-b ${isDark ? 'border-gray-700' : 'border-gray-200'} sticky top-0 z-50`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                <Zap className="w-6 h-6 text-white" />
              </div>
              <span className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>CoolShift</span>
            </div>
            <div className="flex items-center gap-4">
              <button onClick={toggleDark} className={`p-2 rounded-lg ${isDark ? 'bg-gray-700 text-yellow-400' : 'bg-gray-100 text-gray-700'}`}>
                {isDark ? <Sun className="w-5 h-5" /> : <span className="text-lg">🌙</span>}
              </button>
              <button onClick={() => onAuth('login')} className={`px-4 py-2 rounded-lg font-medium ${isDark ? 'text-gray-300 hover:text-white' : 'text-gray-600 hover:text-gray-900'}`}>
                Sign In
              </button>
              <button onClick={() => onAuth('signup')} className="px-4 py-2 rounded-lg font-medium bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:shadow-lg transition-all">
                Sign Up Free
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 text-sm font-medium mb-6">
            <Thermometer className="w-4 h-4" />
            <span>Extreme Heat Energy Optimization</span>
          </div>
          <h1 className={`text-5xl md:text-6xl font-bold ${isDark ? 'text-white' : 'text-gray-900'} leading-tight`}>
            Smart Cooling,<br />
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">Smarter Savings</span>
          </h1>
          <p className={`mt-6 text-xl ${isDark ? 'text-gray-400' : 'text-gray-600'} max-w-2xl mx-auto`}>
            Optimize your AC and cooling systems based on real weather data. Save up to 40% on energy bills while staying comfortable.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <button onClick={() => onAuth('signup')} className="flex items-center gap-2 px-8 py-4 rounded-xl font-semibold text-lg bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:shadow-xl hover:shadow-blue-500/25 transition-all">
              Get Started Free <ArrowRight className="w-5 h-5" />
            </button>
            <button onClick={onGuest} className="flex items-center gap-2 px-8 py-4 rounded-xl font-semibold text-lg border-2 border-gray-300 dark:border-gray-600 hover:border-blue-500 dark:hover:border-blue-400 transition-all">
              <Play className="w-5 h-5" /> Try as Guest
            </button>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className={`py-12 ${isDark ? 'bg-gray-800/50' : 'bg-white/80'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
            {[
              { value: '40%', label: 'Energy Savings' },
              { value: '10K+', label: 'Users Optimized' },
              { value: '50+', label: 'Cities Covered' },
              { value: '24/7', label: 'Live Monitoring' }
            ].map((stat, i) => (
              <div key={i}>
                <div className={`text-3xl md:text-4xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent`}>{stat.value}</div>
                <div className={`mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Why CoolShift?</h2>
            <p className={`mt-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Everything you need to optimize cooling costs</p>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((f, i) => (
              <div key={i} className={`p-6 rounded-2xl ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'} hover:shadow-lg transition-all`}>
                <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center mb-4">
                  <f.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className={`font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{f.title}</h3>
                <p className={`mt-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it Works */}
      <section className={`py-20 ${isDark ? 'bg-gray-800/50' : 'bg-white/80'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>How It Works</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { step: '01', title: 'Upload Your Data', desc: 'Upload your energy consumption data or use our live calculator' },
              { step: '02', title: 'We Analyze & Optimize', desc: 'Our AI creates the perfect cooling schedule for your needs' },
              { step: '03', title: 'Save Money', desc: 'Follow the optimized schedule and watch your bills drop' }
            ].map((item, i) => (
              <div key={i} className="text-center">
                <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4 text-2xl font-bold text-white">{item.step}</div>
                <h3 className={`text-xl font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{item.title}</h3>
                <p className={`mt-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className={`rounded-3xl bg-gradient-to-r from-blue-600 to-purple-600 p-12 text-center`}>
            <h2 className="text-3xl font-bold text-white">Ready to Optimize Your Cooling?</h2>
            <p className="mt-3 text-blue-100 text-lg">Join thousands of users saving on their energy bills</p>
            <button onClick={() => onAuth('signup')} className="mt-8 inline-flex items-center gap-2 px-8 py-4 rounded-xl font-semibold text-lg bg-white text-blue-600 hover:bg-blue-50 transition-all">
              Create Free Account <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className={`py-8 border-t ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <p className={isDark ? 'text-gray-500' : 'text-gray-400'}>© 2026 CoolShift. Smart Energy Optimization Platform.</p>
        </div>
      </footer>
    </div>
  );
}
