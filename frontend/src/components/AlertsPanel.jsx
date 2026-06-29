import { AlertTriangle, AlertCircle, Info, XCircle, TrendingUp, TrendingDown, Minus } from 'lucide-react'

const alertIcons = {
  EXTREME_HEAT: AlertTriangle,
  UNSAFE_COMFORT: XCircle,
  BUDGET_RISK: AlertCircle,
  PEAK_DEMAND: TrendingUp,
  LOW_BATTERY: AlertTriangle,
  GRID_OUTAGE: XCircle,
  INSUFFICIENT_CAPACITY: AlertTriangle,
  MISSING_DATA: Info,
  CONSTRAINT_VIOLATION: AlertCircle
}

const alertColors = {
  critical: {
    bg: 'bg-red-50 border-red-200',
    icon: 'text-red-500',
    badge: 'bg-red-100 text-red-700'
  },
  warning: {
    bg: 'bg-yellow-50 border-yellow-200',
    icon: 'text-yellow-500',
    badge: 'bg-yellow-100 text-yellow-700'
  },
  info: {
    bg: 'bg-blue-50 border-blue-200',
    icon: 'text-blue-500',
    badge: 'bg-blue-100 text-blue-700'
  }
}

export default function AlertsPanel({ alerts, summary }) {
  if (!alerts || alerts.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-green-500" />
          System Alerts
        </h3>
        <div className="text-center py-8 text-gray-500">
          <AlertCircle className="w-12 h-12 mx-auto mb-3 text-green-400" />
          <p>All systems normal - No alerts</p>
        </div>
      </div>
    )
  }

  const getAlertIcon = (type) => {
    const Icon = alertIcons[type] || Info
    return Icon
  }

  const getAlertColors = (severity) => {
    return alertColors[severity] || alertColors.info
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <AlertTriangle className="w-5 h-5 text-orange-500" />
        System Alerts
        <span className="ml-auto text-sm font-normal text-gray-500">
          {summary?.total || alerts.length} alerts
        </span>
      </h3>

      {/* Summary badges */}
      {summary && (
        <div className="flex gap-3 mb-4">
          {summary.by_severity?.critical > 0 && (
            <span className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm font-medium">
              {summary.by_severity.critical} Critical
            </span>
          )}
          {summary.by_severity?.warning > 0 && (
            <span className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded-full text-sm font-medium">
              {summary.by_severity.warning} Warning
            </span>
          )}
        </div>
      )}

      {/* Alert list */}
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {alerts.slice(0, 10).map((alert, idx) => {
          const colors = getAlertColors(alert.severity)
          const Icon = getAlertIcon(alert.alert_type)

          return (
            <div
              key={idx}
              className={`p-4 rounded-lg border ${colors.bg} transition-all hover:shadow-md`}
            >
              <div className="flex items-start gap-3">
                <Icon className={`w-5 h-5 mt-0.5 ${colors.icon}`} />
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors.badge}`}>
                      {alert.alert_type.replace(/_/g, ' ')}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                      alert.severity === 'critical' ? 'bg-red-200 text-red-800' :
                      alert.severity === 'warning' ? 'bg-yellow-200 text-yellow-800' :
                      'bg-blue-200 text-blue-800'
                    }`}>
                      {alert.severity}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700">{alert.message}</p>
                  {alert.details && Object.keys(alert.details).length > 0 && (
                    <div className="mt-2 text-xs text-gray-500">
                      {Object.entries(alert.details).slice(0, 3).map(([key, val]) => (
                        <span key={key} className="mr-3">
                          {key}: <strong>{typeof val === 'number' ? val.toFixed(1) : val}</strong>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {alerts.length > 10 && (
        <p className="text-center text-sm text-gray-500 mt-4">
          + {alerts.length - 10} more alerts
        </p>
      )}
    </div>
  )
}
