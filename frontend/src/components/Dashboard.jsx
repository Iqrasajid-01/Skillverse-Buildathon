// Dashboard - Main dashboard with Manual & Live options
import { useState, useEffect } from 'react';
import { Zap, Upload, Calculator, Sun, Moon, LogOut, User, Activity, ChevronRight, BarChart3, TrendingDown, Leaf, Target, RefreshCw, AlertTriangle, CheckCircle, Play, Calendar, Download, Brain } from 'lucide-react';
import LiveCalculator from './LiveCalculator';
import ComparisonChart from './ComparisonChart';
import KPICard from './KPICard';
import ScheduleTable from './ScheduleTable';
import AlertsPanel from './AlertsPanel';
import ExtendedSummary from './ExtendedSummary';

const API_BASE = 'http://localhost:8003/api';

export default function Dashboard({ user, onLogout }) {
  const [view, setView] = useState('menu'); // menu, manual, live
  const [isDark, setIsDark] = useState(() => localStorage.getItem('coolshift_theme') === 'dark');

  // ML Status
  const [mlStatus, setMlStatus] = useState({ ml_available: false, models: {} });

  // Manual mode state
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenario, setSelectedScenario] = useState('PUB-A');
  const [daysToProcess, setDaysToProcess] = useState(7);
  const [uploadedData, setUploadedData] = useState(null);
  const [scenarioData, setScenarioData] = useState(null);
  const [baselineResult, setBaselineResult] = useState(null);
  const [optimizedResult, setOptimizedResult] = useState(null);
  const [runId, setRunId] = useState(null);
  const [isLoadingBaseline, setIsLoadingBaseline] = useState(false);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [optimizationMethod, setOptimizationMethod] = useState('ortools_milp');
  const [error, setError] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [extendedSummary, setExtendedSummary] = useState(null);

  // Fetch ML status on mount
  useEffect(() => {
    fetch(`${API_BASE}/ml/status`)
      .then(res => res.json())
      .then(data => setMlStatus(data))
      .catch(() => {});
  }, []);

  const toggleDark = () => {
    const nd = !isDark;
    setIsDark(nd);
    document.documentElement.classList.toggle('dark', nd);
    localStorage.setItem('coolshift_theme', nd ? 'dark' : 'light');
  };

  const handleUploadSuccess = (data) => {
    setUploadedData(data);
    setSelectedScenario(null);
  };

  const loadScenarios = async () => {
    try {
      const res = await fetch(`${API_BASE}/scenarios`);
      const data = await res.json();
      setScenarios(data);
    } catch (err) {
      setScenarios([
        { id: 'PUB-A', name: 'Household (No Solar)', type: 'public', days: 30 },
        { id: 'PUB-B', name: 'Household (Solar + Battery)', type: 'public', days: 30 },
        { id: 'PUB-C', name: 'School/Office', type: 'public', days: 30 }
      ]);
    }
  };

  const calculateBaseline = async () => {
    console.log('[Baseline] Starting with:', { uploadedData: !!uploadedData, selectedScenario, daysToProcess });
    if (!uploadedData && !selectedScenario) {
      console.log('[Baseline] No data selected, returning early');
      return;
    }
    setIsLoadingBaseline(true);
    setError(null);
    setBaselineResult(null);
    setOptimizedResult(null);

    try {
      let data;
      if (uploadedData) {
        data = uploadedData.scenario_input;
        console.log('[Baseline] Using uploaded data');
      } else {
        console.log('[Baseline] Fetching public scenario:', selectedScenario, 'days:', daysToProcess);
        const loadRes = await fetch(`${API_BASE}/public/${selectedScenario}?start_day=1&days=${daysToProcess}`);
        if (!loadRes.ok) {
          throw new Error(`Failed to load scenario: ${loadRes.status} ${loadRes.statusText}`);
        }
        data = await loadRes.json();
        console.log('[Baseline] Loaded scenario data, interval count:', data.interval_inputs?.length);
      }
      setScenarioData(data);

      console.log('[Baseline] Calling baseline API...');
      const baselineRes = await fetch(`${API_BASE}/baseline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      console.log('[Baseline] Response status:', baselineRes.status);
      
      if (!baselineRes.ok) {
        const errorText = await baselineRes.text();
        throw new Error(`Baseline API error ${baselineRes.status}: ${errorText}`);
      }
      
      const baseline = await baselineRes.json();
      console.log('[Baseline] Success, got result:', { energy: baseline.total_energy_kwh, cost: baseline.total_cost_pkr });
      
      setBaselineResult({
        total_energy_kwh: baseline.total_energy_kwh,
        total_cost_pkr: baseline.total_cost_pkr,
        total_emissions_kgco2e: baseline.total_emissions_kgco2e,
        peak_demand_kw: baseline.peak_demand_kw,
        comfort_compliance_pct: baseline.comfort_compliance_pct,
        intervals: baseline.intervals || [],
        daily_summaries: baseline.daily_summaries || []
      });
      console.log('[Baseline] State updated successfully');
    } catch (err) {
      console.error('[Baseline] Error:', err);
      setError(err.message);
    } finally {
      setIsLoadingBaseline(false);
    }
  };

  const runOptimization = async () => {
    if (!scenarioData) return;
    setIsOptimizing(true);
    setError(null);

    try {
      const optRes = await fetch(`${API_BASE}/optimize?method=${optimizationMethod}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scenarioData)
      });
      const optData = await optRes.json();
      setRunId(optData.run_id);

      const runRes = await fetch(`${API_BASE}/run/${optData.run_id}`);
      const fullResult = await runRes.json();

      setOptimizedResult({
        scenario_id: fullResult.scenario_id || selectedScenario,
        run_id: optData.run_id,
        summary: fullResult.summary,
        intervals: fullResult.intervals || [],
        daily_summaries: fullResult.daily_summaries || []
      });

      // Fetch alerts
      try {
        const alertsRes = await fetch(`${API_BASE}/alerts/${optData.run_id}`, { method: 'POST' });
        if (alertsRes.ok) {
          const alertsData = await alertsRes.json();
          setAlerts(alertsData.alerts || []);
        }
      } catch (e) {
        console.log('Alerts fetch skipped');
      }

      // Fetch extended summary
      try {
        const summaryRes = await fetch(`${API_BASE}/summary/${optData.run_id}/extended`);
        if (summaryRes.ok) {
          const summaryData = await summaryRes.json();
          setExtendedSummary(summaryData);
        }
      } catch (e) {
        console.log('Summary fetch skipped');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsOptimizing(false);
    }
  };

  const exportCSV = async () => {
    if (!runId) return;
    try {
      const res = await fetch(`${API_BASE}/export/csv/${runId}`, { method: 'POST' });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `coolshift_${runId}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  const exportExcel = async () => {
    if (!runId) return;
    try {
      const res = await fetch(`${API_BASE}/export/excel/${runId}`, { method: 'POST' });
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `coolshift_${runId}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  const savings = baselineResult && optimizedResult?.summary ? {
    cost_savings: baselineResult.total_cost_pkr - optimizedResult.summary.total_cost_pkr,
    cost_savings_pct: ((baselineResult.total_cost_pkr - optimizedResult.summary.total_cost_pkr) / baselineResult.total_cost_pkr * 100),
    energy_savings: baselineResult.total_energy_kwh - optimizedResult.summary.total_energy_kwh,
    energy_savings_pct: ((baselineResult.total_energy_kwh - optimizedResult.summary.total_energy_kwh) / baselineResult.total_energy_kwh * 100),
    emissions_savings: baselineResult.total_emissions_kgco2e - optimizedResult.summary.total_emissions_kgco2e,
    emissions_savings_pct: ((baselineResult.total_emissions_kgco2e - optimizedResult.summary.total_emissions_kgco2e) / baselineResult.total_emissions_kgco2e * 100),
    peak_reduction: baselineResult.peak_demand_kw - (optimizedResult.summary.peak_demand_kw || 0),
  } : null;

  // Menu View
  if (view === 'menu') {
    return (
      <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50'}`}>
        <header className={`${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border-b sticky top-0 z-10`}>
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className={`text-lg font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>CoolShift</h1>
                <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Dashboard</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-sm">
                <User className="w-4 h-4 text-gray-400" />
                <span className={isDark ? 'text-gray-300' : 'text-gray-700'}>{user?.phone || user?.email || 'User'}</span>
              </div>
              <button onClick={toggleDark} className={`p-2 rounded-lg ${isDark ? 'bg-gray-700 text-yellow-400' : 'bg-gray-100 text-gray-700'}`}>
                {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
              </button>
              <button onClick={onLogout} className={`p-2 rounded-lg ${isDark ? 'bg-gray-700 text-red-400' : 'bg-gray-100 text-red-600'}`}>
                <LogOut className="w-5 h-5" />
              </button>
            </div>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center mb-10">
            <h2 className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Choose Your Mode</h2>
            <p className={`mt-2 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Select how you want to optimize your energy</p>
          </div>

          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            {/* Manual Card */}
            <button onClick={() => { setView('manual'); loadScenarios(); }}
              className={`group p-8 rounded-2xl border-2 transition-all text-left hover:shadow-2xl ${isDark ? 'bg-gray-800 border-gray-700 hover:border-blue-500' : 'bg-white border-gray-200 hover:border-blue-500'}`}>
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center mb-6">
                <BarChart3 className="w-8 h-8 text-white" />
              </div>
              <h3 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Manual Mode</h3>
              <p className={`mt-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                Upload your dataset or use built-in scenarios for detailed optimization with full control over parameters.
              </p>
              <div className="mt-6 flex items-center gap-2 text-blue-600 font-medium">
                Upload Dataset <ChevronRight className="w-5 h-5" />
              </div>
            </button>

            {/* Live Card */}
            <button onClick={() => setView('live')}
              className={`group p-8 rounded-2xl border-2 transition-all text-left hover:shadow-2xl ${isDark ? 'bg-gray-800 border-gray-700 hover:border-purple-500' : 'bg-white border-gray-200 hover:border-purple-500'}`}>
              <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-600 rounded-2xl flex items-center justify-center mb-6">
                <Calculator className="w-8 h-8 text-white" />
              </div>
              <h3 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Live Calculator</h3>
              <p className={`mt-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                Real-time weather data, geolocation-based calculations. Get instant savings estimates based on your actual location.
              </p>
              <div className="mt-6 flex items-center gap-2 text-purple-600 font-medium">
                Try Live <ChevronRight className="w-5 h-5" />
              </div>
            </button>
          </div>

          {/* Quick Stats */}
          <div className={`mt-12 p-6 rounded-2xl ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'}`}>
            <h3 className={`font-semibold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Quick Stats</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className={`p-4 rounded-xl ${isDark ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                <Activity className="w-5 h-5 text-green-500 mb-2" />
                <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>-40%</p>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Potential Savings</p>
              </div>
              <div className={`p-4 rounded-xl ${isDark ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                <Zap className="w-5 h-5 text-blue-500 mb-2" />
                <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>24/7</p>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Monitoring</p>
              </div>
              <div className={`p-4 rounded-xl ${isDark ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                <Sun className="w-5 h-5 text-amber-500 mb-2" />
                <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Live</p>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Weather Data</p>
              </div>
              <div className={`p-4 rounded-xl ${isDark ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
                <Calculator className="w-5 h-5 text-purple-500 mb-2" />
                <p className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>AI</p>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Optimization</p>
              </div>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // Manual View
  if (view === 'manual') {
    return (
      <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50'}`}>
        <header className={`${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} border-b sticky top-0 z-10`}>
          <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button onClick={() => setView('menu')} className={`p-2 rounded-lg ${isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}>←</button>
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center">
                <BarChart3 className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className={`text-lg font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Manual Mode</h1>
                <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Upload dataset for optimization</p>
              </div>
            </div>
            <button onClick={toggleDark} className={`p-2 rounded-lg ${isDark ? 'bg-gray-700 text-yellow-400' : 'bg-gray-100 text-gray-700'}`}>
              {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
          </div>
        </header>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {/* Data Source */}
          <div className={`p-6 rounded-2xl ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'} mb-6`}>
            <h2 className={`text-lg font-semibold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Data Source</h2>
            <div className="flex flex-col sm:flex-row gap-4">
              <button onClick={() => setUploadedData(null)} className={`flex items-center gap-2 px-6 py-4 rounded-xl font-semibold transition-all ${!uploadedData ? 'bg-purple-100 text-purple-700 border-2 border-purple-300' : 'bg-gray-50 text-gray-600 border border-gray-200'}`}>
                <BarChart3 className="w-5 h-5" /> Built-in Scenarios
              </button>
              <div className="flex items-center text-gray-400"><span className="text-sm">— OR —</span></div>
              <button onClick={() => document.getElementById('excel-upload').click()} className={`flex items-center gap-2 px-6 py-4 rounded-xl font-semibold transition-all ${uploadedData ? 'bg-purple-100 text-purple-700 border-2 border-purple-300' : 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white'}`}>
                <Upload className="w-5 h-5" /> {uploadedData ? 'Excel Uploaded ✓' : 'Upload Excel'}
              </button>
              <input id="excel-upload" type="file" accept=".xlsx,.xls" className="hidden"
                onChange={async (e) => {
                  const file = e.target.files[0];
                  if (!file) return;
                  const formData = new FormData();
                  formData.append('file', file);
                  const res = await fetch(`${API_BASE}/import/excel`, { method: 'POST', body: formData });
                  const data = await res.json();
                  if (data.status === 'success') handleUploadSuccess(data);
                }} />
            </div>
          </div>

          {/* Scenarios */}
          {!uploadedData && (
            <div className={`p-6 rounded-2xl ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'} mb-6`}>
              <h2 className={`text-lg font-semibold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>Select Scenario</h2>
              <div className="flex flex-wrap gap-3 mb-4">
                {scenarios.map(s => (
                  <button key={s.id} onClick={() => setSelectedScenario(s.id)}
                    className={`px-4 py-3 rounded-lg font-medium transition-all ${selectedScenario === s.id ? 'bg-blue-600 text-white' : isDark ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'}`}>
                    {s.name}
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-4">
                <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Days:</span>
                {[1, 3, 7, 14, 30].map(d => (
                  <button key={d} onClick={() => setDaysToProcess(d)}
                    className={`px-3 py-1 rounded text-sm ${daysToProcess === d ? 'bg-purple-100 text-purple-700 border border-purple-300' : isDark ? 'bg-gray-700 text-gray-400' : 'bg-gray-50 text-gray-500 border border-gray-200'}`}>
                    {d}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Uploaded Banner */}
          {uploadedData && (
            <div className="p-4 bg-purple-50 border border-purple-200 rounded-xl mb-6">
              <p className="text-purple-700">✓ Excel loaded: {uploadedData.scenarios_count} scenarios, {uploadedData.total_intervals} intervals</p>
            </div>
          )}

          {/* Actions */}
          <div className={`p-6 rounded-2xl ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'} mb-6`}>
            <div className="flex flex-wrap items-center gap-4">
              <button onClick={calculateBaseline} disabled={isLoadingBaseline || (!uploadedData && !selectedScenario)}
                className={`flex items-center gap-2 px-6 py-3 rounded-xl font-semibold transition-all ${isLoadingBaseline || (!uploadedData && !selectedScenario) ? 'bg-gray-300 text-gray-500' : 'bg-gradient-to-r from-amber-500 to-orange-600 text-white'}`}>
                {isLoadingBaseline ? 'Calculating...' : 'Calculate Baseline'}
              </button>
              <select value={optimizationMethod} onChange={(e) => setOptimizationMethod(e.target.value)}
                className={`px-4 py-3 rounded-xl font-medium ${isDark ? 'bg-gray-700 text-white border border-gray-600' : 'bg-gray-50 border border-gray-200'}`}>
                <option value="ortools_milp">OR-Tools MILP ✨</option>
                <option value="candidate_scoring">ML Hybrid</option>
                <option value="ml_hybrid">Candidate Scoring</option>
              </select>
              {mlStatus.ml_available && (
                <div className={`flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium ${isDark ? 'bg-green-900 text-green-300' : 'bg-green-100 text-green-700'}`}>
                  <Brain size={14} />
                  ML Active
                </div>
              )}
              <button onClick={runOptimization} disabled={!baselineResult || isOptimizing}
                className={`flex items-center gap-2 px-6 py-3 rounded-xl font-semibold transition-all ${!baselineResult || isOptimizing ? 'bg-gray-300 text-gray-500' : 'bg-gradient-to-r from-green-500 to-emerald-600 text-white'}`}>
                {isOptimizing ? 'Optimizing...' : 'Run Optimization'}
              </button>
            </div>
            {error && <p className="mt-3 text-red-500">{error}</p>}
          </div>

          {/* KPI Cards - Show when baseline is ready */}
          {baselineResult && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <KPICard
                title={optimizedResult ? "Cost Savings" : "Baseline Cost"}
                value={`PKR ${optimizedResult ? Math.max(0, savings?.cost_savings || 0).toLocaleString() : baselineResult.total_cost_pkr.toLocaleString()}`}
                subtitle={optimizedResult ? `${(savings?.cost_savings_pct || 0).toFixed(1)}% reduction` : 'Baseline (before optimization)'}
                icon={TrendingDown}
                color="green"
                trend={savings?.cost_savings_pct || 0}
              />
              <KPICard
                title={optimizedResult ? "Energy Saved" : "Baseline Energy"}
                value={`${optimizedResult ? Math.max(0, savings?.energy_savings || 0) : baselineResult.total_energy_kwh} kWh`}
                subtitle={optimizedResult ? `${Math.abs(savings?.energy_savings_pct || 0).toFixed(1)}% less usage` : 'Baseline energy consumption'}
                icon={Zap}
                color="blue"
                trend={savings?.energy_savings_pct || 0}
              />
              <KPICard
                title={optimizedResult ? "CO₂ Reduced" : "Baseline Emissions"}
                value={`${optimizedResult ? Math.max(0, savings?.emissions_savings || 0) : baselineResult.total_emissions_kgco2e} kg`}
                subtitle={optimizedResult ? `${Math.abs(savings?.emissions_savings_pct || 0).toFixed(1)}% reduction` : 'Carbon footprint'}
                icon={Leaf}
                color="emerald"
                trend={savings?.emissions_savings_pct || 0}
              />
              <KPICard
                title={optimizedResult ? "Peak Reduction" : "Baseline Peak"}
                value={`${optimizedResult ? Math.max(0, savings?.peak_reduction || 0) : baselineResult.peak_demand_kw} kW`}
                subtitle={optimizedResult ? "Peak demand lowered" : "Maximum demand"}
                icon={Target}
                color="purple"
                trend={savings?.peak_reduction ? 15 : 0}
              />
            </div>
          )}

          {/* Results Section - Show when optimization is done */}
          {optimizedResult && (
            <div className="space-y-6">
              {/* Comparison Cards - Baseline vs Optimized */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white rounded-xl shadow-sm p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-blue-600" />
                    Baseline vs Optimized
                  </h3>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-600">Total Cost</span>
                        <span className="font-medium">
                          <span className="text-red-500 line-through">{baselineResult.total_cost_pkr.toLocaleString()} PKR</span>
                          {' → '}
                          <span className="text-green-600">{optimizedResult.summary.total_cost_pkr.toLocaleString()} PKR</span>
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div
                          className="bg-green-500 h-3 rounded-full"
                          style={{ width: `${Math.min(100, (optimizedResult.summary.total_cost_pkr / baselineResult.total_cost_pkr) * 100)}%` }}
                        />
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Saves: PKR {(savings?.cost_savings || 0).toLocaleString()} ({(savings?.cost_savings_pct || 0).toFixed(1)}%)</p>
                    </div>
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-600">Total Energy</span>
                        <span className="font-medium">
                          <span className="text-red-500 line-through">{baselineResult.total_energy_kwh.toFixed(1)} kWh</span>
                          {' → '}
                          <span className="text-green-600">{optimizedResult.summary.total_energy_kwh.toFixed(1)} kWh</span>
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div
                          className="bg-blue-500 h-3 rounded-full"
                          style={{ width: `${Math.min(100, (optimizedResult.summary.total_energy_kwh / baselineResult.total_energy_kwh) * 100)}%` }}
                        />
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Saves: {(savings?.energy_savings || 0).toFixed(1)} kWh ({(savings?.energy_savings_pct || 0).toFixed(1)}%)</p>
                    </div>
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-600">Comfort Compliance</span>
                        <span className="font-medium">
                          <span className="text-yellow-500">{baselineResult.comfort_compliance_pct.toFixed(0)}%</span>
                          {' → '}
                          <span className="text-green-600">{optimizedResult.summary.comfort_compliance_pct.toFixed(0)}%</span>
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div
                          className="bg-green-500 h-3 rounded-full"
                          style={{ width: `${optimizedResult.summary.comfort_compliance_pct}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded-xl shadow-sm p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    <Sun className="w-5 h-5 text-yellow-500" />
                    Energy Optimization Impact
                  </h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                      <div>
                        <p className="font-medium text-gray-900">Energy Saved</p>
                        <p className="text-sm text-gray-500">Daily average reduction</p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-green-600">{(savings?.energy_savings_pct || 0).toFixed(1)}%</p>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                      <div>
                        <p className="font-medium text-gray-900">Cost Reduction</p>
                        <p className="text-sm text-gray-500">PKR saved per day</p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-blue-600">
                          {(daysToProcess > 0 ? ((savings?.cost_savings || 0) / daysToProcess) : 0).toFixed(0)}
                        </p>
                        <p className="text-xs text-gray-500">PKR/day</p>
                      </div>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-purple-50 rounded-lg">
                      <div>
                        <p className="font-medium text-gray-900">Carbon Offset</p>
                        <p className="text-sm text-gray-500">CO₂ emissions avoided</p>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold text-purple-600">{(savings?.emissions_savings || 0).toFixed(1)}</p>
                        <p className="text-xs text-gray-500">kg CO₂</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Charts - Left: Bar Chart, Right: Daily Table */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ComparisonChart baselineResult={baselineResult} optimizedResult={optimizedResult} />
                <div className="bg-white rounded-xl shadow-sm p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                    <Calendar className="w-5 h-5 text-indigo-600" />
                    Daily Overview
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-gray-500 border-b">
                          <th className="pb-2">Day</th>
                          <th className="pb-2 text-right">Peak Temp</th>
                          <th className="pb-2 text-right">Comfort</th>
                          <th className="pb-2 text-right">Solar</th>
                          <th className="pb-2 text-right">Battery</th>
                        </tr>
                      </thead>
                      <tbody>
                        {optimizedResult.daily_summaries?.map((d, i) => (
                          <tr key={i} className="border-b border-gray-100">
                            <td className="py-2 font-medium">{d.day_name || `Day ${i + 1}`}</td>
                            <td className="py-2 text-right">{d.peak_temp || '-'}°C</td>
                            <td className="py-2 text-right">
                              <span className={`${(d.comfort_compliance_pct || 0) > 85 ? 'text-green-600' : 'text-orange-600'}`}>
                                {(d.comfort_compliance_pct || 0).toFixed(0)}%
                              </span>
                            </td>
                            <td className="py-2 text-right text-yellow-600">{d.solar_used_kwh?.toFixed(1) || 0} kWh</td>
                            <td className="py-2 text-right">
                              <div className="flex items-center justify-end gap-2">
                                <div className="w-16 bg-gray-200 rounded-full h-2">
                                  <div
                                    className="bg-blue-500 h-2 rounded-full"
                                    style={{ width: `${Math.min(100, Math.max(0, d.battery_soc_pct || 0))}%` }}
                                  />
                                </div>
                                <span>{Math.round(d.battery_soc_pct || 0)}%</span>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              {/* Alerts & Extended Summary */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                <AlertsPanel
                  alerts={alerts}
                  summary={{
                    total: alerts.length,
                    by_severity: alerts.reduce((acc, a) => {
                      acc[a.severity] = (acc[a.severity] || 0) + 1;
                      return acc;
                    }, { critical: 0, warning: 0, info: 0 })
                  }}
                />
                <ExtendedSummary extendedData={extendedSummary} />
              </div>

              {/* Export Buttons */}
              <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Export Results</h3>
                <div className="flex flex-wrap gap-4">
                  <button
                    onClick={exportCSV}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium bg-green-600 text-white hover:bg-green-700 transition-all"
                  >
                    <Download className="w-5 h-5" />
                    Export CSV
                  </button>
                  <button
                    onClick={exportExcel}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium bg-indigo-600 text-white hover:bg-indigo-700 transition-all"
                  >
                    <Download className="w-5 h-5" />
                    Export Excel
                  </button>
                  <div className="text-sm text-gray-500 self-center ml-4">
                    Run ID: {runId}
                  </div>
                </div>
              </div>

              <ScheduleTable intervals={optimizedResult.intervals} />
            </div>
          )}
        </main>
      </div>
    );
  }

  // Live View
  if (view === 'live') {
    return <LiveCalculator onBack={() => setView('menu')} />;
  }

  return null;
}
