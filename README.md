# Fleet Monitor

A real-time fleet monitoring and analytics system designed for small to medium-sized shipping companies. The system provides vessel tracking, route optimization, and predictive analytics capabilities.

## Features

### Real-time Monitoring
- Vessel position tracking with interactive map
- Engine performance monitoring with real-time metrics
- Weather conditions and forecasts
- Port status and congestion monitoring
- Real-time efficiency metrics

### Vessel Type Specialization
- Tanker vessels with specific features:
  - Tank type and capacity monitoring
  - Cargo temperature tracking
  - Tank cleaning status
  - Heating requirements management
- Bulk carriers with specific features:
  - Hold count and utilization tracking
  - Ballast condition monitoring
  - Hatch status tracking
  - Cargo-specific requirements

### Analytics
- Comprehensive cost analysis per voyage
- Route efficiency metrics
- Performance tracking and analysis
- Historical data comparison
- Fleet-wide statistics

### Data Collection for ML
- Engine performance patterns
- Weather impact analysis
- Port congestion patterns
- Route efficiency metrics
- Cost optimization data

## Technology Stack
- Python 3.11
- Streamlit for dashboard
- SQLite for data storage
- Folium for map visualization
- Plotly for interactive charts
- Stormglass API for weather data

## Installation

1. Clone the repository:
```bash
git clone https://github.com/CruxTheStaff/fleet_monitor.git

Create and activate virtual environment:
BASH

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install dependencies:
BASH

pip install -r requirements.txt
Set up environment variables:
Create a .env file in the root directory
Add your API keys:

STORMGLASS_API_KEY=your_key_here
Run the application:
BASH

streamlit run src/dashboard/main.py
Project Structure

fleet_monitor/
├── src/
│   ├── dashboard/      # UI components
│   ├── database/       # Database operations
│   ├── models/         # Data models and types
│   └── utils/          # Utility functions
├── data/               # Data storage
└── cache/              # Cache storage
Development Status
 Basic vessel tracking
 Weather integration
 Cost analysis
 Route tracking
 Vessel type specialization
 ML data collection
 Advanced analytics
 Real-time data integration
Contributing
This is a portfolio project demonstrating fleet management and analytics capabilities. Feel free to fork and adapt for your needs.

License
This project is for demonstration purposes only.