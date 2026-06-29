"""
Solar Generation Forecast Model
Uses XGBoost for predicting solar output from weather features
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional, List
import pickle
import os

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

class SolarForecastModel:
    """
    Predicts solar generation (kWh) from weather features.
    Features: solar_irradiance, humidity, temperature, time_of_day, day_of_year
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.feature_names = [
            'solar_irradiance_w_m2',
            'temperature_c',
            'humidity_pct',
            'hour',
            'day_of_year',
            'cloud_factor'
        ]
        self._load_or_init_model(model_path)

    def _load_or_init_model(self, model_path: Optional[str]):
        if model_path and os.path.exists(model_path):
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
        elif HAS_XGB:
            self.model = xgb.XGBRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                objective='reg:squarederror',
                random_state=42
            )

    def _prepare_features(self, irradiance: float, temp: float, 
                         humidity: float, timestamp: datetime) -> np.ndarray:
        """Extract features from raw data"""
        hour = timestamp.hour + timestamp.minute / 60
        day_of_year = timestamp.timetuple().tm_yday
        
        # Cloud factor: estimate from humidity and time of day
        # More humidity = more clouds = less solar
        base_cloud_factor = 1.0
        if hour < 8 or hour > 17:
            base_cloud_factor *= 0.3
        elif hour < 10 or hour > 15:
            base_cloud_factor *= 0.8
        
        cloud_factor = base_cloud_factor * (1 - humidity / 200)

        return np.array([[
            irradiance,
            temp,
            humidity,
            hour,
            day_of_year,
            cloud_factor
        ]])

    def predict(self, irradiance: float, temp: float, 
               humidity: float, timestamp: datetime,
               solar_capacity_kw: float = 1.0,
               interval_hours: float = 0.25) -> dict:
        """
        Predict solar generation for this interval.
        
        Returns:
            dict with 'solar_kwh', 'confidence', 'peak_expected'
        """
        features = self._prepare_features(irradiance, temp, humidity, timestamp)
        
        if self.model is not None:
            raw_pred = self.model.predict(features)[0]
        else:
            # Fallback: simple physics-based estimate
            # Solar efficiency ~15-20%, peak at noon
            hour = timestamp.hour + timestamp.minute / 60
            efficiency = 0.18 * max(0, min(1, (hour - 6) / 6)) * max(0, min(1, (20 - hour) / 6))
            raw_pred = irradiance / 1000 * solar_capacity_kw * efficiency * interval_hours

        # Convert to kWh for interval
        solar_kwh = max(0, raw_pred * interval_hours)
        
        # Confidence based on model availability and irradiance
        confidence = 0.9 if self.model else 0.6
        if irradiance < 50:
            confidence *= 0.7
        
        return {
            'solar_kwh': round(solar_kwh, 4),
            'confidence': round(confidence, 2),
            'peak_expected': irradiance > 600
        }

    def predict_ahead(self, weather_forecast: List[dict], 
                     solar_capacity_kw: float = 1.0,
                     interval_hours: float = 0.25) -> List[dict]:
        """Predict solar generation for multiple intervals"""
        results = []
        for w in weather_forecast:
            result = self.predict(
                irradiance=w.get('solar_irradiance_w_m2', 0),
                temp=w.get('temperature_c', 30),
                humidity=w.get('humidity_pct', 50),
                timestamp=w.get('timestamp', datetime.now()),
                solar_capacity_kw=solar_capacity_kw,
                interval_hours=interval_hours
            )
            results.append(result)
        return results

    def train(self, X: np.ndarray, y: np.ndarray, save_path: Optional[str] = None):
        """Train the model"""
        if not HAS_XGB:
            raise ImportError("XGBoost not installed. Run: pip install xgboost")
        
        self.model.fit(X, y)
        
        if save_path:
            with open(save_path, 'wb') as f:
                pickle.dump(self.model, f)

    def get_feature_importance(self) -> dict:
        """Return feature importance scores"""
        if self.model is None or not hasattr(self.model, 'feature_importances_'):
            return {}
        
        return dict(zip(
            self.feature_names,
            self.model.feature_importances_.tolist()
        ))


def generate_training_data_from_scenario(scenario_data: dict) -> tuple:
    """
    Generate training data from scenario JSON.
    Uses actual solar irradiance and known capacity to create labels.
    """
    intervals = scenario_data.get('interval_inputs', [])
    energy_assets = scenario_data.get('energy_assets', {})
    solar_capacity = energy_assets.get('solar_capacity_kw', 0)
    
    if not intervals or solar_capacity == 0:
        return None, None
    
    X, y = [], []
    
    for i, interval in enumerate(intervals):
        irradiance = interval.get('solar_irradiance_w_m2', 0)
        temp = interval.get('temperature_c', 30)
        humidity = interval.get('relative_humidity_pct', 50)
        timestamp = interval.get('timestamp_local', '')
        
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        hour = timestamp.hour + timestamp.minute / 60
        day_of_year = timestamp.timetuple().tm_yday
        
        # Simple cloud estimation
        cloud_factor = 1.0
        if hour < 8 or hour > 17:
            cloud_factor = 0.3
        elif hour < 10 or hour > 15:
            cloud_factor = 0.8
        cloud_factor *= (1 - humidity / 200)
        
        # Label: actual solar generation (estimated from irradiance * efficiency)
        # This is synthetic but physically realistic
        solar_efficiency = 0.18
        solar_generation = irradiance / 1000 * solar_capacity * solar_efficiency * 0.25
        
        X.append([
            irradiance, temp, humidity, hour, day_of_year, cloud_factor
        ])
        y.append(solar_generation)
    
    return np.array(X), np.array(y)


if __name__ == '__main__':
    # Test the model
    model = SolarForecastModel()
    
    # Test prediction
    test_time = datetime(2024, 7, 1, 12, 0)
    result = model.predict(
        irradiance=800,
        temp=38,
        humidity=40,
        timestamp=test_time,
        solar_capacity_kw=5.0
    )
    print(f"Solar prediction at noon: {result}")
    
    # Test with low irradiance
    result2 = model.predict(
        irradiance=100,
        temp=32,
        humidity=70,
        timestamp=test_time,
        solar_capacity_kw=5.0
    )
    print(f"Solar prediction with clouds: {result2}")
