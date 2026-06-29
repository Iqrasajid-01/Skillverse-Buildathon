# CoolShift AI - Smart Energy Optimization Platform

> **Rapid Forge Buildathon | SDG 7 & 13**
> AI-Powered Cooling Management System for Extreme Heat Conditions

---

## 🎯 Overview

**CoolShift AI** is an intelligent energy optimization platform that combines machine learning, constraint-based optimization, and real-time forecasting to minimize electricity costs while maintaining comfort during extreme heat. The system processes 96 daily intervals (15-minute resolution) to generate optimal AC scheduling for households, schools, and commercial buildings.

### Key Metrics
| Metric | Target |
|--------|--------|
| Cost Savings | 35-60% vs Baseline |
| CO₂ Reduction | 25-45% |
| Peak Demand Reduction | 20-40% |
| Solar Utilization | Up to 85% |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CoolShift AI Platform                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐             │
│  │   Frontend   │    │   Backend    │    │  ML Engine   │             │
│  │   (React)    │◄──►│  (FastAPI)   │◄──►│  (PyTorch)   │             │
│  └──────────────┘    └──────────────┘    └──────────────┘             │
│         │                   │                   │                       │
│         ▼                   ▼                   ▼                       │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │                    Core Services Layer                        │       │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│       │
│  │  │   Baseline  │ │ Optimization│ │    Solar + Battery      ││       │
│  │  │   Engine    │ │   Engine     │ │    Management           ││       │
│  │  └─────────────┘ └─────────────┘ └─────────────────────────┘│       │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│       │
│  │  │   Thermal   │ │  Validation  │ │    Export Service       ││       │
│  │  │   Model     │ │   Service    │ │    (CSV/Excel)          ││       │
│  │  └─────────────┘ └─────────────┘ └─────────────────────────┘│       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                  │                                       │
│                                  ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │                    Data Layer                                 │       │
│  │  PostgreSQL │ JSON Scenarios │ Excel Templates │ SQLite     │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Flow
```
User Input → Validation → Baseline Calculation → ML Prediction
                                              ↓
Weather/Tariff Data ──► Optimization Engine ──► Schedule Output
                           │
                    ┌──────┴──────┐
                    ▼             ▼
              OR-Tools LP    Rule-Based
              Solver         Fallback
                    │
                    ▼
             Dashboard + Export
```

---

## 🛠️ Technology Stack

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| **FastAPI** | 0.109.0 | REST API Framework |
| **Uvicorn** | 0.27.0 | ASGI Server |
| **Pydantic** | 2.5.3 | Data Validation |
| **Pandas** | 2.2.0 | Data Processing |
| **NumPy** | 1.26.3 | Numerical Computing |

### Optimization
| Technology | Version | Purpose |
|------------|---------|---------|
| **OR-Tools** | 9.12 | Linear/Integer Programming Solver |
| **SciPy** | - | Scientific Computing |

### Machine Learning
| Technology | Version | Purpose |
|------------|---------|---------|
| **PyTorch** | 2.0+ | Neural Network Training |
| **XGBoost** | 2.0+ | Gradient Boosting |
| **Scikit-learn** | 1.3+ | ML Utilities |

### Data Storage
| Technology | Purpose |
|------------|---------|
| **PostgreSQL** | Primary Database |
| **SQLite** | Local/Testing |
| **JSON** | Scenario Data |
| **Excel** | Import/Export |

### Frontend
| Technology | Purpose |
|------------|---------|
| **React** | UI Framework |
| **Vite** | Build Tool |
| **Recharts** | Data Visualization |
| **Axios** | HTTP Client |

---

## 🤖 AI/ML Capabilities

### 1. Solar Generation Forecasting
```
Input: Weather data (temperature, irradiance, humidity)
       Historical generation patterns
       Time-of-day patterns
Output: 15-minute ahead solar production forecast
Model: XGBoost + Random Forest Ensemble
Accuracy: ~85-90%
```

### 2. Thermal Indoor Prediction (ANN)
```
Input: Outdoor temperature
       AC setpoint
       Building characteristics
       Time of day
Output: Predicted indoor temperature
Model: PyTorch LSTM/GRU Neural Network
Error: ±0.5°C typical
```

### 3. Optimization Engine
```
Methods:
├── OR-Tools Linear Programming (Primary)
│   └── Minimize: Cost + λ×Discomfort + μ×Emissions
│   └── Subject to: Hard constraints (battery SOC, capacity)
│
└── Rule-Based Fallback
    └── Priority: Solar > Battery > Grid
    └── Real-time heuristic evaluation
```

---

## 📁 Project Structure

