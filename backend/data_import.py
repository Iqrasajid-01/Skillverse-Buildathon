"""
Data Import Service - Reads Excel/JSON and converts to ScenarioInput
Handles validation, missing data, and public dataset loading
"""

import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from data_models import *

class DataImportService:
    """Service for importing and parsing scenario data"""
    
    # Public dataset mappings
    SCENARIO_CONFIGS = {
        "PUB-A": {
            "name": "Household without Solar",
            "building_type": BuildingType.HOUSEHOLD,
            "area_m2": 80,
            "has_solar": False,
            "has_battery": False
        },
        "PUB-B": {
            "name": "Household with Solar & Battery",
            "building_type": BuildingType.HOUSEHOLD,
            "area_m2": 100,
            "has_solar": True,
            "has_battery": True,
            "solar_capacity_kw": 5.0,
            "battery_capacity_kwh": 13.5
        },
        "PUB-C": {
            "name": "School/Small Office",
            "building_type": BuildingType.SCHOOL,
            "area_m2": 200,
            "has_solar": True,
            "has_battery": True,
            "solar_capacity_kw": 10.0,
            "battery_capacity_kwh": 20.0
        }
    }
    
    def __init__(self):
        self.public_data_path = self._find_public_dataset()
    
    def _find_public_dataset(self) -> Optional[str]:
        """Find the public Excel dataset"""
        possible_paths = [
            "D:/Hackathon/Hackathon-Current/04_CoolShift_Public_Dataset_and_Templates.xlsx",
            "04_CoolShift_Public_Dataset_and_Templates.xlsx",
            "../04_CoolShift_Public_Dataset_and_Templates.xlsx",
        ]
        for path in possible_paths:
            import os
            if os.path.exists(path):
                return path
        return None
    
    def import_workbook(self, content: bytes) -> Dict:
        """Import Excel workbook and return summary with parsed data"""
        try:
            xls = pd.ExcelFile(BytesIO(content))
            sheets = pd.read_excel(xls, sheet_name=None)

            # Default expected sheets
            expected_sheets = ['interval_inputs', 'scenario_profile', 'appliances', 'energy_assets']
            available_sheets = list(sheets.keys())

            # Count intervals
            intervals_count = 0
            scenario_input = None
            
            if 'interval_inputs' in sheets:
                intervals_count = len(sheets['interval_inputs'])
                
                # Parse scenario input if all required sheets exist
                if all(s in sheets for s in ['scenario_profile', 'appliances', 'energy_assets', 'interval_inputs']):
                    scenario_input = self._parse_excel_sheets(sheets)

            # Parse date range if available
            date_range = None
            if 'interval_inputs' in sheets and 'timestamp_local' in sheets['interval_inputs'].columns:
                df = sheets['interval_inputs']
                dates = pd.to_datetime(df['timestamp_local'])
                date_range = f"{dates.min().strftime('%Y-%m-%d')} to {dates.max().strftime('%Y-%m-%d')}"

            # Detect scenarios
            scenarios_count = 1
            if 'scenario_profile' in sheets:
                scenarios_count = len(sheets['scenario_profile'])
            elif 'interval_inputs' in sheets and 'scenario_id' in sheets['interval_inputs'].columns:
                scenarios_count = sheets['interval_inputs']['scenario_id'].nunique()

            result = {
                "status": "success",
                "valid": True,
                "sheets_found": available_sheets,
                "sheets_expected": expected_sheets,
                "scenarios_count": scenarios_count,
                "total_intervals": intervals_count,
                "date_range": date_range,
                "has_interval_inputs": 'interval_inputs' in sheets,
                "has_profile": 'scenario_profile' in sheets,
                "has_appliances": 'appliances' in sheets,
                "has_energy_assets": 'energy_assets' in sheets,
                "data_preview": self._get_preview(sheets)
            }
            
            # Include scenario_input if parsed successfully
            if scenario_input:
                result["scenario_input"] = scenario_input.model_dump(mode='json')
            
            return result
        except Exception as e:
            raise ValueError(f"Failed to import workbook: {str(e)}")

    def _parse_excel_sheets(self, sheets: Dict) -> ScenarioInput:
        """Parse Excel sheets into ScenarioInput"""
        # Parse scenario profile
        profile_df = sheets['scenario_profile'].iloc[0]
        profile = ScenarioProfile(
            scenario_id=str(profile_df.get('scenario_id', 'CUSTOM')),
            name=str(profile_df.get('name', 'Custom Scenario')),
            timezone=str(profile_df.get('timezone', 'Asia/Karachi')),
            building_type=BuildingType(profile_df.get('building_type', 'household')),
            area_m2=float(profile_df.get('area_m2', 80)),
            room_count=int(profile_df.get('room_count', 1)),
            max_occupancy=int(profile_df.get('max_occupancy', 4)),
            insulation_level=str(profile_df.get('insulation_level', 'medium')),
            sun_exposure=str(profile_df.get('sun_exposure', 'medium')),
            comfort_min_c=float(profile_df.get('comfort_min_c', 22)),
            comfort_max_c=float(profile_df.get('comfort_max_c', 26)),
            vulnerable_occupants=bool(profile_df.get('vulnerable_occupants', False)),
            budget_pkr_per_day=float(profile_df.get('budget_pkr_per_day', 500)),
            maximum_grid_demand_kw=float(profile_df.get('maximum_grid_demand_kw', 10))
        )
        
        # Parse appliances
        appliances = []
        for _, row in sheets['appliances'].iterrows():
            appliances.append(Appliance(
                appliance_id=str(row.get('appliance_id', 'AC-01')),
                zone_id=str(row.get('zone_id', 'main')),
                appliance_type=ApplianceType(row.get('appliance_type', 'ac')),
                quantity=int(row.get('quantity', 1)),
                rated_power_kw=float(row.get('rated_power_kw', 1.5)),
                cooling_capacity_kw=float(row.get('cooling_capacity_kw', 5.0)),
                efficiency_label=str(row.get('efficiency_label', 'A')),
                min_runtime_minutes=int(row.get('min_runtime_minutes', 15)),
                min_setpoint_c=float(row.get('min_setpoint_c', 18)),
                max_setpoint_c=float(row.get('max_setpoint_c', 30))
            ))
        
        # Parse interval inputs - support both naming conventions
        interval_inputs = []
        for _, row in sheets['interval_inputs'].iterrows():
            # Handle column name variations
            timestamp = row.get('timestamp_local') or row.get('timestamp')
            temp = row.get('temperature_c') or row.get('outdoor_temp')
            humidity = row.get('relative_humidity_pct')
            heat_idx = row.get('heat_index_c')
            solar_irr = row.get('solar_irradiance_w_m2')
            occ = row.get('occupancy_count')
            grid = row.get('grid_available')
            tariff_type_val = row.get('tariff_type')
            tariff = row.get('tariff_pkr_per_kwh')
            carbon = row.get('grid_carbon_kgco2_per_kwh')
            non_cool = row.get('non_cooling_load_kw')
            
            interval_inputs.append(IntervalInput(
                timestamp_local=pd.to_datetime(timestamp),
                temperature_c=float(temp) if pd.notna(temp) else 30,
                relative_humidity_pct=float(humidity) if pd.notna(humidity) else 50,
                heat_index_c=float(heat_idx) if pd.notna(heat_idx) else None,
                solar_irradiance_w_m2=float(solar_irr) if pd.notna(solar_irr) else 0,
                occupancy_count=int(occ) if pd.notna(occ) else 0,
                grid_available=bool(grid) if pd.notna(grid) else True,
                tariff_type=TariffType(tariff_type_val) if pd.notna(tariff_type_val) else TariffType.FLAT,
                tariff_pkr_per_kwh=float(tariff) if pd.notna(tariff) else 25,
                grid_carbon_kgco2_per_kwh=float(carbon) if pd.notna(carbon) else 0.5,
                non_cooling_load_kw=float(non_cool) if pd.notna(non_cool) else 0
            ))
        
        # Parse energy assets
        assets_df = sheets['energy_assets'].iloc[0]
        energy_assets = EnergyAssets(
            solar_capacity_kw=float(assets_df.get('solar_capacity_kw', 0)),
            solar_conversion_efficiency=float(assets_df.get('solar_conversion_efficiency', 0.18)),
            battery_capacity_kwh=float(assets_df.get('battery_capacity_kwh', 0)),
            initial_soc_kwh=float(assets_df.get('initial_soc_kwh', 0)),
            minimum_reserve_kwh=float(assets_df.get('minimum_reserve_kwh', 0)),
            max_charge_kw=float(assets_df.get('max_charge_kw', 0)),
            max_discharge_kw=float(assets_df.get('max_discharge_kw', 0)),
            charge_efficiency=float(assets_df.get('charge_efficiency', 0.95)),
            discharge_efficiency=float(assets_df.get('discharge_efficiency', 0.95))
        )
        
        return ScenarioInput(
            scenario_id=str(profile_df.get('scenario_id', 'CUSTOM')),
            profile=profile,
            appliances=appliances,
            interval_inputs=interval_inputs,
            energy_assets=energy_assets
        )
    
    def _get_preview(self, sheets: Dict) -> Dict:
        """Get preview of first few rows from each sheet"""
        preview = {}
        for name, df in sheets.items():
            if len(df) > 0:
                preview[name] = {
                    "columns": list(df.columns),
                    "row_count": len(df),
                    "sample": df.head(3).to_dict(orient='records')
                }
        return preview
    
    def import_json(self, data: ScenarioInput) -> ScenarioInput:
        """Import scenario from JSON/Pydantic model"""
        # Validation is automatic via Pydantic
        return data
    
    def load_public_scenario(self, scenario_id: str, start_day: int = 1, days: int = 7) -> ScenarioInput:
        """Load a public scenario from the dataset or generate synthetic data"""
        
        config = self.SCENARIO_CONFIGS.get(scenario_id)
        if not config:
            raise ValueError(f"Unknown scenario: {scenario_id}")
        
        # Generate synthetic data if no real dataset
        return self._generate_scenario(
            scenario_id=scenario_id,
            config=config,
            start_day=start_day,
            days=days
        )
    
    def _generate_scenario(
        self, 
        scenario_id: str, 
        config: Dict,
        start_day: int,
        days: int
    ) -> ScenarioInput:
        """Generate synthetic scenario data matching public dataset structure"""
        
        # Generate timestamps (15-min intervals)
        start_date = datetime(2024, 7, 1) + timedelta(days=start_day - 1)
        num_intervals = days * 96
        timestamps = [start_date + timedelta(minutes=15 * i) for i in range(num_intervals)]
        
        # Generate weather data (realistic summer pattern)
        interval_inputs = []
        for ts in timestamps:
            hour = ts.hour
            day_of_year = ts.timetuple().tm_yday
            
            # Temperature pattern: cooler at night, peak at 14:00
            base_temp = 32 + 8 * np.sin((hour - 6) * np.pi / 12)
            # Add some noise
            temp = base_temp + np.random.normal(0, 2)
            temp = np.clip(temp, 25, 48)
            
            # Humidity: higher at night
            base_humidity = 60 - 20 * np.sin((hour - 6) * np.pi / 12)
            humidity = np.clip(base_humidity + np.random.normal(0, 10), 20, 95)
            
            # Solar irradiance (peaks at noon)
            solar = max(0, 800 * np.sin((hour - 6) * np.pi / 12)) if 6 <= hour <= 18 else 0
            solar = solar + np.random.normal(0, 50)
            solar = max(0, solar)
            
            # Occupancy based on scenario type
            if config["building_type"] == BuildingType.HOUSEHOLD:
                occupied = 7 <= hour <= 22
                occupancy = np.random.randint(2, 5) if occupied else 0
            elif config["building_type"] == BuildingType.SCHOOL:
                occupied = 8 <= hour <= 17
                occupancy = np.random.randint(10, 30) if occupied else 0
            else:
                occupied = 9 <= hour <= 18
                occupancy = np.random.randint(5, 15) if occupied else 0
            
            # Grid availability (1 = available)
            grid_available = True
            
            # Tariff pattern
            if 17 <= hour <= 21:
                tariff_type = TariffType.PEAK
                tariff = 45.0  # Peak rate PKR/kWh
            elif 22 <= hour or hour <= 6:
                tariff_type = TariffType.OFF_PEAK
                tariff = 15.0  # Off-peak rate
            else:
                tariff_type = TariffType.FLAT
                tariff = 25.0  # Normal rate
            
            # Carbon factor (grid emissions)
            carbon = 0.5  # kgCO2/kWh
            
            # Non-cooling load
            non_cooling = 0.5 + np.random.uniform(0, 0.5)
            
            # Heat index calculation
            heat_index = self._calculate_heat_index(temp, humidity)
            
            interval_inputs.append(IntervalInput(
                timestamp_local=ts,
                temperature_c=round(temp, 1),
                relative_humidity_pct=round(humidity, 1),
                heat_index_c=round(heat_index, 1),
                solar_irradiance_w_m2=round(solar, 0),
                occupancy_count=occupancy,
                grid_available=grid_available,
                tariff_type=tariff_type,
                tariff_pkr_per_kwh=tariff,
                grid_carbon_kgco2_per_kwh=carbon,
                non_cooling_load_kw=round(non_cooling, 2)
            ))
        
        # Create profile
        profile = ScenarioProfile(
            scenario_id=scenario_id,
            name=config["name"],
            timezone="Asia/Karachi",
            building_type=config["building_type"],
            area_m2=config["area_m2"],
            room_count=3 if config["building_type"] == BuildingType.HOUSEHOLD else 5,
            max_occupancy=5 if config["building_type"] == BuildingType.HOUSEHOLD else 30,
            insulation_level="medium",
            sun_exposure="high",
            comfort_min_c=22,
            comfort_max_c=26,
            vulnerable_occupants=False,
            budget_pkr_per_day=500,
            maximum_grid_demand_kw=10
        )
        
        # Create appliances
        if config["building_type"] == BuildingType.HOUSEHOLD:
            appliances = [
                Appliance(
                    appliance_id="AC-LIVING",
                    zone_id="living",
                    appliance_type=ApplianceType.AC,
                    quantity=1,
                    rated_power_kw=1.5,
                    cooling_capacity_kw=5.0,
                    efficiency_label="A",
                    min_runtime_minutes=15,
                    min_setpoint_c=18,
                    max_setpoint_c=30
                ),
                Appliance(
                    appliance_id="FAN-01",
                    zone_id="living",
                    appliance_type=ApplianceType.FAN,
                    quantity=2,
                    rated_power_kw=0.05,
                    cooling_capacity_kw=0.5,
                    efficiency_label="A",
                    min_runtime_minutes=0,
                    min_setpoint_c=18,
                    max_setpoint_c=32
                )
            ]
        else:
            # School/office with multiple zones
            appliances = [
                Appliance(
                    appliance_id="AC-CLASSROOM",
                    zone_id="zone-1",
                    appliance_type=ApplianceType.AC,
                    quantity=2,
                    rated_power_kw=2.0,
                    cooling_capacity_kw=7.0,
                    efficiency_label="A",
                    min_runtime_minutes=30,
                    min_setpoint_c=20,
                    max_setpoint_c=28
                ),
                Appliance(
                    appliance_id="FAN-COMMON",
                    zone_id="common",
                    appliance_type=ApplianceType.FAN,
                    quantity=4,
                    rated_power_kw=0.075,
                    cooling_capacity_kw=0.5,
                    efficiency_label="A",
                    min_runtime_minutes=0,
                    min_setpoint_c=18,
                    max_setpoint_c=32
                )
            ]
        
        # Create energy assets
        energy_assets = EnergyAssets(
            solar_capacity_kw=config.get("solar_capacity_kw", 0),
            solar_conversion_efficiency=0.18,
            battery_capacity_kwh=config.get("battery_capacity_kwh", 0),
            initial_soc_kwh=config.get("battery_capacity_kwh", 0) * 0.5 if config.get("has_battery", False) else 0,
            minimum_reserve_kwh=config.get("battery_capacity_kwh", 0) * 0.2 if config.get("has_battery", False) else 0,
            max_charge_kw=min(5, config.get("solar_capacity_kw", 0)),
            max_discharge_kw=5,
            charge_efficiency=0.95,
            discharge_efficiency=0.95
        )
        
        # Generate baseline schedule
        baseline_schedule = self._generate_baseline_schedule(
            interval_inputs, 
            appliances,
            config["building_type"]
        )
        
        return ScenarioInput(
            scenario_id=scenario_id,
            profile=profile,
            appliances=appliances,
            interval_inputs=interval_inputs,
            energy_assets=energy_assets,
            baseline_schedule=baseline_schedule
        )
    
    def _calculate_heat_index(self, temp_c: float, humidity: float) -> float:
        """Calculate heat index using Rothfusz regression"""
        if temp_c < 27:
            return temp_c
        
        T = temp_c * 9/5 + 32  # Convert to Fahrenheit
        RH = humidity
        
        # Simple heat index formula
        HI = -42.379 + 2.04901523*T + 10.14333127*RH - 0.22475541*T*RH
        HI -= 0.00683783*T*T + 0.05481717*RH*RH + 0.00122874*T*T*RH
        HI += 0.00085282*T*RH*RH - 0.00000199*T*T*RH*RH
        
        return (HI - 32) * 5/9  # Convert back to Celsius
    
    def _generate_baseline_schedule(
        self,
        intervals: List[IntervalInput],
        appliances: List[Appliance],
        building_type: BuildingType
    ) -> List[BaselineSchedule]:
        """Generate a realistic baseline schedule (what user would normally do)"""
        
        schedules = []
        ac_appliance = next((a for a in appliances if a.appliance_type == ApplianceType.AC), None)
        
        if not ac_appliance:
            # No AC available - use fans only
            for interval in intervals:
                schedules.append(BaselineSchedule(
                    timestamp_local=interval.timestamp_local,
                    baseline_ac_units_on=0,
                    baseline_ac_setpoint_c=24,
                    baseline_fan_units_on=1 if interval.occupancy_count > 0 else 0,
                    baseline_other_cooling_kw=0
                ))
            return schedules
        
        for interval in intervals:
            # Baseline behavior: AC on during occupied hours
            is_occupied = interval.occupancy_count > 0
            temp = interval.temperature_c
            
            if building_type == BuildingType.HOUSEHOLD:
                # Household: AC on from noon to midnight at 24°C
                if 12 <= interval.timestamp_local.hour <= 23 and is_occupied:
                    ac_units = 1
                    setpoint = 24
                else:
                    ac_units = 0
                    setpoint = 24
            elif building_type == BuildingType.SCHOOL:
                # School: AC on during school hours
                if 8 <= interval.timestamp_local.hour <= 16 and is_occupied:
                    ac_units = 2
                    setpoint = 24
                else:
                    ac_units = 0
                    setpoint = 24
            else:
                # Office: AC on during work hours
                if 9 <= interval.timestamp_local.hour <= 17 and is_occupied:
                    ac_units = 2
                    setpoint = 23
                else:
                    ac_units = 0
                    setpoint = 24
            
            # Cap by available units
            ac_units = min(ac_units, ac_appliance.quantity)
            
            # Fans when occupied
            fan_units = min(2, interval.occupancy_count) if is_occupied else 0
            
            schedules.append(BaselineSchedule(
                timestamp_local=interval.timestamp_local,
                baseline_ac_units_on=ac_units,
                baseline_ac_setpoint_c=setpoint,
                baseline_fan_units_on=fan_units,
                baseline_other_cooling_kw=0
            ))
        
        return schedules
    
    def parse_excel_sheet(self, df: pd.DataFrame, sheet_type: str) -> pd.DataFrame:
        """Parse and validate an Excel sheet based on type"""
        
        # Common preprocessing
        if 'timestamp_local' in df.columns:
            df['timestamp_local'] = pd.to_datetime(df['timestamp_local'])
        
        # Type-specific validation
        required_columns = {
            'interval_inputs': ['timestamp_local', 'temperature_c', 'tariff_pkr_per_kwh'],
            'appliances': ['appliance_id', 'rated_power_kw'],
            'energy_assets': ['solar_capacity_kw'],
            'scenario_profiles': ['scenario_id', 'name']
        }
        
        required = required_columns.get(sheet_type, [])
        missing = [col for col in required if col not in df.columns]
        
        if missing:
            raise ValueError(f"Missing required columns in {sheet_type}: {missing}")
        
        return df
