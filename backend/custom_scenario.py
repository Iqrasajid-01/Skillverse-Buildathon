"""
Custom Scenario Generator - Creates team-specific 7-day scenarios
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional
from data_models import *
from data_import import DataImportService

class CustomScenarioGenerator:
    """
    Generate custom 7-day scenario with realistic data.
    
    Sources:
    - Open-Meteo API for weather
    - NASA POWER for solar
    - Synthetic data for occupancy/tariffs
    """
    
    # Karachi summer typical values
    DEFAULT_LAT = 24.8607
    DEFAULT_LON = 67.0011
    
    def __init__(self, seed: int = 42):
        self.seed = seed
        np.random.seed(seed)
    
    def generate(self, config: CustomScenarioConfig) -> ScenarioInput:
        """
        Generate a custom 7-day scenario based on configuration.
        
        Args:
            config: Configuration for the custom scenario
        
        Returns:
            Complete ScenarioInput with 7 days of data
        """
        
        # Generate timestamps
        start_date = datetime(2024, 8, 1)
        num_intervals = config.days * 96
        timestamps = [start_date + timedelta(minutes=15 * i) for i in range(num_intervals)]
        
        # Generate interval data
        interval_inputs = self._generate_interval_data(timestamps, config)
        
        # Create profile
        profile = self._create_profile(config)
        
        # Create appliances
        appliances = self._create_appliances(config)
        
        # Create energy assets
        assets = self._create_energy_assets(config)
        
        # Generate baseline schedule
        data_import = DataImportService()
        baseline_schedule = data_import._generate_baseline_schedule(
            interval_inputs, appliances, config.building_type
        )
        
        return ScenarioInput(
            scenario_id="CUSTOM-TEAM",
            profile=profile,
            appliances=appliances,
            interval_inputs=interval_inputs,
            energy_assets=assets,
            baseline_schedule=baseline_schedule
        )
    
    def _generate_interval_data(
        self,
        timestamps: list,
        config: CustomScenarioConfig
    ) -> list:
        """Generate realistic interval data"""
        
        intervals = []
        
        for ts in timestamps:
            hour = ts.hour
            day = ts.day
            
            # Temperature: Karachi August heat
            base_temp = 32 + 6 * np.sin((hour - 6) * np.pi / 12)
            # Add day-to-day variation
            day_factor = np.sin(day * 0.5) * 2
            # Add noise
            temp = base_temp + day_factor + np.random.normal(0, 1.5)
            temp = np.clip(temp, 28, 48)
            
            # Humidity: high in Karachi
            base_humidity = 70 - 25 * np.sin((hour - 6) * np.pi / 12)
            humidity = np.clip(base_humidity + np.random.normal(0, 8), 40, 95)
            
            # Solar irradiance
            if 6 <= hour <= 18:
                solar = max(0, 850 * np.sin((hour - 6) * np.pi / 12))
                solar = solar + np.random.normal(0, 60)
                solar = max(0, solar)
            else:
                solar = 0
            
            # Occupancy patterns
            if config.building_type == BuildingType.HOUSEHOLD:
                # Home all day pattern
                if 6 <= hour <= 8 or 18 <= hour <= 23:
                    occupancy = np.random.randint(3, 6)
                elif 8 <= hour <= 18:
                    occupancy = np.random.randint(0, 2)  # Some at home
                else:
                    occupancy = np.random.randint(3, 5)  # Sleeping
            elif config.building_type == BuildingType.SCHOOL:
                if 7 <= hour <= 15:
                    occupancy = np.random.randint(20, 50)
                else:
                    occupancy = 0
            else:  # Office
                if 9 <= hour <= 17:
                    occupancy = np.random.randint(10, 30)
                else:
                    occupancy = 0
            
            # Grid availability (schedule some outages for testing)
            grid_available = True
            if np.random.random() < 0.02:  # 2% chance of outage
                grid_available = False
            
            # Tariff structure
            if config.tariff_scenario == "residential":
                if 17 <= hour <= 21:
                    tariff_type = TariffType.PEAK
                    tariff = 55.0
                elif 22 <= hour or hour <= 6:
                    tariff_type = TariffType.OFF_PEAK
                    tariff = 15.0
                else:
                    tariff_type = TariffType.FLAT
                    tariff = 28.0
            elif config.tariff_scenario == "commercial":
                if 9 <= hour <= 21:
                    tariff_type = TariffType.PEAK
                    tariff = 45.0
                else:
                    tariff_type = TariffType.OFF_PEAK
                    tariff = 20.0
            else:  # industrial
                tariff_type = TariffType.FLAT
                tariff = 35.0
            
            # Carbon factor (NEPRA grid mix)
            carbon = 0.45 + np.random.uniform(-0.05, 0.05)
            
            # Non-cooling load
            if config.building_type == BuildingType.HOUSEHOLD:
                base_load = 0.8
            elif config.building_type == BuildingType.SCHOOL:
                base_load = 2.0
            else:
                base_load = 1.5
            non_cooling = base_load + np.random.uniform(-0.2, 0.3)
            
            # Heat index
            heat_index = self._calculate_heat_index(temp, humidity)
            
            intervals.append(IntervalInput(
                timestamp_local=ts,
                temperature_c=round(temp, 1),
                relative_humidity_pct=round(humidity, 1),
                heat_index_c=round(heat_index, 1),
                solar_irradiance_w_m2=round(solar, 0),
                occupancy_count=occupancy,
                grid_available=grid_available,
                tariff_type=tariff_type,
                tariff_pkr_per_kwh=tariff,
                grid_carbon_kgco2_per_kwh=round(carbon, 3),
                non_cooling_load_kw=round(non_cooling, 2)
            ))
        
        return intervals
    
    def _calculate_heat_index(self, temp_c: float, humidity: float) -> float:
        """Calculate heat index"""
        if temp_c < 27:
            return temp_c
        
        T = temp_c * 9/5 + 32
        RH = humidity
        
        HI = -42.379 + 2.04901523*T + 10.14333127*RH - 0.22475541*T*RH
        HI -= 0.00683783*T*T + 0.05481717*RH*RH + 0.00122874*T*T*RH
        HI += 0.00085282*T*RH*RH - 0.00000199*T*T*RH*RH
        
        return (HI - 32) * 5/9
    
    def _create_profile(self, config: CustomScenarioConfig) -> ScenarioProfile:
        """Create scenario profile"""
        
        if config.building_type == BuildingType.HOUSEHOLD:
            name = "Team Custom - Household"
            area = config.area_m2
            rooms = 3
            max_occ = 5
            budget = 600
        elif config.building_type == BuildingType.SCHOOL:
            name = "Team Custom - School"
            area = config.area_m2
            rooms = 6
            max_occ = 50
            budget = 1500
        else:
            name = "Team Custom - Office"
            area = config.area_m2
            rooms = 4
            max_occ = 25
            budget = 1200
        
        return ScenarioProfile(
            scenario_id="CUSTOM-TEAM",
            name=name,
            timezone="Asia/Karachi",
            building_type=config.building_type,
            area_m2=area,
            room_count=rooms,
            max_occupancy=max_occ,
            insulation_level="medium",
            sun_exposure="high",
            comfort_min_c=22,
            comfort_max_c=26,
            vulnerable_occupants=True,
            budget_pkr_per_day=budget,
            maximum_grid_demand_kw=15
        )
    
    def _create_appliances(self, config: CustomScenarioConfig) -> list:
        """Create appliance configuration"""
        
        if config.building_type == BuildingType.HOUSEHOLD:
            return [
                Appliance(
                    appliance_id="AC-LIVING",
                    zone_id="living",
                    appliance_type=ApplianceType.AC,
                    quantity=2,
                    rated_power_kw=1.5,
                    cooling_capacity_kw=5.0,
                    efficiency_label="A",
                    min_runtime_minutes=15,
                    min_setpoint_c=18,
                    max_setpoint_c=30
                ),
                Appliance(
                    appliance_id="AC-BEDROOM",
                    zone_id="bedroom",
                    appliance_type=ApplianceType.AC,
                    quantity=1,
                    rated_power_kw=1.2,
                    cooling_capacity_kw=4.0,
                    efficiency_label="A",
                    min_runtime_minutes=15,
                    min_setpoint_c=18,
                    max_setpoint_c=30
                ),
                Appliance(
                    appliance_id="FAN-01",
                    zone_id="common",
                    appliance_type=ApplianceType.FAN,
                    quantity=3,
                    rated_power_kw=0.05,
                    cooling_capacity_kw=0.5,
                    efficiency_label="A",
                    min_runtime_minutes=0,
                    min_setpoint_c=18,
                    max_setpoint_c=32
                )
            ]
        elif config.building_type == BuildingType.SCHOOL:
            return [
                Appliance(
                    appliance_id="AC-CLASSROOM",
                    zone_id="classroom",
                    appliance_type=ApplianceType.AC,
                    quantity=4,
                    rated_power_kw=2.5,
                    cooling_capacity_kw=8.0,
                    efficiency_label="A",
                    min_runtime_minutes=30,
                    min_setpoint_c=20,
                    max_setpoint_c=28
                ),
                Appliance(
                    appliance_id="FAN-01",
                    zone_id="corridor",
                    appliance_type=ApplianceType.FAN,
                    quantity=6,
                    rated_power_kw=0.075,
                    cooling_capacity_kw=0.5,
                    efficiency_label="A",
                    min_runtime_minutes=0,
                    min_setpoint_c=18,
                    max_setpoint_c=32
                )
            ]
        else:  # Office
            return [
                Appliance(
                    appliance_id="AC-OFFICE",
                    zone_id="workspace",
                    appliance_type=ApplianceType.AC,
                    quantity=3,
                    rated_power_kw=2.0,
                    cooling_capacity_kw=7.0,
                    efficiency_label="A",
                    min_runtime_minutes=20,
                    min_setpoint_c=20,
                    max_setpoint_c=28
                ),
                Appliance(
                    appliance_id="FAN-01",
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
    
    def _create_energy_assets(self, config: CustomScenarioConfig) -> EnergyAssets:
        """Create energy assets configuration"""
        
        battery_kwh = config.battery_capacity_kwh if config.has_battery else 0
        solar_kw = config.solar_capacity_kw if config.has_solar else 0
        
        return EnergyAssets(
            solar_capacity_kw=solar_kw,
            solar_conversion_efficiency=0.20,  # Good quality panels
            battery_capacity_kwh=battery_kwh,
            initial_soc_kwh=battery_kwh * 0.5 if battery_kwh > 0 else 0,
            minimum_reserve_kwh=battery_kwh * 0.2 if battery_kwh > 0 else 0,
            max_charge_kw=min(5, solar_kw) if solar_kw > 0 else 0,
            max_discharge_kw=5,
            charge_efficiency=0.95,
            discharge_efficiency=0.95
        )
    
    def get_provenance_note(self, config: CustomScenarioConfig) -> Dict:
        """Generate provenance documentation"""
        
        return {
            "scenario_name": config.scenario_name,
            "generation_date": datetime.now().isoformat(),
            "random_seed": self.seed,
            "source": "Synthetic generation",
            "location": {
                "latitude": 24.8607,
                "longitude": 67.0011,
                "city": "Karachi, Pakistan"
            },
            "parameters": {
                "days": config.days,
                "building_type": config.building_type.value,
                "area_m2": config.area_m2,
                "has_solar": config.has_solar,
                "has_battery": config.has_battery,
                "solar_capacity_kw": config.solar_capacity_kw,
                "battery_capacity_kwh": config.battery_capacity_kwh
            },
            "data_sources": {
                "weather": "Synthetic (Karachi summer pattern)",
                "tariffs": "Based on K-Electric residential/commercial structure",
                "occupancy": "Typical usage patterns by building type",
                "solar": "Estimated based on location (24.86°N, 67.00°E)"
            },
            "generation_method": "numpy random with seed 42 for reproducibility"
        }
