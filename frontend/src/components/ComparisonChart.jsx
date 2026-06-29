import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts'

export default function ComparisonChart({ data, baselineResult, optimizedResult }) {
  let chartData = data;
  
  if (!chartData || !Array.isArray(chartData) || chartData.length === 0) {
    if (baselineResult?.daily_summaries && optimizedResult?.daily_summaries) {
      chartData = baselineResult.daily_summaries.map((bl, idx) => ({
        day_name: bl.day_name || `Day ${idx + 1}`,
        baseline_cost: bl.total_cost_pkr || 0,
        optimized_cost: optimizedResult.daily_summaries[idx]?.total_cost_pkr || 0,
        baseline_energy: bl.total_energy_kwh || 0,
        optimized_energy: optimizedResult.daily_summaries[idx]?.total_energy_kwh || 0
      }));
    }
  }
  
  if (!chartData || !Array.isArray(chartData) || chartData.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Daily Cost & Energy Comparison</h3>
        <p className="text-gray-500 text-center py-8">Run optimization to see comparison</p>
      </div>
    )
  }
  
  const formattedData = chartData.map(d => ({
    name: d.day_name,
    'Baseline Cost': Math.round(d.baseline_cost),
    'Optimized Cost': Math.round(d.optimized_cost),
    'Baseline Energy': Math.round(d.baseline_energy * 10) / 10,
    'Optimized Energy': Math.round(d.optimized_energy * 10) / 10
  }))

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Daily Cost & Energy Comparison</h3>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={formattedData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="name" tick={{ fontSize: 12 }} />
          <YAxis yAxisId="left" orientation="left" tick={{ fontSize: 12 }} />
          <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} />
          <Tooltip 
            contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
            formatter={(value, name) => [
              name.includes('Cost') ? `PKR ${value}` : `${value} kWh`,
              name
            ]}
          />
          <Legend />
          <Bar yAxisId="left" dataKey="Baseline Cost" fill="#ef4444" radius={[4, 4, 0, 0]} />
          <Bar yAxisId="left" dataKey="Optimized Cost" fill="#22c55e" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
