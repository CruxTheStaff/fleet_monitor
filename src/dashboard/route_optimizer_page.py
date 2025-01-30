import streamlit as st
import pandas as pd
from typing import Dict
from src.database.db_manager import DatabaseManager  # Διορθωμένο import



class RouteOptimizerPage:
    def __init__(self):
        self.db = DatabaseManager()

    def show(self):
        st.title("Route Optimization")

        # Tabs for different sections
        tab1, tab2, tab3 = st.tabs([
            "New Route Optimization",
            "Optimization History",
            "Analytics"
        ])

        with tab1:
            self._show_new_optimization()

        with tab2:
            self._show_optimization_history()

        with tab3:
            self._show_analytics()

    def _show_new_optimization(self):
        col1, col2 = st.columns(2)

        with col1:
            origin = st.selectbox("Origin Port", ["Port A", "Port B", "Port C"])
            destination = st.selectbox("Destination Port", ["Port A", "Port B", "Port C"])

        with col2:
            optimization_type = st.radio(
                "Optimization Priority",
                ["Time", "Fuel", "Cost", "Weather"]
            )

        if st.button("Calculate Optimal Route"):
            # Here we would call the actual optimization logic
            optimized_route = self._calculate_optimal_route(
                origin, destination, optimization_type
            )
            self._display_optimization_results(optimized_route)

    def _show_optimization_history(self):
        history = self.db.get_route_history()
        if history:
            df = pd.DataFrame(history)
            st.dataframe(df)

    def _show_analytics(self):
        st.subheader("Optimization Analytics")
        # Add analytics visualizations here

    def _calculate_optimal_route(self, origin: str, destination: str, optimization_type: str) -> dict:
        """Calculate optimal route based on selected criteria"""
        # Simulate route optimization
        return {
            'origin': origin,
            'destination': destination,
            'distance': 450.5,  # Nautical miles
            'estimated_time': 36.5,  # Hours
            'fuel_consumption': 125.3,  # Tons
            'total_cost': 28500.0,  # USD
            'waypoints': [
                (37.9838, 23.7275),  # Example coordinates
                (37.4446, 24.9468),
                (36.9980, 25.9120)
            ],
            'weather_risk': 'Low',
            'optimization_type': optimization_type
        }

    def _display_optimization_results(self, route: dict):
        """Display optimization results"""
        st.subheader("Route Details")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Distance", f"{route['distance']} nm")
            st.metric("Estimated Time", f"{route['estimated_time']} hours")
            st.metric("Fuel Consumption", f"{route['fuel_consumption']} tons")
        with col2:
            st.metric("Total Cost", f"${route['total_cost']:,.2f}")
            st.metric("Weather Risk", route['weather_risk'])
