"""
Solar & Battery Module - Models solar generation and battery storage
Handles charging, discharging, state-of-charge, and energy balance
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from data_models import EnergyAssets, IntervalInput

@dataclass
class BatteryState:
    """Battery state at a point in time"""
    soc_kwh: float
    charge_kwh: float = 0
    discharge_kwh: float = 0
    efficiency: float = 1.0

class SolarBatteryModule:
    """
    Solar and battery energy management module.
    
    Features:
    - Solar generation estimation
    - Battery charge/discharge optimization
    - State-of-charge tracking
    - Energy balance calculation
    """
    
    def __init__(self, assets: EnergyAssets):
        self.assets = assets
        self.current_soc = assets.initial_soc_kwh
        self.total_charge_kwh = 0
        self.total_discharge_kwh = 0
        self.cycle_count = 0
        self.history: List[BatteryState] = []
    
    def calculate_solar_generation(
        self,
        irradiance_w_m2: float,
        interval_hours: float = 0.25
    ) -> float:
        """
        Calculate solar energy generation for an interval.
        
        Args:
            irradiance_w_m2: Solar irradiance in W/m²
            interval_hours: Duration of interval in hours
        
        Returns:
            Solar energy generated in kWh
        """
        if self.assets.solar_capacity_kw <= 0 or irradiance_w_m2 <= 0:
            return 0.0
        
        # Solar energy = Irradiance (kW/m²) × Area factor × Efficiency × Hours
        # Simplified: scale irradiance by capacity
        irradiance_kw_m2 = irradiance_w_m2 / 1000
        
        # Effective capacity considering actual irradiance
        effective_capacity = min(
            self.assets.solar_capacity_kw,
            irradiance_kw_m2 * self.assets.solar_capacity_kw * 10  # Rough area factor
        )
        
        energy_kwh = effective_capacity * self.assets.solar_conversion_efficiency * interval_hours
        
        return max(0, energy_kwh)
    
    def optimize_energy_flow(
        self,
        load_kwh: float,
        solar_available_kwh: float,
        tariff_pkr: float,
        tariff_type: str,
        is_peak: bool,
        grid_available: bool,
        min_soc_kwh: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Optimize energy flow between solar, battery, grid, and load.
        
        Args:
            load_kwh: Total energy demand
            solar_available_kwh: Available solar generation
            tariff_pkr: Current electricity tariff (PKR/kWh)
            tariff_type: Type of tariff (peak, off_peak, flat)
            is_peak: Whether current period is peak tariff
            grid_available: Whether grid is available
            min_soc_kwh: Minimum SOC threshold (optional override)
        
        Returns:
            Dict with grid, solar, battery flows and new SOC
        """
        min_soc = min_soc_kwh if min_soc_kwh is not None else self.assets.minimum_reserve_kwh
        
        result = {
            'solar_used_kwh': 0,
            'battery_discharge_kwh': 0,
            'battery_charge_kwh': 0,
            'grid_drawn_kwh': 0,
            'excess_solar_kwh': 0,
            'new_soc_kwh': self.current_soc
        }
        
        remaining_load = load_kwh
        
        # Step 1: Use solar first (free energy)
        solar_to_use = min(solar_available_kwh, remaining_load)
        result['solar_used_kwh'] = solar_to_use
        remaining_load -= solar_to_use
        
        # Excess solar goes to battery (if not peak tariff - charge during cheap times)
        excess_solar = solar_available_kwh - solar_to_use
        if excess_solar > 0 and not is_peak:
            # Can charge battery
            charge_amount = min(
                excess_solar * self.assets.charge_efficiency,
                self.assets.max_charge_kw * 0.25,  # 15 min interval
                self.assets.battery_capacity_kwh - self.current_soc
            )
            if charge_amount > 0:
                result['battery_charge_kwh'] = charge_amount
                self.current_soc += charge_amount
                result['new_soc_kwh'] = self.current_soc
        
        # Step 2: Use battery ONLY if grid is unavailable (emergency fallback)
        # During peak hours with grid available, use grid (battery is for outage/emergency)
        if remaining_load > 0 and not grid_available:
            # Emergency discharge - only when grid is down
            discharge_amount = min(
                remaining_load,
                self.current_soc - min_soc,
                self.assets.max_discharge_kw * 0.25
            )
            if discharge_amount > 0:
                actual_discharge = discharge_amount / self.assets.discharge_efficiency
                result['battery_discharge_kwh'] = actual_discharge
                self.current_soc -= actual_discharge
                remaining_load -= min(discharge_amount, remaining_load)
                result['new_soc_kwh'] = self.current_soc

        # Step 3: Draw from grid if needed and available
        if remaining_load > 0 and grid_available:
            result['grid_drawn_kwh'] = remaining_load
        
        # Step 4: If grid unavailable and load remains, we have a problem
        if remaining_load > 0 and not grid_available:
            # Could implement load shedding or alert here
            pass
        
        # Track totals
        self.total_charge_kwh += result['battery_charge_kwh']
        self.total_discharge_kwh += result['battery_discharge_kwh']
        
        # Store state
        self.history.append(BatteryState(
            soc_kwh=self.current_soc,
            charge_kwh=result['battery_charge_kwh'],
            discharge_kwh=result['battery_discharge_kwh']
        ))
        
        return result
    
    def get_battery_metrics(self) -> Dict[str, float]:
        """Get battery performance metrics"""
        capacity = self.assets.battery_capacity_kwh
        
        if capacity <= 0:
            return {
                'current_soc_kwh': 0,
                'soc_percentage': 0,
                'capacity_kwh': 0,
                'utilization_pct': 0,
                'total_cycles': self.cycle_count,
                'total_charge_kwh': self.total_charge_kwh,
                'total_discharge_kwh': self.total_discharge_kwh
            }
        
        avg_soc = np.mean([s.soc_kwh for s in self.history]) if self.history else self.current_soc
        
        # Estimate cycles from charge/discharge totals
        estimated_cycles = (self.total_charge_kwh + self.total_discharge_kwh) / (2 * capacity)
        
        return {
            'current_soc_kwh': round(self.current_soc, 2),
            'soc_percentage': round(self.current_soc / capacity * 100, 1),
            'capacity_kwh': capacity,
            'min_reserve_kwh': self.assets.minimum_reserve_kwh,
            'usable_capacity_kwh': capacity - self.assets.minimum_reserve_kwh,
            'utilization_pct': round(avg_soc / capacity * 100, 1) if capacity > 0 else 0,
            'total_cycles': round(estimated_cycles, 2),
            'total_charge_kwh': round(self.total_charge_kwh, 2),
            'total_discharge_kwh': round(self.total_discharge_kwh, 2),
            'max_charge_rate_kw': self.assets.max_charge_kw,
            'max_discharge_rate_kw': self.assets.max_discharge_kw
        }
    
    def reset(self):
        """Reset battery state"""
        self.current_soc = self.assets.initial_soc_kwh
        self.total_charge_kwh = 0
        self.total_discharge_kwh = 0
        self.cycle_count = 0
        self.history = []
    
    def validate_battery_operation(self) -> Dict[str, bool]:
        """Validate battery is operating within constraints"""
        capacity = self.assets.battery_capacity_kwh
        
        violations = []
        
        if self.current_soc < 0:
            violations.append("SOC below 0")
        if self.current_soc > capacity:
            violations.append("SOC above capacity")
        if self.current_soc < self.assets.minimum_reserve_kwh:
            violations.append("SOC below minimum reserve")
        
        return {
            'valid': len(violations) == 0,
            'violations': violations,
            'current_soc': self.current_soc,
            'soc_in_range': 0 <= self.current_soc <= capacity
        }


