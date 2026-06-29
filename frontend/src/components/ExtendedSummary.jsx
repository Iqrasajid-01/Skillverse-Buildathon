import { TrendingUp, TrendingDown, Minus, AlertTriangle, Zap, Calendar, CheckCircle, XCircle } from 'lucide-react'

const TrendIcon = ({ trend }) => {
  if (trend === 'increasing') return <TrendingUp className="w-4 h-4 text-red-500" />
  if (trend === 'decreasing') return <TrendingDown className="w-4 h-4 text-green-500" />
  return <Minus className="w-4 h-4 text-gray-400" />
}

export default function ExtendedSummary({ extendedData }) {
  if (!extendedData) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Calendar className="w-5 h-5 text-blue-600" />
          7-Day Analysis
        </h3>
        <div className="text-center py-8 text-gray-500">
          <p>Run optimization to see extended analysis</p>
        </div>
      </div>
    )
  }

  const { trends, worst_heat_period, highest_demand_period, constraint_violations, audit_info } = extendedData

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <Calendar className="w-5 h-5 text-blue-600" />
        7-Day Extended Analysis
      </h3>

      {/* Trends Section */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 mb-3">Trends</h4>
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <TrendIcon trend={trends?.cost_trend} />
              <span className="text-sm text-gray-600">Cost Trend</span>
            </div>
            <p className="text-lg font-bold text-gray-900 capitalize">
              {trends?.cost_trend || 'N/A'}
            </p>
            <p className="text-xs text-gray-500">
              {trends?.cost_change_pct?.toFixed(1) || 0}% change
            </p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <TrendIcon trend={trends?.energy_trend} />
              <span className="text-sm text-gray-600">Energy Trend</span>
            </div>
            <p className="text-lg font-bold text-gray-900 capitalize">
              {trends?.energy_trend || 'N/A'}
            </p>
            <p className="text-xs text-gray-500">
              {trends?.energy_change_pct?.toFixed(1) || 0}% change
            </p>
          </div>
        </div>
      </div>

      {/* Worst Heat Period */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-orange-500" />
          Worst Heat Period
        </h4>
        <div className="p-4 bg-orange-50 border border-orange-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Date</p>
              <p className="text-lg font-bold text-gray-900">{worst_heat_period?.date || 'N/A'}</p>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-600">Peak Demand</p>
              <p className="text-lg font-bold text-orange-600">{worst_heat_period?.peak_demand_kw?.toFixed(2) || 0} kW</p>
            </div>
          </div>
          <div className="mt-2 pt-2 border-t border-orange-200">
            <p className="text-sm text-gray-600">
              Unsafe Hours: <span className="font-bold text-red-600">{worst_heat_period?.unsafe_hours || 0} hrs</span>
            </p>
          </div>
        </div>
      </div>

      {/* Highest Demand Period */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
          <Zap className="w-4 h-4 text-purple-500" />
          Highest Demand Period
        </h4>
        <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Date</p>
              <p className="text-lg font-bold text-gray-900">{highest_demand_period?.date || 'N/A'}</p>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-600">Peak Demand</p>
              <p className="text-lg font-bold text-purple-600">{highest_demand_period?.peak_demand_kw?.toFixed(2) || 0} kW</p>
            </div>
          </div>
          <div className="mt-2 pt-2 border-t border-purple-200">
            <p className="text-sm text-gray-600">
              Total Energy: <span className="font-bold text-purple-600">{highest_demand_period?.total_energy_kwh?.toFixed(1) || 0} kWh</span>
            </p>
          </div>
        </div>
      </div>

      {/* Constraint Violations */}
      <div className="mb-6">
        <h4 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
          {constraint_violations?.total === 0 ? (
            <CheckCircle className="w-4 h-4 text-green-500" />
          ) : (
            <XCircle className="w-4 h-4 text-red-500" />
          )}
          Constraint Validation
        </h4>
        <div className={`p-4 rounded-lg border ${
          constraint_violations?.total === 0
            ? 'bg-green-50 border-green-200'
            : 'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {constraint_violations?.total === 0 ? (
                <CheckCircle className="w-6 h-6 text-green-500" />
              ) : (
                <XCircle className="w-6 h-6 text-red-500" />
              )}
              <div>
                <p className="font-bold text-gray-900 capitalize">
                  {constraint_violations?.status?.replace(/_/g, ' ') || 'N/A'}
                </p>
                <p className="text-sm text-gray-600">
                  {constraint_violations?.total || 0} violations found
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Audit Information */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-3">Audit Information</h4>
        <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Algorithm Version</p>
              <p className="font-medium text-gray-900">{audit_info?.algorithm_version || '1.0.0'}</p>
            </div>
            <div>
              <p className="text-gray-500">Run ID</p>
              <p className="font-medium text-gray-900 font-mono text-xs">
                {audit_info?.run_id?.substring(0, 8) || 'N/A'}
              </p>
            </div>
            <div>
              <p className="text-gray-500">Scenario</p>
              <p className="font-medium text-gray-900">{audit_info?.scenario_id || 'N/A'}</p>
            </div>
            <div>
              <p className="text-gray-500">Timestamp</p>
              <p className="font-medium text-gray-900 text-xs">
                {audit_info?.calculation_timestamp?.split('T')[0] || 'N/A'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
