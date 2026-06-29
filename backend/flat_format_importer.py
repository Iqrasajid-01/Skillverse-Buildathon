"""
Flat Format Importer - Handles simple Excel format for scenarios
Columns: timestamp, scenario_id, interval_minutes, outdoor_temp, indoor_temp, 
         relative_humidity_pct, heat_index_c, solar_irradiance_w_m2, solar_kw,
         grid_available, grid_carbon_kgco2_per_kwh, tariff_pkr_per_kwh, tariff_type,
         occupancy_count, non_cooling_load_kw, ac_capacity_kw, setpoint_temp_c, source_missing_flag
"""

import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime, timedelta
from typing import Dict, List
from data_models import *

class FlatFormatImporter:
    """Import scenarios from flat Excel format"""

    REQUIRED_COLUMNS = [
        'timestamp', 'scenario_id', 'interval_minutes', 'outdoor_temp',
        'relative_humidity_pct', 'heat_index_c', 'solar_irradiance_w_m2',
        'grid_available', 'grid_carbon_kgco2_per_kwh', 'tariff_pkr_per_kwh',
        'tariff_type', 'occupancy_count', 'non_cooling_load_kw'
    ]

    OPTIONAL_COLUMNS = [
        'indoor_temp', 'solar_kw', 'ac_capacity_kw', 'setpoint_temp_c', 'source_missing_flag'
    ]

    def import_excel(self, content: bytes) -> Dict:
        """Import Excel file with flat format"""
        try:
            xls = pd.ExcelFile(BytesIO(content))
            df = pd.read_excel(xls, sheet_name=0)  # Read first sheet
            
            # Validate columns
            missing = [col for col in self.REQUIRED_COLUMNS if col not in df.columns]
            if missing:
                return {
                    "status": "error",
                    "message": f"Missing required columns: {missing}",
                    "valid": False
                }
            
            # Get unique scenarios
            scenarios = df['scenario_id'].unique().tolist()
            
            # Parse data
            result = {
                "status": "success",
                "valid": True,
                "scenarios_count": len(scenarios),
                "scenarios": scenarios,
                "total_intervals": len(df),
                "date_range": f"{df['timestamp'].min()} to {df['timestamp'].max()}",
                "columns_found": list(df.columns)
            }
            
            return result
        except Exception as e:
            return {"status": "error", "message": str(e), "valid": False}

    def parse_to_scenarios(self, content: bytes) -> List[ScenarioInput]:
        """Parse Excel to list of ScenarioInput objects"""
        xls = pd.ExcelFile(BytesIO(content))
        df = pd.read_excel(xls, sheet_name=0)
        
        # Group by scenario
        scenarios = []
        for scenario_id in df['scenario_id'].unique():
            scenario_df = df[df['scenario_id'] == scenario_id].copy()
            scenario_df['timestamp'] = pd.to_datetime(scenario_df['timestamp'])
            scenario_df = scenario_df.sort_values('timestamp')
            
            scenario = self._parse_scenario(scenario_id, scenario_df)
            scenarios.append(scenario)
        
        return scenarios

    def _parse_scenario(self, scenario_id: str, df: pd.DataFrame) -> ScenarioInput:
        """Parse dataframe rows to ScenarioInput"""
        
        # Create profile from first row or defaults
        first = df.iloc[0]
        
        profile = ScenarioProfile(
            scenario_id=str(scenario_id),
            name=f"Scenario {scenario_id}",
            timezone="Asia/Karachi",
            building_type=BuildingType.HOUSEHOLD,
            area_m2=80.0,
            room_count=3,
            max_occupancy=5,
            insulation_level="medium",
            sun_exposure="high",
            comfort_min_c=22.0,
            comfort_max_c=26.0,
            vulnerable_occupants=False,
            budget_pkr_per_day=500.0,
            maximum_grid_demand_kw=10.0
        )
        
        # Create appliances
        appliances = [
            Appliance(
                appliance_id="AC-01",
                zone_id="main",
                appliance_type=ApplianceType.AC,
                quantity=1,
                rated_power_kw=1.5,
                cooling_capacity_kw=5.0,
                efficiency_label="A",
                min_runtime_minutes=15,
                min_setpoint_c=18.0,
                max_setpoint_c=30.0
            ),
            Appliance(
                appliance_id="FAN-01",
                zone_id="main",
                appliance_type=ApplianceType.FAN,
                quantity=2,
                rated_power_kw=0.05,
                cooling_capacity_kw=0.5,
                efficiency_label="A",
                min_runtime_minutes=0,
                min_setpoint_c=18.0,
                max_setpoint_c=32.0
            )
        ]
        
        # Parse intervals
        interval_inputs = []
        for _, row in df.iterrows():
            try:
                # Handle tariff type
                tariff_type_str = str(row.get('tariff_type', 'flat')).lower()
                if 'peak' in tariff_type_str:
                    tariff_type = TariffType.PEAK
                elif 'off' in tariff_type_str:
                    tariff_type = TariffType.OFF_PEAK
                else:
                    tariff_type = TariffType.FLAT
                
                # Handle grid_available
                grid_val = row.get('grid_available', True)
                if isinstance(grid_val, str):
                    grid_available = grid_val.lower() in ['true', '1', 'yes', 'available']
                else:
                    grid_available = bool(grid_val)
                
                interval = IntervalInput(
                    timestamp_local=pd.to_datetime(row['timestamp']),
                    temperature_c=float(row['outdoor_temp']) if pd.notna(row.get('outdoor_temp')) else 30.0,
                    relative_humidity_pct=float(row['relative_humidity_pct']) if pd.notna(row.get('relative_humidity_pct')) else 50.0,
                    heat_index_c=float(row['heat_index_c']) if pd.notna(row.get('heat_index_c')) else None,
                    solar_irradiance_w_m2=float(row['solar_irradiance_w_m2']) if pd.notna(row.get('solar_irradiance_w_m2')) else 0.0,
                    occupancy_count=int(row['occupancy_count']) if pd.notna(row.get('occupancy_count')) else 0,
                    grid_available=grid_available,
                    tariff_type=tariff_type,
                    tariff_pkr_per_kwh=float(row['tariff_pkr_per_kwh']) if pd.notna(row.get('tariff_pkr_per_kwh')) else 25.0,
                    grid_carbon_kgco2_per_kwh=float(row['grid_carbon_kgco2_per_kwh']) if pd.notna(row.get('grid_carbon_kgco2_per_kwh')) else 0.5,
                    non_cooling_load_kw=float(row['non_cooling_load_kw']) if pd.notna(row.get('non_cooling_load_kw')) else 0.5
                )
                interval_inputs.append(interval)
            except Exception as e:
                print(f"Error parsing row: {e}")
                continue
        
        # Energy assets (default)
        energy_assets = EnergyAssets(
            solar_capacity_kw=0.0,
            solar_conversion_efficiency=0.18,
            battery_capacity_kwh=0.0,
            initial_soc_kwh=0.0,
            minimum_reserve_kwh=0.0,
            max_charge_kw=0.0,
            max_discharge_kw=5.0,
            charge_efficiency=0.95,
            discharge_efficiency=0.95
        )
        
        return ScenarioInput(
            scenario_id=str(scenario_id),
            profile=profile,
            appliances=appliances,
            interval_inputs=interval_inputs,
            energy_assets=energy_assets
        )


