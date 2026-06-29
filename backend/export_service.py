"""
Export Service - Exports optimization results to CSV/Excel
"""

import pandas as pd
from typing import List, Dict
from datetime import datetime
from pathlib import Path
from data_models import RunResult, IntervalOutput, DailySummary

class ExportService:
    """Service for exporting optimization results"""
    
    def __init__(self, output_dir: str = "D:/Hackathon/Hackathon-Current/outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export_csv(self, result: RunResult) -> str:
        """Export run result to CSV file"""
        
        # Prepare interval data
        interval_data = []
        for interval in result.intervals:
            interval_data.append({
                'scenario_id': result.scenario_id,
                'run_id': result.run_id,
                'timestamp_local': interval.timestamp_local.isoformat(),
                'recommended_ac_units_on': interval.recommended_ac_units_on,
                'recommended_ac_setpoint_c': interval.recommended_ac_setpoint_c or '',
                'recommended_fan_units_on': interval.recommended_fan_units_on,
                'grid_energy_kwh': round(interval.grid_energy_kwh, 4),
                'solar_energy_used_kwh': round(interval.solar_energy_used_kwh, 4),
                'battery_charge_kwh': round(interval.battery_charge_kwh, 4),
                'battery_discharge_kwh': round(interval.battery_discharge_kwh, 4),
                'battery_soc_kwh': round(interval.battery_soc_kwh, 2),
                'cooling_energy_kwh': round(interval.cooling_energy_kwh, 4),
                'estimated_indoor_temp_c': interval.estimated_indoor_temp_c,
                'comfort_status': interval.comfort_status.value,
                'interval_cost_pkr': round(interval.interval_cost_pkr, 2),
                'interval_emissions_kgco2e': round(interval.interval_emissions_kgco2e, 4),
                'reason_code': interval.reason_code.value,
                'explanation': interval.explanation,
                'constraint_violation_count': interval.constraint_violation_count
            })
        
        df = pd.DataFrame(interval_data)
        
        # Save file
        filename = f"coolshift_{result.scenario_id}_{result.run_id[:8]}_intervals.csv"
        filepath = self.output_dir / filename
        df.to_csv(filepath, index=False)
        
        return str(filepath)
    
    def export_excel(self, result: RunResult) -> str:
        """Export run result to Excel file with multiple sheets"""
        
        filename = f"coolshift_{result.scenario_id}_{result.run_id[:8]}_report.xlsx"
        filepath = self.output_dir / filename
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            
            # Sheet 1: Summary
            summary_data = {
                'Metric': [
                    'Scenario ID',
                    'Run ID',
                    'Start Timestamp',
                    'End Timestamp',
                    'Total Intervals',
                    'Total Days',
                    'Total Cooling Energy (kWh)',
                    'Total Grid Energy (kWh)',
                    'Total Cost (PKR)',
                    'Total Emissions (kgCO2e)',
                    'Peak Demand (kW)',
                    'Comfort Compliance (%)',
                    'Solar Utilization (%)',
                    'Battery Utilization (%)',
                    'Cost Savings (PKR)',
                    'Energy Savings (kWh)',
                    'Emission Reduction (kgCO2e)'
                ],
                'Value': [
                    result.scenario_id,
                    result.run_id,
                    result.summary.start_timestamp.isoformat(),
                    result.summary.end_timestamp.isoformat(),
                    result.summary.total_intervals,
                    round(result.summary.total_days, 2),
                    result.summary.total_energy_kwh,
                    round(sum(i.grid_energy_kwh for i in result.intervals), 2),
                    result.summary.total_cost_pkr,
                    result.summary.total_emissions_kgco2e,
                    result.summary.peak_demand_kw,
                    result.summary.comfort_compliance_pct,
                    result.summary.solar_utilization_pct,
                    result.summary.battery_utilization_pct,
                    result.summary.total_savings_pkr,
                    result.summary.total_savings_kwh,
                    result.summary.emission_reduction_kgco2e
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            # Sheet 2: Daily Summaries
            daily_data = []
            for daily in result.daily_summaries:
                daily_data.append({
                    'Date': daily.date.isoformat(),
                    'Total Energy (kWh)': daily.total_energy_kwh,
                    'Total Cost (PKR)': daily.total_cost_pkr,
                    'Total Emissions (kgCO2e)': daily.total_emissions_kgco2e,
                    'Peak Demand (kW)': daily.peak_demand_kw,
                    'Comfort Compliance (%)': daily.comfort_compliance_pct,
                    'Unsafe Hours': daily.unsafe_hours,
                    'Solar Utilization (%)': daily.solar_utilization_pct,
                    'Battery Cycles': daily.battery_cycles
                })
            pd.DataFrame(daily_data).to_excel(writer, sheet_name='Daily Summary', index=False)
            
            # Sheet 3: Interval Details
            interval_data = []
            for interval in result.intervals:
                interval_data.append({
                    'Timestamp': interval.timestamp_local.isoformat(),
                    'AC Units On': interval.recommended_ac_units_on,
                    'AC Setpoint (°C)': interval.recommended_ac_setpoint_c or '',
                    'Fan Units On': interval.recommended_fan_units_on,
                    'Grid Energy (kWh)': round(interval.grid_energy_kwh, 4),
                    'Solar Used (kWh)': round(interval.solar_energy_used_kwh, 4),
                    'Battery Charge (kWh)': round(interval.battery_charge_kwh, 4),
                    'Battery Discharge (kWh)': round(interval.battery_discharge_kwh, 4),
                    'Battery SOC (kWh)': round(interval.battery_soc_kwh, 2),
                    'Cooling Energy (kWh)': round(interval.cooling_energy_kwh, 4),
                    'Indoor Temp (°C)': interval.estimated_indoor_temp_c,
                    'Comfort Status': interval.comfort_status.value,
                    'Cost (PKR)': round(interval.interval_cost_pkr, 2),
                    'Emissions (kgCO2e)': round(interval.interval_emissions_kgco2e, 4),
                    'Reason Code': interval.reason_code.value,
                    'Explanation': interval.explanation
                })
            pd.DataFrame(interval_data).to_excel(writer, sheet_name='Interval Details', index=False)
            
            # Sheet 4: Comparison (if baseline available)
            if result.baseline_summary:
                comparison_data = {
                    'Metric': [
                        'Total Energy (kWh)',
                        'Total Cost (PKR)',
                        'Total Emissions (kgCO2e)',
                        'Peak Demand (kW)',
                        'Comfort Compliance (%)'
                    ],
                    'Baseline': [
                        result.baseline_summary.get('total_energy_kwh', 0),
                        result.baseline_summary.get('total_cost_pkr', 0),
                        result.baseline_summary.get('total_emissions_kgco2e', 0),
                        result.baseline_summary.get('peak_demand_kw', 0),
                        result.baseline_summary.get('comfort_compliance_pct', 0)
                    ],
                    'Optimized': [
                        result.summary.total_energy_kwh,
                        result.summary.total_cost_pkr,
                        result.summary.total_emissions_kgco2e,
                        result.summary.peak_demand_kw,
                        result.summary.comfort_compliance_pct
                    ],
                    'Savings': [
                        result.summary.total_savings_kwh,
                        result.summary.total_savings_pkr,
                        result.summary.emission_reduction_kgco2e,
                        result.baseline_summary.get('peak_demand_kw', 0) - result.summary.peak_demand_kw,
                        result.summary.comfort_compliance_pct - result.baseline_summary.get('comfort_compliance_pct', 0)
                    ]
                }
                pd.DataFrame(comparison_data).to_excel(writer, sheet_name='Comparison', index=False)
        
        return str(filepath)
    
    def export_summary_csv(self, results: List[RunResult]) -> str:
        """Export summary of multiple runs to single CSV"""
        
        summary_data = []
        for result in results:
            summary_data.append({
                'scenario_id': result.scenario_id,
                'run_id': result.run_id,
                'total_intervals': result.summary.total_intervals,
                'total_days': round(result.summary.total_days, 2),
                'total_energy_kwh': result.summary.total_energy_kwh,
                'total_cost_pkr': result.summary.total_cost_pkr,
                'total_emissions_kgco2e': result.summary.total_emissions_kgco2e,
                'peak_demand_kw': result.summary.peak_demand_kw,
                'comfort_compliance_pct': result.summary.comfort_compliance_pct,
                'solar_utilization_pct': result.summary.solar_utilization_pct,
                'battery_utilization_pct': result.summary.battery_utilization_pct,
                'cost_savings_pkr': result.summary.total_savings_pkr,
                'energy_savings_kwh': result.summary.total_savings_kwh,
                'emission_reduction_kgco2e': result.summary.emission_reduction_kgco2e
            })
        
        df = pd.DataFrame(summary_data)
        
        filename = f"coolshift_all_scenarios_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = self.output_dir / filename
        df.to_csv(filepath, index=False)
        
        return str(filepath)
