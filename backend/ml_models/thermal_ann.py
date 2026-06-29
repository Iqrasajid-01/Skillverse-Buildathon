"""
ANN-based Thermal Model
Uses neural network to predict indoor temperature from building/weather conditions.
Includes both MLP (static) and LSTM (time-series) variants.
"""

import numpy as np
from typing import Optional, List, Dict
from datetime import datetime
import pickle
import os

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class ThermalMLP(nn.Module):
    """Simple 3-layer MLP for indoor temperature prediction"""
    
    def __init__(self, input_size: int, hidden_size: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
    
    def forward(self, x):
        return self.net(x)


class ThermalLSTM(nn.Module):
    """LSTM for time-series temperature prediction"""
    
    def __init__(self, input_size: int, hidden_size: int = 64, num_layers: int = 2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2
        )
        self.fc = nn.Linear(hidden_size, 1)
    
    def forward(self, x):
        # x shape: (batch, seq_len, features)
        lstm_out, _ = self.lstm(x)
        out = self.fc(lstm_out[:, -1, :])  # Take last output
        return out


class ThermalANNModel:
    """
    Neural network-based indoor temperature prediction.
    
    Supports:
    - MLP: Fast, good for single-step prediction
    - LSTM: Better for time-series, captures thermal inertia
    """
    
    FEATURE_NAMES = [
        'outdoor_temp',
        'setpoint',
        'cooling_on',
        'cooling_capacity_kw',
        'occupancy',
        'solar_gain',
        'building_area',
        'insulation_code',
        'sun_exposure_code',
        'hour',
        'prev_indoor_temp'
    ]
    
    INSULATION_MAP = {'low': 0, 'medium': 1, 'high': 2}
    SUN_EXPOSURE_MAP = {'low': 0, 'medium': 1, 'high': 2}
    
    def __init__(self, model_type: str = 'mlp', model_path: Optional[str] = None):
        self.model_type = model_type
        self.model = None
        self.scaler_X = None
        self.scaler_y = None
        self.device = None
        self._initialized = False
        self._load_or_init(model_path)
    
    def _load_or_init(self, model_path: Optional[str]):
        if model_path and os.path.exists(model_path):
            self._load_model(model_path)
        elif HAS_TORCH:
            self._initialized = True
    
    def _load_model(self, path: str):
        if not HAS_TORCH:
            return
        
        checkpoint = torch.load(path, map_location='cpu', weights_only=False)
        self.model_type = checkpoint.get('model_type', 'mlp')
        
        if self.model_type == 'lstm':
            self.model = ThermalLSTM(
                input_size=checkpoint['input_size'],
                hidden_size=checkpoint.get('hidden_size', 64)
            )
        else:
            self.model = ThermalMLP(
                input_size=checkpoint['input_size'],
                hidden_size=checkpoint.get('hidden_size', 64)
            )
        
        self.model.load_state_dict(checkpoint['model_state'])
        self.model.eval()
        self.scaler_X = checkpoint.get('scaler_X')
        self.scaler_y = checkpoint.get('scaler_y')
        self._initialized = True
    
    def save_model(self, path: str):
        if not HAS_TORCH or self.model is None:
            return
        
        torch.save({
            'model_type': self.model_type,
            'model_state': self.model.state_dict(),
            'input_size': len(self.FEATURE_NAMES),
            'scaler_X': self.scaler_X,
            'scaler_y': self.scaler_y
        }, path)
    
    def _prepare_features(
        self,
        outdoor_temp: float,
        setpoint: Optional[float],
        cooling_on: bool,
        cooling_capacity_kw: float,
        occupancy: int,
        solar_gain: float,
        building_area: float,
        insulation: str,
        sun_exposure: str,
        hour: float,
        prev_indoor_temp: float
    ) -> np.ndarray:
        """Prepare feature vector"""
        
        insulation_code = self.INSULATION_MAP.get(insulation.lower(), 1)
        sun_code = self.SUN_EXPOSURE_MAP.get(sun_exposure.lower(), 1)
        
        features = np.array([[
            outdoor_temp,
            setpoint if setpoint else outdoor_temp,
            1.0 if cooling_on else 0.0,
            cooling_capacity_kw,
            occupancy,
            solar_gain,
            building_area,
            insulation_code,
            sun_code,
            hour,
            prev_indoor_temp if prev_indoor_temp else outdoor_temp
        ]])
        
        return features
    
    def predict(
        self,
        outdoor_temp: float,
        setpoint: Optional[float] = None,
        cooling_on: bool = False,
        cooling_capacity_kw: float = 5.0,
        occupancy: int = 0,
        solar_gain: float = 0,
        building_area: float = 80,
        insulation: str = 'medium',
        sun_exposure: str = 'medium',
        hour: Optional[float] = None,
        prev_indoor_temp: Optional[float] = None
    ) -> dict:
        """
        Predict indoor temperature.
        
        Returns:
            dict with 'indoor_temp', 'confidence', 'predicted_comfort'
        """
        if hour is None:
            hour = datetime.now().hour + datetime.now().minute / 60
        
        if prev_indoor_temp is None:
            prev_indoor_temp = outdoor_temp - 2
        
        features = self._prepare_features(
            outdoor_temp, setpoint, cooling_on, cooling_capacity_kw,
            occupancy, solar_gain, building_area, insulation,
            sun_exposure, hour, prev_indoor_temp
        )
        
        if self.model is not None and HAS_TORCH:
            self.model.eval()
            with torch.no_grad():
                X = torch.FloatTensor(features)
                pred = self.model(X).item()
        else:
            # Fallback to physics-based estimate
            pred = self._physics_fallback(
                outdoor_temp, setpoint, cooling_on, 
                cooling_capacity_kw, prev_indoor_temp
            )
        
        # Ensure physically reasonable bounds
        indoor_temp = max(
            setpoint - 3 if cooling_on and setpoint else outdoor_temp - 5,
            min(
                setpoint + 2 if cooling_on and setpoint else outdoor_temp + 1,
                pred
            )
        )
        
        # Confidence based on model availability
        confidence = 0.9 if self.model else 0.6
        
        return {
            'indoor_temp': round(indoor_temp, 1),
            'confidence': confidence,
            'predicted_comfort': 'comfortable' if 22 <= indoor_temp <= 26 else 'discomfort'
        }
    
    def _physics_fallback(
        self,
        outdoor_temp: float,
        setpoint: Optional[float],
        cooling_on: bool,
        cooling_capacity_kw: float,
        prev_indoor_temp: float
    ) -> float:
        """Simple physics-based fallback when model unavailable"""
        
        if cooling_on and setpoint:
            # AC on: move toward setpoint
            capacity_factor = min(1.0, cooling_capacity_kw / 5.0)
            return prev_indoor_temp + (setpoint - prev_indoor_temp) * capacity_factor * 0.5
        else:
            # AC off: slowly track toward outdoor
            return prev_indoor_temp + (outdoor_temp - prev_indoor_temp) * 0.1
    
    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        epochs: int = 100,
        batch_size: int = 32,
        learning_rate: float = 0.001,
        save_path: Optional[str] = None
    ):
        """
        Train the thermal model.
        
        Args:
            X: Feature array (n_samples, n_features)
            y: Target array (n_samples,) - indoor temperatures
        """
        if not HAS_TORCH:
            print("PyTorch not available. Install with: pip install torch")
            return
        
        # Normalize features
        self.scaler_X = StandardScaler()
        self.scaler_y = StandardScaler()
        
        X_scaled = self.scaler_X.fit_transform(X)
        y_scaled = self.scaler_y.fit_transform(y.reshape(-1, 1)).flatten()
        
        # Create model
        if self.model_type == 'lstm':
            self.model = ThermalLSTM(input_size=X.shape[1])
        else:
            self.model = ThermalMLP(input_size=X.shape[1])
        
        # Prepare data
        X_tensor = torch.FloatTensor(X_scaled)
        y_tensor = torch.FloatTensor(y_scaled)
        dataset = TensorDataset(X_tensor, y_tensor)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        # Training
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        
        self.model.train()
        for epoch in range(epochs):
            total_loss = 0
            for batch_X, batch_y in loader:
                optimizer.zero_grad()
                pred = self.model(batch_X)
                loss = criterion(pred.squeeze(), batch_y)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            
            if epoch % 20 == 0:
                print(f"Epoch {epoch}: Loss = {total_loss / len(loader):.4f}")
        
        self.model.eval()
        
        if save_path:
            self.save_model(save_path)
        
        return self
    
    def predict_sequence(
        self,
        features_sequence: List[Dict],
        initial_indoor_temp: float = 25.0
    ) -> List[float]:
        """
        Predict indoor temperature for a sequence of intervals.
        Uses LSTM-style sequential prediction.
        """
        predictions = []
        prev_temp = initial_indoor_temp
        
        for features in features_sequence:
            result = self.predict(
                outdoor_temp=features['outdoor_temp'],
                setpoint=features.get('setpoint'),
                cooling_on=features.get('cooling_on', False),
                cooling_capacity_kw=features.get('cooling_capacity_kw', 5.0),
                occupancy=features.get('occupancy', 0),
                solar_gain=features.get('solar_gain', 0),
                building_area=features.get('building_area', 80),
                insulation=features.get('insulation', 'medium'),
                sun_exposure=features.get('sun_exposure', 'medium'),
                hour=features.get('hour'),
                prev_indoor_temp=prev_temp
            )
            
            predictions.append(result['indoor_temp'])
            prev_temp = result['indoor_temp']
        
        return predictions


