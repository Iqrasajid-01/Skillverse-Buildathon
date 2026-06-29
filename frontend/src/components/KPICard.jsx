import { TrendingUp, TrendingDown } from 'lucide-react'

const colorClasses = {
  green: 'bg-green-50 text-green-700 border-green-200',
  blue: 'bg-blue-50 text-blue-700 border-blue-200',
  purple: 'bg-purple-50 text-purple-700 border-purple-200',
  emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  yellow: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  red: 'bg-red-50 text-red-700 border-red-200'
}

const iconColors = {
  green: 'text-green-500',
  blue: 'text-blue-500',
  purple: 'text-purple-500',
  emerald: 'text-emerald-500',
  yellow: 'text-yellow-500',
  red: 'text-red-500'
}

export default function KPICard({ title, value, subtitle, icon: Icon, color = 'blue', trend }) {
  const isPositive = trend > 0
  const TrendIcon = isPositive ? TrendingUp : TrendingDown
  
  return (
    <div className={`bg-white rounded-xl shadow-sm border p-5 card-hover ${colorClasses[color]}`}>
      <div className="flex items-start justify-between mb-3">
        <div className={`p-2 rounded-lg bg-white/50`}>
          <Icon className={`w-6 h-6 ${iconColors[color]}`} />
        </div>
        {trend !== undefined && (
          <div className={`flex items-center gap-1 text-xs font-medium ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
            <TrendIcon className="w-3 h-3" />
            {Math.abs(trend).toFixed(1)}%
          </div>
        )}
      </div>
      <h3 className="text-2xl font-bold text-gray-900 mb-1">{value}</h3>
      <p className="text-sm text-gray-600">{title}</p>
      {subtitle && (
        <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
      )}
    </div>
  )
}
