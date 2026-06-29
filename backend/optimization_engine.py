"""
Optimization Engine - Candidate-Evaluation Based Cooling Schedule Optimizer
Multi-objective optimization with constraint satisfaction
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from data_models import *
from baseline_engine import BaselineEngine
from thermal_model import ThermalModel
from solar_battery import SolarBatteryModule, EnergyBalanceCalculator


@dataclass
class CandidateAction:
    """A feasible cooling action candidate with its evaluation scores"""
    ac_units: int
    fan_units: int
    setpoint_c: float
    reason_code: ReasonCode
    explanation: str

    # Energy metrics
    grid_energy_kwh: float
    solar_used_kwh: float
    battery_charge_kwh: float
    battery_discharge_kwh: float
    cooling_load_kwh: float

    # State estimates
    estimated_indoor_temp: float
    comfort_status: ComfortStatus

    # Objective scores (lower is better)
    cost_score: float      # Normalized 0-1
    comfort_score: float   # Normalized 0-1
    emissions_score: float # Normalized 0-1
    peak_score: float      # Normalized 0-1
    total_score: float     # Weighted sum

    # Constraints
    violations: List[str]

    def is_feasible(self) -> bool:
        """Check if candidate satisfies all hard constraints"""
        return len(self.violations) == 0


class OptimizationEngine:
    """
    Candidate-Evaluation Multi-Objective Optimization Engine.

    For each interval:
    1. Generate N candidate cooling actions
    2. Evaluate each candidate on weighted objectives
    3. Filter infeasible candidates (hard constraints)
    4. Select minimum-score feasible candidate

    Objectives (weighted):
    - Minimize electricity cost
    - Maintain comfort during occupied hours
    - Minimize carbon emissions
    - Reduce peak demand
    """

    def __init__(self):
        self.baseline = BaselineEngine()
        self.thermal = ThermalModel()
        self.interval_hours = 0.25  # 15 minutes

        # Setpoint candidates
        self.setpoint_candidates = [20, 22, 24, 26, 28]

        # Score bounds for normalization (updated during optimization)
        self.max_cost = 100
        self.max_peak_kw = 10
        self.max_emissions = 50

    def optimize(
        self,
        scenario: ScenarioInput,
        config: Optional[OptimizationConfig] = None
    ) -> RunResult:
        """
        Generate optimized cooling schedule using candidate evaluation.

        Args:
            scenario: Input scenario with all data
            config: Optimization configuration

        Returns:
            RunResult with optimized intervals and summaries
        """

        if config is None:
            config = OptimizationConfig()

        # Get weights - MORE aggressive on cost/peak
        w_cost = config.objective_weights.get('cost', 0.45)
        w_comfort = config.objective_weights.get('comfort', 0.20)
        w_emissions = config.objective_weights.get('emissions', 0.10)
        w_peak = config.objective_weights.get('peak_demand', 0.25)

        # Get appliances
        ac = next((a for a in scenario.appliances if a.appliance_type == ApplianceType.AC), None)
        fan = next((a for a in scenario.appliances if a.appliance_type == ApplianceType.FAN), None)

        # Initialize solar/battery module
        solar_battery = SolarBatteryModule(scenario.energy_assets)

        # Calculate baseline for comparison
        baseline_result = self.baseline.calculate(scenario)

        # Reset thermal model
        self.thermal.reset()

        # Optimization loop
        optimized_intervals = []
        daily_summaries = []
        constraint_violations = 0

        # Track running peak demand
        running_peak_kw = 0

        # Group intervals by day for daily summaries
        intervals_by_day: Dict[date, List[IntervalOutput]] = {}

        # First pass: estimate bounds for normalization
        self._estimate_score_bounds(scenario, baseline_result)

        for i, interval in enumerate(scenario.interval_inputs):
            # Generate and evaluate candidates
            candidates = self._generate_candidates(
                interval_idx=i,
                interval=interval,
                scenario=scenario,
                config=config,
                ac=ac,
                fan=fan,
                solar_battery=solar_battery,
                running_peak_kw=running_peak_kw
            )

            # Select best feasible candidate
            best_candidate = self._select_best_candidate(candidates, config)

            # Build interval output
            opt_result = self._build_interval_output(
                interval=interval,
                candidate=best_candidate,
                scenario=scenario,
                config=config,
                solar_battery=solar_battery
            )

            optimized_intervals.append(opt_result)

            # Update running peak
            power_kw = (best_candidate.ac_units * (ac.rated_power_kw if ac else 0) +
                       best_candidate.fan_units * (fan.rated_power_kw if fan else 0))
            running_peak_kw = max(running_peak_kw, power_kw)

            # Track by day
            day = interval.timestamp_local.date()
            if day not in intervals_by_day:
                intervals_by_day[day] = []
            intervals_by_day[day].append(opt_result)

            # Count violations
            constraint_violations += opt_result.constraint_violation_count

        # Calculate daily summaries
        for day, day_intervals in sorted(intervals_by_day.items()):
            summary = self._calculate_daily_summary(day, day_intervals)
            daily_summaries.append(summary)

        # Calculate overall summary
        overall_summary = self._calculate_overall_summary(
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

    def _estimate_score_bounds(self, scenario: ScenarioInput, baseline_result) -> None:
        """Estimate bounds for score normalization from scenario data"""
        # Max cost: worst case = peak tariff all day
        max_tariff = max(i.tariff_pkr_per_kwh for i in scenario.interval_inputs)
        total_load = sum(i.non_cooling_load_kw * self.interval_hours for i in scenario.interval_inputs)
        self.max_cost = max_tariff * total_load * 2  # Safety margin

        # Max peak: sum of all cooling capacity
        ac = next((a for a in scenario.appliances if a.appliance_type == ApplianceType.AC), None)
        fan = next((a for a in scenario.appliances if a.appliance_type == ApplianceType.FAN), None)
        max_ac_power = (ac.rated_power_kw * ac.quantity) if ac else 0
        max_fan_power = (fan.rated_power_kw * fan.quantity) if fan else 0
        self.max_peak_kw = max_ac_power + max_fan_power

        # Max emissions
        max_carbon = max(i.grid_carbon_kgco2_per_kwh for i in scenario.interval_inputs)
        self.max_emissions = max_carbon * total_load * 2

    def _generate_candidates(
        self,
        interval_idx: int,
        interval: IntervalInput,
        scenario: ScenarioInput,
        config: OptimizationConfig,
        ac: Optional[Appliance],
        fan: Optional[Appliance],
        solar_battery: SolarBatteryModule,
        running_peak_kw: float
    ) -> List[CandidateAction]:
        """
        Generate candidate cooling actions for this interval.
        """

        hour = interval.timestamp_local.hour
        minute = interval.timestamp_local.minute
        is_occupied = interval.occupancy_count > 0
        occupancy = interval.occupancy_count
        outdoor_temp = interval.temperature_c
        tariff = interval.tariff_pkr_per_kwh
        is_peak_tariff = interval.tariff_type == TariffType.PEAK or tariff >= 40
        is_cheap_tariff = tariff <= 20
        grid_available = interval.grid_available

        # Building parameters
        comfort_min = scenario.profile.comfort_min_c
        comfort_max = scenario.profile.comfort_max_c

        # Solar availability
        solar_kwh = solar_battery.calculate_solar_generation(
            interval.solar_irradiance_w_m2,
            self.interval_hours
        )
        has_battery = scenario.energy_assets.battery_capacity_kwh > 0
        has_solar = scenario.energy_assets.solar_capacity_kw > 0

        # Determine feasible AC/Fan counts and setpoints based on conditions
        max_ac = ac.quantity if ac else 0
        max_fan = fan.quantity if fan else 0

        candidates = []

        # === SOLAR-FREE CANDIDATES ===
        # These evaluate what happens without solar contribution
        # We generate a grid of options

        # AC unit options: 0 to max
        for ac_units in range(max_ac + 1):
            # Fan options: 0 to max
            for fan_units in range(max_fan + 1):
                # Skip "all off" when occupied (will be flagged by high cost)
                if ac_units == 0 and fan_units == 0:
                    continue

                # Setpoint options based on occupancy and tariff
                if is_occupied:
                    # Occupied: vary setpoint from comfortable to warm
                    for setpoint in self.setpoint_candidates:
                        # Skip setpoints outside appliance limits
                        if ac and (setpoint < ac.min_setpoint_c or setpoint > ac.max_setpoint_c):
                            continue

                        candidate = self._evaluate_candidate(
                            ac_units=ac_units,
                            fan_units=fan_units,
                            setpoint=setpoint,
                            interval=interval,
                            scenario=scenario,
                            config=config,
                            ac=ac,
                            fan=fan,
                            solar_battery=solar_battery,
                            solar_kwh=solar_kwh,
                            running_peak_kw=running_peak_kw,
                            grid_available=grid_available,
                            is_occupied=True
                        )
                        candidates.append(candidate)
                else:
                    # Vacant: higher setpoints allowed
                    for setpoint in [26, 28, 30]:
                        if ac and (setpoint < ac.min_setpoint_c or setpoint > ac.max_setpoint_c):
                            continue

                        candidate = self._evaluate_candidate(
                            ac_units=ac_units,
                            fan_units=fan_units,
                            setpoint=setpoint,
                            interval=interval,
                            scenario=scenario,
                            config=config,
                            ac=ac,
                            fan=fan,
                            solar_battery=solar_battery,
                            solar_kwh=solar_kwh,
                            running_peak_kw=running_peak_kw,
                            grid_available=grid_available,
                            is_occupied=False
                        )
                        candidates.append(candidate)

        # === OFF CANDIDATE (always available) ===
        off_candidate = self._evaluate_candidate(
            ac_units=0,
            fan_units=0,
            setpoint=comfort_max + 2,
            interval=interval,
            scenario=scenario,
            config=config,
            ac=ac,
            fan=fan,
            solar_battery=solar_battery,
            solar_kwh=solar_kwh,
            running_peak_kw=running_peak_kw,
            grid_available=grid_available,
            is_occupied=is_occupied
        )
        candidates.append(off_candidate)

        # === PEAK TARIFF AVOIDANCE CANDIDATES ===
        # During peak tariff hours with occupied building, offer alternatives
        if is_peak_tariff and is_occupied and max_ac > 0:
            # Fan-only candidate (cheaper than AC)
            if max_fan > 0:
                fan_only_candidate = self._evaluate_candidate(
                    ac_units=0,
                    fan_units=max_fan,
                    setpoint=comfort_max + 2,
                    interval=interval,
                    scenario=scenario,
                    config=config,
                    ac=ac,
                    fan=fan,
                    solar_battery=solar_battery,
                    solar_kwh=solar_kwh,
                    running_peak_kw=running_peak_kw,
                    grid_available=grid_available,
                    is_occupied=True  # Still occupied, but accepting less cooling
                )
                candidates.append(fan_only_candidate)

            # High setpoint AC candidates (minimal cooling, just maintain)
            for sp in [comfort_max, 28, 30]:
                if ac and comfort_min <= sp <= ac.max_setpoint_c:
                    high_setpoint_candidate = self._evaluate_candidate(
                        ac_units=1,
                        fan_units=0,
                        setpoint=sp,
                        interval=interval,
                        scenario=scenario,
                        config=config,
                        ac=ac,
                        fan=fan,
                        solar_battery=solar_battery,
                        solar_kwh=solar_kwh,
                        running_peak_kw=running_peak_kw,
                        grid_available=grid_available,
                        is_occupied=True
                    )
                    candidates.append(high_setpoint_candidate)

            # AC OFF candidate during peak (save money, accept discomfort)
            ac_off_peak = self._evaluate_candidate(
                ac_units=0,
                fan_units=min(1, max_fan),
                setpoint=comfort_max + 4,
                interval=interval,
                scenario=scenario,
                config=config,
                ac=ac,
                fan=fan,
                solar_battery=solar_battery,
                solar_kwh=solar_kwh,
                running_peak_kw=running_peak_kw,
                grid_available=grid_available,
                is_occupied=True
            )
            candidates.append(ac_off_peak)

        # === SOLAR-OPTIMIZED CANDIDATES ===
        # If solar available, generate max-cooling candidates
        if solar_kwh > 0.1:
            solar_candidate = self._evaluate_candidate(
                ac_units=min(1, max_ac),
                fan_units=max_fan,
                setpoint=comfort_min,
                interval=interval,
                scenario=scenario,
                config=config,
                ac=ac,
                fan=fan,
                solar_battery=solar_battery,
                solar_kwh=solar_kwh,
                running_peak_kw=running_peak_kw,
                grid_available=grid_available,
                is_occupied=True
            )
            candidates.append(solar_candidate)

        # === PRE-COOLING CANDIDATES ===
        # If next 1-2 hours will be peak, cool aggressively NOW during cheap tariff
        if is_cheap_tariff and is_occupied and max_ac > 0:
            # Check if any of next 4-8 intervals (1-2 hours) are peak
            next_is_peak = False
            for j in range(1, 9):
                look_ahead_idx = interval_idx + j
                if look_ahead_idx < len(scenario.interval_inputs):
                    next_interval = scenario.interval_inputs[look_ahead_idx]
                    if next_interval.tariff_type == TariffType.PEAK or next_interval.tariff_pkr_per_kwh >= 40:
                        next_is_peak = True
                        break

            if next_is_peak:
                # Pre-cool aggressively before peak hits
                precool_candidate = self._evaluate_candidate(
                    ac_units=max_ac,
                    fan_units=max_fan,
                    setpoint=comfort_min,
                    interval=interval,
                    scenario=scenario,
                    config=config,
                    ac=ac,
                    fan=fan,
                    solar_battery=solar_battery,
                    solar_kwh=solar_kwh,
                    running_peak_kw=running_peak_kw,
                    grid_available=grid_available,
                    is_occupied=True
                )
                candidates.append(precool_candidate)

        return candidates

    def _evaluate_candidate(
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
        solar_kwh: float,
        running_peak_kw: float,
        grid_available: bool,
        is_occupied: bool
    ) -> CandidateAction:
        """Evaluate a single candidate action"""

        hour = interval.timestamp_local.hour
        tariff = interval.tariff_pkr_per_kwh
        is_peak_tariff = interval.tariff_type == TariffType.PEAK or tariff >= 40
        outdoor_temp = interval.temperature_c
        comfort_min = scenario.profile.comfort_min_c
        comfort_max = scenario.profile.comfort_max_c
        has_battery = scenario.energy_assets.battery_capacity_kwh > 0

        # Calculate energy loads
        ac_power = (ac.rated_power_kw * ac_units) if ac else 0
        fan_power = (fan.rated_power_kw * fan_units) if fan else 0
        cooling_load = (ac_power + fan_power) * self.interval_hours
        total_load = cooling_load + interval.non_cooling_load_kw * self.interval_hours

        # Estimate indoor temperature
        cooling_on = ac_units > 0
        estimated_indoor = self.thermal.estimate_indoor_temp(
            outdoor_temp=outdoor_temp,
            setpoint=setpoint if cooling_on else None,
            cooling_on=cooling_on,
            cooling_capacity_kw=ac.cooling_capacity_kw * ac_units if ac else 0,
            occupancy=interval.occupancy_count,
            solar_gain=interval.solar_irradiance_w_m2,
            building_area=scenario.profile.area_m2,
            insulation=scenario.profile.insulation_level,
            sun_exposure=scenario.profile.sun_exposure
        )

        # Energy flow optimization (simulate battery state)
        energy_flow = solar_battery.optimize_energy_flow(
            load_kwh=total_load,
            solar_available_kwh=solar_kwh,
            tariff_pkr=tariff,
            tariff_type=interval.tariff_type.value,
            is_peak=is_peak_tariff,
            grid_available=grid_available
        )

        # Calculate scores
        # Cost score: lower cost = lower score (normalized 0-1)
        cost_score = self._score_cost(
            energy_flow['grid_drawn_kwh'],
            tariff,
            is_peak_tariff
        )

        # Comfort score: deviation from comfort band
        comfort_score = self._score_comfort(
            estimated_indoor,
            is_occupied,
            comfort_min,
            comfort_max
        )

        # Emissions score: grid energy * carbon intensity
        emissions_score = self._score_emissions(
            energy_flow['grid_drawn_kwh'],
            interval.grid_carbon_kgco2_per_kwh
        )

        # Peak demand score: impact on peak
        peak_score = self._score_peak(
            ac_power + fan_power,
            running_peak_kw
        )

        # Get weights (with defaults if config is None)
        if config is None:
            w_cost, w_comfort, w_emissions, w_peak = 0.35, 0.30, 0.20, 0.15
        else:
            w_cost = config.objective_weights.get('cost', 0.35)
            w_comfort = config.objective_weights.get('comfort', 0.30)
            w_emissions = config.objective_weights.get('emissions', 0.20)
            w_peak = config.objective_weights.get('peak_demand', 0.15)

        # Total weighted score (lower is better)
        total_score = (
            w_cost * cost_score +
            w_comfort * comfort_score +
            w_emissions * emissions_score +
            w_peak * peak_score
        )

        # Determine reason code and explanation
        reason_code, explanation = self._get_reason_and_explanation(
            ac_units=ac_units,
            fan_units=fan_units,
            solar_kwh=solar_kwh,
            is_peak_tariff=is_peak_tariff,
            is_occupied=is_occupied,
            has_battery=has_battery,
            energy_flow=energy_flow,
            tariff=tariff,
            estimated_indoor=estimated_indoor,
            comfort_min=comfort_min,
            comfort_max=comfort_max,
            grid_available=grid_available
        )

        # Check constraints
        violations = self._check_constraints(
            ac_units=ac_units,
            fan_units=fan_units,
            setpoint=setpoint,
            energy_flow=energy_flow,
            estimated_indoor=estimated_indoor,
            scenario=scenario,
            grid_available=grid_available,
            comfort_min=comfort_min,
            comfort_max=comfort_max,
            is_occupied=is_occupied
        )

        # Comfort status
        comfort_status = self._get_comfort_status(
            estimated_indoor, is_occupied, comfort_min, comfort_max
        )

        return CandidateAction(
            ac_units=ac_units,
            fan_units=fan_units,
            setpoint_c=setpoint,
            reason_code=reason_code,
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

    def _score_cost(self, grid_kwh: float, tariff: float, is_peak: bool) -> float:
        """Score cost: 0 (best) to 1 (worst) - AGGRESSIVE peak penalty"""
        cost = grid_kwh * tariff

        # Normalize against max cost
        if self.max_cost > 0:
            normalized = min(1.0, cost / self.max_cost)
        else:
            normalized = 0

        # AGGRESSIVE peak penalty - heavily discourage usage during peak tariff
        if is_peak and grid_kwh > 0:
            normalized *= 2.5  # 2.5x multiplier instead of 1.2x

        # Extra penalty for peak tariff with high grid consumption
        if is_peak and grid_kwh > 0.3:
            normalized = min(1.0, normalized * 1.5)

        return min(1.0, normalized)

    def _score_comfort(
        self,
        indoor_temp: float,
        is_occupied: bool,
        comfort_min: float,
        comfort_max: float
    ) -> float:
        """
        Score comfort: 0 (best/comfortable) to 1 (worst/unsafe).
        Penalizes deviation from comfort band, especially when occupied.
        """
        if not is_occupied:
            # Vacant: small penalty only if dangerously hot
            if indoor_temp > comfort_max + 8:
                return 0.3
            return 0.05  # Very low penalty when vacant

        # Calculate deviation
        if indoor_temp < comfort_min:
            deviation = comfort_min - indoor_temp
        elif indoor_temp > comfort_max:
            deviation = indoor_temp - comfort_max
        else:
            deviation = 0

        # Score: steeper quadratic penalty for deviation
        score = min(1.0, (deviation / 3) ** 2)

        return score

    def _score_emissions(self, grid_kwh: float, carbon_intensity: float) -> float:
        """Score emissions: 0 (best) to 1 (worst)"""
        emissions = grid_kwh * carbon_intensity

        if self.max_emissions > 0:
            return min(1.0, emissions / self.max_emissions)
        return 0

    def _score_peak(self, current_power_kw: float, running_peak_kw: float) -> float:
        """
        Score peak demand: 0 (best) to 1 (worst).
        AGGRESSIVELY penalizes both absolute power and contribution to peak.
        """
        # Absolute power score
        if self.max_peak_kw > 0:
            abs_score = min(1.0, (current_power_kw / self.max_peak_kw) ** 1.5)  # Exponential penalty
        else:
            abs_score = 0

        # Peak contribution: would this push us to a new peak?
        projected_peak = max(running_peak_kw, current_power_kw)
        if running_peak_kw > 0:
            peak_delta = (projected_peak - running_peak_kw) / running_peak_kw
        else:
            peak_delta = 0

        # Combined score - MORE weight on peak contribution
        score = abs_score * 0.4 + min(1.0, peak_delta) * 0.6

        return min(1.0, score)

    def _get_reason_and_explanation(
        self,
        ac_units: int,
        fan_units: int,
        solar_kwh: float,
        is_peak_tariff: bool,
        is_occupied: bool,
        has_battery: bool,
        energy_flow: Dict,
        tariff: float,
        estimated_indoor: float,
        comfort_min: float,
        comfort_max: float,
        grid_available: bool
    ) -> Tuple[ReasonCode, str]:
        """Determine reason code and explanation based on selected action"""

        if not grid_available:
            if solar_kwh > 0.1:
                return ReasonCode.GRID_UNAVAILABLE, "Grid down - Solar only"
            else:
                return ReasonCode.GRID_UNAVAILABLE, "Grid down - Off"

        if ac_units == 0 and fan_units == 0:
            if is_occupied:
                return ReasonCode.VACANT, "Vacant - off"
            else:
                return ReasonCode.VACANT, "Vacant - off"

        if solar_kwh > 0.15 and energy_flow['solar_used_kwh'] > 0.1:
            return ReasonCode.SOLAR_AVAILABLE, f"FREE solar! ({solar_kwh:.2f} kWh)"

        if has_battery and is_peak_tariff and energy_flow['battery_discharge_kwh'] > 0.01:
            return ReasonCode.BATTERY_DISCHARGE, "Battery (peak avoided)"

        if is_peak_tariff:
            if estimated_indoor < comfort_max:
                return ReasonCode.PEAK_TARIFF, f"Peak: Minimal cooling"
            else:
                return ReasonCode.PEAK_TARIFF, f"Peak: AC on"

        if estimated_indoor < comfort_min:
            return ReasonCode.OCCUPIED_COMFORT, f"Cooling active"

        if estimated_indoor <= comfort_max:
            return ReasonCode.OCCUPIED_COMFORT, f"Comfort maintained"

        return ReasonCode.COMFORT_OPTIMIZED, f"Comfort cooling"

    def _check_constraints(
        self,
        ac_units: int,
        fan_units: int,
        setpoint: float,
        energy_flow: Dict,
        estimated_indoor: float,
        scenario: ScenarioInput,
        grid_available: bool,
        comfort_min: float,
        comfort_max: float,
        is_occupied: bool
    ) -> List[str]:
        """Check hard constraints, return list of violations"""
        violations = []

        # Constraint 1: Grid availability
        if not grid_available and energy_flow['grid_drawn_kwh'] > 0.01:
            violations.append("Grid draw when unavailable")

        # Constraint 2: Battery SOC bounds (with floating point tolerance)
        new_soc = energy_flow['new_soc_kwh']
        tolerance = 0.05  # 50Wh tolerance for floating point precision
        if new_soc < -tolerance:
            violations.append("Battery SOC below 0")
        if new_soc > scenario.energy_assets.battery_capacity_kwh + tolerance:
            violations.append("Battery SOC above capacity")
        if new_soc < scenario.energy_assets.minimum_reserve_kwh - tolerance:
            violations.append(f"Battery below minimum reserve ({new_soc:.3f} < {scenario.energy_assets.minimum_reserve_kwh})")

        # Constraint 3: Appliance capacity limits
        ac = next((a for a in scenario.appliances if a.appliance_type == ApplianceType.AC), None)
        if ac and ac_units > ac.quantity:
            violations.append("AC units exceed available quantity")
        if ac and setpoint < ac.min_setpoint_c:
            violations.append(f"Setpoint {setpoint} below minimum {ac.min_setpoint_c}")
        if ac and setpoint > ac.max_setpoint_c:
            violations.append(f"Setpoint {setpoint} above maximum {ac.max_setpoint_c}")

        # Constraint 4: Safety limits
        if estimated_indoor > comfort_max + 5:
            violations.append(f"Indoor temp {estimated_indoor} exceeds safety limit")

        # Constraint 5: Energy balance (simplified - grid + solar = load + battery change)
        # Note: This is already validated by the solar_battery module
        # We just check for extreme cases here
        total_in = energy_flow['grid_drawn_kwh'] + energy_flow['solar_used_kwh']
        total_out = energy_flow['battery_charge_kwh'] + 0.01  # At least some load expected

        # Relaxed balance check - only flag extreme imbalance
        if total_in > total_out + 2.0:
            violations.append(f"Energy imbalance: excess in={total_in:.3f}, out={total_out:.3f}")

        return violations

    def _get_comfort_status(
        self,
        temp: float,
        occupied: bool,
        comfort_min: float,
        comfort_max: float
    ) -> ComfortStatus:
        """Determine comfort status"""
        if not occupied:
            return ComfortStatus.WITHIN_RANGE

        if temp > comfort_max + 3 or temp < comfort_min - 3:
            return ComfortStatus.UNSAFE
        elif temp > comfort_max or temp < comfort_min:
            return ComfortStatus.WARNING
        else:
            return ComfortStatus.WITHIN_RANGE

    def _select_best_candidate(
        self,
        candidates: List[CandidateAction],
        config: OptimizationConfig
    ) -> CandidateAction:
        """
        Select best feasible candidate.
        Priority:
        1. Feasible candidates only (respects hard constraints)
        2. Among feasible, select minimum total score
        3. Tie-breaker: prefer lower comfort score (more comfortable)
        """
        feasible = [c for c in candidates if c.is_feasible()]

        if not feasible:
            # No feasible candidate - find the one with fewest violations
            # and add violations to its score
            candidates.sort(key=lambda c: len(c.violations))
            fallback = candidates[0]
            fallback.total_score += 10  # Heavy penalty
            return fallback

        # Sort by total score, then by comfort score (tie-breaker)
        feasible.sort(key=lambda c: (c.total_score, c.comfort_score))

        return feasible[0]

    def _build_interval_output(
        self,
        interval: IntervalInput,
        candidate: CandidateAction,
        scenario: ScenarioInput,
        config: OptimizationConfig,
        solar_battery: SolarBatteryModule
    ) -> IntervalOutput:
        """Build IntervalOutput from selected candidate"""

        tariff = interval.tariff_pkr_per_kwh

        # Cost and emissions
        grid_energy = candidate.grid_energy_kwh
        interval_cost = grid_energy * tariff
        interval_emissions = grid_energy * interval.grid_carbon_kgco2_per_kwh

        return IntervalOutput(
            timestamp_local=interval.timestamp_local,
            # Include input data for frontend display
            temperature_c=interval.temperature_c,
            solar_irradiance_w_m2=interval.solar_irradiance_w_m2,
            occupancy_count=interval.occupancy_count,
            tariff_pkr_per_kwh=interval.tariff_pkr_per_kwh,
            tariff_type=interval.tariff_type.value if hasattr(interval.tariff_type, 'value') else str(interval.tariff_type),
            grid_available=interval.grid_available,
            # Optimization output
            recommended_ac_units_on=candidate.ac_units,
            recommended_ac_setpoint_c=candidate.setpoint_c if candidate.ac_units > 0 else None,
            recommended_fan_units_on=candidate.fan_units,
            grid_energy_kwh=candidate.grid_energy_kwh,
            solar_energy_used_kwh=candidate.solar_used_kwh,
            battery_charge_kwh=candidate.battery_charge_kwh,
            battery_discharge_kwh=candidate.battery_discharge_kwh,
            battery_soc_kwh=round(solar_battery.current_soc, 2),
            cooling_energy_kwh=candidate.cooling_load_kwh,
            estimated_indoor_temp_c=candidate.estimated_indoor_temp,
            comfort_status=candidate.comfort_status,
            interval_cost_pkr=round(interval_cost, 2),
            interval_emissions_kgco2e=round(interval_emissions, 4),
            reason_code=candidate.reason_code,
            explanation=candidate.explanation,
            constraint_violation_count=len(candidate.violations),
            constraint_violations=candidate.violations
        )

    def _calculate_daily_summary(self, date: date, intervals: List[IntervalOutput]) -> DailySummary:
        """Calculate daily summary metrics"""
        total_energy = sum(i.cooling_energy_kwh for i in intervals)
        total_cost = sum(i.interval_cost_pkr for i in intervals)
        total_emissions = sum(i.interval_emissions_kgco2e for i in intervals)

        # Peak demand (max power)
        powers = [i.cooling_energy_kwh / 0.25 for i in intervals if i.cooling_energy_kwh > 0]
        peak_demand = max(powers) if powers else 0

        # Comfort compliance
        occupied_intervals = [i for i in intervals if i.comfort_status != ComfortStatus.WITHIN_RANGE]
        compliance = 100 - (len(occupied_intervals) / len(intervals) * 100) if intervals else 100

        # Unsafe hours
        unsafe_count = sum(1 for i in intervals if i.comfort_status == ComfortStatus.UNSAFE)
        unsafe_hours = unsafe_count * 0.25

        # Solar utilization
        total_solar = sum(i.solar_energy_used_kwh for i in intervals)
        total_available = sum(i.solar_energy_used_kwh + i.battery_charge_kwh for i in intervals)
        solar_util = (total_solar / total_available * 100) if total_available > 0 else 0

        # Battery cycles (approximate)
        battery_cycles = sum(i.battery_discharge_kwh for i in intervals) / 13.5 if any(i.battery_soc_kwh > 0 for i in intervals) else 0

        # Peak temperature (max outdoor temp from intervals)
        peak_temp = max((i.temperature_c for i in intervals), default=0)

        # Average battery SOC
        battery_socs = [i.battery_soc_kwh for i in intervals if i.battery_soc_kwh > 0]
        avg_battery_soc = sum(battery_socs) / len(battery_socs) if battery_socs else 0
        # Estimate battery capacity from any interval's SOC
        battery_capacity = max((i.battery_soc_kwh for i in intervals), default=13.5)
        battery_soc_pct = (avg_battery_soc / battery_capacity * 100) if battery_capacity > 0 else 0

        # Day name
        from datetime import date as date_type
        day_name = date.strftime('%a') if isinstance(date, date_type) else str(date)

        return DailySummary(
            date=date,
            day_name=day_name,
            total_energy_kwh=round(total_energy, 2),
            total_cost_pkr=round(total_cost, 2),
            total_emissions_kgco2e=round(total_emissions, 3),
            peak_demand_kw=round(peak_demand, 2),
            peak_temp=round(peak_temp, 1),
            comfort_compliance_pct=round(compliance, 1),
            unsafe_hours=round(unsafe_hours, 2),
            solar_utilization_pct=round(solar_util, 1),
            solar_used_kwh=round(total_solar, 2),
            battery_soc_pct=round(battery_soc_pct, 1),
            battery_cycles=round(battery_cycles, 2)
        )

    def _calculate_overall_summary(
        self,
        scenario_id: str,
        intervals: List[IntervalOutput],
        baseline_result
    ) -> RunSummary:
        """Calculate overall summary metrics"""

        total_energy = sum(i.cooling_energy_kwh for i in intervals)
        total_grid = sum(i.grid_energy_kwh for i in intervals)
        total_cost = sum(i.interval_cost_pkr for i in intervals)
        total_emissions = sum(i.interval_emissions_kgco2e for i in intervals)

        # Peak demand
        powers = [i.cooling_energy_kwh / 0.25 for i in intervals if i.cooling_energy_kwh > 0]
        peak_demand = max(powers) if powers else 0

        # Comfort compliance
        compliant = sum(1 for i in intervals if i.comfort_status == ComfortStatus.WITHIN_RANGE)
        compliance = (compliant / len(intervals) * 100) if intervals else 100

        # Solar utilization
        total_solar = sum(i.solar_energy_used_kwh for i in intervals)
        total_solar_available = sum(i.solar_energy_used_kwh + i.battery_charge_kwh for i in intervals)
        solar_util = (total_solar / total_solar_available * 100) if total_solar_available > 0 else 0

        # Battery utilization
        max_soc = max(i.battery_soc_kwh for i in intervals) if intervals else 0
        avg_soc = np.mean([i.battery_soc_kwh for i in intervals]) if intervals else 0
        battery_util = (avg_soc / max_soc * 100) if max_soc > 0 else 0

        # Savings
        cost_savings = baseline_result.total_cost_pkr - total_cost
        energy_savings = baseline_result.total_energy_kwh - total_energy
        emission_savings = baseline_result.total_emissions_kgco2e - total_emissions

        start_ts = intervals[0].timestamp_local if intervals else datetime.now()
        end_ts = intervals[-1].timestamp_local if intervals else datetime.now()

        return RunSummary(
            scenario_id=scenario_id,
            run_id="",
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            total_intervals=len(intervals),
            total_days=len(intervals) / 96 if intervals else 0,
            total_energy_kwh=round(total_energy, 2),
            total_cost_pkr=round(total_cost, 2),
            total_emissions_kgco2e=round(total_emissions, 3),
            peak_demand_kw=round(peak_demand, 2),
            comfort_compliance_pct=round(compliance, 1),
            solar_utilization_pct=round(solar_util, 1),
            battery_utilization_pct=round(battery_util, 1),
            total_savings_pkr=round(cost_savings, 2),
            total_savings_kwh=round(energy_savings, 2),
            emission_reduction_kgco2e=round(emission_savings, 3)
        )
