"""
ML Training Pipeline
Trains solar forecast and thermal models from scenario data
"""

import json
import os
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from .solar_forecast import SolarForecastModel, generate_training_data_from_scenario
from .thermal_ann import ThermalANNModel, generate_thermal_training_data


class MLTrainingPipeline:
    """
    End-to-end ML pipeline:
    1. Load scenario data
    2. Generate training data
    3. Train models
    4. Save trained models
    """
    
    def __init__(self, data_dir: str = None, model_dir: str = None):
        self.data_dir = data_dir or os.path.join(os.path.dirname(__file__), '..', 'data')
        self.model_dir = model_dir or os.path.dirname(__file__)
        
        self.solar_model = SolarForecastModel()
        self.thermal_model = ThermalANNModel(model_type='mlp')
        
        self.is_trained = False
    
    def load_scenarios(self, scenario_ids: List[str] = None) -> List[dict]:
        """Load scenario data from JSON files"""
        scenarios = []
        
        if scenario_ids is None:
            scenario_ids = ['PUB-A', 'PUB-B', 'PUB-C']
        
        for sid in scenario_ids:
            path = os.path.join(self.data_dir, f'{sid.lower()}.json')
            
            # Also check backend folder
            if not os.path.exists(path):
                backend_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', f'scenario_{sid.lower()}.json')
                if os.path.exists(backend_path):
                    path = backend_path
            
            if os.path.exists(path):
                with open(path, 'r') as f:
                    data = json.load(f)
                    scenarios.append(data)
                    print(f"Loaded scenario: {sid}")
            else:
                print(f"Scenario not found: {sid}")
        
        return scenarios
    
    def generate_solar_training_data(self, scenarios: List[dict]) -> tuple:
        """Generate training data for solar forecast model"""
        X_list, y_list = [], []
        
        for scenario in scenarios:
            X, y = generate_training_data_from_scenario(scenario)
            if X is not None:
                X_list.append(X)
                y_list.append(y)
        
        if not X_list:
            return None, None
        
        X = np.vstack(X_list)
        y = np.concatenate(y_list)
        
        print(f"Solar training data: {X.shape[0]} samples, {X.shape[1]} features")
        return X, y
    
    def generate_thermal_training_data(self, scenarios: List[dict]) -> tuple:
        """Generate training data for thermal model"""
        # Run optimization to get thermal behavior
        # For now, use physics simulation to generate synthetic labels
        X_list, y_list = [], []
        
        for scenario in scenarios:
            X, y = self._simulate_thermal_data(scenario)
            if X is not None:
                X_list.append(X)
                y_list.append(y)
        
        if not X_list:
            return None, None
        
        X = np.vstack(X_list)
        y = np.concatenate(y_list)
        
        print(f"Thermal training data: {X.shape[0]} samples, {X.shape[1]} features")
        return X, y
    
    def _simulate_thermal_data(self, scenario: dict) -> tuple:
        """Generate synthetic thermal training data using physics simulation"""
        intervals = scenario.get('interval_inputs', [])
        appliances = scenario.get('appliances', [])
        profile = scenario.get('profile', {})
        
        if not intervals:
            return None, None
        
        ac = next((a for a in appliances if a.get('appliance_type') == 'ac'), None)
        cooling_capacity = ac.get('cooling_capacity_kw', 5.0) if ac else 5.0
        
        building_area = profile.get('area_m2', 80)
        insulation = profile.get('insulation_level', 'medium')
        sun_exposure = profile.get('sun_exposure', 'high')
        
        insulation_r = {'low': 0.1, 'medium': 0.3, 'high': 0.6}.get(insulation, 0.3)
        solar_factor = {'low': 0.3, 'medium': 0.5, 'high': 0.7}.get(sun_exposure, 0.5)
        
        X, y = [], []
        
        # Initial indoor temp
        indoor_temp = intervals[0].get('temperature_c', 30) - 3
        prev_indoor = indoor_temp
        
        for i, interval in enumerate(intervals):
            outdoor_temp = interval.get('temperature_c', 30)
            solar_gain = interval.get('solar_irradiance_w_m2', 0)
            occupancy = interval.get('occupancy_count', 0)
            timestamp = interval.get('timestamp_local', '')
            
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            hour = timestamp.hour + timestamp.minute / 60
            
            # Smart cooling decision for energy savings
            tariff = interval.get('tariff_pkr_per_kwh', 25)
            is_peak = interval.get('tariff_type') == 'PEAK' or tariff >= 40
            comfort_min = profile.get('comfort_min_c', 22)
            comfort_max = profile.get('comfort_max_c', 28)

            # Energy-efficient cooling decisions
            if outdoor_temp > 32 and occupancy > 0:
                # High temp - cooling needed but optimize setpoint
                if is_peak and indoor_temp < comfort_max + 1:
                    # Peak tariff - pre-cool if comfortable, then minimize
                    cooling_on = True
                    setpoint = comfort_min
                else:
                    cooling_on = True
                    setpoint = 24
            elif outdoor_temp > 35:
                # Extreme heat - always cool
                cooling_on = True
                setpoint = 26
            elif outdoor_temp > 30 and occupancy > 0 and indoor_temp > comfort_max:
                cooling_on = True
                setpoint = 26
            else:
                cooling_on = False
                setpoint = None
            
            # Physics-based indoor temp calculation
            if cooling_on:
                # Move toward setpoint based on cooling capacity
                cooling_effect = min(1.0, cooling_capacity / 5.0)
                indoor_temp = indoor_temp + (setpoint - indoor_temp) * cooling_effect * 0.4
            else:
                # Track toward outdoor with thermal lag
                indoor_temp = indoor_temp + (outdoor_temp - indoor_temp) * 0.05
            
            # Solar gain effect
            solar_heat = solar_gain * solar_factor * building_area / 10000
            indoor_temp += solar_heat * 0.02
            
            # Occupancy heat
            indoor_temp += occupancy * 0.1
            
            indoor_temp = max(20, min(outdoor_temp + 2, indoor_temp))
            
            # Feature vector
            features = [
                outdoor_temp,
                setpoint if setpoint else outdoor_temp,
                1.0 if cooling_on else 0.0,
                cooling_capacity if cooling_on else 0.0,
                occupancy,
                solar_gain,
                building_area,
                {'low': 0, 'medium': 1, 'high': 2}.get(insulation, 1),
                {'low': 0, 'medium': 1, 'high': 2}.get(sun_exposure, 1),
                hour,
                prev_indoor
            ]
            
            X.append(features)
            y.append(indoor_temp)
            
            prev_indoor = indoor_temp
        
        return np.array(X), np.array(y)
    
    def train_all(self, scenarios: List[dict] = None, save_models: bool = True) -> dict:
        """Train both solar and thermal models"""
        
        print("=" * 50)
        print("ML Training Pipeline")
        print("=" * 50)
        
        # Load scenarios
        if scenarios is None:
            scenarios = self.load_scenarios()
        
        if not scenarios:
            print("No scenarios loaded!")
            return {}
        
        # Train solar model
        print("\n[1/2] Training Solar Forecast Model...")
        X_solar, y_solar = self.generate_solar_training_data(scenarios)
        
        if X_solar is not None:
            try:
                self.solar_model.train(X_solar, y_solar)
                if save_models:
                    solar_path = os.path.join(self.model_dir, 'solar_model.pkl')
                    print(f"Solar model saved to: {solar_path}")
            except ImportError as e:
                print(f"Solar model training skipped: {e}")
        else:
            print("No solar training data generated")
        
        # Train thermal model
        print("\n[2/2] Training Thermal ANN Model...")
        X_thermal, y_thermal = self.generate_thermal_training_data(scenarios)
        
        if X_thermal is not None:
            try:
                self.thermal_model.train(X_thermal, y_thermal, epochs=100)
                if save_models:
                    thermal_path = os.path.join(self.model_dir, 'thermal_model.pt')
                    self.thermal_model.save_model(thermal_path)
                    print(f"Thermal model saved to: {thermal_path}")
            except ImportError as e:
                print(f"Thermal model training skipped: {e}")
        else:
            print("No thermal training data generated")
        
        self.is_trained = True
        
        print("\n" + "=" * 50)
        print("Training Complete!")
        print("=" * 50)
        
        return {
            'solar_model': self.solar_model,
            'thermal_model': self.thermal_model
        }
    
    def load_trained_models(self) -> bool:
        """Load pre-trained models if available"""
        solar_path = os.path.join(self.model_dir, 'solar_model.pkl')
        thermal_path = os.path.join(self.model_dir, 'thermal_model.pt')
        
        solar_loaded = False
        thermal_loaded = False
        
        if os.path.exists(solar_path):
            self.solar_model = SolarForecastModel(model_path=solar_path)
            solar_loaded = True
            print(f"Loaded solar model from: {solar_path}")
        
        if os.path.exists(thermal_path):
            self.thermal_model = ThermalANNModel(model_path=thermal_path)
            thermal_loaded = True
            print(f"Loaded thermal model from: {thermal_path}")
        
        self.is_trained = solar_loaded and thermal_loaded
        return self.is_trained
    
    def evaluate_models(self, test_scenario: dict) -> dict:
        """Evaluate models on a test scenario"""
        results = {}
        
        # Solar evaluation
        if self.solar_model.model is not None:
            X, y = generate_training_data_from_scenario(test_scenario)
            if X is not None:
                predictions = self.solar_model.model.predict(X)
                mse = np.mean((predictions - y) ** 2)
                mae = np.mean(np.abs(predictions - y))
                results['solar_mse'] = mse
                results['solar_mae'] = mae
                print(f"Solar Model - MSE: {mse:.4f}, MAE: {mae:.4f}")
        
        # Thermal evaluation
        if self.thermal_model.model is not None:
            X, y = self._simulate_thermal_data(test_scenario)
            if X is not None:
                scaler_X = self.thermal_model.scaler_X
                scaler_y = self.thermal_model.scaler_y
                
                X_scaled = scaler_X.transform(X)
                y_pred = []
                
                self.thermal_model.model.eval()
                with torch.no_grad():
                    for i in range(len(X_scaled)):
                        pred = self.thermal_model.model(
                            torch.FloatTensor(X_scaled[i:i+1])
                        ).item()
                        y_pred.append(pred)
                
                y_pred = np.array(y_pred) * scaler_y.std_ + scaler_y.mean_
                mse = np.mean((y_pred - y) ** 2)
                mae = np.mean(np.abs(y_pred - y))
                results['thermal_mse'] = mse
                results['thermal_mae'] = mae
                print(f"Thermal Model - MSE: {mse:.4f}, MAE: {mae:.4f}")
        
        return results


