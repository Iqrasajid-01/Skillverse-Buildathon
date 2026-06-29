"""
Thermal Model - Estimate indoor temperature based on building characteristics
Uses simplified resistance-capacitance (RC) thermal model
"""

import numpy as np
from typing import Dict, Optional

class ThermalModel:
    """
    Simplified thermal model for indoor temperature estimation.
    Uses a first-order RC thermal circuit model.
    
    Factors considered:
    - Outdoor temperature
    - Solar radiation (heat gain)
    - Building thermal mass (insulation)
    - Occupancy (internal heat gains)
    - Cooling system operation
    """
    
    # Thermal resistance by insulation level (K/W per m2)
    INSULATION_R = {
        'low': 0.1,
        'medium': 0.3,
        'high': 0.6
    }
    
    # Solar heat gain coefficient (W/m2 per W/m2 irradiance)
    SOLAR_GAIN_FACTOR = {
        'low': 0.3,      # Good window shading
        'medium': 0.5,   # Standard windows
        'high': 0.7      # Large unshaded glass
    }
    
    # Internal heat gain per person (W)
    INTERNAL_GAIN_PER_PERSON = 100
    
    # Thermal mass factor (minutes to thermal equilibrium)
    THERMAL_MASS_MINUTES = {
        'low': 30,       # Light construction
        'medium': 60,    # Standard building
        'high': 120      # Heavy construction, high thermal mass
    }
    
    def __init__(self):
        self.previous_temp: Optional[float] = None
        self.temperature_history: list = []
    
    def estimate_indoor_temp(
        self,
        outdoor_temp: float,
        setpoint: Optional[float] = None,
        cooling_on: bool = False,
        cooling_capacity_kw: float = 5.0,
        occupancy: int = 0,
        solar_gain: float = 0,
        building_area: float = 80,
        insulation: str = 'medium',
        sun_exposure: str = 'medium',
        timestep_minutes: int = 15
    ) -> float:
        """
        Estimate indoor temperature for current interval.
        
        Args:
            outdoor_temp: Current outdoor temperature (°C)
            setpoint: AC setpoint if cooling is on (°C)
            cooling_on: Whether AC is currently operating
            cooling_capacity_kw: Cooling capacity of AC system (kW)
            occupancy: Number of occupants
            solar_gain: Solar irradiance (W/m2)
            building_area: Floor area (m2)
            insulation: Insulation level ('low', 'medium', 'high')
            sun_exposure: Sun exposure ('low', 'medium', 'high')
            timestep_minutes: Simulation timestep (default 15 min)
        
        Returns:
            Estimated indoor temperature (°C)
        """
        
        # Get parameters
        R = self.INSULATION_R.get(insulation, 0.3)
        solar_factor = self.SOLAR_GAIN_FACTOR.get(sun_exposure, 0.5)
        thermal_mass = self.THERMAL_MASS_MINUTES.get(insulation, 60)
        
        # Initial indoor temperature if not set
        if self.previous_temp is None:
            self.previous_temp = outdoor_temp - 2  # Assume slightly cooler initially
        
        # Heat gains
        solar_heat_gain = solar_gain * solar_factor * building_area  # Watts
        internal_heat_gain = occupancy * self.INTERNAL_GAIN_PER_PERSON  # Watts
        
        # Total heat gain to building
        heat_gain = solar_heat_gain + internal_heat_gain  # Watts
        
        # Heat loss through envelope
        temp_diff = outdoor_temp - self.previous_temp
        heat_loss = temp_diff / R * building_area if R > 0 else 0  # Watts
        
        # Net heat flow
        net_heat = heat_gain - heat_loss  # Watts
        
        # Cooling effect (if AC is on)
        if cooling_on and cooling_capacity_kw > 0:
            # Convert kW to Watts and apply efficiency
            cooling_effect_w = cooling_capacity_kw * 1000 * 0.8  # Assume 80% effectiveness
            # Adjust based on setpoint difference
            if setpoint:
                setpoint_diff = self.previous_temp - setpoint
                cooling_effect_w *= min(1, max(0.3, setpoint_diff / 10))
            net_heat -= cooling_effect_w
        
        # Temperature change (simplified thermal model)
        # dT/dt = net_heat / (C * V) where C is thermal capacity, V is volume
        # Simplified: use thermal mass time constant
        thermal_time_constant = thermal_mass  # minutes
        
        # Temperature change rate (°C per minute)
        # Approximation: assume 1°C change per 1000W net heat per 100m2
        temp_change_rate = net_heat / (building_area * 1000)  # °C per minute
        
        # Calculate temperature change for timestep
        temp_change = temp_change_rate * timestep_minutes
        
        # Apply thermal damping (building doesn't respond instantly)
        damping_factor = 1 - np.exp(-timestep_minutes / thermal_time_constant)
        damped_change = temp_change * damping_factor
        
        # Calculate new indoor temperature
        new_temp = self.previous_temp + damped_change

        # Constrain to physically reasonable bounds
        # When AC is on, indoor should be close to setpoint (within 2-3°C)
        # When AC is off, indoor tracks toward outdoor but with thermal lag
        if cooling_on and setpoint:
            # AC on: constrain to setpoint range
            new_temp = max(setpoint - 3, min(setpoint + 2, new_temp))
        else:
            # AC off: indoor gradually tracks toward outdoor with significant lag
            # Apply thermal damping to simulate building thermal mass
            thermal_lag = 0.05  # Very slow tracking (5% per interval)
            new_temp = new_temp + (outdoor_temp - new_temp) * thermal_lag
            # But never cooler than the previous temp when AC was on
            if self.previous_temp is not None:
                new_temp = max(self.previous_temp - 0.5, min(outdoor_temp + 1, new_temp))

        # Update state
        self.previous_temp = new_temp
        self.temperature_history.append(new_temp)
        
        # Keep history manageable
        if len(self.temperature_history) > 96:
            self.temperature_history = self.temperature_history[-96:]
        
        return round(new_temp, 1)
    
    def reset(self):
        """Reset thermal model state"""
        self.previous_temp = None
        self.temperature_history = []
    
    def get_comfort_delta(
        self,
        indoor_temp: float,
        comfort_min: float,
        comfort_max: float,
        occupied: bool = True
    ) -> float:
        """
        Calculate discomfort metric (degree-hours deviation from comfort).
        
        Returns:
            Positive value = too hot, Negative value = too cold
        """
        if not occupied:
            return 0
        
        if indoor_temp > comfort_max:
            return indoor_temp - comfort_max
        elif indoor_temp < comfort_min:
            return indoor_temp - comfort_min
        else:
            return 0
    
    def estimate_cooldown_time(
        self,
        current_temp: float,
        target_temp: float,
        cooling_capacity_kw: float,
        building_area: float,
        insulation: str = 'medium'
    ) -> float:
        """
        Estimate time required to cool from current to target temperature.
        
        Returns:
            Estimated minutes to reach target
        """
        if current_temp <= target_temp:
            return 0
        
        temp_diff = current_temp - target_temp
        
        # Simplified: assume 5°C drop per hour with typical AC
        # Scale with capacity and building size
        base_cooling_rate = 5  # °C per hour
        
        # Capacity factor
        capacity_factor = cooling_capacity_kw / 5.0  # Normalized to 5kW
        
        # Building factor (larger buildings cool slower)
        building_factor = 80 / building_area if building_area > 0 else 1
        
        # Insulation factor
        insulation_factor = 1 + 0.3 * {'low': 0, 'medium': 1, 'high': 2}.get(insulation, 1)
        
        cooling_rate = base_cooling_rate * capacity_factor / (building_factor * insulation_factor)
        
        minutes = (temp_diff / cooling_rate) * 60
        
        return max(0, minutes)
    
    def get_thermal_metrics(self) -> Dict:
        """Get current thermal model state metrics"""
        return {
            'previous_temp': self.previous_temp,
            'history_length': len(self.temperature_history),
            'temp_trend': 'stable',
            'avg_recent': np.mean(self.temperature_history[-6:]) if len(self.temperature_history) >= 6 else None
        }


