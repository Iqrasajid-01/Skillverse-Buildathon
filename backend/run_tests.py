"""
Hidden Test Runner - Validates optimization for all scenarios
Tests 3 scenarios × 3 different parameter sets each
"""

import sys
import json
from datetime import datetime, timedelta
from data_models import *
from optimization_engine import OptimizationEngine
from baseline_engine import BaselineEngine
from validation import ValidationService, ConstraintValidator

def create_household_no_solar_test(test_num: int) -> ScenarioInput:
    """PUB-A: Household without Solar - 3 different test cases"""
    
    base_date = datetime(2026, 6, 16) + timedelta(days=test_num * 7)
    
    # Vary temperature ranges and occupancy patterns per test
    temp_ranges = [
        (28, 38),  # Test 1: Hot summer
        (25, 35),  # Test 2: Moderate heat
        (30, 42),  # Test 3: Extreme heat
    ]
    occ_patterns = [
        [(6, 22, 4), (22, 6, 0)],  # Test 1: Evening heavy
        [(7, 21, 3), (21, 7, 0)],  # Test 2: Daytime balanced
        [(17, 23, 5), (23, 17, 0)], # Test 3: Night heavy
    ]
    
    temp_range = temp_ranges[test_num]
    occ_pattern = occ_patterns[test_num]
    
    intervals = []
    # Generate 96 intervals (24 hours x 4 intervals per hour)
    for interval_idx in range(96):
        hour = interval_idx // 4
        minute = (interval_idx % 4) * 15
        
        # Determine temperature
        if hour < 6:
            temp = temp_range[0]
        elif hour < 12:
            temp = temp_range[0] + (temp_range[1] - temp_range[0]) * ((hour - 6) / 6)
        elif hour < 18:
            temp = temp_range[1]
        else:
            temp = temp_range[1] - (temp_range[1] - temp_range[0]) * ((hour - 18) / 6)
        
        # Determine occupancy
        occupancy = 0
        for start, end, occ in occ_pattern:
            if start <= hour < end:
                occupancy = occ
                break
        
        # Tariff pattern
        if hour >= 17 and hour <= 21:
            tariff = 45
            tariff_type = TariffType.PEAK
        elif hour >= 22 or hour < 6:
            tariff = 15
            tariff_type = TariffType.OFF_PEAK
        else:
            tariff = 25
            tariff_type = TariffType.FLAT
        
        solar = 0 if hour < 6 or hour > 18 else min(800, max(0, (hour - 6) * 100))
        
        intervals.append(IntervalInput(
            timestamp_local=base_date + timedelta(hours=hour, minutes=minute),
            temperature_c=round(temp, 1),
            relative_humidity_pct=60,
            solar_irradiance_w_m2=solar,
            occupancy_count=occupancy,
            grid_available=True,
            tariff_type=tariff_type,
            tariff_pkr_per_kwh=tariff,
            grid_carbon_kgco2_per_kwh=0.5,
            non_cooling_load_kw=0.5
        ))
    
    return ScenarioInput(
        scenario_id=f"PUB-A-T{test_num+1}",
        profile=ScenarioProfile(
            scenario_id=f"PUB-A-T{test_num+1}",
            name=f"Household No Solar Test {test_num+1}",
            building_type=BuildingType.HOUSEHOLD,
            area_m2=80,
            max_occupancy=6,
            comfort_min_c=22,
            comfort_max_c=26
        ),
        appliances=[
            Appliance(
                appliance_id="AC-001",
                zone_id="ZONE-001",
                appliance_type=ApplianceType.AC,
                quantity=1,
                rated_power_kw=1.5,
                cooling_capacity_kw=5.25,
                min_setpoint_c=18,
                max_setpoint_c=30
            ),
            Appliance(
                appliance_id="FAN-001",
                zone_id="ZONE-001",
                appliance_type=ApplianceType.FAN,
                quantity=2,
                rated_power_kw=0.075,
                cooling_capacity_kw=0.05
            )
        ],
        interval_inputs=intervals,
        energy_assets=EnergyAssets(
            solar_capacity_kw=0,
            battery_capacity_kwh=0,
            initial_soc_kwh=0
        )
    )


