import streamlit as st
import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import folium_static
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from src.models.vessel import Vessel, WeatherCondition, PortCongestion
from src.utils.api_handler import MarineTrafficAPI


class Dashboard:
    def __init__(self):
        self.api = MarineTrafficAPI("test_key")
    def run(self):
        st.title("Vessel Fleet Monitor")

        # Get test data
        try:
            vessels = self.api.get_sample_data()
            if not vessels:
                st.error("No vessel data available")
                return
        except Exception as e:
            st.error(f"Error loading vessel data: {str(e)}")
            return

        # Create tabs for better organization
        tab1, tab2, tab3, tab4 = st.tabs([
            "Fleet Overview",
            "Engine Monitoring",
            "Efficiency Analysis",
            "Cost Analysis"
        ])

        with tab1:
            self._show_fleet_overview(vessels)

        with tab2:
            self._show_engine_monitoring(vessels)

        with tab3:
            self._show_efficiency_analysis(vessels)

        with tab4:
            self._show_cost_analysis(vessels)

    def _show_fleet_overview(self, vessels):
        # Create two columns
        map_col, info_col = st.columns([2, 1])

        with map_col:
            # Create map
            m = folium.Map(location=[37.9838, 23.7275],
                           zoom_start=9,
                           tiles="OpenStreetMap")

            # Add vessels to map with interactive popups
            for vessel in vessels:
                status_info = vessel.get_status_info()
                popup_content = self._create_enhanced_popup(vessel, status_info)

                folium.Marker(
                    vessel.position,
                    popup=popup_content,
                    icon=folium.Icon(
                        color=vessel.get_marker_color(),
                        icon='ship',
                        prefix='fa'
                    )
                ).add_to(m)

            self._add_legend(m)
            folium_static(m)

        with info_col:
            st.subheader("Fleet Status Overview")
            for vessel in vessels:
                status_info = vessel.get_status_info()
                weather_info = vessel.get_weather_summary()

                with st.expander(f"🚢 {vessel.name}"):
                    # Status and ETA
                    st.write("📍 **Current Status**")
                    status_color = "🟢" if not vessel.is_delayed() else "🔴"
                    st.write(f"{status_color} Status: {status_info['status']}")

                    # Time Information
                    st.write("⏰ **Time Information**")
                    original_eta = status_info['original_eta'].strftime('%Y-%m-%d %H:%M')
                    current_eta = status_info['current_eta'].strftime('%Y-%m-%d %H:%M')
                    st.write(f"Original ETA: {original_eta}")
                    st.write(f"Current ETA: {current_eta}")

                    # Port Status
                    if vessel.port_status['congestion_level'] != PortCongestion.NONE:
                        st.warning(f"""
                            🚧 **Port Congestion Alert**
                            - Level: {vessel.port_status['congestion_level'].value}
                            - Available Berths: {vessel.port_status['available_berths']}
                            - Queue Position: {vessel.port_status['queue_position'] or 'N/A'}
                            - Estimated Waiting: {vessel.port_status['estimated_waiting_time']}
                        """)

                    # Delays
                    if status_info['total_delay'].total_seconds() > 0:
                        st.write("⚠️ **Delays**")
                        st.warning(
                            f"Current Delay: {status_info['current_delay']}\n"
                            f"Weather Delay: {status_info['weather_delay']}\n"
                            f"Total Delay: {status_info['total_delay']}\n"
                            f"Estimated Cost: ${status_info['total_delay_cost']:,.2f}"
                        )

                    # Simplified Weather Information
                    st.write("🌊 **Weather**")
                    st.write(f"Current: {weather_info['current']}")

                    if weather_info['next_hours']:
                        st.write("Next few hours:")
                        for hour in weather_info['next_hours']:
                            st.write(f"- {hour['time']}: {hour['condition']}")

                    if weather_info['destination']:
                        st.write(f"At destination ({weather_info['destination']['time']}): "
                                 f"{weather_info['destination']['condition']}")

                    # Weather Alerts
                    if weather_info['alerts']:
                        for alert in weather_info['alerts']:
                            st.error(f"""
                                ⚠️ Severe Weather Alert
                                Time: {alert['time'].strftime('%H:%M')}
                                Condition: {alert['condition']}
                                Wind: {alert['wind_speed']:.1f} knots
                                Waves: {alert['wave_height']:.1f}m
                            """)

                    # Performance Metrics
                    st.write("📊 **Performance**")
                    st.write(f"Speed: {status_info['speed']:.1f} knots")
                    st.write(f"Fuel Level: {status_info['fuel_level']:.1f}%")
    def _show_engine_monitoring(self, vessels):
        # Vessel selector
        selected_vessel = st.selectbox(
            "Select Vessel",
            options=[v.name for v in vessels],
            key="engine_monitor_selector"
        )
        vessel = next(v for v in vessels if v.name == selected_vessel)

        # Engine status overview
        st.subheader("Engine Status")
        engine_status = vessel.check_engine_parameters()

        # Create metrics in columns
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "RPM",
                f"{engine_status['current_values']['rpm']:.1f}",
                delta=f"{engine_status['current_values']['rpm'] - vessel.normal_parameters['rpm_range'][0]:.1f}"
            )

        with col2:
            st.metric(
                "Engine Load",
                f"{engine_status['current_values']['load']:.1f}%",
                delta=f"{engine_status['current_values']['load'] - vessel.normal_parameters['load_range'][0]:.1f}%"
            )

        with col3:
            st.metric(
                "Fuel Pressure",
                f"{engine_status['current_values']['pressure']:.2f} bar",
                delta=f"{engine_status['current_values']['pressure'] - vessel.normal_parameters['pressure_range'][0]:.2f}"
            )

        with col4:
            st.metric(
                "Temperature",
                f"{engine_status['current_values']['temperature']:.1f}°C",
                delta=f"{engine_status['current_values']['temperature'] - vessel.normal_parameters['temp_range'][0]:.1f}"
            )

        # Show parameter trends
        st.subheader("Parameter Trends")
        if vessel.engine.readings_history:
            history_df = pd.DataFrame(vessel.engine.readings_history)

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=list(range(len(history_df))),
                y=history_df['rpm'],
                name='RPM'
            ))
            fig.add_trace(go.Scatter(
                x=list(range(len(history_df))),
                y=history_df['load'],
                name='Load %'
            ))

            fig.update_layout(
                title='Engine Parameters History',
                xaxis_title='Time',
                yaxis_title='Value',
                height=400
            )

            st.plotly_chart(fig, use_container_width=True)

        # Show alerts if any
        if engine_status['has_alerts']:
            st.warning("⚠️ Engine Parameter Alerts")
            for alert in engine_status['alerts']:
                severity_color = "🔴" if alert['severity'] == "high" else "🟡"
                st.error(f"""
                    {severity_color} {alert['parameter']} Alert
                    Current: {alert['value']:.2f}
                    Normal Range: {alert['normal_range'][0]:.2f} - {alert['normal_range'][1]:.2f}
                    Severity: {alert['severity'].upper()}
                """)

    def _show_efficiency_analysis(self, vessels):
        st.subheader("Fleet Efficiency Overview")

        # Create efficiency comparison chart
        efficiency_data = []
        for vessel in vessels:
            metrics = vessel.get_efficiency_metrics()
            efficiency_data.append({
                'Vessel': vessel.name,
                'Current Efficiency': metrics['current_consumption_per_mile'],
                'Average Efficiency': metrics['average_consumption_per_mile'],
                'Status': vessel.status.value
            })

        df = pd.DataFrame(efficiency_data)

        # Bar chart comparing current vs average efficiency
        fig = go.Figure(data=[
            go.Bar(name='Current', x=df['Vessel'], y=df['Current Efficiency']),
            go.Bar(name='Average', x=df['Vessel'], y=df['Average Efficiency'])
        ])

        fig.update_layout(
            title='Fleet Fuel Efficiency (tons/nm)',
            barmode='group',
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

        # Detailed vessel analysis
        st.subheader("Vessel Details")
        selected_vessel = st.selectbox(
            "Select Vessel for Detailed Analysis",
            options=[v.name for v in vessels],
            key="efficiency_analysis_selector"
        )

        vessel = next(v for v in vessels if v.name == selected_vessel)
        metrics = vessel.get_efficiency_metrics()
        status_info = vessel.get_status_info()

        # Show metrics in columns
        col1, col2 = st.columns(2)

        with col1:
            st.info(f"""
                🚢 Vessel Status
                - Current Status: {vessel.status.value}
                - Speed: {metrics['speed']} knots
                - Load: {metrics['load_percentage']}%
                - Hull Efficiency: {metrics['hull_efficiency']}%
            """)

        with col2:
            st.info(f"""
                ⛽ Efficiency Metrics
                - Current: {metrics['current_consumption_per_mile']:.4f} tons/nm
                - Average: {metrics['average_consumption_per_mile']:.4f} tons/nm
                - Weather Impact: {(metrics['weather_impact'] - 1) * 100:.1f}%
            """)

    def _show_cost_analysis(self, vessels):
        """Display cost analysis tab content"""
        st.subheader("Cost Analysis")

        # Vessel selector
        selected_vessel = st.selectbox(
            "Select Vessel",
            options=[v.name for v in vessels],
            key="cost_analysis_selector"
        )
        vessel = next(v for v in vessels if v.name == selected_vessel)

        # Date range selector
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "From Date",
                value=datetime.now() - timedelta(days=30)
            )
        with col2:
            end_date = st.date_input(
                "To Date",
                value=datetime.now()
            )

        # Get voyage history for selected period
        voyages = vessel.get_voyage_history(
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.max.time())
        )

        if not voyages:
            st.warning("No voyage data available for selected period")
            return

        # Create main metrics
        self._show_voyage_metrics(voyages)

        # Show detailed voyage analysis
        with st.expander("📊 Detailed Voyage Analysis", expanded=True):
            self._show_detailed_voyage_analysis(vessel, voyages)

        # Show voyage comparison
        with st.expander("🔄 Voyage Comparison"):
            self._show_voyage_comparison(voyages)

    def _show_voyage_metrics(self, voyages):
        """Display key metrics for voyages"""
        total_fuel = sum(v.fuel_consumption for v in voyages)
        total_distance = sum(v.distance for v in voyages)
        total_cost = sum(v.total_cost for v in voyages)
        avg_efficiency = total_fuel / total_distance if total_distance > 0 else 0

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total Voyages",
                len(voyages)
            )
        with col2:
            st.metric(
                "Total Distance (nm)",
                f"{total_distance:,.1f}"
            )
        with col3:
            st.metric(
                "Fuel Efficiency (t/nm)",
                f"{avg_efficiency:.3f}"
            )
        with col4:
            st.metric(
                "Total Cost",
                f"${total_cost:,.2f}"
            )

    def _show_detailed_voyage_analysis(self, vessel, voyages):
        """Display detailed analysis for each voyage"""
        for voyage in voyages:
            with st.container():
                st.subheader(f"Voyage {voyage.voyage_id}: {voyage.origin} → {voyage.destination}")

                # Basic voyage info
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write("📅 **Duration**")
                    duration = voyage.end_date - voyage.start_date
                    st.write(f"{duration.total_seconds() / 3600:.1f} hours")

                    st.write("🚢 **Cargo Load**")
                    st.write(f"{voyage.cargo_load:.1f}%")

                with col2:
                    st.write("⛽ **Fuel Consumption**")
                    st.write(f"{voyage.fuel_consumption:.1f} tons")

                    st.write("⚡ **Efficiency**")
                    st.write(f"{voyage.fuel_consumption / voyage.distance:.3f} t/nm")

                with col3:
                    st.write("💨 **Average Speed**")
                    st.write(f"{voyage.average_speed:.1f} knots")

                    st.write("📊 **Route Efficiency**")
                    st.write(f"{voyage.route_efficiency * 100:.1f}%")

                # Weather conditions
                st.write("🌊 **Weather Conditions**")
                weather_text = ", ".join([w.value for w in voyage.weather_conditions])
                st.write(weather_text)

                # Port delays
                if voyage.port_waiting_times:
                    st.write("⏰ **Port Delays**")
                    for port, delay in voyage.port_waiting_times.items():
                        st.write(f"{port}: {delay.total_seconds() / 3600:.1f} hours")

                # Cost breakdown
                costs = vessel.calculate_voyage_costs(voyage)
                st.write("💰 **Cost Breakdown**")
                fig = px.pie(
                    values=[costs['fuel_cost'], costs['port_costs'], costs['delay_costs']],
                    names=['Fuel', 'Port Fees', 'Delay Costs'],
                    title='Cost Distribution'
                )
                st.plotly_chart(fig, use_container_width=True)

                st.markdown("---")

        def _show_voyage_comparison(self, voyages):
            """Display voyage comparison charts"""
            if len(voyages) < 2:
                st.info("Need at least 2 voyages for comparison")
                return

            # Prepare data for comparison
            comparison_data = []
            for v in voyages:
                comparison_data.append({
                    'Voyage': v.voyage_id,
                    'Fuel Efficiency': v.fuel_consumption / v.distance,
                    'Speed': v.average_speed,
                    'Route Efficiency': v.route_efficiency,
                    'Cost per Mile': v.total_cost / v.distance
                })

            df = pd.DataFrame(comparison_data)

            # Create comparison charts
            metrics = ['Fuel Efficiency', 'Speed', 'Route Efficiency', 'Cost per Mile']
            for metric in metrics:
                fig = px.bar(
                    df,
                    x='Voyage',
                    y=metric,
                    title=f'{metric} Comparison'
                )
                st.plotly_chart(fig, use_container_width=True)

        def _create_enhanced_popup(self, vessel, status_info):
            """Create enhanced popup with weather and delay information"""
            weather_info = vessel.get_weather_summary()
            port_status = "🟢 Normal"
            if vessel.port_status['congestion_level'] != PortCongestion.NONE:
                port_status = f"🚧 {vessel.port_status['congestion_level'].value}"

            return f"""
            <div style='font-family: Arial; font-size: 14px; width: 200px;'>
                <h3 style='margin-bottom: 10px;'>{vessel.name}</h3>
                <p><b>Status:</b> {status_info['status']}</p>
                <p><b>Destination:</b> {vessel.destination}</p>
                <p><b>ETA:</b> {status_info['current_eta'].strftime('%Y-%m-%d %H:%M')}</p>
                <p><b>Port Status:</b> {port_status}</p>

                <hr style='margin: 10px 0;'>

                <p><b>Weather:</b> {weather_info['current']}</p>
                <p><b>Speed:</b> {status_info['speed']:.1f} knots</p>

                {self._format_delay_info(status_info) if status_info['total_delay'].total_seconds() > 0 else ''}

                <hr style='margin: 10px 0;'>

                <a href="#" onclick="alert('Check vessel details for more information')">
                    View Details
                </a>
            </div>
            """

        @staticmethod
        def _format_delay_info(status_info):
            """Format delay information for popup"""
            return f"""
            <div style='background-color: #fff3cd; padding: 5px; margin: 5px 0; border-radius: 4px;'>
                <p style='color: #856404; margin: 0;'>
                    <b>Delay Alert:</b><br>
                    Total Delay: {status_info['total_delay']}<br>
                    Cost Impact: ${status_info['total_delay_cost']:,.2f}
                </p>
            </div>
            """

        @staticmethod
        def _add_legend(m):
            """Add enhanced legend to map"""
            legend_html = '''
            <div style="position: fixed; 
                        bottom: 50px; right: 50px; 
                        border:2px solid grey; z-index:9999; 
                        background-color:white;
                        padding: 10px;
                        font-size:14px;
                        ">
            <p><i class="fa fa-ship fa-1x" style="color:blue"></i> En Route</p>
            <p><i class="fa fa-ship fa-1x" style="color:green"></i> Approaching</p>
            <p><i class="fa fa-ship fa-1x" style="color:orange"></i> Loading</p>
            <p><i class="fa fa-ship fa-1x" style="color:purple"></i> Unloading</p>
            <p><i class="fa fa-ship fa-1x" style="color:red"></i> Docked</p>
            <hr>
            <p>☀️ Calm</p>
            <p>🌤️ Moderate</p>
            <p>🌊 Rough</p>
            <p>⛈️ Severe</p>
            <hr>
            <p>🟢 No Congestion</p>
            <p>🚧 Port Congestion</p>
            </div>
            '''
            m.get_root().html.add_child(folium.Element(legend_html))

    def _show_voyage_comparison(self, voyages):
        """Display voyage comparison charts"""
        if len(voyages) < 2:
            st.info("Need at least 2 voyages for comparison")
            return

        # Prepare data for comparison
        comparison_data = []
        for v in voyages:
            comparison_data.append({
                'Voyage': v.voyage_id,
                'Fuel Efficiency': v.fuel_consumption / v.distance,
                'Speed': v.average_speed,
                'Route Efficiency': v.route_efficiency,
                'Cost per Mile': v.total_cost / v.distance
            })

        df = pd.DataFrame(comparison_data)

        # Create comparison charts
        metrics = ['Fuel Efficiency', 'Speed', 'Route Efficiency', 'Cost per Mile']
        for metric in metrics:
            fig = px.bar(
                df,
                x='Voyage',
                y=metric,
                title=f'{metric} Comparison'
            )
            st.plotly_chart(fig, use_container_width=True)

    def _create_enhanced_popup(self, vessel, status_info):
        """Create enhanced popup with weather and delay information"""
        weather_info = vessel.get_weather_summary()
        port_status = "🟢 Normal"
        if vessel.port_status['congestion_level'] != PortCongestion.NONE:
            port_status = f"🚧 {vessel.port_status['congestion_level'].value}"

        return f"""
        <div style='font-family: Arial; font-size: 14px; width: 200px;'>
            <h3 style='margin-bottom: 10px;'>{vessel.name}</h3>
            <p><b>Status:</b> {status_info['status']}</p>
            <p><b>Destination:</b> {vessel.destination}</p>
            <p><b>ETA:</b> {status_info['current_eta'].strftime('%Y-%m-%d %H:%M')}</p>
            <p><b>Port Status:</b> {port_status}</p>

            <hr style='margin: 10px 0;'>

            <p><b>Weather:</b> {weather_info['current']}</p>
            <p><b>Speed:</b> {status_info['speed']:.1f} knots</p>

            {self._format_delay_info(status_info) if status_info['total_delay'].total_seconds() > 0 else ''}

            <hr style='margin: 10px 0;'>

            <a href="#" onclick="alert('Check vessel details for more information')">
                View Details
            </a>
        </div>
        """

    @staticmethod
    def _format_delay_info(status_info):
        """Format delay information for popup"""
        return f"""
        <div style='background-color: #fff3cd; padding: 5px; margin: 5px 0; border-radius: 4px;'>
            <p style='color: #856404; margin: 0;'>
                <b>Delay Alert:</b><br>
                Total Delay: {status_info['total_delay']}<br>
                Cost Impact: ${status_info['total_delay_cost']:,.2f}
            </p>
        </div>
        """

    @staticmethod
    def _add_legend(m):
        """Add enhanced legend to map"""
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; right: 50px; 
                    border:2px solid grey; z-index:9999; 
                    background-color:white;
                    padding: 10px;
                    font-size:14px;
                    ">
        <p><i class="fa fa-ship fa-1x" style="color:blue"></i> En Route</p>
        <p><i class="fa fa-ship fa-1x" style="color:green"></i> Approaching</p>
        <p><i class="fa fa-ship fa-1x" style="color:orange"></i> Loading</p>
        <p><i class="fa fa-ship fa-1x" style="color:purple"></i> Unloading</p>
        <p><i class="fa fa-ship fa-1x" style="color:red"></i> Docked</p>
        <hr>
        <p>☀️ Calm</p>
        <p>🌤️ Moderate</p>
        <p>🌊 Rough</p>
        <p>⛈️ Severe</p>
        <hr>
        <p>🟢 No Congestion</p>
        <p>🚧 Port Congestion</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))

if __name__ == "__main__":
    st.set_page_config(
    page_title="Fleet Monitor",
    page_icon="🚢",
    layout="wide"
        )

    dashboard = Dashboard()
    dashboard.run()