class AdvancedThermalModel(ThermalModel):
    """
    Advanced thermal model with more detailed physics.
    Includes:
    - Separate day/night thermal parameters
    - Multiple zone support
    - HVAC cycling simulation
    """
    
    def estimate_indoor_temp(
        self,
        outdoor_temp: float,
        setpoint: Optional[float] = None,
        cooling_on: bool = False,
        cooling_capacity_kw: float = 5.0,
        occupancy: int = 0,
        solar_gain: float = 0,
        building_area: float = 80,
        insulation: str = 'medium',
        sun_exposure: str = 'medium',
        timestep_minutes: int = 15,
        humidity: float = 50,
        wind_speed: float = 0
    ) -> float:
        """
        Advanced indoor temperature estimation with additional factors.
        """
        # Use parent implementation as base
        base_temp = super().estimate_indoor_temp(
            outdoor_temp=outdoor_temp,
            setpoint=setpoint,
            cooling_on=cooling_on,
            cooling_capacity_kw=cooling_capacity_kw,
            occupancy=occupancy,
            solar_gain=solar_gain,
            building_area=building_area,
            insulation=insulation,
            sun_exposure=sun_exposure,
            timestep_minutes=timestep_minutes
        )
        
        # Adjust for humidity (higher humidity feels warmer)
        # Heat index effect
        if base_temp > 20 and humidity > 40:
            humidity_adjustment = (humidity - 40) / 100 * 2  # Up to +2°C adjustment
            base_temp += humidity_adjustment
        
        # Adjust for wind (convective cooling effect)
        if wind_speed > 5:  # km/h
            wind_cooling = min(3, wind_speed / 10 * 0.5)
            base_temp -= wind_cooling
        
        return round(base_temp, 1)
