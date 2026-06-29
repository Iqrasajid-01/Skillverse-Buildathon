// Live Calculator Component - Real-time energy calculation with geolocation + weather
import { useState, useEffect } from 'react';
import { MapPin, Sun, Moon, Thermometer, Calculator, TrendingDown, CheckCircle, Loader2, Clock, ArrowRight, Navigation } from 'lucide-react';

const API_BASE = 'http://localhost:8003/api';

const scenarios = [
  { id: 'household_no_solar', name: 'Household without Solar', icon: '🏠', desc: 'Regular home without solar panels' },
  { id: 'household_solar', name: 'Household with Solar & Battery', icon: '☀️', desc: 'Home with solar panels and battery storage' },
  { id: 'school', name: 'School / Small Office', icon: '🏫', desc: 'Commercial space with multiple AC units' }
];

const appliances = [
  { key: 'has_fridge', label: 'Refrigerator', icon: '🧊' },
  { key: 'has_washing_machine', label: 'Washing Machine', icon: '👕' },
  { key: 'has_blender', label: 'Blender/Mixer', icon: '🍹' },
  { key: 'has_water_motor', label: 'Water Motor', icon: '💧' },
  { key: 'has_iron', label: 'Iron', icon: '👔' },
  { key: 'has_dispenser', label: 'Water Dispenser', icon: '🚰' }
];

const PAKISTANI_CITIES = ['Karachi', 'Lahore', 'Islamabad', 'Faisalabad', 'Multan', 'Peshawar', 'Rawalpindi', 'Hyderabad', 'Quetta', 'Sukkur', 'Sialkot', 'Gujranwala', 'Abbottabad', 'Bahawalpur'];

