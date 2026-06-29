"""
OR-Tools MILP Optimizer for CoolShift Energy Management
Mixed Integer Linear Programming based optimization using Google OR-Tools

Improved version with:
- Pre-cooling strategy (cool during off-peak to reduce peak demand)
- Better battery utilization for peak shaving
- Aggressive peak tariff avoidance
- Discrete setpoint optimization
- Better temperature dynamics
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
from ortools.linear_solver import pywraplp

from data_models import *
from baseline_engine import BaselineEngine
from solar_battery import SolarBatteryModule


class ORToolsOptimizer:
    """
    MILP-based Optimization Engine using Google OR-Tools.

    Key improvements over baseline:
    1. Pre-cooling: Cool aggressively during off-peak, reduce peak usage
    2. Peak shaving: Use battery + reduced cooling during peak hours
    3. Solar maximization: Use all available solar for cooling
    4. Discrete setpoints: Optimize specific temperature setpoints
    """

    def __init__(self):
        self.baseline = BaselineEngine()
        self.interval_hours = 0.25

    def optimize(
        self,
        scenario: ScenarioInput,
        config: Optional[OptimizationConfig] = None
    ) -> RunResult:
        """
        Generate optimized cooling schedule using OR-Tools MILP.
        """

        if config is None:
            config = OptimizationConfig()

        # Get weights - MORE aggressive for peak avoidance
        w_cost = config.objective_weights.get('cost', 0.45)
        w_comfort = config.objective_weights.get('comfort', 0.20)
        w_emissions = config.objective_weights.get('emissions', 0.10)
        w_peak = config.objective_weights.get('peak_demand', 0.25)

        # Extract scenario parameters
        ac = next((a for a in scenario.appliances if a.appliance_type == ApplianceType.AC), None)
        fan = next((a for a in scenario.appliances if a.appliance_type == ApplianceType.FAN), None)

        # Appliance parameters
        ac_power = ac.rated_power_kw if ac else 0
        ac_cooling = ac.cooling_capacity_kw if ac else 0
        fan_power = fan.rated_power_kw if fan else 0
        max_ac = ac.quantity if ac else 0
        max_fan = fan.quantity if fan else 0
        min_setpoint = ac.min_setpoint_c if ac else 20
        max_setpoint = ac.max_setpoint_c if ac else 30

        # Profile parameters
        comfort_min = scenario.profile.comfort_min_c
        comfort_max = scenario.profile.comfort_max_c
        area_m2 = scenario.profile.area_m2

        # Solar/Battery setup
        solar_battery = SolarBatteryModule(scenario.energy_assets)
        has_battery = scenario.energy_assets.battery_capacity_kwh > 0
        has_solar = scenario.energy_assets.solar_capacity_kw > 0

        # Create solver
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver:
            raise RuntimeError("Could not create OR-Tools solver")

        # Set time limit for optimization
        solver.SetTimeLimit(60000)  # 60 seconds for better solutions

        n_intervals = len(scenario.interval_inputs)

        # ============ DECISION VARIABLES ============

        # AC units on (integer 0 to max)
        ac_on = {}
        for i in range(n_intervals):
            ac_on[i] = solver.IntVar(0, max_ac, f'ac_on_{i}')

        # Fan units on (integer 0 to max)
        fan_on = {}
        for i in range(n_intervals):
            fan_on[i] = solver.IntVar(0, max_fan, f'fan_on_{i}')

        # Discrete setpoint (use specific temperature values)
        # Setpoints: 20, 22, 24, 26, 28
        setpoint_bins = [20.0, 22.0, 24.0, 26.0, 28.0]
        setpoint_on = {}  # Binary for each setpoint option
        for i in range(n_intervals):
            for idx, sp in enumerate(setpoint_bins):
                setpoint_on[(i, idx)] = solver.IntVar(0, 1, f'sp_{i}_{idx}')

        # Grid energy drawn (continuous, non-negative)
        grid_drawn = {}
        for i in range(n_intervals):
            grid_drawn[i] = solver.NumVar(0, 100, f'grid_{i}')

        # Solar used (continuous)
        solar_used = {}
        for i in range(n_intervals):
            solar_used[i] = solver.NumVar(0, 100, f'solar_used_{i}')

        # Indoor temperature estimate (continuous)
        indoor_temp = {}
        for i in range(n_intervals):
            indoor_temp[i] = solver.NumVar(15, 50, f'indoor_temp_{i}')

        # Battery state (if applicable)
        battery_soc = {}
        if has_battery:
            for i in range(n_intervals):
                battery_soc[i] = solver.NumVar(
                    scenario.energy_assets.minimum_reserve_kwh,
                    scenario.energy_assets.battery_capacity_kwh,
                    f'batt_soc_{i}'
                )
            battery_charge = {i: solver.NumVar(0, scenario.energy_assets.max_charge_kw,
                                              f'batt_charge_{i}') for i in range(n_intervals)}
            battery_discharge = {i: solver.NumVar(0, scenario.energy_assets.max_discharge_kw,
                                                  f'batt_disc_{i}') for i in range(n_intervals)}

        # Pre-cooling indicator (cooling during off-peak to reduce peak)
        precool_score = {}
        for i in range(n_intervals):
            precool_score[i] = solver.NumVar(0, 10, f'precool_{i}')

        # ============ CONSTRAINTS ============

        # 1. Setpoint selection (exactly one setpoint per interval)
        for i in range(n_intervals):
            solver.Add(sum(setpoint_on[(i, idx)] for idx in range(len(setpoint_bins))) == 1)

        # 2. Energy balance for each interval
        for i, interval in enumerate(scenario.interval_inputs):
            cooling_load = (ac_power * ac_on[i] + fan_power * fan_on[i]) * self.interval_hours
            non_cooling = interval.non_cooling_load_kw * self.interval_hours
            total_load = cooling_load + non_cooling

            # Solar generation for this interval
            solar_gen = solar_battery.calculate_solar_generation(
                interval.solar_irradiance_w_m2,
                self.interval_hours
            )

            # Energy balance with battery
            if has_battery:
                # Net energy = grid + solar + battery_discharge - battery_charge
                solver.Add(
                    grid_drawn[i] + solar_used[i] + battery_discharge[i] * self.interval_hours >=
                    total_load + battery_charge[i] * self.interval_hours
                )
                solver.Add(solar_used[i] <= solar_gen)

                # Battery SOC dynamics
                if i == 0:
                    solver.Add(battery_soc[i] == scenario.energy_assets.initial_soc_kwh + battery_charge[i] * self.interval_hours * scenario.energy_assets.charge_efficiency
                             - battery_discharge[i] * self.interval_hours / scenario.energy_assets.discharge_efficiency)
                else:
                    solver.Add(
                        battery_soc[i] == battery_soc[i-1] + battery_charge[i] * self.interval_hours * scenario.energy_assets.charge_efficiency
                        - battery_discharge[i] * self.interval_hours / scenario.energy_assets.discharge_efficiency
                    )
            else:
                solver.Add(grid_drawn[i] + solar_used[i] >= total_load)
                solver.Add(solar_used[i] <= solar_gen)

        # 3. Indoor temperature dynamics (improved model)
        for i, interval in enumerate(scenario.interval_inputs):
            outdoor_temp = interval.temperature_c

            if i == 0:
                # Initial temperature based on outdoor
                solver.Add(indoor_temp[i] >= outdoor_temp - 6)
                solver.Add(indoor_temp[i] <= outdoor_temp + 2)
            else:
                prev_temp = indoor_temp[i-1]
                is_occupied = interval.occupancy_count > 0

                # Calculate effective setpoint from binary selection
                effective_setpoint = sum(setpoint_bins[idx] * setpoint_on[(i, idx)] for idx in range(len(setpoint_bins)))

                # Temperature moves toward setpoint when AC is on
                # Temperature drifts toward outdoor when AC is off
                cooling_on = ac_on[i]

                if is_occupied:
                    # When occupied: move toward setpoint, constrained by comfort
                    # Temperature can decrease (cooling) or increase (drift toward outdoor)
                    # But should stay within comfort band
                    solver.Add(indoor_temp[i] <= effective_setpoint + 1)
                    solver.Add(indoor_temp[i] <= outdoor_temp + 1)
                    solver.Add(indoor_temp[i] >= effective_setpoint - 1)
                    solver.Add(indoor_temp[i] >= comfort_min - 2)

                    # Also constrain based on previous temp and cooling
                    solver.Add(indoor_temp[i] <= prev_temp + 0.5 + 0.5 * (outdoor_temp - prev_temp))
                else:
                    # When vacant: let temperature drift toward outdoor
                    solver.Add(indoor_temp[i] >= prev_temp - 0.5)
                    solver.Add(indoor_temp[i] <= prev_temp + 0.8 + 0.5 * (outdoor_temp - prev_temp))

        # 4. AC on requires positive setpoint
        for i in range(n_intervals):
            solver.Add(ac_on[i] <= sum(setpoint_on[(i, idx)] for idx in range(len(setpoint_bins))))

        # 5. Comfort constraints during occupied hours - TIGHTER
        for i, interval in enumerate(scenario.interval_inputs):
            is_occupied = interval.occupancy_count > 0
            effective_setpoint = sum(setpoint_bins[idx] * setpoint_on[(i, idx)] for idx in range(len(setpoint_bins)))

            if is_occupied:
                # TIGHTER: Must be within comfort band when occupied
                solver.Add(indoor_temp[i] >= comfort_min - 0.5)
                solver.Add(indoor_temp[i] <= comfort_max + 0.5)
                # If AC on, setpoint should be in comfort range
                solver.Add(effective_setpoint >= comfort_min)
                solver.Add(effective_setpoint <= comfort_max + 1)
            else:
                # Vacant: allow higher temperatures to save energy
                solver.Add(indoor_temp[i] >= comfort_min - 5)
                solver.Add(indoor_temp[i] <= comfort_max + 12)
                solver.Add(effective_setpoint >= comfort_min)
                solver.Add(effective_setpoint <= max_setpoint)

        # Detect peak hours (moved earlier)
        peak_hours = set()
        off_peak_hours = set()
        for i, interval in enumerate(scenario.interval_inputs):
            hour = interval.timestamp_local.hour
            tariff = interval.tariff_pkr_per_kwh
            is_peak = interval.tariff_type == TariffType.PEAK or tariff >= 40
            if is_peak:
                peak_hours.add(i)
            else:
                off_peak_hours.add(i)

        # 5b. TIGHTER: During peak + occupied, constrain AC usage
        for i in peak_hours:
            interval = scenario.interval_inputs[i]
            if interval.occupancy_count == 0:
                # Unoccupied during peak - MUST be off
                solver.Add(ac_on[i] == 0)
                solver.Add(fan_on[i] == 0)
            else:
                # During peak with occupancy - limit to max 1 AC unit
                solver.Add(ac_on[i] <= 1)
                # Prefer high setpoints during peak (26-28 only)
                for idx, sp in enumerate(setpoint_bins):
                    if sp < 26:
                        solver.Add(setpoint_on[(i, idx)] == 0)  # Disable low setpoints

        # 6. Grid availability constraints
        for i, interval in enumerate(scenario.interval_inputs):
            max_grid_power = scenario.profile.maximum_grid_demand_kw * self.interval_hours
            if not interval.grid_available:
                solver.Add(grid_drawn[i] <= 0.01)
            else:
                solver.Add(grid_drawn[i] <= max_grid_power)

        # 7. Peak tariff avoidance - reduce cooling during peak
        # (peak_hours already defined above)
        # ADDITIONAL CONSTRAINT: During peak, minimize cooling
        for i in peak_hours:
            interval = scenario.interval_inputs[i]
            if interval.occupancy_count == 0:
                # Unoccupied during peak - must be off
                solver.Add(ac_on[i] == 0)
            else:
                # During peak with occupancy - PREFER high setpoints (26-28)
                # Don't hard constraint, just heavily penalize in objective
                pass  # Removed hard constraint - will be handled by objective

        # ============ OBJECTIVE FUNCTION ============

        total_cost = 0
        total_discomfort = 0
        total_emissions = 0
        total_peak = 0
        peak_penalty = 0
        solar_bonus = 0

        # Pre-compute solar generation for all intervals
        solar_gens = []
        for i, interval in enumerate(scenario.interval_inputs):
            sg = solar_battery.calculate_solar_generation(
                interval.solar_irradiance_w_m2,
                self.interval_hours
            )
            solar_gens.append(sg)

        for i, interval in enumerate(scenario.interval_inputs):
            is_occupied = interval.occupancy_count > 0
            tariff = interval.tariff_pkr_per_kwh
            carbon = interval.grid_carbon_kgco2_per_kwh
            is_peak = interval.tariff_type == TariffType.PEAK or tariff >= 40
            effective_setpoint = sum(setpoint_bins[idx] * setpoint_on[(i, idx)] for idx in range(len(setpoint_bins)))

            # Cost term (major component)
            total_cost += grid_drawn[i] * tariff * w_cost

            # Emissions term
            total_emissions += grid_drawn[i] * carbon * w_emissions

            # Peak penalty - EXTREME for peak hours
            power = ac_power * ac_on[i] + fan_power * fan_on[i]
            if is_peak:
                # EXTREME penalty for peak usage (6x the tariff)
                peak_penalty += grid_drawn[i] * tariff * 6.0 * w_cost  # 6x extra cost penalty
                peak_penalty += power * 300  # Very high power penalty during peak
                peak_penalty += ac_on[i] * 800  # Extra penalty for AC ON during peak

                # Extra penalty for ANY setpoint during peak (discourage AC entirely)
                for idx, sp in enumerate(setpoint_bins):
                    peak_penalty += setpoint_on[(i, idx)] * 150 * w_cost
            else:
                # Light penalty to discourage high power during off-peak
                total_peak += power * w_peak * 0.1

            # Discomfort penalty (only when occupied)
            if is_occupied:
                below_min = solver.NumVar(0, 20, f'below_min_{i}')
                above_max = solver.NumVar(0, 20, f'above_max_{i}')

                solver.Add(below_min >= comfort_min - indoor_temp[i])
                solver.Add(above_max >= indoor_temp[i] - comfort_max)

                # Higher penalty for being above comfort max (hot is worse)
                total_discomfort += (below_min * 0.5 + above_max * w_comfort * 15)

            # Solar bonus - reward for using solar
            if solar_gens[i] > 0:
                solar_util = solver.NumVar(0, solar_gens[i], f'solar_util_{i}')
                solver.Add(solar_util <= solar_used[i])
                solver.Add(solar_util <= solar_gens[i])
                solar_bonus -= solar_util * tariff * 0.3 * w_cost

            # Pre-cooling incentive: if cooling during off-peak when next hour is peak
            # Look ahead to see if next intervals are peak (3 hour window)
            if i + 12 < n_intervals:  # Next 3 hours
                next_is_peak = any(
                    scenario.interval_inputs[j].tariff_type == TariffType.PEAK or
                    scenario.interval_inputs[j].tariff_pkr_per_kwh >= 40
                    for j in range(i + 1, min(i + 12, n_intervals))
                )
                if next_is_peak and not is_peak and is_occupied:
                    # STRONG bonus for cooling during off-peak before peak
                    precool_contribution = solver.NumVar(0, 10, f'precool_contrib_{i}')
                    solver.Add(precool_contribution <= ac_on[i] * 3)
                    precool_score[i] = precool_contribution
                    peak_penalty -= precool_contribution * 25 * w_cost  # Stronger bonus

        # Battery discharge bonus during peak
        if has_battery:
            for i, interval in enumerate(scenario.interval_inputs):
                is_peak = interval.tariff_type == TariffType.PEAK or interval.tariff_pkr_per_kwh >= 40
                if is_peak and battery_discharge:
                    peak_penalty -= battery_discharge[i] * interval.tariff_pkr_per_kwh * 0.3 * w_cost

        solver.Minimize(total_cost + total_discomfort + total_emissions + total_peak + peak_penalty + solar_bonus)

        # ============ SOLVE ============

        status = solver.Solve()

        if status != pywraplp.Solver.OPTIMAL and status != pywraplp.Solver.FEASIBLE:
            raise RuntimeError(f"OR-Tools solver failed with status: {status}")

        # ============ EXTRACT SOLUTION ============

        optimized_intervals = []
        running_peak_kw = 0
        intervals_by_day: Dict[date, List] = {}

        # Calculate baseline for comparison
        baseline_result = self.baseline.calculate(scenario)

        # Current battery SOC for tracking
        current_soc = scenario.energy_assets.initial_soc_kwh

        for i, interval in enumerate(scenario.interval_inputs):
            # Get solution values
            ac_units_val = int(ac_on[i].solution_value()) if ac_on[i].solution_value() else 0
            fan_units_val = int(fan_on[i].solution_value()) if fan_on[i].solution_value() else 0
            grid_val = grid_drawn[i].solution_value() if grid_drawn[i].solution_value() else 0
            solar_val = solar_used[i].solution_value() if solar_used[i].solution_value() else 0
            indoor_val = indoor_temp[i].solution_value() if indoor_temp[i].solution_value() else 25

            # Get effective setpoint
            setpoint_val = 24.0
            for idx, sp in enumerate(setpoint_bins):
                sp_val = setpoint_on[(i, idx)].solution_value() if setpoint_on[(i, idx)].solution_value() else 0
                if sp_val > 0.5:
                    setpoint_val = sp
                    break

            # Solar generation
            solar_gen = solar_gens[i]

            # Battery state
            if has_battery:
                discharge_val = battery_discharge[i].solution_value() if battery_discharge[i].solution_value() else 0
                charge_val = battery_charge[i].solution_value() if battery_charge[i].solution_value() else 0
                current_soc = battery_soc[i].solution_value() if battery_soc[i].solution_value() else current_soc
            else:
                discharge_val = 0
                charge_val = 0
                current_soc = 0

            # Energy calculations
            cooling_load = (ac_power * ac_units_val + fan_power * fan_units_val) * self.interval_hours

            # Determine reason code
            reason_code, explanation = self._get_reason_code(
                ac_units=ac_units_val,
                fan_units=fan_units_val,
                solar_val=solar_val,
                solar_gen=solar_gen,
                tariff_type=interval.tariff_type,
                tariff=interval.tariff_pkr_per_kwh,
                is_occupied=interval.occupancy_count > 0,
                has_battery=has_battery,
                discharge_val=discharge_val,
                indoor_temp=indoor_val,
                comfort_min=comfort_min,
                comfort_max=comfort_max,
                grid_available=interval.grid_available
            )

            # Comfort status
            comfort_status = self._get_comfort_status(indoor_val, interval.occupancy_count > 0,
                                                      comfort_min, comfort_max)

            # Cost and emissions
            interval_cost = grid_val * interval.tariff_pkr_per_kwh
            interval_emissions = grid_val * interval.grid_carbon_kgco2_per_kwh

            # Peak tracking
            power_kw = ac_power * ac_units_val + fan_power * fan_units_val
            running_peak_kw = max(running_peak_kw, power_kw)

            # Constraint violations
            violations = self._check_violations(
                indoor_temp=indoor_val,
                comfort_min=comfort_min,
                comfort_max=comfort_max,
                is_occupied=interval.occupancy_count > 0,
                grid_available=interval.grid_available,
                grid_drawn=grid_val,
                battery_soc=current_soc,
                capacity=scenario.energy_assets.battery_capacity_kwh,
                min_reserve=scenario.energy_assets.minimum_reserve_kwh
            )

            output = IntervalOutput(
                timestamp_local=interval.timestamp_local,
                temperature_c=interval.temperature_c,
                solar_irradiance_w_m2=interval.solar_irradiance_w_m2,
                occupancy_count=interval.occupancy_count,
                tariff_pkr_per_kwh=interval.tariff_pkr_per_kwh,
                tariff_type=interval.tariff_type.value,
                grid_available=interval.grid_available,
                recommended_ac_units_on=ac_units_val,
                recommended_ac_setpoint_c=round(setpoint_val, 1),
                recommended_fan_units_on=fan_units_val,
                grid_energy_kwh=round(grid_val, 4),
                solar_energy_used_kwh=round(solar_val, 4),
                battery_charge_kwh=round(charge_val * self.interval_hours, 4),
                battery_discharge_kwh=round(discharge_val * self.interval_hours, 4),
                battery_soc_kwh=round(current_soc, 4),
                cooling_energy_kwh=round(cooling_load, 4),
                estimated_indoor_temp_c=round(indoor_val, 1),
                comfort_status=comfort_status,
                interval_cost_pkr=round(interval_cost, 2),
                interval_emissions_kgco2e=round(interval_emissions, 4),
                reason_code=reason_code,
                explanation=explanation,
                constraint_violation_count=len(violations),
                constraint_violations=violations
            )

            optimized_intervals.append(output)

            # Track by day
            day = interval.timestamp_local.date()
            if day not in intervals_by_day:
                intervals_by_day[day] = []
            intervals_by_day[day].append(output)

        # Calculate daily summaries
        daily_summaries = []
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
            constraints_satisfied=all(len(i.constraint_violations) == 0 for i in optimized_intervals),
            algorithm_version="ortools_milp_2.0"
        )

    def _get_reason_code(
        self,
        ac_units: int,
        fan_units: int,
        solar_val: float,
        solar_gen: float,
        tariff_type: TariffType,
        tariff: float,
        is_occupied: bool,
        has_battery: bool,
        discharge_val: float,
        indoor_temp: float,
        comfort_min: float,
        comfort_max: float,
        grid_available: bool
    ) -> Tuple[ReasonCode, str]:
        """Determine reason code based on optimal solution"""

        if not grid_available:
            if solar_gen > 0.1:
                return ReasonCode.GRID_UNAVAILABLE, "Grid down - Solar only"
            else:
                return ReasonCode.GRID_UNAVAILABLE, "Grid down - Off"

        if ac_units == 0 and fan_units == 0:
            if is_occupied:
                return ReasonCode.VACANT, "Vacant - off"
            else:
                return ReasonCode.VACANT, "Vacant - off"

        if solar_gen > 0.1 and solar_val > solar_gen * 0.5:
            return ReasonCode.SOLAR_AVAILABLE, f"FREE solar! ({solar_gen:.2f} kWh)"

        if has_battery and discharge_val > 0.01:
            return ReasonCode.BATTERY_DISCHARGE, "Battery (peak avoided)"

        if tariff_type == TariffType.PEAK or tariff >= 40:
            return ReasonCode.PEAK_TARIFF, f"Peak: Minimal cooling"

        if indoor_temp < comfort_min:
            return ReasonCode.OCCUPIED_COMFORT, f"Cooling active"

        if indoor_temp <= comfort_max:
            return ReasonCode.OCCUPIED_COMFORT, f"Comfort maintained"

        return ReasonCode.COMFORT_OPTIMIZED, f"Comfort cooling"

    def _get_comfort_status(
        self,
        indoor_temp: float,
        is_occupied: bool,
        comfort_min: float,
        comfort_max: float
    ) -> ComfortStatus:
        """Determine comfort status"""
        if not is_occupied:
            return ComfortStatus.WARNING

        if comfort_min <= indoor_temp <= comfort_max:
            return ComfortStatus.WITHIN_RANGE
        elif indoor_temp < comfort_min - 2 or indoor_temp > comfort_max + 3:
            return ComfortStatus.UNSAFE
        else:
            return ComfortStatus.WARNING

    def _check_violations(
        self,
        indoor_temp: float,
        comfort_min: float,
        comfort_max: float,
        is_occupied: bool,
        grid_available: bool,
        grid_drawn: float,
        battery_soc: float,
        capacity: float,
        min_reserve: float
    ) -> List[str]:
        """Check for constraint violations"""
        violations = []

        if not grid_available and grid_drawn > 0.01:
            violations.append("Grid draw when unavailable")

        if battery_soc < min_reserve - 0.1:
            violations.append(f"Battery below minimum reserve")

        if battery_soc > capacity + 0.1:
            violations.append("Battery SOC exceeds capacity")

        if is_occupied and indoor_temp > comfort_max + 5:
            violations.append(f"Indoor temp {indoor_temp} exceeds safety limit")

        return violations

    def _calculate_daily_summary(self, day: date, intervals: List[IntervalOutput]) -> DailySummary:
        """Calculate daily summary from intervals"""
        total_energy = sum(i.cooling_energy_kwh + i.grid_energy_kwh for i in intervals)
        total_cost = sum(i.interval_cost_pkr for i in intervals)
        total_emissions = sum(i.interval_emissions_kgco2e for i in intervals)

        # Peak demand
        peak_demand = 0
        for i in intervals:
            power = i.recommended_ac_units_on * 1.5 + i.recommended_fan_units_on * 0.05
            peak_demand = max(peak_demand, power)

        # Comfort compliance
        occupied_intervals = [i for i in intervals if i.occupancy_count > 0]
        if occupied_intervals:
            comfortable = sum(1 for i in occupied_intervals
                            if i.comfort_status == ComfortStatus.WITHIN_RANGE)
            comfort_pct = (comfortable / len(occupied_intervals)) * 100
        else:
            comfort_pct = 100

        # Unsafe hours
        unsafe_hours = sum(1 for i in intervals
                          if i.comfort_status == ComfortStatus.UNSAFE)

        # Solar utilization
        total_solar_gen = sum(i.solar_irradiance_w_m2 * 0.25 / 1000 for i in intervals)
        total_solar_used = sum(i.solar_energy_used_kwh for i in intervals)
        solar_util = (total_solar_used / total_solar_gen * 100) if total_solar_gen > 0 else 0

        # Battery cycles
        battery_cycles = 0

        return DailySummary(
            date=day,
            total_energy_kwh=round(total_energy, 2),
            total_cost_pkr=round(total_cost, 2),
            total_emissions_kgco2e=round(total_emissions, 4),
            peak_demand_kw=round(peak_demand, 2),
            comfort_compliance_pct=round(comfort_pct, 1),
            unsafe_hours=unsafe_hours * 0.25,
            solar_utilization_pct=round(solar_util, 1),
            battery_cycles=round(battery_cycles, 2)
        )

    def _calculate_overall_summary(
        self,
        scenario_id: str,
        intervals: List[IntervalOutput],
        baseline_result
    ) -> RunSummary:
        """Calculate overall run summary"""
        n = len(intervals)

        total_energy = sum(i.cooling_energy_kwh + i.grid_energy_kwh for i in intervals)
        total_cost = sum(i.interval_cost_pkr for i in intervals)
        total_emissions = sum(i.interval_emissions_kgco2e for i in intervals)

        peak_demand = max(
            i.recommended_ac_units_on * 1.5 + i.recommended_fan_units_on * 0.05
            for i in intervals
        ) if intervals else 0

        # Comfort compliance
        occupied_intervals = [i for i in intervals if i.occupancy_count > 0]
        if occupied_intervals:
            comfortable = sum(1 for i in occupied_intervals
                            if i.comfort_status == ComfortStatus.WITHIN_RANGE)
            comfort_pct = (comfortable / len(occupied_intervals)) * 100
        else:
            comfort_pct = 100

        # Solar and battery utilization
        total_solar_gen = sum(i.solar_irradiance_w_m2 * 0.25 / 1000 for i in intervals)
        total_solar_used = sum(i.solar_energy_used_kwh for i in intervals)
        solar_util = (total_solar_used / total_solar_gen * 100) if total_solar_gen > 0 else 0

        avg_battery_soc = sum(i.battery_soc_kwh for i in intervals) / n if n > 0 else 0
        max_battery = max(i.battery_soc_kwh for i in intervals) if intervals else 0
        battery_util = (avg_battery_soc / max_battery * 100) if max_battery > 0 else 0

        # Savings vs baseline
        savings_pkr = baseline_result.total_cost_pkr - total_cost
        savings_kwh = baseline_result.total_energy_kwh - total_energy
        emission_reduction = baseline_result.total_emissions_kgco2e - total_emissions

        return RunSummary(
            scenario_id=scenario_id,
            run_id="",
            start_timestamp=intervals[0].timestamp_local if intervals else datetime.now(),
            end_timestamp=intervals[-1].timestamp_local if intervals else datetime.now(),
            total_intervals=n,
            total_days=n / 96 if n > 0 else 0,
            total_energy_kwh=round(total_energy, 2),
            total_cost_pkr=round(total_cost, 2),
            total_emissions_kgco2e=round(total_emissions, 4),
            peak_demand_kw=round(peak_demand, 2),
            comfort_compliance_pct=round(comfort_pct, 1),
            solar_utilization_pct=round(solar_util, 1),
            battery_utilization_pct=round(battery_util, 1),
            total_savings_pkr=round(savings_pkr, 2),
            total_savings_kwh=round(savings_kwh, 2),
            emission_reduction_kgco2e=round(emission_reduction, 4)
        )
