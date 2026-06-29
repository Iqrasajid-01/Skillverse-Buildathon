import pandas as pd
from datetime import datetime, timedelta

# Create 7 days of 15-min interval data
start = datetime(2024, 7, 1)
timestamps = [start + timedelta(minutes=15*i) for i in range(96*7)]

# interval_inputs with USER's column names
interval_data = []
for ts in timestamps:
    hour = ts.hour
    interval_data.append({
        'timestamp': ts,
        'scenario_id': 'CUSTOM',
        'interval_minutes': 15,
        'outdoor_temp': round(35 + 5*abs(hour - 14)/14, 1),  # Vary temp by hour
        'indoor_temp': 30,
        'relative_humidity_pct': 60,
        'heat_index_c': 38,
        'solar_irradiance_w_m2': 800 if 6 <= hour <= 18 else 0,
        'solar_kw': 0,
        'grid_available': True,
        'grid_carbon_kgco2_per_kwh': 0.5,
        'tariff_pkr_per_kwh': 45 if 17 <= hour <= 21 else 25 if 7 <= hour <= 16 else 15,
        'tariff_type': 'peak' if 17 <= hour <= 21 else 'flat' if 7 <= hour <= 16 else 'off_peak',
        'occupancy_count': 3 if 7 <= hour <= 22 else 0,
        'non_cooling_load_kw': 0.5,
        'ac_capacity_kw': 1.5,
        'setpoint_temp_c': 24,
        'source_missing_flag': False
    })
df_intervals = pd.DataFrame(interval_data)

# scenario_profile
profile = pd.DataFrame([{
    'scenario_id': 'CUSTOM',
    'name': 'Custom Scenario',
    'timezone': 'Asia/Karachi',
    'building_type': 'household',
    'area_m2': 80,
    'room_count': 3,
    'max_occupancy': 4,
    'insulation_level': 'medium',
    'sun_exposure': 'medium',
    'comfort_min_c': 22,
    'comfort_max_c': 26,
    'vulnerable_occupants': False,
    'budget_pkr_per_day': 500,
    'maximum_grid_demand_kw': 10
}])

# appliances
appliances = pd.DataFrame([{
    'scenario_id': 'CUSTOM',
    'appliance_id': 'AC-01',
    'zone_id': 'main',
    'appliance_type': 'ac',
    'quantity': 1,
    'rated_power_kw': 1.5,
    'cooling_capacity_kw': 5.0,
    'efficiency_label': 'A',
    'min_runtime_minutes': 15,
    'min_setpoint_c': 18,
    'max_setpoint_c': 30
}])

# energy_assets
assets = pd.DataFrame([{
    'scenario_id': 'CUSTOM',
    'solar_capacity_kw': 0,
    'solar_conversion_efficiency': 0.18,
    'battery_capacity_kwh': 0,
    'initial_soc_kwh': 0,
    'minimum_reserve_kwh': 0,
    'max_charge_kw': 0,
    'max_discharge_kw': 0,
    'charge_efficiency': 0.95,
    'discharge_efficiency': 0.95
}])

# baseline_schedule with user's columns
baseline_data = []
for ts in timestamps:
    hour = ts.hour
    if 12 <= hour <= 23 and (7 <= hour <= 22):
        baseline_data.append({
            'scenario_id': 'CUSTOM',
            'timestamp': ts,
            'baseline_ac_units_on': 1,
            'baseline_ac_setpoint_c': 24,
            'baseline_fan_units_on': 2,
            'baseline_other_cooling_kw': 0
        })
    else:
        baseline_data.append({
            'scenario_id': 'CUSTOM',
            'timestamp': ts,
            'baseline_ac_units_on': 0,
            'baseline_ac_setpoint_c': 24,
            'baseline_fan_units_on': 0,
            'baseline_other_cooling_kw': 0
        })
baseline = pd.DataFrame(baseline_data)

path = '../data/CoolShift_Template.xlsx'
with pd.ExcelWriter(path, engine='openpyxl') as writer:
    profile.to_excel(writer, sheet_name='scenario_profile', index=False)
    appliances.to_excel(writer, sheet_name='appliances', index=False)
    assets.to_excel(writer, sheet_name='energy_assets', index=False)
    df_intervals.to_excel(writer, sheet_name='interval_inputs', index=False)
    baseline.to_excel(writer, sheet_name='baseline_schedule', index=False)

print(f'Template created: {path}')
