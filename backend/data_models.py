"""
CoolShift Data Models - Pydantic schemas for all inputs/outputs
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, date
from enum import Enum
import numpy as np

# ============ ENUMS ============
class BuildingType(str, Enum):
    HOUSEHOLD = "household"
    SCHOOL = "school"
    OFFICE = "office"
    CLINIC = "clinic"
    RETAIL = "retail"
    HOSTEL = "hostel"
    COMMUNITY = "community"

class ApplianceType(str, Enum):
    AC = "ac"
    FAN = "fan"
    EVAPORATIVE_COOLER = "evaporative_cooler"
    HEAT_PUMP = "heat_pump"

class ComfortStatus(str, Enum):
    WITHIN_RANGE = "within_range"
    WARNING = "warning"
    UNSAFE = "unsafe"
    INFEASIBLE = "infeasible"

class TariffType(str, Enum):
    FLAT = "flat"
    PEAK = "peak"
    OFF_PEAK = "off_peak"
    DEMAND_CHARGE = "demand_charge"

class GridStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"

class ReasonCode(str, Enum):
    OCCUPIED_COMFORT = "OCCUPIED_COMFORT"
    HEAT_RISK = "HEAT_RISK"
    SOLAR_AVAILABLE = "SOLAR_AVAILABLE"
    PEAK_TARIFF = "PEAK_TARIFF"
    OFF_PEAK_CHARGING = "OFF_PEAK_CHARGING"
    OFF_PEAK_COOLING = "OFF_PEAK_COOLING"
    PRE_COOLING = "PRE_COOLING"
    GRID_UNAVAILABLE = "GRID_UNAVAILABLE"
    BATTERY_DISCHARGE = "BATTERY_DISCHARGE"
    BATTERY_LOW = "BATTERY_LOW"
    MAINTENANCE = "MAINTENANCE"
    VACANT = "VACANT"
    COMFORT_OPTIMIZED = "COMFORT_OPTIMIZED"
    COST_OPTIMIZED = "COST_OPTIMIZED"
    BALANCED = "BALANCED"
    COMFORT_PRIORITY = "COMFORT_PRIORITY"
    ML_PREDICTED = "ML_PREDICTED"

class OptimizationMethod(str, Enum):
    CANDIDATE_SCORING = "candidate_scoring"
    ORTOOLS_MILP = "ortools_milp"

# ============ INPUT MODELS ============
class EnergyAssets(BaseModel):
    solar_capacity_kw: float = Field(..., ge=0, description="Solar panel capacity in kW")
    solar_conversion_efficiency: float = Field(default=0.18, ge=0, le=1, description="Solar panel efficiency")
    battery_capacity_kwh: float = Field(default=0, ge=0, description="Battery capacity in kWh")
    initial_soc_kwh: float = Field(default=0, ge=0, description="Initial battery state of charge")
    minimum_reserve_kwh: float = Field(default=0, ge=0, description="Minimum battery reserve")
    max_charge_kw: float = Field(default=0, ge=0, description="Maximum charging rate")
    max_discharge_kw: float = Field(default=0, ge=0, description="Maximum discharging rate")
    charge_efficiency: float = Field(default=0.95, ge=0, le=1)
    discharge_efficiency: float = Field(default=0.95, ge=0, le=1)

class Appliance(BaseModel):
    appliance_id: str
    zone_id: str
    appliance_type: ApplianceType
    quantity: int = Field(..., ge=0)
    rated_power_kw: float = Field(..., gt=0, description="Power per unit in kW")
    cooling_capacity_kw: float = Field(..., gt=0, description="Cooling capacity per unit")
    efficiency_label: str = Field(default="A")
    min_runtime_minutes: int = Field(default=15, ge=0)
    min_setpoint_c: float = Field(default=18)
    max_setpoint_c: float = Field(default=30)

class ScenarioProfile(BaseModel):
    scenario_id: str
    name: str
    timezone: str = Field(default="Asia/Karachi")
    building_type: BuildingType
    area_m2: float = Field(..., gt=0)
    room_count: int = Field(default=1, ge=1)
    max_occupancy: int = Field(default=4, ge=1)
    insulation_level: str = Field(default="medium")  # low, medium, high
    sun_exposure: str = Field(default="medium")  # low, medium, high
    comfort_min_c: float = Field(default=22, description="Minimum comfortable temperature")
    comfort_max_c: float = Field(default=26, description="Maximum comfortable temperature")
    vulnerable_occupants: bool = Field(default=False)
    budget_pkr_per_day: float = Field(default=500, ge=0)
    maximum_grid_demand_kw: float = Field(default=10, gt=0)

class IntervalInput(BaseModel):
    timestamp_local: datetime
    temperature_c: float = Field(..., ge=-20, le=60)
    relative_humidity_pct: float = Field(..., ge=0, le=100)
    heat_index_c: Optional[float] = None
    solar_irradiance_w_m2: float = Field(default=0, ge=0)
    occupancy_count: int = Field(default=0, ge=0)
    grid_available: bool = Field(default=True)
    tariff_type: TariffType = Field(default=TariffType.FLAT)
    tariff_pkr_per_kwh: float = Field(..., ge=0)
    grid_carbon_kgco2_per_kwh: float = Field(default=0.5, ge=0)
    non_cooling_load_kw: float = Field(default=0, ge=0)
    
    @field_validator('heat_index_c', mode='before')
    @classmethod
    def calculate_heat_index(cls, v, info):
        if v is None or v <= 0:
            temp = info.data.get('temperature_c', 25)
            humidity = info.data.get('relative_humidity_pct', 50)
            return cls._heat_index(temp, humidity)
        return v
    
    @staticmethod
    def _heat_index(temp_c: float, humidity: float) -> float:
        """Calculate heat index using simplified formula"""
        if temp_c < 27:
            return temp_c
        t = temp_c * 9/5 + 32
        rh = humidity
        hi = -42.379 + 2.04901523*t + 10.14333127*rh - 0.22475541*t*rh - 6.83783e-3*t*t - 5.481717e-2*rh*rh + 1.22874e-3*t*t*rh + 8.5282e-4*t*rh*rh - 1.99e-6*t*t*rh*rh
        return (hi - 32) * 5/9

class BaselineSchedule(BaseModel):
    timestamp_local: datetime
    baseline_ac_units_on: int = Field(default=0, ge=0)
    baseline_ac_setpoint_c: float = Field(default=24)
    baseline_fan_units_on: int = Field(default=0, ge=0)
    baseline_other_cooling_kw: float = Field(default=0, ge=0)

class ScenarioInput(BaseModel):
    scenario_id: str
    profile: ScenarioProfile
    appliances: List[Appliance]
    interval_inputs: List[IntervalInput]
    energy_assets: EnergyAssets
    baseline_schedule: Optional[List[BaselineSchedule]] = None

# ============ OPTIMIZATION CONFIG ============
class OptimizationConfig(BaseModel):
    objective_weights: Dict[str, float] = Field(default={
        "cost": 0.35,
        "comfort": 0.30,
        "emissions": 0.20,
        "peak_demand": 0.15
    })
    max_ac_units: Optional[int] = None
    comfort_priority: Literal["comfort", "cost", "balanced"] = "balanced"
    allow_battery_override: bool = Field(default=False)
    peak_tariff_threshold_pkr: float = Field(default=50)
    solar_priority: bool = Field(default=True)
    optimization_method: OptimizationMethod = Field(default=OptimizationMethod.CANDIDATE_SCORING)

# ============ OUTPUT MODELS ============
class IntervalOutput(BaseModel):
    timestamp_local: datetime
    # Input data fields (for frontend display)
    temperature_c: float = Field(default=35, description="Outdoor temperature input")
    solar_irradiance_w_m2: float = Field(default=0, description="Solar irradiance input")
    occupancy_count: int = Field(default=0, description="Occupancy input")
    tariff_pkr_per_kwh: float = Field(default=25, description="Tariff input")
    tariff_type: str = Field(default="flat", description="Tariff type input")
    grid_available: bool = Field(default=True, description="Grid availability input")
    # Optimization output fields
    recommended_ac_units_on: int = Field(ge=0)
    recommended_ac_setpoint_c: Optional[float] = None
    recommended_fan_units_on: int = Field(default=0, ge=0)
    grid_energy_kwh: float = Field(ge=0)
    solar_energy_used_kwh: float = Field(ge=0)
    battery_charge_kwh: float = Field(ge=0)
    battery_discharge_kwh: float = Field(ge=0)
    battery_soc_kwh: float = Field(ge=0)
    cooling_energy_kwh: float = Field(ge=0)
    estimated_indoor_temp_c: float
    comfort_status: ComfortStatus
    interval_cost_pkr: float = Field(ge=0)
    interval_emissions_kgco2e: float = Field(ge=0)
    reason_code: ReasonCode
    explanation: str
    constraint_violation_count: int = Field(default=0)
    constraint_violations: List[str] = Field(default_factory=list)

class DailySummary(BaseModel):
    date: date
    day_name: str = ""
    total_energy_kwh: float
    total_cost_pkr: float
    total_emissions_kgco2e: float
    peak_demand_kw: float
    peak_temp: float = 0
    comfort_compliance_pct: float
    unsafe_hours: float
    solar_utilization_pct: float
    solar_used_kwh: float = 0
    battery_soc_pct: float = 0
    battery_cycles: float

class RunSummary(BaseModel):
    scenario_id: str
    run_id: str
    start_timestamp: datetime
    end_timestamp: datetime
    total_intervals: int
    total_days: float
    total_energy_kwh: float
    total_cost_pkr: float
    total_emissions_kgco2e: float
    peak_demand_kw: float
    comfort_compliance_pct: float
    solar_utilization_pct: float
    battery_utilization_pct: float
    total_savings_pkr: float = 0
    total_savings_kwh: float = 0
    emission_reduction_kgco2e: float = 0

class RunResult(BaseModel):
    run_id: str = ""
    scenario_id: str
    profile: ScenarioProfile
    intervals: List[IntervalOutput]
    daily_summaries: List[DailySummary]
    summary: RunSummary
    baseline_summary: Optional[Dict[str, float]] = None
    constraints_satisfied: bool = True
    algorithm_version: str = "1.0.0"
    calculation_timestamp: datetime = Field(default_factory=datetime.now)

class ScenarioInfo(BaseModel):
    id: str
    name: str
    type: str
    days: int

class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    missing_fields: List[str] = Field(default_factory=list)
    outlier_count: int = 0

class CustomScenarioConfig(BaseModel):
    scenario_name: str
    building_type: BuildingType
    area_m2: float = 80
    days: int = 7
    has_solar: bool = False
    has_battery: bool = False
    solar_capacity_kw: float = 0
    battery_capacity_kwh: float = 0
    location_lat: float = 24.8607  # Karachi
    location_lon: float = 67.0011
    tariff_scenario: Literal["residential", "commercial", "industrial"] = "residential"

class ComparisonResult(BaseModel):
    baseline: Dict[str, float]
    optimized: Dict[str, float]
    savings: Dict[str, float]