def create_template_excel(filepath: str):
    """Create template Excel with exact columns"""
    import pandas as pd
    
    # Sample data for 1 day (96 intervals)
    timestamps = pd.date_range('2024-07-01 00:00', periods=96, freq='15min')
    
    # Generate sample data
    data = {
        'timestamp': timestamps,
        'scenario_id': ['PUB-A'] * 96,
        'interval_minutes': [15] * 96,
        'outdoor_temp': [32 + 8 * np.sin((t.hour - 6) * np.pi / 12) for t in timestamps],
        'indoor_temp': [25.0] * 96,
        'relative_humidity_pct': [60 - 20 * np.sin((t.hour - 6) * np.pi / 12) for t in timestamps],
        'heat_index_c': [30 + 5 * np.sin((t.hour - 6) * np.pi / 12) for t in timestamps],
        'solar_irradiance_w_m2': [max(0, 800 * np.sin((t.hour - 6) * np.pi / 12)) if 6 <= t.hour <= 18 else 0 for t in timestamps],
        'solar_kw': [0.0] * 96,
        'grid_available': [True] * 96,
        'grid_carbon_kgco2_per_kwh': [0.5] * 96,
        'tariff_pkr_per_kwh': [15 if t.hour >= 22 or t.hour < 6 else (45 if 17 <= t.hour <= 21 else 25) for t in timestamps],
        'tariff_type': ['off_peak' if t.hour >= 22 or t.hour < 6 else ('peak' if 17 <= t.hour <= 21 else 'flat') for t in timestamps],
        'occupancy_count': [4 if 7 <= t.hour <= 22 else 0 for t in timestamps],
        'non_cooling_load_kw': [0.5 + np.random.uniform(-0.1, 0.2) for _ in timestamps],
        'ac_capacity_kw': [5.0] * 96,
        'setpoint_temp_c': [24.0] * 96,
        'source_missing_flag': [False] * 96
    }
    
    df = pd.DataFrame(data)
    df.to_excel(filepath, index=False, sheet_name='interval_inputs')
    print(f"Template created: {filepath}")

if __name__ == "__main__":
    create_template_excel('D:/Hackathon/Hackathon-Current/CoolShift_Template_Flat.xlsx')