class StandardScaler:
    """Simple standard scaler for normalization"""
    
    def __init__(self):
        self.mean_ = None
        self.std_ = None
    
    def fit(self, X):
        self.mean_ = np.mean(X, axis=0)
        self.std_ = np.std(X, axis=0) + 1e-8
        return self
    
    def transform(self, X):
        return (X - self.mean_) / self.std_
    
    def fit_transform(self, X):
        return self.fit(X).transform(X)
    
    def inverse_transform(self, X):
        return X * self.std_ + self.mean_


def generate_thermal_training_data(
    scenario_data: dict,
    thermal_model_output: list
) -> tuple:
    """
    Generate training data from scenario + thermal simulation output.
    
    Args:
        scenario_data: Scenario JSON with interval inputs
        thermal_model_output: List of estimated indoor temps from simulation
    
    Returns:
        X, y arrays for training
    """
    intervals = scenario_data.get('interval_inputs', [])
    appliances = scenario_data.get('appliances', [])
    profile = scenario_data.get('profile', {})
    
    # Find AC appliance
    ac = next((a for a in appliances if a.get('appliance_type') == 'ac'), None)
    
    building_area = profile.get('area_m2', 80)
    insulation = profile.get('insulation_level', 'medium')
    sun_exposure = profile.get('sun_exposure', 'medium')
    
    X, y = [], []
    
    for i, (interval, indoor_temp) in enumerate(zip(intervals, thermal_model_output)):
        timestamp = interval.get('timestamp_local', '')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        hour = timestamp.hour + timestamp.minute / 60
        
        # Determine if AC was on (estimate from indoor temp trend)
        outdoor = interval.get('temperature_c', 30)
        cooling_on = indoor_temp < outdoor - 2
        
        # Estimate setpoint from AC operation
        setpoint = 24 if cooling_on else None
        
        solar_gain = interval.get('solar_irradiance_w_m2', 0)
        occupancy = interval.get('occupancy_count', 0)
        
        prev_indoor = thermal_model_output[i-1] if i > 0 else indoor_temp
        
        features = [
            outdoor,
            setpoint if setpoint else outdoor,
            1.0 if cooling_on else 0.0,
            (ac.get('cooling_capacity_kw', 5.0) if ac else 5.0) if cooling_on else 0.0,
            occupancy,
            solar_gain,
            building_area,
            ThermalANNModel.INSULATION_MAP.get(insulation.lower(), 1),
            ThermalANNModel.SUN_EXPOSURE_MAP.get(sun_exposure.lower(), 1),
            hour,
            prev_indoor
        ]
        
        X.append(features)
        y.append(indoor_temp)
    
    return np.array(X), np.array(y)


if __name__ == '__main__':
    # Test the model
    model = ThermalANNModel(model_type='mlp')
    
    # Test prediction
    result = model.predict(
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
    print(f"Predicted indoor temp: {result}")
    
    # Test without AC
    result2 = model.predict(
        outdoor_temp=38,
        cooling_on=False,
        occupancy=0,
        solar_gain=100,
        building_area=80,
        insulation='medium',
        sun_exposure='high',
        hour=16.0,
        prev_indoor_temp=32.0
    )
    print(f"Predicted indoor temp (AC off): {result2}")