export default function LiveCalculator({ onBack }) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [weather, setWeather] = useState(null);
  const [results, setResults] = useState(null);
  const [isDark, setIsDark] = useState(() => localStorage.getItem('coolshift_theme') === 'dark');
  const [showLocationPopup, setShowLocationPopup] = useState(true);
  const [locationLoading, setLocationLoading] = useState(false);
  const [locationError, setLocationError] = useState('');

  const [formData, setFormData] = useState({
    scenario_type: '',
    ac_count: 1,
    fan_count: 2,
    has_fridge: false,
    has_washing_machine: false,
    has_blender: false,
    has_water_motor: false,
    has_iron: false,
    has_dispenser: false,
    unit_price: 50,
    city: 'Karachi',
    latitude: null,
    longitude: null
  });

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark);
    localStorage.setItem('coolshift_theme', isDark ? 'dark' : 'light');
  }, [isDark]);

  // Fetch weather when city changes
  useEffect(() => {
    if (formData.city) {
      fetch(`${API_BASE}/weather/${formData.city}`)
        .then(res => res.json())
        .then(setWeather)
        .catch(() => setWeather(null));
    }
  }, [formData.city]);

  // Get user's location
  const getLocation = () => {
    setLocationLoading(true);
    setLocationError('');

    if (!navigator.geolocation) {
      setLocationError('Geolocation not supported by your browser');
      setLocationLoading(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords;
        setFormData(prev => ({ ...prev, latitude, longitude }));

        // Reverse geocode to get city
        try {
          const res = await fetch(`https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json`);
          const data = await res.json();
          const city = data.address?.city || data.address?.town || data.address?.village || '';
          if (city && PAKISTANI_CITIES.some(c => city.toLowerCase().includes(c.toLowerCase()))) {
            setFormData(prev => ({ ...prev, city }));
          }
        } catch (e) {
          console.log('Reverse geocode failed');
        }

        setLocationLoading(false);
        setShowLocationPopup(false);
      },
      (error) => {
        setLocationError('Unable to get location. Please select city manually.');
        setLocationLoading(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  // Skip location and select city manually
  const skipLocation = () => {
    setShowLocationPopup(false);
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/live/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      const data = await res.json();
      setResults(data);
      setStep(3);
    } catch (err) {
      console.error('Calculation failed:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50'}`}>
      {/* Location Popup Modal */}
      {showLocationPopup && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className={`w-full max-w-md rounded-2xl ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white'} shadow-2xl p-8`}>
            <div className="text-center">
              <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-pink-600 rounded-full flex items-center justify-center mx-auto mb-6">
                <Navigation className="w-10 h-10 text-white" />
              </div>
              <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Enable Location</h2>
              <p className={`mt-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                We need your location to show accurate weather data for your area and calculate energy costs based on real conditions.
              </p>

              {locationError && (
                <div className="mt-4 p-3 bg-red-100 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-lg">
                  <p className="text-red-600 dark:text-red-400 text-sm">{locationError}</p>
                </div>
              )}

              <div className="mt-6 space-y-3">
                <button onClick={getLocation} disabled={locationLoading}
                  className="w-full flex items-center justify-center gap-2 px-6 py-4 rounded-xl font-semibold bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:shadow-lg transition-all">
                  {locationLoading ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : (
                    <MapPin className="w-5 h-5" />
                  )}
                  {locationLoading ? 'Getting Location...' : 'Share My Location'}
                </button>
                <button onClick={skipLocation}
                  className={`w-full py-3 text-sm ${isDark ? 'text-gray-400 hover:text-gray-300' : 'text-gray-500 hover:text-gray-600'}`}>
                  Skip - Select city manually
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Manual City Selection Popup */}
      {showLocationPopup === 'select_city' && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className={`w-full max-w-md rounded-2xl ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white'} shadow-2xl p-8`}>
            <h2 className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Select Your City</h2>
            <p className={`mt-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Choose your city from the list</p>
            <div className="mt-4 grid grid-cols-2 gap-2 max-h-64 overflow-y-auto">
              {PAKISTANI_CITIES.map(city => (
                <button key={city} onClick={() => {
                  setFormData(prev => ({ ...prev, city }));
                  setShowLocationPopup(false);
                }}
                  className={`p-3 rounded-lg text-left text-sm ${formData.city === city ? 'bg-purple-100 dark:bg-purple-900/50 text-purple-700 dark:text-purple-300 border border-purple-300' : isDark ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-50 text-gray-700 hover:bg-gray-100'}`}>
                  {city}
                </button>
              ))}
            </div>
            <button onClick={() => setShowLocationPopup(true)} className={`mt-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>← Back</button>
          </div>
        </div>
      )}

      <header className={`${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border-b sticky top-0 z-10`}>
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {step > 1 ? (
              <button onClick={() => setStep(step - 1)} className={`p-2 rounded-lg ${isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}>←</button>
            ) : (
              <button onClick={onBack} className={`p-2 rounded-lg ${isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}>←</button>
            )}
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl flex items-center justify-center">
              <Calculator className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className={`text-lg font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Live Calculator</h1>
              <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Step {step} of 3</p>
            </div>
          </div>
          <button onClick={() => setIsDark(!isDark)} className={`p-2 rounded-lg ${isDark ? 'bg-gray-700 text-yellow-400' : 'bg-gray-100 text-gray-700'}`}>
            {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
        </div>
        <div className={`h-1 ${isDark ? 'bg-gray-700' : 'bg-gray-100'}`}>
          <div className="h-full bg-gradient-to-r from-purple-500 to-pink-600 transition-all duration-300" style={{ width: `${(step / 3) * 100}%` }} />
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6">
        {/* Step 1: Scenario */}
        {step === 1 && (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>What type of place is this?</h2>
              <p className={`mt-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Select your scenario type</p>
            </div>
            <div className="space-y-4">
              {scenarios.map((s) => (
                <button key={s.id} onClick={() => setFormData(prev => ({ ...prev, scenario_type: s.id }))}
                  className={`w-full p-5 rounded-2xl border-2 transition-all text-left ${formData.scenario_type === s.id ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/30' : isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'}`}>
                  <div className="flex items-start gap-4">
                    <span className="text-4xl">{s.icon}</span>
                    <div className="flex-1">
                      <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{s.name}</h3>
                      <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{s.desc}</p>
                    </div>
                    {formData.scenario_type === s.id && <CheckCircle className="w-6 h-6 text-purple-500" />}
                  </div>
                </button>
              ))}
            </div>
            <button onClick={() => setStep(2)} disabled={!formData.scenario_type}
              className={`w-full py-4 rounded-xl font-semibold text-lg transition-all flex items-center justify-center gap-2 ${formData.scenario_type ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white' : isDark ? 'bg-gray-700 text-gray-500' : 'bg-gray-200 text-gray-400'}`}>
              Continue <ArrowRight className="w-5 h-5" />
            </button>
          </div>
        )}

        {/* Step 2: Details */}
        {step === 2 && (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Tell us about your setup</h2>
              <p className={`mt-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Enter your appliances and location</p>
            </div>

            {/* Weather Card */}
            {weather && (
              <div className={`p-4 rounded-2xl ${isDark ? 'bg-gradient-to-r from-amber-900/30 to-orange-900/30 border border-amber-700' : 'bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-amber-100 dark:bg-amber-900 rounded-full flex items-center justify-center">
                      <Thermometer className="w-6 h-6 text-amber-600 dark:text-amber-400" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className={`font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{weather.city}</p>
                        <button onClick={() => setShowLocationPopup('select_city')} className="text-xs text-purple-500 underline">Change</button>
                      </div>
                      <p className={`text-sm ${isDark ? 'text-amber-300' : 'text-amber-600'}`}>{weather.temperature_c}°C - {weather.condition}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`text-2xl font-bold ${isDark ? 'text-amber-300' : 'text-amber-600'}`}>{weather.hourly_forecast?.[14]?.temp_c || weather.temperature_c}°C</p>
                    <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Peak at 2PM</p>
                  </div>
                </div>
              </div>
            )}

            {/* AC & Fans */}
            <div className={`p-5 rounded-2xl ${isDark ? 'bg-gray-800' : 'bg-white'} border ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
              <h3 className={`font-semibold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Cooling Appliances</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={`block text-sm mb-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Number of ACs</label>
                  <div className="flex items-center gap-3">
                    <button onClick={() => setFormData(p => ({ ...p, ac_count: Math.max(0, p.ac_count - 1) }))} className={`w-10 h-10 rounded-lg ${isDark ? 'bg-gray-700' : 'bg-gray-100'} font-bold`}>-</button>
                    <span className={`text-2xl font-bold w-8 text-center ${isDark ? 'text-white' : 'text-gray-900'}`}>{formData.ac_count}</span>
                    <button onClick={() => setFormData(p => ({ ...p, ac_count: Math.min(10, p.ac_count + 1) }))} className={`w-10 h-10 rounded-lg ${isDark ? 'bg-gray-700' : 'bg-gray-100'} font-bold`}>+</button>
                  </div>
                </div>
                <div>
                  <label className={`block text-sm mb-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Number of Fans</label>
                  <div className="flex items-center gap-3">
                    <button onClick={() => setFormData(p => ({ ...p, fan_count: Math.max(0, p.fan_count - 1) }))} className={`w-10 h-10 rounded-lg ${isDark ? 'bg-gray-700' : 'bg-gray-100'} font-bold`}>-</button>
                    <span className={`text-2xl font-bold w-8 text-center ${isDark ? 'text-white' : 'text-gray-900'}`}>{formData.fan_count}</span>
                    <button onClick={() => setFormData(p => ({ ...p, fan_count: Math.min(20, p.fan_count + 1) }))} className={`w-10 h-10 rounded-lg ${isDark ? 'bg-gray-700' : 'bg-gray-100'} font-bold`}>+</button>
                  </div>
                </div>
              </div>
            </div>

            {/* Other Appliances */}
            <div className={`p-5 rounded-2xl ${isDark ? 'bg-gray-800' : 'bg-white'} border ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
              <h3 className={`font-semibold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Other Appliances</h3>
              <div className="grid grid-cols-2 gap-3">
                {appliances.map((app) => (
                  <button key={app.key} onClick={() => setFormData(p => ({ ...p, [app.key]: !p[app.key] }))}
                    className={`p-3 rounded-xl border-2 flex items-center gap-3 transition-all ${formData[app.key] ? 'border-green-500 bg-green-50 dark:bg-green-900/30' : isDark ? 'border-gray-700 bg-gray-700/50' : 'border-gray-200 bg-gray-50'}`}>
                    <span className="text-2xl">{app.icon}</span>
                    <span className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-700'}`}>{app.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Unit Price */}
            <div className={`p-5 rounded-2xl ${isDark ? 'bg-gray-800' : 'bg-white'} border ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
              <h3 className={`font-semibold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Electricity Unit Price</h3>
              <div className="flex items-center gap-3">
                <input type="number" value={formData.unit_price} onChange={(e) => setFormData(p => ({ ...p, unit_price: Number(e.target.value) }))}
                  className={`flex-1 px-4 py-3 rounded-xl border-2 ${isDark ? 'bg-gray-700 border-gray-600 text-white' : 'bg-gray-50 border-gray-200'}`} min="1" max="200" />
                <span className={`font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>PKR / unit</span>
              </div>
            </div>

            <button onClick={handleSubmit} disabled={loading}
              className={`w-full py-4 rounded-xl font-semibold text-lg transition-all flex items-center justify-center gap-2 ${!loading ? 'bg-gradient-to-r from-green-500 to-emerald-600 text-white' : 'bg-gray-400 text-white'}`}>
              {loading ? <><Loader2 className="w-5 h-5 animate-spin" /> Calculating...</> : <><TrendingDown className="w-5 h-5" /> Calculate My Savings</>}
            </button>
          </div>
        )}

        {/* Step 3: Results */}
        {step === 3 && results && (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-gradient-to-br from-green-400 to-emerald-500 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
                <TrendingDown className="w-8 h-8 text-white" />
              </div>
              <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Your Energy Report</h2>
              <p className={`mt-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Based on {formData.city} live weather data</p>
            </div>

            {/* Main Savings Card */}
            <div className={`p-6 rounded-2xl ${isDark ? 'bg-gradient-to-br from-green-900/50 to-emerald-900/50 border border-green-700' : 'bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200'}`}>
              <div className="text-center">
                <p className={`text-sm font-medium ${isDark ? 'text-green-400' : 'text-green-600'}`}>Estimated Daily Cost</p>
                <p className={`text-5xl font-bold mt-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>PKR {results.summary.total_cost_pkr}</p>
                <p className={`text-sm mt-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{results.summary.total_energy_kwh} kWh energy consumption</p>
              </div>
            </div>

            {/* Savings Potential */}
            <div className={`p-5 rounded-2xl ${isDark ? 'bg-gray-800' : 'bg-white'} border ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
              <h3 className={`font-semibold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>💰 Savings Potential with CoolShift</h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Monthly Savings</span>
                  <span className={`font-bold text-lg ${isDark ? 'text-green-400' : 'text-green-600'}`}>PKR {results.savings_potential.monthly_savings_pkr}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Annual Savings</span>
                  <span className={`font-bold text-lg ${isDark ? 'text-green-400' : 'text-green-600'}`}>PKR {results.savings_potential.annual_savings_pkr}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Optimization</span>
                  <span className="px-3 py-1 bg-purple-100 dark:bg-purple-900/50 text-purple-600 dark:text-purple-400 rounded-full text-sm font-medium">{results.savings_potential.optimization_percent}% better</span>
                </div>
              </div>
            </div>

            {/* Hourly Breakdown */}
            <div className={`p-5 rounded-2xl ${isDark ? 'bg-gray-800' : 'bg-white'} border ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
              <h3 className={`font-semibold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Hourly Breakdown</h3>
              <div className="max-h-64 overflow-y-auto space-y-2">
                {results.hourly_breakdown.map((hour) => (
                  <div key={hour.hour} className={`flex items-center justify-between p-2 rounded-lg ${hour.is_peak ? isDark ? 'bg-amber-900/30' : 'bg-amber-50' : isDark ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                    <div className="flex items-center gap-3">
                      <Clock className={`w-4 h-4 ${hour.is_peak ? 'text-amber-500' : isDark ? 'text-gray-500' : 'text-gray-400'}`} />
                      <span className={isDark ? 'text-white' : 'text-gray-900'}>{hour.hour_label}</span>
                      {hour.is_peak && <span className="text-xs px-2 py-0.5 bg-amber-100 dark:bg-amber-900 text-amber-600 dark:text-amber-400 rounded">Peak</span>}
                    </div>
                    <div className="text-right">
                      <span className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{hour.energy_kwh} kWh</span>
                      <span className={`ml-2 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>PKR {hour.cost_pkr}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <button onClick={() => { setStep(2); setResults(null); }} className={`flex-1 py-3 rounded-xl font-medium ${isDark ? 'bg-gray-700 text-white' : 'bg-gray-100 text-gray-700'}`}>Recalculate</button>
              <button onClick={onBack} className="flex-1 py-3 rounded-xl font-medium bg-gradient-to-r from-purple-600 to-pink-600 text-white">Back to Dashboard</button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
