CREATE TABLE IF NOT EXISTS routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    origin TEXT NOT NULL,
    destination TEXT NOT NULL,
    distance REAL NOT NULL,
    estimated_time REAL NOT NULL,
    fuel_consumption REAL NOT NULL,
    weather_conditions TEXT,
    created_at TIMESTAMP NOT NULL,
    actual_time REAL,
    actual_fuel_consumption REAL,
    status TEXT DEFAULT 'planned'
);

CREATE TABLE IF NOT EXISTS route_optimization_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    route_id INTEGER,
    optimization_type TEXT NOT NULL,
    original_cost REAL,
    optimized_cost REAL,
    savings_percentage REAL,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (route_id) REFERENCES routes (id)
);

CREATE TABLE IF NOT EXISTS ml_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_imo INTEGER NOT NULL,
    timestamp DATETIME NOT NULL,
    data TEXT NOT NULL,
    metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);