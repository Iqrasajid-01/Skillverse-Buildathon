"""
Train ML Models
Run this script to train solar forecast and thermal ANN models
"""

import json
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from ml_models import MLTrainingPipeline


def load_scenario(scenario_id: str) -> dict:
    """Load scenario from JSON file"""
    path = os.path.join(os.path.dirname(__file__), '..', 'scenario.json')
    if os.path.exists(path):
        with open(path, 'r') as f:
            data = json.load(f)
            if data.get('scenario_id') == scenario_id:
                return data
    
    # Try PUB-A, PUB-B, PUB-C naming
    for name in [scenario_id, scenario_id.lower(), f'scenario_{scenario_id.lower()}']:
        path = os.path.join(os.path.dirname(__file__), '..', f'{name}.json')
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    
    return None


def main():
    print("=" * 60)
    print("ML Model Training for CoolShift")
    print("=" * 60)
    
    # Load scenarios
    scenario_ids = ['PUB-A', 'PUB-B', 'PUB-C']
    scenarios = []
    
    for sid in scenario_ids:
        scenario = load_scenario(sid)
        if scenario:
            scenarios.append(scenario)
            print(f"Loaded: {sid}")
        else:
            print(f"Not found: {sid}")
    
    if not scenarios:
        print("\nNo scenarios found! Using synthetic data for training...")
        # Generate synthetic training data
        from ml_models import SolarForecastModel, ThermalANNModel
        import numpy as np
        from datetime import datetime
        
        # Generate synthetic solar data
        print("\nGenerating synthetic solar training data...")
        np.random.seed(42)
        n_samples = 1000
        
        X_solar = []
        y_solar = []
        
        for _ in range(n_samples):
            hour = np.random.uniform(6, 18)
            day_of_year = np.random.randint(1, 365)
            irradiance = np.random.uniform(0, 1000) * max(0, min(1, (hour - 6) / 12))
            temp = np.random.uniform(25, 45)
            humidity = np.random.uniform(20, 90)
            cloud_factor = 1 - humidity / 200
            
            solar_kwh = irradiance / 1000 * 5 * 0.18 * 0.25 * cloud_factor
            
            X_solar.append([irradiance, temp, humidity, hour, day_of_year, cloud_factor])
            y_solar.append(solar_kwh)
        
        X_solar = np.array(X_solar)
        y_solar = np.array(y_solar)
        
        print(f"Generated {len(X_solar)} solar training samples")
        
        # Generate synthetic thermal data
        print("\nGenerating synthetic thermal training data...")
        X_thermal = []
        y_thermal = []
        
        indoor_temp = 28
        for _ in range(n_samples):
            outdoor_temp = np.random.uniform(28, 45)
            hour = np.random.uniform(0, 24)
            solar_gain = np.random.uniform(0, 900)
            occupancy = np.random.randint(0, 6)
            
            cooling_on = np.random.choice([True, False])
            setpoint = 24 if cooling_on else outdoor_temp
            
            if cooling_on:
                indoor_temp = indoor_temp + (setpoint - indoor_temp) * 0.4
            else:
                indoor_temp = indoor_temp + (outdoor_temp - indoor_temp) * 0.05
            
            indoor_temp = max(20, min(45, indoor_temp))
            
            X_thermal.append([
                outdoor_temp, setpoint, 1 if cooling_on else 0,
                5 if cooling_on else 0, occupancy, solar_gain,
                80, 1, 1, hour, indoor_temp
            ])
            y_thermal.append(indoor_temp)
        
        X_thermal = np.array(X_thermal)
        y_thermal = np.array(y_thermal)
        
        print(f"Generated {len(X_thermal)} thermal training samples")
        
        # Train models
        model_dir = os.path.join(os.path.dirname(__file__), 'ml_models')
        
        # Solar model
        print("\n" + "=" * 40)
        print("Training Solar Forecast Model")
        print("=" * 40)
        
        try:
            from ml_models import SolarForecastModel
            solar_model = SolarForecastModel()
            solar_model.train(X_solar, y_solar)
            
            # Save
            import pickle
            save_path = os.path.join(model_dir, 'solar_model.pkl')
            with open(save_path, 'wb') as f:
                pickle.dump(solar_model.model, f)
            print(f"Solar model saved to: {save_path}")
        except ImportError:
            print("XGBoost not available. Install with: pip install xgboost")
        
        # Thermal model
        print("\n" + "=" * 40)
        print("Training Thermal ANN Model")
        print("=" * 40)
        
        try:
            from ml_models import ThermalANNModel
            thermal_model = ThermalANNModel(model_type='mlp')
            thermal_model.train(X_thermal, y_thermal, epochs=100)
            
            # Save
            thermal_path = os.path.join(model_dir, 'thermal_model.pt')
            thermal_model.save_model(thermal_path)
            print(f"Thermal model saved to: {thermal_path}")
        except ImportError:
            print("PyTorch not available. Install with: pip install torch")
    
    else:
        # Train from real scenarios
        pipeline = MLTrainingPipeline()
        models = pipeline.train_all(scenarios=scenarios)
    
    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)
    
    # Quick test
    print("\nQuick Test Predictions:")
    print("-" * 40)
    
    try:
        from ml_models import SolarForecastModel, ThermalANNModel
        from datetime import datetime
        
        model_dir = os.path.join(os.path.dirname(__file__), 'ml_models')
        
        solar_model = SolarForecastModel(
            model_path=os.path.join(model_dir, 'solar_model.pkl')
        )
        
        test_time = datetime(2024, 7, 1, 12, 0)
        solar_result = solar_model.predict(
            irradiance=800, temp=38, humidity=40,
            timestamp=test_time, solar_capacity_kw=5.0
        )
        print(f"Solar at noon: {solar_result['solar_kwh']:.3f} kWh (confidence: {solar_result['confidence']})")
        
        thermal_model = ThermalANNModel(
            model_path=os.path.join(model_dir, 'thermal_model.pt')
        )
        thermal_result = thermal_model.predict(
            outdoor_temp=40, setpoint=24, cooling_on=True,
            cooling_capacity_kw=5.0, occupancy=3, solar_gain=700,
            building_area=80, insulation='medium', sun_exposure='high',
            hour=14.0, prev_indoor_temp=26.0
        )
        print(f"Indoor temp (AC on): {thermal_result['indoor_temp']}°C (confidence: {thermal_result['confidence']})")
        
    except Exception as e:
        print(f"Test failed: {e}")
    
    print("\nTo use ML models, run ml_optimization_engine.py instead of optimization_engine.py")


if __name__ == '__main__':
    main()