# Also import torch for evaluation
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


if __name__ == '__main__':
    # Run training
    pipeline = MLTrainingPipeline()
    models = pipeline.train_all()
    
    # Test predictions
    print("\n" + "=" * 50)
    print("Testing Predictions")
    print("=" * 50)
    
    test_time = datetime(2024, 7, 1, 12, 0)
    
    # Solar test
    solar_result = pipeline.solar_model.predict(
        irradiance=800,
        temp=38,
        humidity=40,
        timestamp=test_time,
        solar_capacity_kw=5.0
    )
    print(f"\nSolar Prediction (noon, clear sky):")
    print(f"  Solar kWh: {solar_result['solar_kwh']}")
    print(f"  Confidence: {solar_result['confidence']}")
    
    # Thermal test
    thermal_result = pipeline.thermal_model.predict(
        outdoor_temp=40,
        setpoint=24,
        cooling_on=True,
        cooling_capacity_kw=5.0,
        occupancy=3,
        solar_gain=700,
        building_area=80,
        insulation='medium',
        sun_exposure='high',
        hour=14.0,
        prev_indoor_temp=26.0
    )
    print(f"\nThermal Prediction (hot day, AC on):")
    print(f"  Indoor Temp: {thermal_result['indoor_temp']}°C")
    print(f"  Confidence: {thermal_result['confidence']}")
    print(f"  Comfort: {thermal_result['predicted_comfort']}")
