"""
Validation Service - Validates all input data against requirements
"""

from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import numpy as np
from data_models import *

class ValidationService:
    """
    Validates scenario inputs for completeness, correctness, and constraints.
    """
    
    # Validation thresholds
    TEMP_MIN = -20
    TEMP_MAX = 60
    HUMIDITY_MIN = 0
    HUMIDITY_MAX = 100
    SOLAR_MAX = 1200  # W/m2
    TARIFF_MAX = 200  # PKR/kWh
    CARBON_MAX = 2.0  # kgCO2/kWh
    
    def validate_scenario(self, scenario: ScenarioInput) -> ValidationResult:
        """
        Validate all inputs for a scenario.
        
        Returns:
            ValidationResult with errors, warnings, and validity status
        """
        errors = []
        warnings = []
        missing_fields = []
        outlier_count = 0
        
        # 1. Profile validation
        profile_errors = self._validate_profile(scenario.profile)
        errors.extend(profile_errors)
        
        # 2. Appliances validation
        appliance_errors = self._validate_appliances(scenario.appliances)
        errors.extend(appliance_errors)
        
        # 3. Energy assets validation
        asset_errors = self._validate_energy_assets(scenario.energy_assets)
        errors.extend(asset_errors)
        
        # 4. Interval inputs validation
        interval_errors, interval_warnings, missing, outliers = self._validate_intervals(
            scenario.interval_inputs
        )
        errors.extend(interval_errors)
        warnings.extend(interval_warnings)
        missing_fields.extend(missing)
        outlier_count += outliers
        
        # 5. Timestamp continuity check
        continuity_errors = self._check_timestamp_continuity(scenario.interval_inputs)
        errors.extend(continuity_errors)
        
        # 6. Cross-field validation
        cross_errors = self._cross_field_validation(scenario)
        errors.extend(cross_errors)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            missing_fields=missing_fields,
            outlier_count=outlier_count
        )
    
    def _validate_profile(self, profile: ScenarioProfile) -> List[str]:
        """Validate scenario profile"""
        errors = []
        
        if not profile.scenario_id:
            errors.append("Missing scenario ID")
        
        if profile.area_m2 <= 0:
            errors.append("Building area must be positive")
        
        if profile.comfort_min_c >= profile.comfort_max_c:
            errors.append("Comfort min must be less than comfort max")
        
        if profile.budget_pkr_per_day < 0:
            errors.append("Budget cannot be negative")
        
        return errors
    
    def _validate_appliances(self, appliances: List[Appliance]) -> List[str]:
        """Validate appliance definitions"""
        errors = []
        
        if not appliances:
            errors.append("No appliances defined")
            return errors
        
        for appliance in appliances:
            if appliance.rated_power_kw <= 0:
                errors.append(f"Appliance {appliance.appliance_id}: rated power must be positive")
            
            if appliance.quantity <= 0:
                errors.append(f"Appliance {appliance.appliance_id}: quantity must be positive")
            
            if appliance.min_setpoint_c >= appliance.max_setpoint_c:
                errors.append(f"Appliance {appliance.appliance_id}: min setpoint must be less than max")
        
        return errors
    
    def _validate_energy_assets(self, assets: EnergyAssets) -> List[str]:
        """Validate energy assets"""
        errors = []
        
        if assets.solar_capacity_kw < 0:
            errors.append("Solar capacity cannot be negative")
        
        if assets.battery_capacity_kwh < 0:
            errors.append("Battery capacity cannot be negative")
        
        if assets.initial_soc_kwh > assets.battery_capacity_kwh:
            errors.append("Initial SOC cannot exceed battery capacity")
        
        if assets.minimum_reserve_kwh > assets.battery_capacity_kwh:
            errors.append("Minimum reserve cannot exceed battery capacity")
        
        if not 0 <= assets.charge_efficiency <= 1:
            errors.append("Charge efficiency must be between 0 and 1")
        
        if not 0 <= assets.discharge_efficiency <= 1:
            errors.append("Discharge efficiency must be between 0 and 1")
        
        return errors
    
    def _validate_intervals(
        self,
        intervals: List[IntervalInput]
    ) -> Tuple[List[str], List[str], List[str], int]:
        """Validate interval inputs"""
        errors = []
        warnings = []
        missing = []
        outliers = 0
        
        if not intervals:
            errors.append("No interval data provided")
            return errors, warnings, missing, outliers
        
        for i, interval in enumerate(intervals):
            # Temperature
            if interval.temperature_c < self.TEMP_MIN or interval.temperature_c > self.TEMP_MAX:
                warnings.append(f"Interval {i}: Temperature {interval.temperature_c}°C outside normal range")
                outliers += 1
            
            # Humidity
            if interval.relative_humidity_pct < self.HUMIDITY_MIN or interval.relative_humidity_pct > self.HUMIDITY_MAX:
                errors.append(f"Interval {i}: Humidity {interval.relative_humidity_pct}% out of bounds")
            
            # Solar irradiance
            if interval.solar_irradiance_w_m2 < 0:
                errors.append(f"Interval {i}: Negative solar irradiance")
            
            if interval.solar_irradiance_w_m2 > self.SOLAR_MAX:
                warnings.append(f"Interval {i}: Solar irradiance {interval.solar_irradiance_w_m2} W/m² unusually high")
                outliers += 1
            
            # Occupancy
            if interval.occupancy_count < 0:
                errors.append(f"Interval {i}: Negative occupancy")
            
            # Tariff
            if interval.tariff_pkr_per_kwh < 0:
                errors.append(f"Interval {i}: Negative tariff")
            
            if interval.tariff_pkr_per_kwh > self.TARIFF_MAX:
                warnings.append(f"Interval {i}: Tariff {interval.tariff_pkr_per_kwh} PKR unusually high")
            
            # Carbon factor
            if interval.grid_carbon_kgco2_per_kwh < 0:
                errors.append(f"Interval {i}: Negative carbon factor")
            
            if interval.grid_carbon_kgco2_per_kwh > self.CARBON_MAX:
                warnings.append(f"Interval {i}: Carbon factor {interval.grid_carbon_kgco2_per_kwh} unusually high")
                outliers += 1
        
        return errors, warnings, missing, outliers
    
    def _check_timestamp_continuity(self, intervals: List[IntervalInput]) -> List[str]:
        """Check for missing or duplicate timestamps"""
        errors = []
        
        if not intervals or len(intervals) < 2:
            return errors
        
        # Sort by timestamp
        sorted_intervals = sorted(intervals, key=lambda x: x.timestamp_local)
        
        expected_delta = timedelta(minutes=15)
        
        for i in range(1, len(sorted_intervals)):
            actual_delta = sorted_intervals[i].timestamp_local - sorted_intervals[i-1].timestamp_local
            
            if actual_delta != expected_delta:
                # Check for duplicates
                if actual_delta == timedelta(0):
                    errors.append(f"Duplicate timestamp at index {i}")
                # Check for gaps
                elif actual_delta > expected_delta:
                    gaps = actual_delta / expected_delta - 1
                    errors.append(f"Timestamp gap at index {i}: {int(gaps)} intervals missing")
        
        return errors
    
    def _cross_field_validation(self, scenario: ScenarioInput) -> List[str]:
        """Validate relationships between fields"""
        errors = []
        
        # Check if max occupancy is reasonable for area
        max_occupancy_per_room = scenario.profile.max_occupancy / max(1, scenario.profile.room_count)
        if max_occupancy_per_room > 10:
            errors.append(f"Max occupancy ({scenario.profile.max_occupancy}) seems high for area")
        
        # Check AC capacity vs building size
        total_ac_capacity = sum(
            a.cooling_capacity_kw * a.quantity 
            for a in scenario.appliances 
            if a.appliance_type == ApplianceType.AC
        )
        
        # Rough rule: need ~50W per m2 for cooling
        required_capacity = scenario.profile.area_m2 * 0.05
        
        if total_ac_capacity < required_capacity * 0.5:
            errors.append(f"AC capacity ({total_ac_capacity} kW) may be insufficient for area")
        
        # Check battery assets vs solar
        if scenario.energy_assets.battery_capacity_kwh > 0 and scenario.energy_assets.solar_capacity_kw == 0:
            errors.append("Battery defined but no solar capacity")
        
        return errors


