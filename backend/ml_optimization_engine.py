"""
ML-Enhanced Optimization Engine
Integrates ML models (solar forecast, thermal ANN) with rule-based optimization
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import os

from optimization_engine import OptimizationEngine, CandidateAction
from solar_battery import SolarBatteryModule
from data_models import *


class MLOptimizedEngine:
    """
    Hybrid optimization engine that uses ML models to improve predictions.
    
    Enhancements:
    1. ML-based solar generation forecasting (with look-ahead)
    2. ML-based indoor temperature prediction (more accurate)
    3. Better pre-cooling decisions based on predicted weather
    """
    
    def __init__(self, use_ml: bool = True, model_dir: str = None):
        self.base_engine = OptimizationEngine()
        self.use_ml = use_ml
        
        # ML models
        self.solar_model = None
        self.thermal_model = None
        
        # Model directory
        if model_dir is None:
            model_dir = os.path.join(os.path.dirname(__file__), 'ml_models')
        
        self.model_dir = model_dir
        
        if use_ml:
            self._load_ml_models()
    
    def _load_ml_models(self):
        """Load trained ML models"""
        try:
            from ml_models import SolarForecastModel, ThermalANNModel
            
            solar_path = os.path.join(self.model_dir, 'solar_model.pkl')
            thermal_path = os.path.join(self.model_dir, 'thermal_model.pt')
            
            if os.path.exists(solar_path):
                self.solar_model = SolarForecastModel(model_path=solar_path)
                print("ML: Solar forecast model loaded")
            
            if os.path.exists(thermal_path):
                self.thermal_model = ThermalANNModel(model_path=thermal_path)
                print("ML: Thermal ANN model loaded")
            
            if not self.solar_model or not self.thermal_model:
                print("ML: No trained models found, will use physics fallback")
                
        except ImportError as e:
            print(f"ML models not available: {e}")
            self.use_ml = False
    
    def optimize(
        self,
        scenario: ScenarioInput,
        config: Optional[OptimizationConfig] = None
    ) -> RunResult:
        """
        Run ML-enhanced optimization.
        Uses base engine but with ML-improved predictions.
        """
        
        # Pre-compute ML predictions for look-ahead
        ml_predictions = {}
        
        if self.use_ml and self.solar_model:
            ml_predictions['solar_forecast'] = self._forecast_solar(scenario)
        
        if self.use_ml and self.thermal_model:
            ml_predictions['thermal'] = self._init_thermal_model(scenario)
        
        # Store ML predictions in engine context
        self._ml_context = ml_predictions
        
        # Run base optimization with ML enhancements
        return self._ml_optimize(scenario, config, ml_predictions)
    
    def _forecast_solar(self, scenario: ScenarioInput) -> Dict[int, dict]:
        """Pre-compute solar generation forecasts for all intervals"""
        forecasts = {}
        
        for i, interval in enumerate(scenario.interval_inputs):
            timestamp = interval.timestamp_local
            
            # Use ML model if available
            if self.solar_model:
                solar_capacity = scenario.energy_assets.solar_capacity_kw
                result = self.solar_model.predict(
                    irradiance=interval.solar_irradiance_w_m2,
                    temp=interval.temperature_c,
                    humidity=interval.relative_humidity_pct,
                    timestamp=timestamp,
                    solar_capacity_kw=solar_capacity,
                    interval_hours=0.25
                )
                forecasts[i] = result
            else:
                # Fallback to simple calculation
                solar_capacity = scenario.energy_assets.solar_capacity_kw
                efficiency = 0.18
                solar_kwh = interval.solar_irradiance_w_m2 / 1000 * solar_capacity * efficiency * 0.25
                forecasts[i] = {
                    'solar_kwh': max(0, solar_kwh),
                    'confidence': 0.6,
                    'peak_expected': interval.solar_irradiance_w_m2 > 600
                }
        
        return forecasts
    
    def _init_thermal_model(self, scenario: ScenarioInput) -> 'ThermalANNModel':
        """Initialize thermal model for this scenario"""
        return self.thermal_model
    
    def _ml_optimize(
        self,
        scenario: ScenarioInput,
        config: Optional[OptimizationConfig],
        ml_predictions: Dict
    ) -> RunResult:
        """
        ML-enhanced optimization loop.
        Overrides thermal estimation and solar forecasting.
        """
        
        if config is None:
            config = OptimizationConfig()
        
        # Get weights
        w_cost = config.objective_weights.get('cost', 0.45)
        w_comfort = config.objective_weights.get('comfort', 0.20)
        w_emissions = config.objective_weights.get('emissions', 0.10)
        w_peak = config.objective_weights.get('peak_demand', 0.25)
        
        # Get appliances
        ac = next((a for a in scenario.appliances if a.appliance_type == ApplianceType.AC), None)
        fan = next((a for a in scenario.appliances if a.appliance_type == ApplianceType.FAN), None)
        
        # Initialize modules
        from solar_battery import SolarBatteryModule
        solar_battery = SolarBatteryModule(scenario.energy_assets)
        
        # Calculate baseline
        baseline_result = self.base_engine.baseline.calculate(scenario)
        
        # Reset thermal model
        self.base_engine.thermal.reset()
        
        # Get ML solar forecasts
        solar_forecasts = ml_predictions.get('solar_forecast', {})
        ml_thermal = ml_predictions.get('thermal')
        
        # Track thermal history for ML model
        thermal_history = []
        
        # Optimization loop
        optimized_intervals = []
        daily_summaries = []
        constraint_violations = 0
        running_peak_kw = 0
        
        intervals_by_day: Dict[date, List[IntervalOutput]] = {}
        
        # Estimate score bounds for proper normalization
        self.base_engine._estimate_score_bounds(scenario, baseline_result)

        # Ensure max_cost is reasonable (at least 100 PKR)
        if self.base_engine.max_cost < 100:
            self.base_engine.max_cost = baseline_result.total_cost_pkr / len(scenario.interval_inputs) * 4
        
        for i, interval in enumerate(scenario.interval_inputs):
            # Get ML-enhanced solar prediction
            solar_pred = solar_forecasts.get(i, {})
            ml_solar_kwh = solar_pred.get('solar_kwh', 0)
            
            # Get previous indoor temp for thermal model
            prev_indoor = thermal_history[-1] if thermal_history else None
            
            # Generate candidates with ML-enhanced thermal
            candidates = self._generate_ml_candidates(
                interval_idx=i,
                interval=interval,
                scenario=scenario,
                config=config,
                ac=ac,
                fan=fan,
                solar_battery=solar_battery,
                ml_solar_kwh=ml_solar_kwh,
                ml_thermal=ml_thermal,
                prev_indoor=prev_indoor,
                running_peak_kw=running_peak_kw
            )
            
            # Select best candidate
            best_candidate = self.base_engine._select_best_candidate(candidates, config)
            
            # Build interval output
            opt_result = self.base_engine._build_interval_output(
                interval=interval,
                candidate=best_candidate,
                scenario=scenario,
                config=config,
                solar_battery=solar_battery
            )
            
            optimized_intervals.append(opt_result)
            
            # Track thermal history
            thermal_history.append(best_candidate.estimated_indoor_temp)
            if len(thermal_history) > 96:
                thermal_history = thermal_history[-96:]
            
            # Update running peak
            power_kw = (best_candidate.ac_units * (ac.rated_power_kw if ac else 0) +
                       best_candidate.fan_units * (fan.rated_power_kw if fan else 0))
            running_peak_kw = max(running_peak_kw, power_kw)
            
            # Track by day
            day = interval.timestamp_local.date()
            if day not in intervals_by_day:
                intervals_by_day[day] = []
            intervals_by_day[day].append(opt_result)
            
            constraint_violations += opt_result.constraint_violation_count
        
        # Calculate summaries
        for day, day_intervals in sorted(intervals_by_day.items()):
            summary = self.base_engine._calculate_daily_summary(day, day_intervals)
            daily_summaries.append(summary)
        
        overall_summary = self.base_engine._calculate_overall_summary(
            scenario.scenario_id,
            optimized_intervals,
            baseline_result
        )
        
        return RunResult(
            scenario_id=scenario.scenario_id,
            profile=scenario.profile,
            intervals=optimized_intervals,
            daily_summaries=daily_summaries,
            summary=overall_summary,
            baseline_summary={
                'total_energy_kwh': baseline_result.total_energy_kwh,
                'total_cost_pkr': baseline_result.total_cost_pkr,
                'total_emissions_kgco2e': baseline_result.total_emissions_kgco2e,
                'peak_demand_kw': baseline_result.peak_demand_kw,
                'comfort_compliance_pct': baseline_result.comfort_compliance_pct
            },
            constraints_satisfied=constraint_violations == 0
        )
    
    def _generate_ml_candidates(
        self,
        interval_idx: int,
        interval: IntervalInput,
        scenario: ScenarioInput,
        config: OptimizationConfig,
        ac: Optional[Appliance],
        fan: Optional[Appliance],
        solar_battery: SolarBatteryModule,
        ml_solar_kwh: float,
        ml_thermal,
        prev_indoor: Optional[float],
        running_peak_kw: float
    ) -> List[CandidateAction]:
        """Generate candidates with ML-enhanced evaluation"""
        
        hour = interval.timestamp_local.hour + interval.timestamp_local.minute / 60
        is_occupied = interval.occupancy_count > 0
        tariff = interval.tariff_pkr_per_kwh
        is_peak_tariff = interval.tariff_type == TariffType.PEAK or tariff >= 40
        is_cheap_tariff = tariff <= 20
        grid_available = interval.grid_available
        outdoor_temp = interval.temperature_c
        comfort_min = scenario.profile.comfort_min_c
        comfort_max = scenario.profile.comfort_max_c
        
        max_ac = ac.quantity if ac else 0
        max_fan = fan.quantity if fan else 0
        
        candidates = []
        
        # Generate candidate grid
        for ac_units in range(max_ac + 1):
            for fan_units in range(max_fan + 1):
                if ac_units == 0 and fan_units == 0:
                    continue
                
                # Setpoint options
                setpoints = [20, 22, 24, 26, 28] if is_occupied else [26, 28, 30]
                
                for setpoint in setpoints:
                    if ac and (setpoint < ac.min_setpoint_c or setpoint > ac.max_setpoint_c):
                        continue
                    
                    candidate = self._evaluate_ml_candidate(
                        ac_units=ac_units,
                        fan_units=fan_units,
                        setpoint=setpoint,
                        interval=interval,
                        scenario=scenario,
                        config=config,
                        ac=ac,
                        fan=fan,
                        solar_battery=solar_battery,
                        ml_solar_kwh=ml_solar_kwh,
                        ml_thermal=ml_thermal,
                        prev_indoor=prev_indoor,
                        running_peak_kw=running_peak_kw,
                        grid_available=grid_available,
                        is_occupied=is_occupied
                    )
                    candidates.append(candidate)
        
        # Off candidate
        off_candidate = self._evaluate_ml_candidate(
            ac_units=0, fan_units=0, setpoint=comfort_max + 2,
            interval=interval, scenario=scenario, config=config,
            ac=ac, fan=fan, solar_battery=solar_battery,
            ml_solar_kwh=ml_solar_kwh, ml_thermal=ml_thermal,
            prev_indoor=prev_indoor, running_peak_kw=running_peak_kw,
            grid_available=grid_available, is_occupied=is_occupied
        )
        candidates.append(off_candidate)
        
        # Peak avoidance candidates
        if is_peak_tariff and is_occupied and max_ac > 0:
            for sp in [comfort_max, 28, 30]:
                if ac and comfort_min <= sp <= ac.max_setpoint_c:
                    candidate = self._evaluate_ml_candidate(
                        ac_units=1, fan_units=0, setpoint=sp,
                        interval=interval, scenario=scenario, config=config,
                        ac=ac, fan=fan, solar_battery=solar_battery,
                        ml_solar_kwh=ml_solar_kwh, ml_thermal=ml_thermal,
                        prev_indoor=prev_indoor, running_peak_kw=running_peak_kw,
                        grid_available=grid_available, is_occupied=True
                    )
                    candidates.append(candidate)
        
        # Solar optimization candidate
        if ml_solar_kwh > 0.1 and is_occupied:
            candidate = self._evaluate_ml_candidate(
                ac_units=min(1, max_ac), fan_units=max_fan,
                setpoint=comfort_min,
                interval=interval, scenario=scenario, config=config,
                ac=ac, fan=fan, solar_battery=solar_battery,
                ml_solar_kwh=ml_solar_kwh, ml_thermal=ml_thermal,
                prev_indoor=prev_indoor, running_peak_kw=running_peak_kw,
                grid_available=grid_available, is_occupied=True
            )
            candidates.append(candidate)
        
        # Pre-cooling candidate
        if is_cheap_tariff and is_occupied and max_ac > 0:
            next_is_peak = False
            for j in range(1, 9):
                look_idx = interval_idx + j
                if look_idx < len(scenario.interval_inputs):
                    if scenario.interval_inputs[look_idx].tariff_pkr_per_kwh >= 40:
                        next_is_peak = True
                        break
            
            if next_is_peak:
                candidate = self._evaluate_ml_candidate(
                    ac_units=max_ac, fan_units=max_fan,
                    setpoint=comfort_min,
                    interval=interval, scenario=scenario, config=config,
                    ac=ac, fan=fan, solar_battery=solar_battery,
                    ml_solar_kwh=ml_solar_kwh, ml_thermal=ml_thermal,
                    prev_indoor=prev_indoor, running_peak_kw=running_peak_kw,
                    grid_available=grid_available, is_occupied=True
                )
                candidates.append(candidate)
        
        return candidates
    
    def _evaluate_ml_candidate(
        self,
        ac_units: int,
        fan_units: int,
        setpoint: float,
        interval: IntervalInput,
        scenario: ScenarioInput,
        config: OptimizationConfig,
        ac: Optional[Appliance],
        fan: Optional[Appliance],
        solar_battery: SolarBatteryModule,
        ml_solar_kwh: float,
        ml_thermal,
        prev_indoor: Optional[float],
        running_peak_kw: float,
        grid_available: bool,
        is_occupied: bool
    ) -> CandidateAction:
        """Evaluate candidate using ML-enhanced predictions"""
        
        hour = interval.timestamp_local.hour + interval.timestamp_local.minute / 60
        tariff = interval.tariff_pkr_per_kwh
        is_peak_tariff = interval.tariff_type == TariffType.PEAK or tariff >= 40
        outdoor_temp = interval.temperature_c
        comfort_min = scenario.profile.comfort_min_c
        comfort_max = scenario.profile.comfort_max_c
        solar_gain = interval.solar_irradiance_w_m2
        
        # Energy calculation
        ac_power = (ac.rated_power_kw * ac_units) if ac else 0
        fan_power = (fan.rated_power_kw * fan_units) if fan else 0
        cooling_load = (ac_power + fan_power) * 0.25
        total_load = cooling_load + interval.non_cooling_load_kw * 0.25
        
        # ML-enhanced indoor temperature
        if ml_thermal and self.use_ml:
            ml_result = ml_thermal.predict(
                outdoor_temp=outdoor_temp,
                setpoint=setpoint if ac_units > 0 else None,
                cooling_on=ac_units > 0,
                cooling_capacity_kw=(ac.cooling_capacity_kw * ac_units) if ac else 0,
                occupancy=interval.occupancy_count,
                solar_gain=solar_gain,
                building_area=scenario.profile.area_m2,
                insulation=scenario.profile.insulation_level,
                sun_exposure=scenario.profile.sun_exposure,
                hour=hour,
                prev_indoor_temp=prev_indoor
            )
            estimated_indoor = ml_result['indoor_temp']
        else:
            # Fallback to physics model
            estimated_indoor = self.base_engine.thermal.estimate_indoor_temp(
                outdoor_temp=outdoor_temp,
                setpoint=setpoint if ac_units > 0 else None,
                cooling_on=ac_units > 0,
                cooling_capacity_kw=(ac.cooling_capacity_kw * ac_units) if ac else 0,
                occupancy=interval.occupancy_count,
                solar_gain=solar_gain,
                building_area=scenario.profile.area_m2,
                insulation=scenario.profile.insulation_level,
                sun_exposure=scenario.profile.sun_exposure
            )
        
        # Energy flow with ML solar forecast
        energy_flow = solar_battery.optimize_energy_flow(
            load_kwh=total_load,
            solar_available_kwh=ml_solar_kwh,
            tariff_pkr=tariff,
            tariff_type=interval.tariff_type.value,
            is_peak=is_peak_tariff,
            grid_available=grid_available
        )
        
        # Scores
        cost_score = self.base_engine._score_cost(
            energy_flow['grid_drawn_kwh'], tariff, is_peak_tariff
        )
        comfort_score = self.base_engine._score_comfort(
            estimated_indoor, is_occupied, comfort_min, comfort_max
        )
        emissions_score = self.base_engine._score_emissions(
            energy_flow['grid_drawn_kwh'], interval.grid_carbon_kgco2_per_kwh
        )
        peak_score = self.base_engine._score_peak(
            ac_power + fan_power, running_peak_kw
        )

        # Balanced weights for energy savings without negative values
        w_cost = config.objective_weights.get('cost', 0.40)
        w_comfort = config.objective_weights.get('comfort', 0.35)
        w_emissions = config.objective_weights.get('emissions', 0.10)
        w_peak = config.objective_weights.get('peak_demand', 0.15)
        
        total_score = (
            w_cost * cost_score +
            w_comfort * comfort_score +
            w_emissions * emissions_score +
            w_peak * peak_score
        )
        
        # Reason code
        if ml_solar_kwh > 0.5:
            reason = ReasonCode.SOLAR_AVAILABLE
            explanation = "ML forecast: High solar generation expected"
        elif is_peak_tariff:
            reason = ReasonCode.PEAK_TARIFF
            explanation = "Peak tariff period - minimizing grid usage"
        else:
            reason = ReasonCode.COMFORT_PRIORITY
            explanation = "Normal operation - maintaining comfort"
        
        # Constraints
        violations = self.base_engine._check_constraints(
            ac_units, fan_units, setpoint, energy_flow,
            estimated_indoor, scenario, grid_available,
            comfort_min, comfort_max, is_occupied
        )
        
        comfort_status = self.base_engine._get_comfort_status(
            estimated_indoor, is_occupied, comfort_min, comfort_max
        )
        
        return CandidateAction(
            ac_units=ac_units,
            fan_units=fan_units,
            setpoint_c=setpoint,
            reason_code=reason,
            explanation=explanation,
            grid_energy_kwh=round(energy_flow['grid_drawn_kwh'], 4),
            solar_used_kwh=round(energy_flow['solar_used_kwh'], 4),
            battery_charge_kwh=round(energy_flow['battery_charge_kwh'], 4),
            battery_discharge_kwh=round(energy_flow['battery_discharge_kwh'], 4),
            cooling_load_kwh=round(cooling_load, 4),
            estimated_indoor_temp=estimated_indoor,
            comfort_status=comfort_status,
            cost_score=cost_score,
            comfort_score=comfort_score,
            emissions_score=emissions_score,
            peak_score=peak_score,
            total_score=total_score,
            violations=violations
        )


# For backwards compatibility
IntervalInput = IntervalInput
ApplianceType = ApplianceType
TariffType = TariffType
