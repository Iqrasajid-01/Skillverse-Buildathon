"""
Baseline Engine - Calculates current energy usage, cost, emissions
This represents what the user is currently doing (without optimization)
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from data_models import *
from thermal_model import ThermalModel

class BaselineEngine:
    """Calculate baseline cooling schedule and metrics"""
    
    def __init__(self):
        self.thermal = ThermalModel()
    
    def calculate(self, scenario: ScenarioInput) -> 'BaselineResult':
        """
        Calculate baseline energy usage, cost, and emissions
        based on the baseline_schedule or default rules
        """

        if scenario.baseline_schedule and len(scenario.baseline_schedule) > 0:
            schedules = {bs.timestamp_local: bs for bs in scenario.baseline_schedule}
        else:
            schedules = self._generate_default_baseline(scenario)

        # Calculate per-interval metrics
        results = []
        battery_soc = scenario.energy_assets.initial_soc_kwh

        for interval in scenario.interval_inputs:
            ts = interval.timestamp_local

            # Get baseline schedule for this interval
            if ts in schedules:
                bs = schedules[ts]
                ac_units = bs.baseline_ac_units_on
                setpoint = bs.baseline_ac_setpoint_c
                fan_units = bs.baseline_fan_units_on
            else:
                # Default: no cooling
                ac_units = 0
                setpoint = 24
                fan_units = 0

            # Get AC appliance
            ac = next((a for a in scenario.appliances if a.appliance_type == ApplianceType.AC), None)
            fan = next((a for a in scenario.appliances if a.appliance_type == ApplianceType.FAN), None)

            # Calculate energy consumption
            interval_hours = 0.25  # 15 minutes = 0.25 hours

            # AC energy
            ac_power_kw = ac.rated_power_kw * ac_units if ac else 0
            ac_energy_kwh = ac_power_kw * interval_hours

            # Fan energy
            fan_power_kw = fan.rated_power_kw * fan_units if fan else 0
            fan_energy_kwh = fan_power_kw * interval_hours

            # Total cooling energy
            cooling_energy = ac_energy_kwh + fan_energy_kwh

            # Grid energy (accounting for non-cooling load)
            total_load = cooling_energy + interval.non_cooling_load_kw * interval_hours

            # Solar offset (if available)
            solar_available_kwh = self._calculate_solar(
                interval.solar_irradiance_w_m2,
                scenario.energy_assets.solar_capacity_kw,
                scenario.energy_assets.solar_conversion_efficiency,
                interval_hours
            )

            # Battery discharge (simplified - assume baseline doesn't use battery)
            battery_used = 0

            # Grid energy
            grid_energy = max(0, total_load - solar_available_kwh - battery_used)

            # Cost calculation
            cost = grid_energy * interval.tariff_pkr_per_kwh

            # Emissions
            emissions = grid_energy * interval.grid_carbon_kgco2_per_kwh

            # Indoor temperature estimate
            indoor_temp = self.thermal.estimate_indoor_temp(
                outdoor_temp=interval.temperature_c,
                setpoint=setpoint if ac_units > 0 else None,
                cooling_on=ac_units > 0,
                occupancy=interval.occupancy_count,
                solar_gain=interval.solar_irradiance_w_m2,
                building_area=scenario.profile.area_m2,
                insulation=scenario.profile.insulation_level
            )

            # Comfort status
            comfort_status = self._determine_comfort_status(
                indoor_temp,
                interval.occupancy_count,
                scenario.profile.comfort_min_c,
                scenario.profile.comfort_max_c
            )

            # Update battery SOC (simplified - baseline doesn't actively manage)
            battery_soc = min(
                scenario.energy_assets.battery_capacity_kwh,
                max(0, battery_soc)
            )

            results.append({
                'timestamp': ts,
                'date': ts.date(),
                'ac_units_on': ac_units,
                'setpoint': setpoint,
                'fan_units_on': fan_units,
                'grid_energy_kwh': grid_energy,
                'solar_energy_kwh': min(solar_available_kwh, total_load),
                'cooling_energy_kwh': cooling_energy,
                'cost_pkr': cost,
                'emissions_kgco2e': emissions,
                'indoor_temp_c': indoor_temp,
                'comfort_status': comfort_status,
                'battery_soc_kwh': battery_soc
            })

        # Aggregate results
        df = pd.DataFrame(results)

        # Calculate peak demand
        df['power_kw'] = df['grid_energy_kwh'] / 0.25  # Convert energy to power
        peak_demand_kw = df['power_kw'].max()

        # Calculate totals
        total_energy_kwh = df['cooling_energy_kwh'].sum()
        total_grid_energy = df['grid_energy_kwh'].sum()
        total_cost = df['cost_pkr'].sum()
        total_emissions = df['emissions_kgco2e'].sum()

        # Comfort compliance
        occupied_intervals = df[df['comfort_status'] != 'unsafe']
        comfort_compliance_pct = (len(occupied_intervals) / len(df) * 100) if len(df) > 0 else 100

        # Peak period energy
        peak_energy = df[df['comfort_status'] == 'unsafe']['grid_energy_kwh'].sum() if df['comfort_status'].dtype == 'object' else 0

        # Solar utilization
        total_solar_available = self._calculate_total_solar(scenario)
        solar_utilization = (df['solar_energy_kwh'].sum() / total_solar_available * 100) if total_solar_available > 0 else 0

        # Calculate daily summaries
        daily_summaries = []
        if len(df) > 0:
            for date, day_df in df.groupby('date'):
                daily_summaries.append({
                    'date': date,
                    'total_energy_kwh': round(day_df['cooling_energy_kwh'].sum(), 2),
                    'total_cost_pkr': round(day_df['cost_pkr'].sum(), 2),
                    'total_emissions_kgco2e': round(day_df['emissions_kgco2e'].sum(), 3),
                    'peak_demand_kw': round(day_df['power_kw'].max(), 2),
                    'comfort_compliance_pct': round((len(day_df[day_df['comfort_status'] != 'unsafe']) / len(day_df) * 100), 1) if len(day_df) > 0 else 100,
                    'unsafe_hours': int((day_df['comfort_status'] == 'unsafe').sum() * 0.25),
                    'solar_utilization_pct': round((day_df['solar_energy_kwh'].sum() / total_solar_available * 100) if total_solar_available > 0 else 0, 1),
                    'battery_cycles': 0
                })

        return BaselineResult(
            total_energy_kwh=round(total_energy_kwh, 3),
            total_grid_energy_kwh=round(total_grid_energy, 3),
            total_cost_pkr=round(total_cost, 2),
            total_emissions_kgco2e=round(total_emissions, 3),
            peak_demand_kw=round(peak_demand_kw, 2),
            comfort_compliance_pct=round(comfort_compliance_pct, 1),
            unsafe_hours=int((df['comfort_status'] == 'unsafe').sum() * 0.25),
            solar_utilization_pct=round(solar_utilization, 1),
            battery_cycles=0,
            intervals=results,
            daily_summaries=daily_summaries
        )
    
    def _generate_default_baseline(self, scenario: ScenarioInput) -> Dict[datetime, BaselineSchedule]:
        """
        Generate realistic default baseline if none provided.
        Represents typical user behavior: run AC consistently during occupied hours
        to maintain comfort, regardless of cost/tariff.
        """
        schedules = {}
        
        # Get comfort settings from profile
        comfort_min = scenario.profile.comfort_min_c
        comfort_max = scenario.profile.comfort_max_c
        # Baseline setpoint is typically in the middle of comfort band
        baseline_setpoint = (comfort_min + comfort_max) / 2

        for interval in scenario.interval_inputs:
            hour = interval.timestamp_local.hour
            is_occupied = interval.occupancy_count > 0

            # REALISTIC BASELINE: AC on during ALL occupied hours
            # Users typically run AC whenever they're home during hot weather
            if scenario.profile.building_type == BuildingType.HOUSEHOLD:
                # Household: AC on during typical home hours (7-23)
                ac_on = 7 <= hour <= 23 and is_occupied
            else:
                # School/Office: AC on during business hours (7-19)
                ac_on = 7 <= hour <= 19 and is_occupied

            # Fans always on when occupied (for air circulation)
            fan_on = min(2, interval.occupancy_count) if is_occupied else 0

            schedules[interval.timestamp_local] = BaselineSchedule(
                timestamp_local=interval.timestamp_local,
                baseline_ac_units_on=1 if ac_on else 0,
                baseline_ac_setpoint_c=baseline_setpoint,  # Comfort-band setpoint
                baseline_fan_units_on=fan_on,
                baseline_other_cooling_kw=0
            )

        return schedules
    
    def _calculate_solar(
        self,
        irradiance_w_m2: float,
        capacity_kw: float,
        efficiency: float,
        interval_hours: float
    ) -> float:
        """Calculate solar energy production"""
        if capacity_kw <= 0 or irradiance_w_m2 <= 0:
            return 0
        
        # Solar production = irradiance * area * efficiency * capacity_factor
        # Simplified: use irradiance directly with capacity
        energy_kwh = irradiance_w_m2 / 1000 * capacity_kw * efficiency * interval_hours
        return max(0, energy_kwh)
    
    def _calculate_total_solar(self, scenario: ScenarioInput) -> float:
        """Calculate total available solar energy for the period"""
        total = 0
        interval_hours = 0.25
        
        for interval in scenario.interval_inputs:
            total += self._calculate_solar(
                interval.solar_irradiance_w_m2,
                scenario.energy_assets.solar_capacity_kw,
                scenario.energy_assets.solar_conversion_efficiency,
                interval_hours
            )
        
        return total
    
    def _determine_comfort_status(
        self,
        indoor_temp: float,
        occupancy: int,
        comfort_min: float,
        comfort_max: float
    ) -> str:
        """Determine comfort status"""
        if occupancy == 0:
            return 'within_range'  # Vacant is always comfortable
        
        if indoor_temp < comfort_min - 2 or indoor_temp > comfort_max + 3:
            return 'unsafe'
        elif indoor_temp < comfort_min or indoor_temp > comfort_max:
            return 'warning'
        else:
            return 'within_range'


class BaselineResult:
    """Results from baseline calculation"""

    def __init__(
        self,
        total_energy_kwh: float,
        total_grid_energy_kwh: float,
        total_cost_pkr: float,
        total_emissions_kgco2e: float,
        peak_demand_kw: float,
        comfort_compliance_pct: float,
        unsafe_hours: int,
        solar_utilization_pct: float,
        battery_cycles: float,
        intervals: List[Dict],
        daily_summaries: List[Dict]
    ):
        self.total_energy_kwh = total_energy_kwh
        self.total_grid_energy_kwh = total_grid_energy_kwh
        self.total_cost_pkr = total_cost_pkr
        self.total_emissions_kgco2e = total_emissions_kgco2e
        self.peak_demand_kw = peak_demand_kw
        self.comfort_compliance_pct = comfort_compliance_pct
        self.unsafe_hours = unsafe_hours
        self.solar_utilization_pct = solar_utilization_pct
        self.battery_cycles = battery_cycles
        self.intervals = intervals
        self.daily_summaries = daily_summaries