```
CoolShift/
│
├── backend/
│   ├── main.py                    # FastAPI application entry
│   ├── data_models.py             # Pydantic schemas
│   │
│   ├── core_engine/
│   │   ├── data_import.py         # Excel/JSON import service
│   │   ├── baseline_engine.py      # Current usage calculation
│   │   ├── optimization_engine.py  # Rule-based optimizer
│   │   └── ortools_optimizer.py    # OR-Tools LP solver
│   │
│   ├── ml_engine/
│   │   ├── ml_models/
│   │   │   ├── solar_forecast.py   # XGBoost solar predictor
│   │   │   ├── thermal_ann.py      # LSTM thermal model
│   │   │   ├── training_pipeline.py # Training orchestration
│   │   │   └── train_ml_models.py  # Training script
│   │   └── ml_optimization_engine.py # ML-enhanced optimizer
│   │
│   ├── energy_modules/
│   │   ├── solar_battery.py       # Solar + battery simulation
│   │   └── thermal_model.py       # RC thermal model
│   │
│   ├── services/
│   │   ├── validation.py          # I/O validation
│   │   ├── export_service.py      # CSV/Excel export
│   │   ├── alerts.py              # Alert generation
│   │   └── database.py            # PostgreSQL integration
│   │
│   ├── auth.py                    # Authentication
│   └── requirements.txt           # Python dependencies
│
├── src/
│   ├── client/                    # React frontend
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── Dashboard.jsx
│   │   │   │   ├── KPICard.jsx
│   │   │   │   ├── ComparisonChart.jsx
│   │   │   │   └── ScheduleTable.jsx
│   │   │   ├── services/api.js
│   │   │   └── App.jsx
│   │   └── package.json
│   │
│   └── server/                    # Express proxy (optional)
│
├── data/                         # Scenario data
│   ├── scenarios/
│   └── outputs/
│
├── public/                       # Static assets
│
├── package.json                  # Root package config
├── README.md                     # This file
└── ARCHITECTURE.md              # Detailed architecture docs
```

---

## ⚙️ Core Modules

### Baseline Engine
Calculates current energy consumption without optimization:
- Reads actual tariff rates (peak/off-peak)
- Computes interval-by-interval energy costs
- Generates comparison baseline for savings

### Optimization Engine
Multi-objective optimization with configurable weights:
```python
weights = {
    "cost": 0.35,        # Minimize electricity cost
    "comfort": 0.30,     # Maintain indoor temperature
    "emissions": 0.20,   # Reduce carbon footprint
    "peak_demand": 0.15  # Shift load away from peaks
}
```

### Solar + Battery Module
- Simulates solar panel generation
- Manages battery charge/discharge cycles
- Respects SOC bounds and minimum reserves

### Validation Service
- Ensures grid availability respected
- Validates battery SOC (0 to capacity)
- Checks appliance capacity limits
- Verifies setpoint bounds

---

## 📊 Data Specifications

### Input Scenarios
| Scenario | Description | Duration | Intervals |
|----------|-------------|----------|-----------|
| PUB-A | Household (No Solar) | 30 days | 8,640 |
| PUB-B | Household (Solar + Battery) | 30 days | 8,640 |
| PUB-C | School/Small Office | 30 days | 8,640 |

### Output Windows
- **Default**: 7 days (672 intervals)
- **Extended**: 30 days (2,880 intervals)
- **Custom**: Up to 30 days

---

## 🚀 Quick Start

### Prerequisites
```bash
# Python 3.10+
python --version

# Node.js 18+
node --version

# PostgreSQL (optional, for production)
```

### Installation

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python main.py
```
API: http://localhost:8000

**Frontend:**
```bash
cd src/client
npm install
npm run dev
```
Dashboard: http://localhost:3000

### Run Full Stack
```bash
# Terminal 1 - Backend
cd backend && python main.py

# Terminal 2 - Frontend
cd src/client && npm run dev
```

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | System health check |
| GET | `/api/scenarios` | List available scenarios |
| POST | `/api/import/excel` | Import Excel data |
| POST | `/api/run/baseline` | Calculate baseline |
| POST | `/api/run/optimize` | Run optimization |
| GET | `/api/results/{run_id}` | Get results |
| POST | `/api/export/csv` | Export to CSV |

---

## 📈 Dashboard Features

### KPIs
- **Cost Savings** (PKR)
- **Energy Reduction** (kWh)
- **CO₂ Avoided** (kg)
- **Peak Reduction** (kW)

### Visualizations
- Daily Cost Comparison (Bar Chart)
- Temperature & Resources (Area Chart)
- 24-Hour Schedule Table

---

## 🎯 Optimization Modes

### 1. Cost Priority
Maximize savings regardless of comfort
```
Weights: cost=0.6, comfort=0.1, emissions=0.2, peak=0.1
```

### 2. Comfort Priority
Maintain ideal temperature range
```
Weights: cost=0.2, comfort=0.5, emissions=0.2, peak=0.1
```

### 3. Eco Mode
Minimize carbon footprint
```
Weights: cost=0.2, comfort=0.3, emissions=0.4, peak=0.1
```

### 4. Balanced
Equal priorities
```
Weights: cost=0.25, comfort=0.25, emissions=0.25, peak=0.25
```

---

## 🔒 Constraints Enforced

| Constraint | Description |
|------------|-------------|
| Grid Availability | Cannot use grid during outages |
| Battery SOC | 0 ≤ SOC ≤ capacity |
| Minimum Reserve | SOC ≥ min_reserve_kwh |
| Appliance Capacity | Units ≤ max_ac_units |
| Setpoint Bounds | min_setpoint ≤ T ≤ max_setpoint |
| Energy Balance | Generation = Consumption |

---

## 🧪 Testing

```bash
cd backend
python run_tests.py
```

---

## 📜 License

MIT License

---

**Built for Rapid Forge Buildathon | SDG 7 & 13**