class EnergyBalanceCalculator:
    """Calculate and validate energy balance for each interval"""
    
    @staticmethod
    def calculate_balance(
        grid_in: float,
        solar_in: float,
        battery_discharge: float,
        battery_charge: float,
        load: float,
        charge_eff: float = 0.95,
        discharge_eff: float = 0.95
    ) -> Dict[str, float]:
        """
        Calculate energy balance for an interval.
        
        Energy In = Grid + Solar + Battery Discharge
        Energy Out = Load + Battery Charge
        
        Balance should be approximately zero (within losses)
        """
        energy_in = grid_in + solar_in + (battery_discharge * discharge_eff)
        energy_out = load + (battery_charge / charge_eff) if charge_eff > 0 else load + battery_charge
        
        balance = energy_in - energy_out
        
        return {
            'energy_in_kwh': round(energy_in, 4),
            'energy_out_kwh': round(energy_out, 4),
            'balance_kwh': round(balance, 4),
            'balance_valid': abs(balance) < 0.01,  # Within 10Wh tolerance
            'losses_kwh': round(max(0, -balance), 4)
        }
    
    @staticmethod
    def validate_interval(
        grid_energy: float,
        solar_used: float,
        battery_charge: float,
        battery_discharge: float,
        total_load: float,
        grid_available: bool
    ) -> Tuple[bool, List[str]]:
        """
        Validate an interval's energy flows.
        
        Returns:
            Tuple of (is_valid, list of violation messages)
        """
        violations = []
        
        # Rule 1: No grid when unavailable
        if not grid_available and grid_energy > 0.01:
            violations.append(f"Grid draw of {grid_energy} kWh when grid unavailable")
        
        # Rule 2: Battery SOC constraints handled by module
        # Rule 3: Charge/discharge rate limits
        if battery_charge < 0 or battery_discharge < 0:
            violations.append("Negative charge/discharge values")
        
        # Rule 4: Energy balance
        balance_check = EnergyBalanceCalculator.calculate_balance(
            grid_energy, solar_used, battery_discharge, battery_charge, total_load
        )
        if not balance_check['balance_valid']:
            violations.append(f"Energy imbalance: {balance_check['balance_kwh']} kWh")
        
        return len(violations) == 0, violations