class ConstraintValidator:
    """Validates that optimization results satisfy all constraints"""
    
    def validate_interval_output(
        self,
        output: IntervalOutput,
        interval_input: IntervalInput,
        assets: EnergyAssets,
        appliances: List[Appliance],
        max_ac_units: int
    ) -> Tuple[bool, List[str]]:
        """Validate a single interval output against constraints"""
        violations = []

        # Floating point tolerance for battery checks (50Wh)
        tolerance = 0.05

        # 1. Grid availability constraint
        if not interval_input.grid_available and output.grid_energy_kwh > 0.01:
            violations.append(f"Grid draw when grid unavailable: {output.grid_energy_kwh} kWh")

        # 2. Battery SOC bounds (with floating point tolerance)
        if output.battery_soc_kwh < -tolerance:
            violations.append(f"Battery SOC below 0: {output.battery_soc_kwh} kWh")

        if output.battery_soc_kwh > assets.battery_capacity_kwh + tolerance:
            violations.append(f"Battery SOC exceeds capacity: {output.battery_soc_kwh} kWh")

        if output.battery_soc_kwh < assets.minimum_reserve_kwh - tolerance:
            violations.append(f"Battery SOC below reserve: {output.battery_soc_kwh} kWh")
        
        # 3. Appliance limits
        ac = next((a for a in appliances if a.appliance_type == ApplianceType.AC), None)
        if ac and output.recommended_ac_units_on > ac.quantity:
            violations.append(f"AC units ({output.recommended_ac_units_on}) exceed available ({ac.quantity})")
        
        if output.recommended_ac_units_on > max_ac_units:
            violations.append(f"AC units exceed max allowed: {output.recommended_ac_units_on}")
        
        # 4. Setpoint limits
        if output.recommended_ac_setpoint_c:
            if ac:
                if output.recommended_ac_setpoint_c < ac.min_setpoint_c:
                    violations.append(f"Setpoint below minimum: {output.recommended_ac_setpoint_c}°C")
                if output.recommended_ac_setpoint_c > ac.max_setpoint_c:
                    violations.append(f"Setpoint above maximum: {output.recommended_ac_setpoint_c}°C")
        
        # 5. Energy balance (within 250Wh tolerance for floating point precision)
        total_in = output.grid_energy_kwh + output.solar_energy_used_kwh + output.battery_discharge_kwh
        total_out = output.cooling_energy_kwh + interval_input.non_cooling_load_kw * 0.25 + output.battery_charge_kwh
        imbalance = abs(total_in - total_out)

        if imbalance > 0.25:  # 250Wh tolerance
            violations.append(f"Energy imbalance: {imbalance:.4f} kWh")
        
        return len(violations) == 0, violations
    
    def validate_all_intervals(
        self,
        outputs: List[IntervalOutput],
        inputs: List[IntervalInput],
        assets: EnergyAssets,
        appliances: List[Appliance],
        max_ac_units: int
    ) -> Dict:
        """Validate all interval outputs"""
        
        all_violations = []
        
        for i, (out, inp) in enumerate(zip(outputs, inputs)):
            valid, violations = self.validate_interval_output(
                out, inp, assets, appliances, max_ac_units
            )
            if not valid:
                all_violations.append({
                    'interval': i,
                    'timestamp': out.timestamp_local,
                    'violations': violations
                })
        
        return {
            'all_valid': len(all_violations) == 0,
            'violation_count': len(all_violations),
            'violations': all_violations
        }
