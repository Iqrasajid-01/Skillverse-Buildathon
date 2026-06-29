"""
Debug Schedule - Verify all interval calculations
"""

import sys
from datetime import datetime, timedelta
from data_models import *
from optimization_engine import OptimizationEngine

def create_test_scenario() -> ScenarioInput:
    """Create a test scenario with all parameters"""
    
    base_date = datetime(2026, 6, 16)
    intervals = []
    
    # 24 hours x 4 intervals = 96 intervals
    for i in range(96):
        hour = i // 4
        minute = (i % 4) * 15
        
        # Temperature: varies 28-38
        if hour < 6:
            temp = 28
        elif hour < 12:
            temp = 28 + 10 * ((hour - 6) / 6)
        elif hour < 18:
            temp = 38
        else:
            temp = 38 - 10 * ((hour - 18) / 6)
        
        # Occupancy: 4 people 7am-10pm
        occupancy = 4 if 7 <= hour <= 22 else 0
        
        # Tariff: peak 5-9pm
        if 17 <= hour <= 21:
            tariff = 45
            tariff_type = TariffType.PEAK
        elif hour >= 22 or hour < 6:
            tariff = 15
            tariff_type = TariffType.OFF_PEAK
        else:
            tariff = 25
            tariff_type = TariffType.FLAT
        
        # Solar: peaks at noon
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
            non_cooling_load_kw=0.5  # Lights, TV, etc.
        ))
    
    return ScenarioInput(
        scenario_id="DEBUG-001",
        profile=ScenarioProfile(
            scenario_id="DEBUG-001",
            name="Debug Test with Solar & Battery",
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
            solar_capacity_kw=5.0,
            battery_capacity_kwh=13.5,
            initial_soc_kwh=10.0,  # Start at ~74%
            minimum_reserve_kwh=2.7,  # 20%
            max_charge_kw=5.0,
            max_discharge_kw=5.0
        )
    )

def main():
    print("=" * 100)
    print("SCHEDULE CALCULATION DEBUG")
    print("=" * 100)
    
    scenario = create_test_scenario()
    
    # Run optimization
    engine = OptimizationEngine()
    result = engine.optimize(scenario)
    
    # Print header
    print(f"\n{'Time':<8} {'OutT':<5} {'InT':<5} {'Solar':<6} {'AC':<3} {'Setpt':<5} {'Grid':<7} {'SolarUsed':<9} {'BatChg':<7} {'BatDis':<7} {'BatSOC%':<7} {'Cost':<8} {'Comfort':<10} {'Reason'}")
    print("-" * 140)
    
    # Print each interval
    for i, interval in enumerate(result.intervals):
        hour = interval.timestamp_local.hour
        minute = interval.timestamp_local.minute
        time_str = f"{hour:02d}:{minute:02d}"
        
        # Tariff type
        tariff_type = interval.tariff_type
        peak_marker = " [PEAK]" if tariff_type in ['PEAK', 'peak'] else ""
        
        # Comfort status
        comfort = interval.comfort_status.value if hasattr(interval.comfort_status, 'value') else interval.comfort_status
        
        print(f"{time_str:<8} "
              f"{interval.temperature_c:<5.1f} "
              f"{interval.estimated_indoor_temp_c:<5.1f} "
              f"{interval.solar_irradiance_w_m2:<6.0f} "
              f"{interval.recommended_ac_units_on:<3} "
              f"{interval.recommended_ac_setpoint_c if interval.recommended_ac_setpoint_c else '-':<5} "
              f"{interval.grid_energy_kwh:<7.4f} "
              f"{interval.solar_energy_used_kwh:<9.4f} "
              f"{interval.battery_charge_kwh:<7.4f} "
              f"{interval.battery_discharge_kwh:<7.4f} "
              f"{(interval.battery_soc_kwh/13.5*100):<7.1f} "
              f"PKR {interval.interval_cost_pkr:<7.2f} "
              f"{comfort:<10} "
              f"{interval.explanation[:50]}{peak_marker}")
    
    # Summary
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    
    total_grid = sum(i.grid_energy_kwh for i in result.intervals)
    total_solar = sum(i.solar_energy_used_kwh for i in result.intervals)
    total_cost = sum(i.interval_cost_pkr for i in result.intervals)
    peak_intervals = [i for i in result.intervals if 'PEAK' in (i.tariff_type or '').upper()]
    
    print(f"Total Grid Energy: {total_grid:.2f} kWh")
    print(f"Total Solar Used: {total_solar:.2f} kWh")
    print(f"Total Cost: PKR {total_cost:.2f}")
    print(f"Peak Hours Count: {len(peak_intervals)}")
    
    # Show peak hour details
    if peak_intervals:
        print(f"\n--- PEAK HOURS DETAIL ---")
        for interval in peak_intervals[:6]:  # First 6 peak intervals
            hour = interval.timestamp_local.hour
            print(f"Hour {hour:02d}:00 | Grid={interval.grid_energy_kwh:.4f}kWh | Solar={interval.solar_energy_used_kwh:.4f}kWh | "
                  f"BatSOC={interval.battery_soc_kwh:.2f}kWh | Cost=PKR {interval.interval_cost_pkr:.2f} | AC={interval.recommended_ac_units_on}")

if __name__ == "__main__":
    main()
