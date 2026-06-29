"""
Alerts System - Generates alerts for various conditions
"""

from typing import List, Dict
from datetime import datetime
from enum import Enum

class AlertType(str, Enum):
    EXTREME_HEAT = "EXTREME_HEAT"
    UNSAFE_COMFORT = "UNSAFE_COMFORT"
    BUDGET_RISK = "BUDGET_RISK"
    PEAK_DEMAND = "PEAK_DEMAND"
    LOW_BATTERY = "LOW_BATTERY"
    GRID_OUTAGE = "GRID_OUTAGE"
    INSUFFICIENT_CAPACITY = "INSUFFICIENT_CAPACITY"
    MISSING_DATA = "MISSING_DATA"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class Alert:
    def __init__(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        message: str,
        timestamp: datetime,
        details: Dict = None
    ):
        self.alert_type = alert_type
        self.severity = severity
        self.message = message
        self.timestamp = timestamp
        self.details = details or {}

    def to_dict(self):
        return {
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }

class AlertsGenerator:
    """Generate alerts based on scenario data and optimization results"""

    # Thresholds
    EXTREME_HEAT_THRESHOLD = 40  # °C
    HIGH_HEAT_THRESHOLD = 35    # °C
    LOW_BATTERY_THRESHOLD = 20   # %
    BUDGET_WARNING_THRESHOLD = 0.8  # 80% of daily budget
    PEAK_DEMAND_THRESHOLD = 8    # kW

    def generate_intervals_alerts(
        self,
        interval_data: List,
        scenario_profile: dict,
        energy_assets: dict
    ) -> List[Alert]:
        """Generate alerts for interval data"""
        alerts = []

        for interval in interval_data:
            # Extreme heat
            if interval.get('temperature_c', 0) >= self.EXTREME_HEAT_THRESHOLD:
                alerts.append(Alert(
                    alert_type=AlertType.EXTREME_HEAT,
                    severity=AlertSeverity.CRITICAL,
                    message=f"Extreme heat: {interval['temperature_c']}°C at {interval['timestamp_local']}",
                    timestamp=interval['timestamp_local'],
                    details={
                        "temperature": interval['temperature_c'],
                        "heat_index": interval.get('heat_index_c', 0)
                    }
                ))

            # Unsafe comfort
            if interval.get('comfort_status') == 'unsafe':
                alerts.append(Alert(
                    alert_type=AlertType.UNSAFE_COMFORT,
                    severity=AlertSeverity.CRITICAL,
                    message=f"Unsafe indoor temperature: {interval.get('indoor_temp', 'N/A')}°C at {interval['timestamp_local']}",
                    timestamp=interval['timestamp_local'],
                    details={
                        "indoor_temp": interval.get('indoor_temp'),
                        "outdoor_temp": interval.get('temperature_c')
                    }
                ))

            # Low battery
            battery_soc = interval.get('battery_soc_kwh', 0)
            battery_capacity = energy_assets.get('battery_capacity_kwh', 0)
            if battery_capacity > 0:
                soc_percent = (battery_soc / battery_capacity) * 100
                if soc_percent <= self.LOW_BATTERY_THRESHOLD:
                    alerts.append(Alert(
                        alert_type=AlertType.LOW_BATTERY,
                        severity=AlertSeverity.WARNING,
                        message=f"Low battery: {soc_percent:.1f}% at {interval['timestamp_local']}",
                        timestamp=interval['timestamp_local'],
                        details={
                            "battery_soc": battery_soc,
                            "battery_capacity": battery_capacity,
                            "soc_percent": soc_percent
                        }
                    ))

            # Grid outage
            if not interval.get('grid_available', True):
                alerts.append(Alert(
                    alert_type=AlertType.GRID_OUTAGE,
                    severity=AlertSeverity.CRITICAL,
                    message=f"Grid unavailable at {interval['timestamp_local']}",
                    timestamp=interval['timestamp_local'],
                    details={"duration": "15 minutes"}
                ))

            # Peak demand
            if interval.get('cooling_energy_kwh', 0) / 0.25 > self.PEAK_DEMAND_THRESHOLD:
                alerts.append(Alert(
                    alert_type=AlertType.PEAK_DEMAND,
                    severity=AlertSeverity.WARNING,
                    message=f"High demand: {interval['cooling_energy_kwh'] / 0.25:.2f} kW at {interval['timestamp_local']}",
                    timestamp=interval['timestamp_local'],
                    details={"demand_kw": interval['cooling_energy_kwh'] / 0.25}
                ))

            # Constraint violations
            if interval.get('constraint_violation_count', 0) > 0:
                alerts.append(Alert(
                    alert_type=AlertType.CONSTRAINT_VIOLATION,
                    severity=AlertSeverity.WARNING,
                    message=f"Constraint violation at {interval['timestamp_local']}",
                    timestamp=interval['timestamp_local'],
                    details={
                        "violations": interval.get('constraint_violations', [])
                    }
                ))

        return alerts

    def generate_summary_alerts(
        self,
        daily_summaries: List[dict],
        baseline_metrics: dict,
        budget_per_day: float
    ) -> List[Alert]:
        """Generate alerts based on daily summaries"""
        alerts = []

        for day in daily_summaries:
            # Budget risk
            daily_cost = day.get('total_cost_pkr', 0)
            if daily_cost > budget_per_day * self.BUDGET_WARNING_THRESHOLD:
                alerts.append(Alert(
                    alert_type=AlertType.BUDGET_RISK,
                    severity=AlertSeverity.WARNING,
                    message=f"Budget risk: {daily_cost:.2f} PKR on {day['date']} (Budget: {budget_per_day} PKR)",
                    timestamp=datetime.fromisoformat(day['date']),
                    details={
                        "cost": daily_cost,
                        "budget": budget_per_day,
                        "over_budget_pct": ((daily_cost - budget_per_day) / budget_per_day * 100) if budget_per_day > 0 else 0
                    }
                ))

            # Unsafe hours
            unsafe_hours = day.get('unsafe_hours', 0)
            if unsafe_hours > 0:
                alerts.append(Alert(
                    alert_type=AlertType.UNSAFE_COMFORT,
                    severity=AlertSeverity.CRITICAL,
                    message=f"Unsafe conditions for {unsafe_hours:.1f} hours on {day['date']}",
                    timestamp=datetime.fromisoformat(day['date']),
                    details={"unsafe_hours": unsafe_hours}
                ))

        return alerts

    def get_alert_summary(self, alerts: List[Alert]) -> Dict:
        """Get summary statistics of alerts"""
        summary = {
            "total": len(alerts),
            "by_severity": {
                "critical": len([a for a in alerts if a.severity == AlertSeverity.CRITICAL]),
                "warning": len([a for a in alerts if a.severity == AlertSeverity.WARNING]),
                "info": len([a for a in alerts if a.severity == AlertSeverity.INFO])
            },
            "by_type": {},
            "critical_alerts": [a.to_dict() for a in alerts if a.severity == AlertSeverity.CRITICAL]
        }

        for alert_type in AlertType:
            count = len([a for a in alerts if a.alert_type == alert_type])
            if count > 0:
                summary["by_type"][alert_type.value] = count

        return summary