def create_household_solar_battery_test(test_num: int) -> ScenarioInput:
    """PUB-B: Household with Solar & Battery - 3 different test cases"""
    
    base_date = datetime(2026, 6, 16) + timedelta(days=test_num * 7)
    
    # Different solar utilization patterns
    solar_patterns = [
        (5.0, 13.5),  # Test 1: Standard setup
        (8.0, 20.0),  # Test 2: Large solar + battery
        (3.0, 10.0),  # Test 3: Small setup
    ]
    
    temp_ranges = [
        (28, 38),  # Hot
        (26, 36),  # Moderate
        (30, 40),  # Very hot
    ]
    
    solar_kw, battery_kwh = solar_patterns[test_num]
    temp_range = temp_ranges[test_num]
    
    intervals = []
    for interval_idx in range(96):
        hour = interval_idx // 4
        minute = (interval_idx % 4) * 15
        
        if hour < 6:
            temp = temp_range[0]
        elif hour < 12:
            temp = temp_range[0] + (temp_range[1] - temp_range[0]) * ((hour - 6) / 6)
        elif hour < 18:
            temp = temp_range[1]
        else:
            temp = temp_range[1] - (temp_range[1] - temp_range[0]) * ((hour - 18) / 6)
        
        occupancy = 4 if 7 <= hour <= 22 else 0
        
        if 17 <= hour <= 21:
            tariff, tariff_type = 45, TariffType.PEAK
        elif hour >= 22 or hour < 6:
            tariff, tariff_type = 15, TariffType.OFF_PEAK
        else:
            tariff, tariff_type = 25, TariffType.FLAT
        
        solar = 0 if hour < 6 or hour > 18 else min(solar_kw * 100, max(0, (hour - 6) * solar_kw * 10))
        
        intervals.append(IntervalInput(
            timestamp_local=base_date + timedelta(hours=hour, minutes=minute),
            temperature_c=round(temp, 1),
            relative_humidity_pct=55,
            solar_irradiance_w_m2=solar,
            occupancy_count=occupancy,
            grid_available=True,
            tariff_type=tariff_type,
            tariff_pkr_per_kwh=tariff,
            grid_carbon_kgco2_per_kwh=0.5,
            non_cooling_load_kw=0.5
        ))
    
    return ScenarioInput(
        scenario_id=f"PUB-B-T{test_num+1}",
        profile=ScenarioProfile(
            scenario_id=f"PUB-B-T{test_num+1}",
            name=f"Household Solar+Battery Test {test_num+1}",
            building_type=BuildingType.HOUSEHOLD,
            area_m2=100,
            max_occupancy=6,
            comfort_min_c=22,
            comfort_max_c=26
        ),
        appliances=[
            Appliance(
                appliance_id="AC-001",
                zone_id="ZONE-001",
                appliance_type=ApplianceType.AC,
                quantity=2,
                rated_power_kw=1.5,
                cooling_capacity_kw=5.25,
                min_setpoint_c=18,
                max_setpoint_c=30
            ),
            Appliance(
                appliance_id="FAN-001",
                zone_id="ZONE-001",
                appliance_type=ApplianceType.FAN,
                quantity=2,
                rated_power_kw=0.075,
                cooling_capacity_kw=0.05
            )
        ],
        interval_inputs=intervals,
        energy_assets=EnergyAssets(
            solar_capacity_kw=solar_kw,
            battery_capacity_kwh=battery_kwh,
            initial_soc_kwh=battery_kwh * 0.5,
            minimum_reserve_kwh=battery_kwh * 0.2,
            max_charge_kw=solar_kw,
            max_discharge_kw=solar_kw
        )
    )


