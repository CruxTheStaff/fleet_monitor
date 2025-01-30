import sqlite3
from datetime import datetime
from typing import Dict, List

class DatabaseManager:
    def __init__(self, db_path: str = "fleet_monitor.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            with open('src/database/schema.sql') as f:
                conn.executescript(f.read())

    def save_route(self, route_data: Dict):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO routes (
                    origin, destination, distance, estimated_time,
                    fuel_consumption, weather_conditions, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                route_data['origin'],
                route_data['destination'],
                route_data['distance'],
                route_data['estimated_time'],
                route_data['fuel_consumption'],
                route_data['weather_conditions'],
                datetime.now()
            ))
            return cursor.lastrowid

    def get_route_history(self) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM routes ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def store_ml_data(self, ml_data: Dict):
        """Store ML-related data in the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ml_data (
                    vessel_imo,
                    timestamp,
                    data,
                    metadata
                ) VALUES (?, ?, ?, ?)
            """, (
                ml_data['imo'],
                ml_data['timestamp'],
                str(ml_data['features']),  # Convert dict to string
                str(ml_data['metadata'])  # Convert dict to string
            ))
            return cursor.lastrowid
