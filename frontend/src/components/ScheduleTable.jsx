import { useState, useMemo } from 'react'
import { ChevronDown, ChevronUp, Search } from 'lucide-react'

export default function ScheduleTable({ data, intervals }) {
  const [sortField, setSortField] = useState('hour')
  const [sortDirection, setSortDirection] = useState('asc')
  const [filter, setFilter] = useState('')

  const tableData = data || intervals;

  // Transform backend data to frontend expected format
  const transformedData = useMemo(() => {
    if (!tableData || !Array.isArray(tableData)) return []
    // Default battery capacity 13.5 kWh for percentage calculation
    const BATTERY_CAPACITY = 13.5
    return tableData.map(item => {
      // Get battery SOC in kWh (backend returns actual value)
      const batteryKwh = item.battery_soc_kwh ?? item.battery_soc ?? 0
      // Calculate percentage, clamp to 0-100, show 0% if no battery data
      const batteryPercent = batteryKwh > 0 ? (batteryKwh / BATTERY_CAPACITY) * 100 : 0
      return {
        timestamp: item.timestamp_local || item.timestamp || '',
        timestamp_date: item.timestamp_local ? new Date(item.timestamp_local) : new Date(),
        outdoor_temp: item.temperature_c || item.outdoor_temp || 35,
        indoor_temp: item.estimated_indoor_temp_c || item.indoor_temp || 25,
        solar_irradiance: item.solar_irradiance_w_m2 || item.solar_irradiance || 0,
        ac_units: item.recommended_ac_units_on ?? item.ac_units ?? 0,
        setpoint: item.recommended_ac_setpoint_c || item.setpoint || 26,
        grid_energy: item.grid_energy_kwh || item.grid_energy || 0,
        battery_soc: Math.min(100, Math.max(0, Math.round(batteryPercent))),
        battery_soc_kwh: batteryKwh,
        cost: item.interval_cost_pkr || item.cost || 0,
        comfort_status: item.comfort_status?.value || item.comfort_status || 'within_range',
        reason: item.explanation || item.reason || '',
        reason_code: item.reason_code || '',
        is_peak: item.tariff_type === 'PEAK' || item.tariff_type === 'peak' || item.is_peak || false
      }
    })
  }, [data])

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('asc')
    }
  }

  const filteredData = transformedData.filter(item =>
    (item.reason && item.reason.toLowerCase().includes(filter.toLowerCase())) ||
    (item.timestamp && item.timestamp.includes(filter))
  )

  const sortedData = [...filteredData].sort((a, b) => {
    let aVal = a[sortField]
    let bVal = b[sortField]

    if (aVal === undefined || aVal === null) return 1
    if (bVal === undefined || bVal === null) return -1

    if (typeof aVal === 'string') {
      aVal = aVal.toLowerCase()
      bVal = String(bVal).toLowerCase()
    }

    if (sortDirection === 'asc') {
      return aVal > bVal ? 1 : -1
    }
    return aVal < bVal ? 1 : -1
  })

  const SortIcon = ({ field }) => {
    if (sortField !== field) return null
    return sortDirection === 'asc'
      ? <ChevronUp className="w-4 h-4" />
      : <ChevronDown className="w-4 h-4" />
  }

  const comfortBadge = (status) => {
    if (!status) return null
    const statusStr = typeof status === 'string' ? status : status.value || 'within_range'
    const classes = {
      'within_range': 'bg-green-100 text-green-700',
      'warning': 'bg-yellow-100 text-yellow-700',
      'unsafe': 'bg-red-100 text-red-700',
      'infeasible': 'bg-gray-100 text-gray-700'
    }
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${classes[statusStr] || classes['within_range']}`}>
        {statusStr.replace(/_/g, ' ')}
      </span>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-sm overflow-hidden">
      <div className="p-4 border-b border-gray-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h3 className="text-lg font-semibold text-gray-900">24-Hour Cooling Schedule</h3>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Filter by reason..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th 
                className="px-4 py-3 text-left font-semibold text-gray-700 cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('hour')}
              >
                <div className="flex items-center gap-1">
                  Time <SortIcon field="hour" />
                </div>
              </th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">
                <div className="flex items-center gap-1">
                  Out/In Temp <SortIcon field="outdoor_temp" />
                </div>
              </th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">
                Solar (W/m²)
              </th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">
                <div className="flex items-center gap-1">
                  AC Units <SortIcon field="ac_units" />
                </div>
              </th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">
                Setpoint
              </th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">
                <div className="flex items-center gap-1">
                  Grid (kWh) <SortIcon field="grid_energy" />
                </div>
              </th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">
                Battery
              </th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">
                <div className="flex items-center gap-1">
                  Cost <SortIcon field="cost" />
                </div>
              </th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">
                Comfort
              </th>
              <th className="px-4 py-3 text-left font-semibold text-gray-700">
                Reason
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedData.map((interval, idx) => (
              <tr 
                key={idx} 
                className={`border-t border-gray-100 hover:bg-gray-50 ${
                  interval.is_peak ? 'bg-orange-50' : ''
                }`}
              >
                <td className="px-4 py-3 font-medium">
                  <div className="flex items-center gap-2">
                    {interval.is_peak && (
                      <span className="w-2 h-2 bg-orange-500 rounded-full"></span>
                    )}
                    {interval.timestamp}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className="text-gray-600">{interval.outdoor_temp}°</span>
                  <span className="text-gray-400 mx-1">→</span>
                  <span className="font-medium">{interval.indoor_temp}°</span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    {interval.solar_irradiance > 0 && (
                      <span className="text-yellow-500">☀</span>
                    )}
                    {interval.solar_irradiance}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1">
                    {interval.ac_units > 0 ? (
                      <>
                        <span className="w-6 h-6 bg-blue-500 text-white rounded flex items-center justify-center text-xs font-bold">
                          {interval.ac_units}
                        </span>
                        <span className="text-gray-500 text-xs">units</span>
                      </>
                    ) : (
                      <span className="text-gray-400">Off</span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  {interval.setpoint}°C
                </td>
                <td className="px-4 py-3 font-medium">
                  {interval.grid_energy.toFixed(2)}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-blue-500 h-2 rounded-full"
                        style={{ width: `${interval.battery_soc}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500">{interval.battery_soc}%</span>
                  </div>
                </td>
                <td className="px-4 py-3 font-medium text-gray-900">
                  PKR {interval.cost.toFixed(2)}
                </td>
                <td className="px-4 py-3">
                  {comfortBadge(interval.comfort_status)}
                </td>
                <td className="px-4 py-3 text-gray-600 text-xs max-w-xs truncate">
                  {interval.reason}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      <div className="p-4 border-t border-gray-200 bg-gray-50 text-sm text-gray-500 flex items-center justify-between">
        <span>Showing {sortedData.length} of {tableData?.length || 0} intervals</span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 bg-orange-500 rounded-full"></span>
          Peak tariff hours
        </span>
      </div>
    </div>
  )
}
