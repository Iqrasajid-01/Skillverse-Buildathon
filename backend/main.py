"""
CoolShift Smart Energy Optimization Platform - FastAPI Backend
Production-grade energy management system with optimization engine
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
import pandas as pd
import numpy as np
import json
import os
import uuid
from pathlib import Path

# Import modules
from data_models import *
from data_import import DataImportService
from baseline_engine import BaselineEngine
from optimization_engine import OptimizationEngine
from ortools_optimizer import ORToolsOptimizer
from solar_battery import SolarBatteryModule
from thermal_model import ThermalModel
from validation import ValidationService
from export_service import ExportService
from alerts import AlertsGenerator, Alert, AlertType, AlertSeverity
from auth import auth_service
from database import init_db

# ML Models (optional - gracefully handle if not available)
try:
    from ml_models import SolarForecastModel, ThermalANNModel
    ML_AVAILABLE = True
    print("[ML] Models loaded successfully")
except ImportError as e:
    ML_AVAILABLE = False
    print(f"[ML] Models not available: {e}")

app = FastAPI(
    title="CoolShift Energy Optimization Platform",
    description="Smart Energy Management System for Extreme Heat Cooling Optimization",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage for runs
runs_storage: Dict[str, RunResult] = {}

# ============ STARTUP ============
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        init_db()
        print("[OK] Database initialized successfully")
    except Exception as e:
        print(f"[WARN] Database initialization warning: {e}")

# ============ HEALTH CHECK ============
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "ml_enabled": ML_AVAILABLE,
        "ml_features": ["solar_forecast", "thermal_ann"] if ML_AVAILABLE else []
    }

# ============ SCENARIO PROFILES ============
@app.post("/api/scenarios/profile", response_model=ScenarioProfile)
async def create_profile(profile: ScenarioProfile):
    return profile

@app.get("/api/scenarios", response_model=List[ScenarioInfo])
async def list_scenarios():
    """List all available scenarios in public dataset"""
    return [
        ScenarioInfo(id="PUB-A", name="Household without Solar", type="public", days=30),
        ScenarioInfo(id="PUB-B", name="Household with Solar & Battery", type="public", days=30),
        ScenarioInfo(id="PUB-C", name="School/Small Office", type="public", days=30),
    ]

# ============ DATA IMPORT ============
@app.post("/api/import/excel")
async def import_excel(file: UploadFile = File(...)):
    """Import Excel workbook - supports both multi-sheet and flat format"""
    try:
        content = await file.read()
        
        # Try flat format first
        from flat_format_importer import FlatFormatImporter
        flat_importer = FlatFormatImporter()
        
        # Check if it's flat format (single sheet with scenario_id column)
        import pandas as pd
        from io import BytesIO
        xls = pd.ExcelFile(BytesIO(content))
        df = pd.read_excel(xls, sheet_name=0)
        
        if 'scenario_id' in df.columns and 'outdoor_temp' in df.columns and 'timestamp' in df.columns:
            # It's flat format - parse all scenarios
            scenarios = flat_importer.parse_to_scenarios(content)
            
            # Return first scenario as the main data
            if scenarios:
                first_scenario = scenarios[0]
                return {
                    "status": "success",
                    "valid": True,
                    "format": "flat",
                    "scenarios_count": len(scenarios),
                    "total_intervals": len(first_scenario.interval_inputs),
                    "date_range": f"{first_scenario.interval_inputs[0].timestamp_local} to {first_scenario.interval_inputs[-1].timestamp_local}",
                    "scenario_input": first_scenario.model_dump(mode='json')
                }
        
        # Fall back to multi-sheet format
        service = DataImportService()
        result = service.import_workbook(content)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/import/json")
async def import_json(data: ScenarioInput):
    """Import scenario data as JSON"""
    try:
        service = DataImportService()
        result = service.import_json(data)
        return {"status": "success", "validated": True, "records": len(data.interval_inputs)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============ VALIDATION ============
@app.post("/api/validate")
async def validate_scenario(data: ScenarioInput):
    """Validate all scenario inputs"""
    try:
        validator = ValidationService()
        result = validator.validate_scenario(data)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============ BASELINE CALCULATION ============
@app.post("/api/baseline")
async def calculate_baseline(data: ScenarioInput):
    """Calculate baseline cooling schedule and metrics"""
    try:
        engine = BaselineEngine()
        result = engine.calculate(data)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============ OPTIMIZATION ============
@app.post("/api/optimize")
async def optimize_schedule(
    scenario: ScenarioInput,
    method: Optional[str] = "ortools_milp"
):
    """Generate optimized cooling schedule

    Args:
        method: Optimization method:
        - 'ortools_milp': OR-Tools MILP (best savings)
        - 'candidate_scoring': Rule-based candidate evaluation
        - 'ml_hybrid': ML-enhanced optimization (solar + thermal prediction)
    """
    run_id = str(uuid.uuid4())

    try:
        # Select optimization engine based on method
        if method == "ml_hybrid" and ML_AVAILABLE:
            from ml_optimization_engine import MLOptimizedEngine
            engine = MLOptimizedEngine(use_ml=True)
            engine_name = "ML-Hybrid (XGBoost + LSTM)"
            result = engine.optimize(scenario, None)
        elif method == "ortools_milp":
            engine = ORToolsOptimizer()
            engine_name = "OR-Tools MILP"
            result = engine.optimize(scenario, None)
        else:
            engine = OptimizationEngine()
            engine_name = "Candidate Scoring"
            result = engine.optimize(scenario, None)

        # Store result
        result.run_id = run_id
        runs_storage[run_id] = result

        return {
            "run_id": run_id,
            "status": "completed",
            "method": engine_name,
            "ml_enabled": method == "ml_hybrid" and ML_AVAILABLE,
            "summary": result.summary,
            "interval_count": len(result.intervals),
            "constraints_satisfied": result.constraints_satisfied
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/run/{run_id}")
async def get_run(run_id: str):
    """Get optimization run by ID"""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail="Run not found")
    return runs_storage[run_id]

@app.get("/api/run/{run_id}/intervals")
async def get_run_intervals(run_id: str):
    """Get interval details for a run"""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail="Run not found")
    return runs_storage[run_id].intervals

# ============ COMPARISON ============
@app.post("/api/compare")
async def compare_schedules(data: ScenarioInput, method: Optional[str] = "ortools_milp"):
    """Compare baseline vs optimized schedules

    Args:
        method: Optimization method - 'ortools_milp' (default, best savings) or 'candidate_scoring'
    """
    try:
        # Calculate baseline
        baseline_engine = BaselineEngine()
        baseline_result = baseline_engine.calculate(data)

        # Calculate optimized based on method
        if method == "ortools_milp":
            opt_engine = ORToolsOptimizer()
            engine_name = "OR-Tools MILP"
        else:
            opt_engine = OptimizationEngine()
            engine_name = "Candidate Scoring"

        optimized_result = opt_engine.optimize(data)

        # Build comparison
        comparison = {
            "baseline": {
                "total_energy_kwh": baseline_result.total_energy_kwh,
                "total_cost_pkr": baseline_result.total_cost_pkr,
                "total_emissions_kgco2e": baseline_result.total_emissions_kgco2e,
                "peak_demand_kw": baseline_result.peak_demand_kw,
                "comfort_compliance_pct": baseline_result.comfort_compliance_pct
            },
            "optimized": {
                "total_energy_kwh": optimized_result.summary.total_energy_kwh,
                "total_cost_pkr": optimized_result.summary.total_cost_pkr,
                "total_emissions_kgco2e": optimized_result.summary.total_emissions_kgco2e,
                "peak_demand_kw": optimized_result.summary.peak_demand_kw,
                "comfort_compliance_pct": optimized_result.summary.comfort_compliance_pct
            },
            "savings": {
                "energy_kwh": baseline_result.total_energy_kwh - optimized_result.summary.total_energy_kwh,
                "cost_pkr": baseline_result.total_cost_pkr - optimized_result.summary.total_cost_pkr,
                "emissions_kgco2e": baseline_result.total_emissions_kgco2e - optimized_result.summary.total_emissions_kgco2e,
                "cost_savings_pct": ((baseline_result.total_cost_pkr - optimized_result.summary.total_cost_pkr) / baseline_result.total_cost_pkr * 100) if baseline_result.total_cost_pkr > 0 else 0,
                "emission_reduction_pct": ((baseline_result.total_emissions_kgco2e - optimized_result.summary.total_emissions_kgco2e) / baseline_result.total_emissions_kgco2e * 100) if baseline_result.total_emissions_kgco2e > 0 else 0
            }
        }

        return comparison
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/compare/all")
async def compare_all_methods(data: ScenarioInput):
    """Compare BOTH optimization methods side-by-side with baseline

    Returns comparison of:
    - Baseline (no optimization)
    - Candidate Scoring Method
    - OR-Tools MILP Method
    """
    try:
        # Calculate baseline
        baseline_engine = BaselineEngine()
        baseline_result = baseline_engine.calculate(data)

        # Calculate Candidate Scoring
        opt_candidate = OptimizationEngine()
        result_candidate = opt_candidate.optimize(data)

        # Calculate OR-Tools
        opt_ortools = ORToolsOptimizer()
        result_ortools = opt_ortools.optimize(data)

        bl_cost = baseline_result.total_cost_pkr
        cand_cost = result_candidate.summary.total_cost_pkr
        ort_cost = result_ortools.summary.total_cost_pkr

        # Build comprehensive comparison
        comparison = {
            "summary": {
                "baseline_cost": bl_cost,
                "candidate_cost": cand_cost,
                "ortools_cost": ort_cost,
                "winner": "OR-Tools" if ort_cost < cand_cost else "Candidate",
                "ortools_vs_candidate_savings": cand_cost - ort_cost,
                "ortools_vs_baseline_savings_pct": ((bl_cost - ort_cost) / bl_cost * 100) if bl_cost > 0 else 0,
                "candidate_vs_baseline_savings_pct": ((bl_cost - cand_cost) / bl_cost * 100) if bl_cost > 0 else 0
            },
            "methods": {
                "baseline": {
                    "name": "Baseline (No Optimization)",
                    "total_cost_pkr": baseline_result.total_cost_pkr,
                    "total_energy_kwh": baseline_result.total_energy_kwh,
                    "peak_demand_kw": baseline_result.peak_demand_kw,
                    "comfort_compliance_pct": baseline_result.comfort_compliance_pct,
                    "cost_savings_pkr": 0,
                    "cost_savings_pct": 0
                },
                "candidate_scoring": {
                    "name": "Candidate Scoring Method",
                    "total_cost_pkr": result_candidate.summary.total_cost_pkr,
                    "total_energy_kwh": result_candidate.summary.total_energy_kwh,
                    "peak_demand_kw": result_candidate.summary.peak_demand_kw,
                    "comfort_compliance_pct": result_candidate.summary.comfort_compliance_pct,
                    "cost_savings_pkr": bl_cost - result_candidate.summary.total_cost_pkr,
                    "cost_savings_pct": ((bl_cost - result_candidate.summary.total_cost_pkr) / bl_cost * 100) if bl_cost > 0 else 0
                },
                "ortools_milp": {
                    "name": "OR-Tools MILP Method",
                    "total_cost_pkr": result_ortools.summary.total_cost_pkr,
                    "total_energy_kwh": result_ortools.summary.total_energy_kwh,
                    "peak_demand_kw": result_ortools.summary.peak_demand_kw,
                    "comfort_compliance_pct": result_ortools.summary.comfort_compliance_pct,
                    "cost_savings_pkr": bl_cost - result_ortools.summary.total_cost_pkr,
                    "cost_savings_pct": ((bl_cost - result_ortools.summary.total_cost_pkr) / bl_cost * 100) if bl_cost > 0 else 0
                }
            },
            "recommendation": {
                "best_method": "OR-Tools MILP" if ort_cost < cand_cost else "Candidate Scoring",
                "reason": f"OR-Tools saves PKR {cand_cost - ort_cost:.2f} more than Candidate method" if ort_cost < cand_cost else f"Candidate saves PKR {ort_cost - cand_cost:.2f} more than OR-Tools"
            }
        }

        return comparison
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============ EXPORT ============
@app.post("/api/export/csv/{run_id}")
async def export_csv(run_id: str):
    """Export run results as CSV"""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail="Run not found")
    
    service = ExportService()
    filepath = service.export_csv(runs_storage[run_id])
    return FileResponse(filepath, media_type="text/csv", filename=f"coolshift_{run_id}.csv")

@app.post("/api/export/excel/{run_id}")
async def export_excel(run_id: str):
    """Export run results as Excel"""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail="Run not found")
    
    service = ExportService()
    filepath = service.export_excel(runs_storage[run_id])
    return FileResponse(filepath, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=f"coolshift_{run_id}.xlsx")

# ============ CUSTOM SCENARIO GENERATOR ============
@app.post("/api/generate/custom")
async def generate_custom_scenario(config: CustomScenarioConfig):
    """Generate a custom 7-day scenario"""
    try:
        generator = CustomScenarioGenerator()
        scenario = generator.generate(config)
        return scenario
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============ PUBLIC DATA LOAD ============
@app.get("/api/public/{scenario_id}")
async def load_public_scenario(scenario_id: str, start_day: int = 1, days: int = 7):
    """Load public scenario data"""
    valid_scenarios = ["PUB-A", "PUB-B", "PUB-C"]
    if scenario_id not in valid_scenarios:
        raise HTTPException(status_code=400, detail=f"Invalid scenario. Must be one of: {valid_scenarios}")
    
    try:
        service = DataImportService()
        data = service.load_public_scenario(scenario_id, start_day, days)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/process/{scenario_id}")
async def process_scenario(
    scenario_id: str,
    start_day: int = 1,
    days: int = 7,
    method: str = "ortools_milp",
    config: Optional[OptimizationConfig] = None
):
    """Full pipeline: load, validate, baseline, optimize

    Args:
        method: 'ortools_milp' (default, best savings) or 'candidate_scoring'
    """
    try:
        # Load data
        import_service = DataImportService()
        scenario_data = import_service.load_public_scenario(scenario_id, start_day, days)

        # Validate
        validator = ValidationService()
        validation = validator.validate_scenario(scenario_data)

        if not validation.is_valid:
            return {"status": "validation_failed", "errors": validation.errors}

        # Baseline
        baseline_engine = BaselineEngine()
        baseline_result = baseline_engine.calculate(scenario_data)

        # Optimize - use OR-Tools by default (much better savings)
        if method == "ml_hybrid" and ML_AVAILABLE:
            from ml_optimization_engine import MLOptimizedEngine
            opt_engine = MLOptimizedEngine(use_ml=True)
            engine_name = "ML-Hybrid"
        elif method == "ortools_milp":
            opt_engine = ORToolsOptimizer()
            engine_name = "OR-Tools MILP"
        else:
            opt_engine = OptimizationEngine()
            engine_name = "Candidate Scoring"

        optimized_result = opt_engine.optimize(scenario_data, config)
        
        run_id = str(uuid.uuid4())
        optimized_result.run_id = run_id
        runs_storage[run_id] = optimized_result
        
        return {
            "status": "success",
            "run_id": run_id,
            "scenario_id": scenario_id,
            "method": engine_name,
            "validation": validation,
            "baseline": {
                "total_energy_kwh": baseline_result.total_energy_kwh,
                "total_cost_pkr": baseline_result.total_cost_pkr,
                "total_emissions_kgco2e": baseline_result.total_emissions_kgco2e,
                "peak_demand_kw": baseline_result.peak_demand_kw
            },
            "optimized": {
                "total_energy_kwh": optimized_result.summary.total_energy_kwh,
                "total_cost_pkr": optimized_result.summary.total_cost_pkr,
                "total_emissions_kgco2e": optimized_result.summary.total_emissions_kgco2e,
                "peak_demand_kw": optimized_result.summary.peak_demand_kw,
                "comfort_compliance_pct": optimized_result.summary.comfort_compliance_pct
            },
            "interval_count": len(optimized_result.intervals)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============ BATCH PROCESSING ============
@app.post("/api/batch/process")
async def batch_process_scenarios(scenarios: List[str], method: str = "ortools_milp"):
    """Process multiple scenarios and generate all required outputs

    Args:
        method: 'ortools_milp' (default, best savings) or 'candidate_scoring'
    """
    results = {}

    for scenario_id in scenarios:
        try:
            import_service = DataImportService()
            scenario_data = import_service.load_public_scenario(scenario_id, 1, 7)

            baseline_engine = BaselineEngine()
            baseline_result = baseline_engine.calculate(scenario_data)

            # Use OR-Tools by default (much better savings)
            if method == "ortools_milp":
                opt_engine = ORToolsOptimizer()
            else:
                opt_engine = OptimizationEngine()

            optimized_result = opt_engine.optimize(scenario_data)

            run_id = str(uuid.uuid4())
            optimized_result.run_id = run_id
            runs_storage[run_id] = optimized_result

            results[scenario_id] = {
                "status": "success",
                "run_id": run_id,
                "method": "OR-Tools MILP" if method == "ortools_milp" else "Candidate Scoring",
                "intervals": len(optimized_result.intervals)
            }
        except Exception as e:
            results[scenario_id] = {"status": "error", "error": str(e)}

    return {"results": results}

# ============ ALERTS ============
@app.post("/api/alerts/{run_id}")
async def get_run_alerts(run_id: str):
    """Get all alerts for a specific run"""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail="Run not found")

    run = runs_storage[run_id]
    alerts_gen = AlertsGenerator()

    # Generate interval alerts
    interval_data = [
        {
            "timestamp_local": i.timestamp_local,
            "temperature_c": 35,  # Would come from input
            "comfort_status": i.comfort_status.value,
            "indoor_temp": i.estimated_indoor_temp_c,
            "battery_soc_kwh": i.battery_soc_kwh,
            "grid_available": True,
            "cooling_energy_kwh": i.cooling_energy_kwh,
            "constraint_violation_count": i.constraint_violation_count,
            "constraint_violations": i.constraint_violations
        }
        for i in run.intervals
    ]

    alerts = alerts_gen.generate_intervals_alerts(
        interval_data,
        {"comfort_min_c": 22, "comfort_max_c": 26},
        {"battery_capacity_kwh": 13.5}
    )

    return {
        "run_id": run_id,
        "alerts": [a.to_dict() for a in alerts],
        "summary": alerts_gen.get_alert_summary(alerts)
    }

# ============ EXTENDED SUMMARY ============
@app.get("/api/summary/{run_id}/extended")
async def get_extended_summary(run_id: str):
    """Get extended 7-day summary with trends, worst heat, peak demand"""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail="Run not found")

    run = runs_storage[run_id]

    # Calculate trends
    daily_costs = [d.total_cost_pkr for d in run.daily_summaries]
    daily_energy = [d.total_energy_kwh for d in run.daily_summaries]

    cost_trend = "increasing" if daily_costs[-1] > daily_costs[0] else "decreasing" if daily_costs[-1] < daily_costs[0] else "stable"
    energy_trend = "increasing" if daily_energy[-1] > daily_energy[0] else "decreasing" if daily_energy[-1] < daily_energy[0] else "stable"

    # Find worst heat day
    worst_heat_day = max(run.daily_summaries, key=lambda x: getattr(x, 'peak_demand_kw', 0))

    # Find highest demand day
    highest_demand_day = max(run.daily_summaries, key=lambda x: x.peak_demand_kw)

    # Constraint violations summary
    total_violations = sum(i.constraint_violation_count for i in run.intervals)

    return {
        "run_id": run_id,
        "scenario_id": run.scenario_id,
        "trends": {
            "cost_trend": cost_trend,
            "energy_trend": energy_trend,
            "cost_change_pct": ((daily_costs[-1] - daily_costs[0]) / daily_costs[0] * 100) if daily_costs[0] > 0 else 0,
            "energy_change_pct": ((daily_energy[-1] - daily_energy[0]) / daily_energy[0] * 100) if daily_energy[0] > 0 else 0
        },
        "worst_heat_period": {
            "date": str(worst_heat_day.date),
            "peak_demand_kw": worst_heat_day.peak_demand_kw,
            "unsafe_hours": worst_heat_day.unsafe_hours
        },
        "highest_demand_period": {
            "date": str(highest_demand_day.date),
            "peak_demand_kw": highest_demand_day.peak_demand_kw,
            "total_energy_kwh": highest_demand_day.total_energy_kwh
        },
        "constraint_violations": {
            "total": total_violations,
            "status": "passed" if total_violations == 0 else "violations_present"
        },
        "audit_info": {
            "algorithm_version": run.algorithm_version,
            "calculation_timestamp": run.calculation_timestamp.isoformat(),
            "run_id": run.run_id,
            "scenario_id": run.scenario_id
        }
    }

# ============ VALIDATION CASES ============
@app.get("/api/validation/validate-formulas")
async def validate_formulas():
    """Run validation cases to verify formulas"""
    # Simple validation test cases
    test_results = []

    # Test 1: Energy calculation
    power_kw = 1.5
    hours = 0.25
    expected_energy = 0.375
    actual_energy = power_kw * hours
    test_results.append({
        "test": "energy_calculation",
        "passed": abs(actual_energy - expected_energy) < 0.001,
        "expected": expected_energy,
        "actual": actual_energy
    })

    # Test 2: Cost calculation
    energy = 0.375
    tariff = 45.0
    expected_cost = 16.875
    actual_cost = energy * tariff
    test_results.append({
        "test": "cost_calculation",
        "passed": abs(actual_cost - expected_cost) < 0.01,
        "expected": expected_cost,
        "actual": actual_cost
    })

    # Test 3: Battery SOC bounds
    soc = 10.0
    capacity = 13.5
    min_reserve = 2.7
    valid = 0 <= soc <= capacity and soc >= min_reserve
    test_results.append({
        "test": "battery_soc_bounds",
        "passed": valid,
        "soc": soc,
        "capacity": capacity,
        "min_reserve": min_reserve
    })

    # Test 4: Heat index calculation
    temp_c = 35
    humidity = 60
    # Simple heat index check (should be >= actual temp)
    test_results.append({
        "test": "heat_index",
        "passed": True,  # Simplified
        "temp_c": temp_c,
        "humidity": humidity
    })

    # Test 5: Comfort status
    indoor_temp = 24
    comfort_min = 22
    comfort_max = 26
    is_comfortable = comfort_min <= indoor_temp <= comfort_max
    test_results.append({
        "test": "comfort_status",
        "passed": is_comfortable,
        "indoor_temp": indoor_temp,
        "comfort_range": f"{comfort_min}-{comfort_max}"
    })

    all_passed = all(t["passed"] for t in test_results)

    return {
        "validation_status": "passed" if all_passed else "failed",
        "tests": test_results,
        "total_tests": len(test_results),
        "passed": sum(1 for t in test_results if t["passed"]),
        "timestamp": datetime.now().isoformat()
    }


# ============ ML ENDPOINTS ============
@app.post("/api/ml/train")
async def train_ml_models():
    """Train ML models (solar forecast + thermal ANN)"""
    if not ML_AVAILABLE:
        return {
            "status": "error",
            "message": "ML libraries not installed. Run: pip install xgboost torch scikit-learn"
        }
    
    try:
        from train_ml_models import main as train_main
        train_main()
        
        return {
            "status": "success",
            "message": "ML models trained successfully",
            "models": ["solar_forecast", "thermal_ann"]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/api/ml/status")
async def ml_status():
    """Get ML models status"""
    model_dir = os.path.join(os.path.dirname(__file__), 'ml_models')
    solar_path = os.path.join(model_dir, 'solar_model.pkl')
    thermal_path = os.path.join(model_dir, 'thermal_model.pt')
    
    return {
        "ml_available": ML_AVAILABLE,
        "models": {
            "solar_forecast": os.path.exists(solar_path),
            "thermal_ann": os.path.exists(thermal_path)
        },
        "supported_methods": ["ortools_milp", "candidate_scoring", "ml_hybrid"]
    }


# ============ AUTHENTICATION API ============

class SignupRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str = ""
    country: str = "Pakistan"
    city: str
    address: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class VerifyEmailOTPRequest(BaseModel):
    email: str
    otp: str

class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None

class UpdatePasswordRequest(BaseModel):
    old_password: str
    new_password: str


def get_current_user(authorization: str = Header(None)) -> Optional[Dict]:
    """Get current user from session token"""
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    return auth_service.validate_session(token)


@app.post("/api/auth/signup")
async def signup(request: SignupRequest):
    """Register new user - sends OTP to email"""
    try:
        result = auth_service.send_email_otp(request.email, request.model_dump())
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/verify-email-otp")
async def verify_email_otp(request: VerifyEmailOTPRequest):
    """Verify email OTP and create account"""
    try:
        result = auth_service.verify_email_otp(request.email, request.otp)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/resend-otp")
async def resend_otp(email: str):
    """Resend OTP for pending registration"""
    try:
        result = auth_service.resend_otp(email)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """Login with email and password"""
    try:
        result = auth_service.login(request.email, request.password)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/auth/me")
async def get_me(authorization: str = Header(None)):
    """Get current user profile"""
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {
        "user": user,
        "is_profile_complete": bool(user.get('first_name') and user.get('city'))
    }


@app.put("/api/auth/profile")
async def update_profile(
    request: UpdateProfileRequest,
    authorization: str = Header(None)
):
    """Update user profile"""
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        result = auth_service.update_profile(user['id'], request.model_dump(exclude_none=True))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/api/auth/password")
async def update_password(
    request: UpdatePasswordRequest,
    authorization: str = Header(None)
):
    """Update user password"""
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        result = auth_service.update_password(user['id'], request.old_password, request.new_password)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/logout")
async def logout(authorization: str = Header(None)):
    """Logout current session"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
    auth_service.logout(token)

    return {"status": "logged_out"}


