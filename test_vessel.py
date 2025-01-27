from src.models.vessel import Vessel
from datetime import datetime

# Create test vessel
test_vessel = Vessel(
    name="TEST SHIP",
    lat=37.9838,
    lon=23.7275,
    destination="Piraeus",
    eta=datetime.now(),
    cargo_status="En Route",
    fuel_level=80
)

# Check efficiency metrics
print("\nEfficiency Metrics:")
metrics = test_vessel.get_efficiency_metrics()
for key, value in metrics.items():
    if isinstance(value, list):
        print(f"{key}: {[round(x, 4) for x in value]}")
    else:
        print(f"{key}: {round(value, 4) if isinstance(value, float) else value}")

# Check anomaly detection
print("\nAnomaly Check:")
anomaly = test_vessel.check_consumption_anomaly()
for key, value in anomaly.items():
    if key != "contributing_factors":
        print(f"{key}: {round(value, 4) if isinstance(value, float) else value}")

# If there are contributing factors, show them
if anomaly["contributing_factors"]:
    print("\nContributing Factors:")
    for factor, impact in anomaly["contributing_factors"].items():
        print(f"{factor}: {round(impact, 2)}%")