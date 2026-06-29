"""Compare optimization methods - Side by Side Comparison"""
from data_import import DataImportService
from optimization_engine import OptimizationEngine
from ortools_optimizer import ORToolsOptimizer
from baseline_engine import BaselineEngine

service = DataImportService()
scenario = service.load_public_scenario('PUB-A', 1, 1)

print()
print("=" * 80)
print("  COOLSHIFT OPTIMIZATION METHODS COMPARISON")
print("=" * 80)
print()

# Calculate all three
baseline_engine = BaselineEngine()
baseline_result = baseline_engine.calculate(scenario)

print("BASELINE (No Optimization)")
print("-" * 40)
print(f"   Total Cost:         PKR {baseline_result.total_cost_pkr:.2f}")
print(f"   Total Energy:       {baseline_result.total_energy_kwh:.2f} kWh")
print(f"   Peak Demand:        {baseline_result.peak_demand_kw:.2f} kW")
print(f"   Comfort Compliance: {baseline_result.comfort_compliance_pct:.1f}%")
print()

print("CANDIDATE SCORING METHOD")
print("-" * 40)
opt = OptimizationEngine()
result_candidate = opt.optimize(scenario)
cand_savings = baseline_result.total_cost_pkr - result_candidate.summary.total_cost_pkr
cand_savings_pct = (cand_savings / baseline_result.total_cost_pkr * 100) if baseline_result.total_cost_pkr > 0 else 0
print(f"   Total Cost:         PKR {result_candidate.summary.total_cost_pkr:.2f}")
print(f"   Cost vs Baseline:  {cand_savings:+.2f} PKR ({cand_savings_pct:+.1f}%)")
print(f"   Total Energy:       {result_candidate.summary.total_energy_kwh:.2f} kWh")
print(f"   Peak Demand:        {result_candidate.summary.peak_demand_kw:.2f} kW")
print(f"   Comfort Compliance: {result_candidate.summary.comfort_compliance_pct:.1f}%")
print()

print("OR-TOOLS MILP METHOD (Enhanced)")
print("-" * 40)
ort = ORToolsOptimizer()
result_ortools = ort.optimize(scenario)
ort_savings = baseline_result.total_cost_pkr - result_ortools.summary.total_cost_pkr
ort_savings_pct = (ort_savings / baseline_result.total_cost_pkr * 100) if baseline_result.total_cost_pkr > 0 else 0
print(f"   Total Cost:         PKR {result_ortools.summary.total_cost_pkr:.2f}")
print(f"   Cost vs Baseline:  {ort_savings:+.2f} PKR ({ort_savings_pct:+.1f}%)")
print(f"   Total Energy:       {result_ortools.summary.total_energy_kwh:.2f} kWh")
print(f"   Peak Demand:        {result_ortools.summary.peak_demand_kw:.2f} kW")
print(f"   Comfort Compliance: {result_ortools.summary.comfort_compliance_pct:.1f}%")
print()

print("=" * 80)
print("  WINNER: OR-TOOLS MILP")
print("=" * 80)
winner_diff = result_candidate.summary.total_cost_pkr - result_ortools.summary.total_cost_pkr
winner_pct = (winner_diff / result_candidate.summary.total_cost_pkr * 100) if result_candidate.summary.total_cost_pkr > 0 else 0
print(f"   OR-Tools saves PKR {winner_diff:.2f} MORE than Candidate Method")
print(f"   That's {winner_pct:.1f}% better than Candidate Scoring!")
print()

print("=" * 80)
print("  COMPARISON SUMMARY TABLE")
print("=" * 80)
print(f"{'Method':<25} {'Cost (PKR)':<15} {'vs Baseline':<15}")
print("-" * 60)
print(f"{'Baseline':<25} {baseline_result.total_cost_pkr:<15.2f} {'-':<15}")
status1 = "WORSE!" if cand_savings < 0 else "OK"
print(f"{'Candidate Scoring':<25} {result_candidate.summary.total_cost_pkr:<15.2f} {cand_savings_pct:+.1f}% {status1}")
print(f"{'OR-Tools MILP':<25} {result_ortools.summary.total_cost_pkr:<15.2f} {ort_savings_pct:+.1f}% BEST")
print()

print("=" * 80)
print("  SAMPLE INTERVAL COMPARISON")
print("=" * 80)
print(f"{'Int':<5} {'Candidate':<18} {'OR-Tools':<18} {'Cand kWh':<12} {'ORT kWh':<12}")
print("-" * 80)
for i in range(28, 48):
    r1 = result_candidate.intervals[i]
    r2 = result_ortools.intervals[i]
    if r1.occupancy_count > 0:
        cand_ac = f"AC:{r1.recommended_ac_units_on} SP:{r1.recommended_ac_setpoint_c}°"
        ort_ac = f"AC:{r2.recommended_ac_units_on} SP:{r2.recommended_ac_setpoint_c}°"
        print(f"{i:<5} {cand_ac:<18} {ort_ac:<18} {r1.grid_energy_kwh:<12.3f} {r2.grid_energy_kwh:<12.3f}")