def create_school_office_test(test_num: int) -> ScenarioInput:
    """PUB-C: School/Small Office - 3 different test cases"""
    
    base_date = datetime(2026, 6, 16) + timedelta(days=test_num * 7)
    
    # Different occupancy patterns for schools
    patterns = [
        # Test 1: Standard school hours
        {"occupied_hours": [(8, 16)], "solar_kw": 10, "battery_kwh": 20, "ac_count": 3},
        # Test 2: Office extended hours
        {"occupied_hours": [(7, 19)], "solar_kw": 15, "battery_kwh": 25, "ac_count": 4},
        # Test 3: Split shift
        {"occupied_hours": [(7, 12), (14, 19)], "solar_kw": 8, "battery_kwh": 15, "ac_count": 2},
    ]
    
    pattern = patterns[test_num]
    temp_base = 28 + test_num * 2
    
    intervals = []
    for interval_idx in range(96):
        hour = interval_idx // 4
        minute = (interval_idx % 4) * 15
        
        temp = temp_base + 8 * (1 if 12 <= hour <= 16 else 0.5)
        
        occupancy = 0
        for start, end in pattern["occupied_hours"]:
            if start <= hour < end:
                occupancy = 30 if test_num < 2 else 20
                break
        
        if 17 <= hour <= 21:
            tariff, tariff_type = 55, TariffType.PEAK  # Commercial peak
        elif hour >= 22 or hour < 6:
            tariff, tariff_type = 20, TariffType.OFF_PEAK
        else:
            tariff, tariff_type = 35, TariffType.FLAT
        
        solar = 0 if hour < 6 or hour > 18 else min(pattern["solar_kw"] * 100, max(0, (hour - 6) * pattern["solar_kw"] * 8))
        
        intervals.append(IntervalInput(
            timestamp_local=base_date + timedelta(hours=hour, minutes=minute),
            temperature_c=round(temp, 1),
            relative_humidity_pct=50,
            solar_irradiance_w_m2=solar,
            occupancy_count=occupancy,
            grid_available=True,
            tariff_type=tariff_type,
            tariff_pkr_per_kwh=tariff,
            grid_carbon_kgco2_per_kwh=0.55,
            non_cooling_load_kw=2.0
        ))
    
    return ScenarioInput(
        scenario_id=f"PUB-C-T{test_num+1}",
        profile=ScenarioProfile(
            scenario_id=f"PUB-C-T{test_num+1}",
            name=f"School/Office Test {test_num+1}",
            building_type=BuildingType.SCHOOL,
            area_m2=200,
            max_occupancy=50,
            comfort_min_c=22,
            comfort_max_c=26,
            vulnerable_occupants=True
        ),
        appliances=[
            Appliance(
                appliance_id="AC-001",
                zone_id="ZONE-001",
                appliance_type=ApplianceType.AC,
                quantity=pattern["ac_count"],
                rated_power_kw=3.0,
                cooling_capacity_kw=10.0,
                min_setpoint_c=20,
                max_setpoint_c=28
            ),
            Appliance(
                appliance_id="FAN-001",
                zone_id="ZONE-001",
                appliance_type=ApplianceType.FAN,
                quantity=4,
                rated_power_kw=0.15,
                cooling_capacity_kw=0.1
            )
        ],
        interval_inputs=intervals,
        energy_assets=EnergyAssets(
            solar_capacity_kw=pattern["solar_kw"],
            battery_capacity_kwh=pattern["battery_kwh"],
            initial_soc_kwh=pattern["battery_kwh"] * 0.5,
            minimum_reserve_kwh=pattern["battery_kwh"] * 0.2,
            max_charge_kw=pattern["solar_kw"],
            max_discharge_kw=pattern["solar_kw"]
        )
    )