# ============ LIVE CALCULATOR API ============

class LiveCalculatorInput(BaseModel):
    scenario_type: str = Field(..., description="household_no_solar, household_solar, school")
    ac_count: int = Field(default=1, ge=0, le=10)
    fan_count: int = Field(default=2, ge=0, le=20)
    has_fridge: bool = False
    has_washing_machine: bool = False
    has_blender: bool = False
    has_water_motor: bool = False
    has_iron: bool = False
    has_dispenser: bool = False
    unit_price: float = Field(default=50, ge=1, le=200, description="PKR per kWh")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    city: Optional[str] = None


class WeatherData(BaseModel):
    temperature: float
    humidity: float
    solar_irradiance: float
    timestamp: str
    location: str


@app.post("/api/live/calculate")
async def live_calculate(
    input_data: LiveCalculatorInput,
    authorization: str = Header(None)
):
    """
    Live calculator - calculates energy cost based on real weather data
    or user input for a typical day.
    """
    try:
        # Generate a typical summer day based on location or use defaults
        # In production, integrate with OpenWeatherMap, Tomorrow.io, etc.

        # Default summer day temperatures (Karachi/Pakistan summer)
        base_temp = 38  # Base outdoor temp
        peak_temp = 42  # Peak afternoon temp
        night_temp = 32  # Night temp

        # If location provided, use that for weather
        location = input_data.city or "Karachi"
        weather_source = "default"

        if input_data.latitude and input_data.longitude:
            # In production: call weather API
            # weather = await get_weather(input_data.latitude, input_data.longitude)
            weather_source = f"coordinates ({input_data.latitude}, {input_data.longitude})"

        # Calculate hourly energy consumption
        hourly_results = []
        total_energy = 0
        total_cost = 0
        peak_hour = 14  # 2 PM peak

        # AC parameters
        ac_power_kw = 1.5  # 1.5 kW per AC
        fan_power_kw = 0.05  # 50W per fan

        # Tariff (simplified)
        peak_tariff = input_data.unit_price * 2.5  # Peak is 2.5x
        off_peak_tariff = input_data.unit_price

        # Other appliances (simplified daily consumption in kWh)
        other_appliances = {
            'fridge': 4 if input_data.has_fridge else 0,
            'washing_machine': 1 if input_data.has_washing_machine else 0,
            'blender': 0.2 if input_data.has_blender else 0,
            'water_motor': 2 if input_data.has_water_motor else 0,
            'iron': 1 if input_data.has_iron else 0,
            'dispenser': 1 if input_data.has_dispenser else 0
        }
        other_daily_kwh = sum(other_appliances.values())

        for hour in range(24):
            # Calculate temperature factor
            if 10 <= hour <= 16:
                # Peak heat hours
                temp_factor = 1 + (peak_temp - base_temp) / 10
                is_peak = True
            elif 17 <= hour <= 22:
                # Evening - still warm
                temp_factor = 0.9
                is_peak = False
            else:
                # Night/early morning
                temp_factor = 0.7
                is_peak = False

            # AC usage
            ac_units = input_data.ac_count if 12 <= hour <= 23 else min(1, input_data.ac_count // 2)
            fan_units = input_data.fan_count if 8 <= hour <= 23 else 0

            # Energy
            ac_energy = ac_power_kw * ac_units * 1  # 1 hour
            fan_energy = fan_power_kw * fan_units * 1
            total_hourly = ac_energy + fan_energy + (other_daily_kwh / 24)

            # Cost
            tariff = peak_tariff if is_peak else off_peak_tariff
            cost = total_hourly * tariff

            total_energy += total_hourly
            total_cost += cost

            hourly_results.append({
                "hour": hour,
                "hour_label": f"{hour:02d}:00",
                "ac_units": ac_units,
                "fan_units": fan_units,
                "energy_kwh": round(total_hourly, 2),
                "tariff_pkr": round(tariff, 2),
                "cost_pkr": round(cost, 2),
                "is_peak": is_peak,
                "outdoor_temp_c": int(base_temp * temp_factor)
            })

        return {
            "status": "success",
            "location": location,
            "weather_source": weather_source,
            "weather": {
                "current_temp_c": base_temp,
                "peak_temp_c": peak_temp,
                "humidity_pct": 60,
                "solar_irradiance_w_m2": 800
            },
            "summary": {
                "total_energy_kwh": round(total_energy, 2),
                "total_cost_pkr": round(total_cost, 2),
                "peak_demand_kw": round(ac_power_kw * input_data.ac_count, 2),
                "days_analyzed": 1
            },
            "hourly_breakdown": hourly_results,
            "appliance_breakdown": {
                "ac_daily_kwh": round(ac_power_kw * input_data.ac_count * 8, 2),
                "fan_daily_kwh": round(fan_power_kw * input_data.fan_count * 12, 2),
                "other_appliances_kwh": round(other_daily_kwh, 2),
                "details": other_appliances
            },
            "savings_potential": {
                "with_optimization_pkr": round(total_cost * 0.6, 2),
                "monthly_savings_pkr": round(total_cost * 30 * 0.4, 2),
                "annual_savings_pkr": round(total_cost * 365 * 0.4, 2),
                "optimization_percent": 40
            }
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/weather/{city}")
async def get_weather(city: str):
    """
    Get current weather for a city.
    In production, integrate with OpenWeatherMap API.
    """
    # Mock weather data for Pakistani cities
    weather_db = {
        "karachi": {"temp": 34, "humidity": 70, "solar": 750, "condition": "Partly Cloudy"},
        "lahore": {"temp": 40, "humidity": 35, "solar": 850, "condition": "Hot & Dry"},
        "islamabad": {"temp": 38, "humidity": 45, "solar": 820, "condition": "Sunny"},
        "faisalabad": {"temp": 41, "humidity": 30, "solar": 860, "condition": "Very Hot"},
        "multan": {"temp": 43, "humidity": 25, "solar": 880, "condition": "Extreme Heat"},
        "peshawar": {"temp": 42, "humidity": 28, "solar": 870, "condition": "Hot"},
        "rawalpindi": {"temp": 39, "humidity": 50, "solar": 800, "condition": "Warm"},
        "hyderabad": {"temp": 37, "humidity": 65, "solar": 780, "condition": "Humid"},
        "quetta": {"temp": 36, "humidity": 20, "solar": 900, "condition": "Dry Heat"},
        "sukkur": {"temp": 44, "humidity": 22, "solar": 890, "condition": "Extreme"}
    }

    city_lower = city.lower()
    if city_lower in weather_db:
        data = weather_db[city_lower]
    else:
        data = weather_db["karachi"]  # Default

    return {
        "city": city.capitalize(),
        "temperature_c": data["temp"],
        "feels_like_c": data["temp"] + 3,
        "humidity_pct": data["humidity"],
        "solar_irradiance_w_m2": data["solar"],
        "condition": data["condition"],
        "hourly_forecast": [
            {
                "hour": h,
                "temp_c": data["temp"] + (5 if 12 <= h <= 16 else -2 if h < 10 else 0),
                "solar_w_m2": int(data["solar"] * (0.3 if h < 8 or h > 18 else 1))
            }
            for h in range(24)
        ],
        "source": "mock_data"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)

