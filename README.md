# CoolShift - Smart Energy Optimization Platform

**Rapid Forge Buildathon | SDG 7 & 13**

An intelligent digital platform for affordable, energy-efficient, and low-carbon cooling during extreme heat.

## 🎯 Challenge

Build a decision and optimization platform that helps users operate cooling appliances more intelligently while:
- Maintaining safe and comfortable indoor conditions
- Reducing electricity cost
- Minimizing peak-hour energy demand
- Reducing carbon emissions

## 📋 Requirements Met

### ✅ Mandatory Workflow
- [x] User and Building Profiles
- [x] Data Import and Validation
- [x] Weather and Heat Analysis
- [x] Baseline Engine (current usage calculation)
- [x] Optimization Engine (constraint-aware scheduling)
- [x] Clean-Energy Module (solar + battery)
- [x] Outage Handling
- [x] Dashboard with KPIs
- [x] Explainability (reason codes)
- [x] History and Export

### ✅ Data Requirements
- [x] 3 Public Scenarios (PUB-A, PUB-B, PUB-C)
- [x] 30 days × 96 intervals = 8,640 records capacity
- [x] 7-day output windows
- [x] Custom scenario generator (672+ intervals)
- [x] Minimum 2,688 interval outputs

### ✅ Hard Constraints
- [x] Grid availability respected
- [x] Battery SOC bounds (0 to capacity)
- [x] Minimum reserve respected
- [x] Appliance capacity limits
- [x] Setpoint limits
- [x] Energy balance validation

## 🚀 Quick Start

### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
python main.py
```
Backend runs on: http://localhost:8000

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```
Frontend runs on: http://localhost:3000

### Or Run Both
```bash
# Terminal 1 - Backend
cd backend && python main.py

# Terminal 2 - Frontend
cd frontend && npm run dev
```

## 📊 Features

### Dashboard KPIs
- Cost Savings (PKR)
- Energy Reduction (kWh)
- CO₂ Emissions Avoided
- Peak Demand Reduction

### Visualizations
- Daily Cost Comparison (Bar Chart)
- Temperature & Resources (Area Chart)
- 24-Hour Schedule Table with:
  - Outdoor/Indoor Temperature
  - Solar Generation
  - AC Units Control
  - Battery SOC
  - Cost per Interval
  - Comfort Status
  - Reason Codes

### Optimization Engine
- Multi-objective optimization (cost, comfort, emissions, peak)
- Solar utilization maximization
- Battery charge/discharge optimization
- Grid outage handling
- Comfort priority during occupied hours

## 📁 Project Structure

```
CoolShift/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── data_models.py       # Pydantic schemas
│   ├── data_import.py       # Excel/JSON import
│   ├── baseline_engine.py   # Baseline calculations
│   ├── optimization_engine.py # Optimization logic
│   ├── solar_battery.py     # Solar & battery module
│   ├── thermal_model.py     # Indoor temperature estimation
│   ├── validation.py        # Input/output validation
│   ├── export_service.py    # CSV/Excel export
│   └── custom_scenario.py   # Custom scenario generator
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main application
│   │   ├── components/
│   │   │   ├── KPICard.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── ComparisonChart.jsx
│   │   │   └── ScheduleTable.jsx
│   │   └── services/
│   │       └── api.js
│   └── package.json
└── README.md
```

## 🔧 Configuration

### Scenarios
- **PUB-A**: Household without Solar - Tests affordability & peak tariff
- **PUB-B**: Household with Solar & Battery - Tests solar utilization
- **PUB-C**: School/Small Office - Tests multi-zone optimization

### Optimization Weights (Configurable)
```python
objective_weights = {
    "cost": 0.35,      # Electricity cost priority
    "comfort": 0.30,   # Comfort maintenance
    "emissions": 0.20, # Carbon reduction
    "peak_demand": 0.15 # Peak load reduction
}
```

## 📤 Output Format

### Interval Output
| Field | Description |
|-------|-------------|
| timestamp_local | 15-minute interval timestamp |
| recommended_ac_units_on | AC units to operate |
| recommended_ac_setpoint_c | Target temperature |
| grid_energy_kwh | Grid electricity used |
| solar_energy_used_kwh | Solar energy consumed |
| battery_charge_kwh | Battery charging |
| battery_discharge_kwh | Battery discharging |
| battery_soc_kwh | End-of-interval SOC |
| estimated_indoor_temp_c | Indoor temperature |
| comfort_status | within_range/warning/unsafe |
| interval_cost_pkr | Electricity cost |
| reason_code | HEAT_RISK/SOLAR_AVAILABLE/etc |
| explanation | Human-readable reason |

## 📈 Judging Criteria

| Criterion | Weight |
|-----------|--------|
| Optimization & Constraints | 20% |
| Completion + Correctness | 15% + 15% |
| SDG Impact | 10% |
| Architecture | 10% |
| Innovation | 10% |
| UX + Explainability | 10% |
| Testing + Documentation | 5% |
| Pitch + Demo | 5% |

## 👥 Team

Built for the Rapid Forge Buildathon CoolShift Challenge.

## 📜 License

MIT License