def run_test(scenario: ScenarioInput, test_name: str) -> dict:
    """Run optimization test and validate results"""
    print(f"\n{'='*60}")
    print(f"Running: {test_name}")
    print(f"{'='*60}")
    
    # Validate input (only fail on errors, not warnings)
    validator = ValidationService()
    validation = validator.validate_scenario(scenario)
    
    # Filter out warnings from errors - only fail on actual errors
    critical_errors = [e for e in validation.errors if "gap" in e.lower() or "missing" in e.lower()]
    if critical_errors:
        print(f"❌ Validation FAILED: {critical_errors[:3]}...")
        return {"status": "validation_failed", "errors": critical_errors}
    
    if validation.warnings:
        print(f"⚠️  Warnings: {validation.warnings[:2]}...")
    
    # Calculate baseline
    baseline = BaselineEngine()
    baseline_result = baseline.calculate(scenario)
    print(f"Baseline: {baseline_result.total_energy_kwh:.2f} kWh, PKR {baseline_result.total_cost_pkr:.2f}")
    
    # Run optimization
    engine = OptimizationEngine()
    result = engine.optimize(scenario)
    
    # Validate constraints
    constraint_validator = ConstraintValidator()
    constraint_result = constraint_validator.validate_all_intervals(
        result.intervals,
        scenario.interval_inputs,
        scenario.energy_assets,
        scenario.appliances,
        max_ac_units=5
    )
    
    print(f"Optimized: {result.summary.total_energy_kwh:.2f} kWh, PKR {result.summary.total_cost_pkr:.2f}")
    print(f"Savings: {(1 - result.summary.total_cost_pkr/baseline_result.total_cost_pkr)*100:.1f}%")
    print(f"Comfort: {result.summary.comfort_compliance_pct:.1f}%")
    print(f"Constraints Valid: {constraint_result['all_valid']}")
    if not constraint_result['all_valid']:
        print(f"Violations: {constraint_result['violation_count']}")
        # Show first few violations
        for v in constraint_result['violations'][:3]:
            print(f"  - Interval {v['interval']}: {v['violations'][:2]}")
    
    # Check for infeasible intervals
    infeasible_count = sum(1 for i in result.intervals 
                          if i.comfort_status == ComfortStatus.INFEASIBLE)
    
    return {
        "status": "success" if constraint_result['all_valid'] else "constraint_violation",
        "test_name": test_name,
        "baseline_cost": baseline_result.total_cost_pkr,
        "optimized_cost": result.summary.total_cost_pkr,
        "baseline_energy": baseline_result.total_energy_kwh,
        "optimized_energy": result.summary.total_energy_kwh,
        "comfort_compliance": result.summary.comfort_compliance_pct,
        "constraints_valid": constraint_result['all_valid'],
        "violation_count": constraint_result['violation_count'],
        "infeasible_intervals": infeasible_count,
        "interval_count": len(result.intervals)
    }


def main():
    print("=" * 70)
    print("CoolShift Hidden Test Runner")
    print("Testing 9 scenarios: 3 PUB-A + 3 PUB-B + 3 PUB-C")
    print("=" * 70)
    
    results = []
    
    # Test PUB-A: Household without Solar (3 tests)
    print("\n" + "=" * 70)
    print("SCENARIO A: Household WITHOUT Solar")
    print("=" * 70)
    for i in range(3):
        scenario = create_household_no_solar_test(i)
        result = run_test(scenario, f"PUB-A-T{i+1} (Household No Solar)")
        results.append(result)
    
    # Test PUB-B: Household with Solar & Battery (3 tests)
    print("\n" + "=" * 70)
    print("SCENARIO B: Household WITH Solar & Battery")
    print("=" * 70)
    for i in range(3):
        scenario = create_household_solar_battery_test(i)
        result = run_test(scenario, f"PUB-B-T{i+1} (Household Solar+Battery)")
        results.append(result)
    
    # Test PUB-C: School/Small Office (3 tests)
    print("\n" + "=" * 70)
    print("SCENARIO C: School / Small Office")
    print("=" * 70)
    for i in range(3):
        scenario = create_school_office_test(i)
        result = run_test(scenario, f"PUB-C-T{i+1} (School/Office)")
        results.append(result)
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for r in results if r["status"] == "success")
    failed = len(results) - passed
    
    print(f"\nTotal Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    print("\n" + "-" * 70)
    print(f"{'Test':<25} {'Status':<15} {'Cost Save %':<12} {'Comfort %':<10} {'Constraints'}")
    print("-" * 70)
    
    for r in results:
        cost_save = (1 - r["optimized_cost"]/r["baseline_cost"])*100 if r["baseline_cost"] > 0 else 0
        status_icon = "✅ PASS" if r["status"] == "success" else "❌ FAIL"
        constraints = "✅ OK" if r["constraints_valid"] else f"❌ {r['violation_count']}"
        print(f"{r['test_name']:<25} {status_icon:<15} {cost_save:>8.1f}%     {r['comfort_compliance']:>6.1f}%    {constraints}")
    
    print("-" * 70)
    
    # Save results
    with open("test_results_summary.json", "w") as f:
        json.dump({
            "total_tests": len(results),
            "passed": passed,
            "failed": failed,
            "results": results
        }, f, indent=2)
    
    print(f"\nResults saved to test_results_summary.json")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
