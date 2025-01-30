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

from src.utils.api_handler import MarineTrafficAPI
from route_optimizer_page import RouteOptimizerPage
from src.models.types import PortCongestion
from src.database.db_manager import DatabaseManager

class Dashboard:
    def __init__(self):
        self.api = MarineTrafficAPI("test_key")
        self.route_optimizer = RouteOptimizerPage()
        self.db_manager = DatabaseManager()

    def run(self):
        st.sidebar.title("Fleet Monitor")
        page = st.sidebar.radio(
            "Navigation",
            ["Fleet Overview", "Route Optimization", "Analytics"]
        )

        if page == "Fleet Overview":
            self._show_main_dashboard()
        elif page == "Route Optimization":
            self.route_optimizer.show()
        elif page == "Analytics":
            self._show_analytics()

    def _show_main_dashboard(self):
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

                # Add vessel track history
                if vessel.track_history:
                    folium.PolyLine(
                        vessel.track_history,
                        weight=2,
                        color='blue',
                        opacity=0.8
                    ).add_to(m)

                # Enhanced marker with vessel heading
                folium.Marker(
                    vessel.position,
                    popup=popup_content,
                    icon=folium.Icon(
                        color=vessel.get_marker_color(),
                        icon='ship',
                        prefix='fa',
                        angle=vessel.heading  # Add vessel heading
                    )
                ).add_to(m)

            self._add_legend(m)

            # Add map control buttons
            st.button("Center Map", on_click=self._center_map)
            st.button("Show All Tracks", on_click=self._toggle_tracks)

            folium_static(m)

        with info_col:
            st.subheader("Fleet Status Overview")

            # Add status filters
            status_filter = st.multiselect(
                "Filter by Status",
                options=["On Time", "Delayed", "In Port", "En Route"]
            )

            # Sort vessels
            sort_by = st.selectbox(
                "Sort vessels by",
                ["Name", "Status", "Delay Time", "ETA"]
            )
            vessels = self._sort_vessels(vessels, sort_by)

            # Display fleet-wide statistics
            self._show_fleet_summary(vessels)

            # Display individual vessel cards
            for vessel in vessels:
                if not status_filter or vessel.get_status_info()['status'] in status_filter:
                    self._show_vessel_card(vessel)

        def _show_vessel_card(self, vessel):
            """Display individual vessel information card"""
            status_info = vessel.get_status_info()
            weather_info = vessel.get_weather_summary()

            with st.expander(f"🚢 {vessel.name}"):
                # Status and ETA information
                self._display_status_info(vessel, status_info)

                # Port status information
                self._display_port_status(vessel)

                # Delay information
                self._display_delay_info(status_info)

                # Weather information
                self._display_weather_info(weather_info)

                # Add speed history graph
                if vessel.speed_history:
                    st.line_chart(vessel.speed_history)

                # Action buttons
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Detailed Report", key=f"report_{vessel.name}"):
                        self._show_vessel_report(vessel)
                with col2:
                    if st.button("Track History", key=f"track_{vessel.name}"):
                        self._show_vessel_track(vessel)

        def _show_fleet_summary(self, vessels):
            """Display fleet-wide summary metrics"""
            total_vessels = len(vessels)
            delayed_vessels = sum(1 for v in vessels if v.is_delayed())
            total_delay_cost = sum(v.get_status_info()['total_delay_cost'] for v in vessels)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Vessels", total_vessels)
            with col2:
                st.metric("Delayed Vessels", delayed_vessels)
            with col3:
                st.metric("Total Delay Cost", f"${total_delay_cost:,.2f}")

    def _show_engine_monitoring(self, vessels):
        """Display engine monitoring dashboard for selected vessel"""
        # Vessel selector with additional info
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_vessel = st.selectbox(
                "Select Vessel",
                options=[v.name for v in vessels],
                key="engine_monitor_selector"
            )
        with col2:
            refresh_rate = st.selectbox(
                "Refresh Rate",
                options=["5s", "10s", "30s", "1m"],
                key="refresh_rate"
            )

        vessel = next(v for v in vessels if v.name == selected_vessel)
        engine_status = vessel.check_engine_parameters()

        # Main engine status metrics
        st.subheader("Engine Status")
        col1, col2, col3, col4 = st.columns(4)

        # Enhanced metrics with color coding and trends
        with col1:
            rpm_status = self._get_parameter_status(
                engine_status['current_values']['rpm'],
                vessel.normal_parameters['rpm_range']
            )
            st.metric(
                "RPM",
                f"{engine_status['current_values']['rpm']:.1f}",
                delta=f"{engine_status['current_values']['rpm'] - vessel.normal_parameters['rpm_range'][0]:.1f}",
                delta_color=rpm_status
            )

        with col2:
            load_status = self._get_parameter_status(
                engine_status['current_values']['load'],
                vessel.normal_parameters['load_range']
            )
            st.metric(
                "Engine Load",
                f"{engine_status['current_values']['load']:.1f}%",
                delta=f"{engine_status['current_values']['load'] - vessel.normal_parameters['load_range'][0]:.1f}%",
                delta_color=load_status
            )

        with col3:
            pressure_status = self._get_parameter_status(
                engine_status['current_values']['pressure'],
                vessel.normal_parameters['pressure_range']
            )
            st.metric(
                "Fuel Pressure",
                f"{engine_status['current_values']['pressure']:.2f} bar",
                delta=f"{engine_status['current_values']['pressure'] - vessel.normal_parameters['pressure_range'][0]:.2f}",
                delta_color=pressure_status
            )

        with col4:
            temp_status = self._get_parameter_status(
                engine_status['current_values']['temperature'],
                vessel.normal_parameters['temp_range']
            )
            st.metric(
                "Temperature",
                f"{engine_status['current_values']['temperature']:.1f}°C",
                delta=f"{engine_status['current_values']['temperature'] - vessel.normal_parameters['temp_range'][0]:.1f}",
                delta_color=temp_status
            )

        # Enhanced parameter trends with multiple view options
        st.subheader("Parameter Trends")
        trend_options = st.multiselect(
            "Select Parameters to Display",
            ["RPM", "Load", "Pressure", "Temperature"],
            default=["RPM", "Load"]
        )

        time_range = st.slider(
            "Time Range",
            min_value=1,
            max_value=24,
            value=6,
            help="Select time range in hours"
        )

        if vessel.engine.readings_history:
            history_df = pd.DataFrame(vessel.engine.readings_history)

            # Filter data based on selected time range
            history_df = history_df.tail(int(time_range * 3600 / 5))  # Assuming 5-second intervals

            fig = go.Figure()

            for param in trend_options:
                param_lower = param.lower()
                if param_lower in history_df.columns:
                    fig.add_trace(go.Scatter(
                        x=list(range(len(history_df))),
                        y=history_df[param_lower],
                        name=param,
                        mode='lines'
                    ))

            fig.update_layout(
                title='Engine Parameters History',
                xaxis_title='Time',
                yaxis_title='Value',
                height=400,
                hovermode='x unified'
            )

            st.plotly_chart(fig, use_container_width=True)

        # Enhanced alerts section with filtering and sorting
        if engine_status['has_alerts']:
            st.warning("⚠️ Engine Parameter Alerts")

            # Alert filtering
            severity_filter = st.radio(
                "Filter by Severity",
                options=["All", "High", "Medium", "Low"],
                horizontal=True
            )

            filtered_alerts = [
                alert for alert in engine_status['alerts']
                if severity_filter == "All" or alert['severity'] == severity_filter.lower()
            ]

            for alert in filtered_alerts:
                severity_color = {
                    "high": "🔴",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(alert['severity'], "⚪")

                st.error(f"""
                    {severity_color} {alert['parameter']} Alert
                    Current: {alert['value']:.2f}
                    Normal Range: {alert['normal_range'][0]:.2f} - {alert['normal_range'][1]:.2f}
                    Severity: {alert['severity'].upper()}
                    Time: {alert.get('timestamp', 'N/A')}
                """)

        # Add maintenance recommendations if needed
        if engine_status.get('maintenance_needed'):
            st.info("🔧 Maintenance Recommendations")
            for rec in engine_status['maintenance_recommendations']:
                st.write(f"- {rec}")

    def _get_parameter_status(self, value, normal_range):
        """Helper method to determine parameter status color"""
        if value < normal_range[0]:
            return "inverse"  # Red for below normal
        elif value > normal_range[1]:
            return "off"  # Yellow for above normal
        return "normal"  # Green for normal range

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

        # Get current voyage and historical data
        current_voyage = self._get_current_voyage(vessel)
        if not current_voyage:
            st.warning("No active voyage found")
            return

        # Tabs for different views
        tab1, tab2, tab3 = st.tabs([
            "Current Voyage",
            "Historical Comparison",
            "Monthly Statistics"
        ])

        with tab1:
            self._show_current_voyage_analysis(vessel, current_voyage)

        with tab2:
            self._show_historical_comparison(vessel, current_voyage)

        with tab3:
            self._show_monthly_statistics(vessel)

    def _show_current_voyage_analysis(self, vessel, voyage):
        """Show analysis of current voyage"""
        # Update vessel metrics before displaying
        vessel.update_metrics()

        st.subheader(f"Current Voyage: {voyage.voyage_id}")

        # Basic voyage info in columns
        col1, col2 = st.columns(2)
        with col1:
            st.write("📍 **Route**")
            st.write(f"{voyage.origin} → {voyage.destination}")
            st.write("⏱️ **Progress**")
            progress = self._calculate_voyage_progress(voyage)
            st.progress(progress)

        with col2:
            costs = vessel.calculate_voyage_costs(voyage)
            st.write("💰 **Current Costs**")
            st.metric("Total Cost", f"${costs['total_cost']:,.2f}")
            st.metric("Cost per Mile", f"${costs['cost_per_mile']:.2f}")

        # Cost breakdown pie chart
        fig = px.pie(
            values=[
                costs['fuel_cost'],
                costs['port_costs'],
                costs['port_delay_costs'],
                costs['schedule_deviation_costs']
            ],
            names=[
                'Fuel',
                'Port Fees',
                'Port Delay Costs',
                'Schedule Deviation Costs'
            ],
            title='Current Voyage Cost Distribution'
        )
        st.plotly_chart(fig, use_container_width=True)

        # NEW SECTION: Real-time Metrics
        with st.expander("📊 Real-time Performance Metrics", expanded=True):
            # Speed and Efficiency Metrics
            col1, col2, col3 = st.columns(3)

            with col1:
                speed_delta = vessel.speed - vessel.optimal_speed
                delta_color = "normal" if abs(speed_delta) < 2 else "inverse"
                st.metric(
                    "Speed Optimization",
                    f"{vessel.speed:.1f} knots",
                    f"{speed_delta:+.1f} from optimal",
                    delta_color=delta_color
                )

            with col2:
                consumption_delta = vessel.current_consumption - vessel.baseline_consumption
                delta_color = "normal" if consumption_delta <= 0 else "inverse"
                st.metric(
                    "Fuel Efficiency",
                    f"{vessel.current_consumption:.2f} t/nm",
                    f"{consumption_delta:+.2f} t/nm",
                    delta_color=delta_color
                )

            with col3:
                eta_color = "normal" if vessel.eta_deviation <= 0 else "inverse"
                st.metric(
                    "Schedule Adherence",
                    f"ETA: {vessel.current_eta.strftime('%H:%M %d/%m')}",
                    f"{vessel.eta_deviation:+.1f} hours",
                    delta_color=eta_color
                )

            # Additional Performance Indicators
            st.markdown("---")
            col1, col2 = st.columns(2)

            with col1:
                st.info(f"""
                    🚢 **Vessel Performance**
                    - Hull Efficiency: {vessel.hull_efficiency}%
                    - Load Status: {vessel.load_percentage}%
                    - Weather Impact: {((vessel.WEATHER_IMPACT[vessel.current_weather] - 1) * 100):.1f}%
                """)

            with col2:
                st.info(f"""
                    ⚡ **Engine Status**
                    - RPM: {vessel.engine.rpm}
                    - Load: {vessel.engine.load}%
                    - Temperature: {vessel.engine.temperature}°C
                """)

            # Performance Trends
            if vessel.speed_history:
                st.markdown("### Performance Trends")
                speed_df = pd.DataFrame({
                    'Speed': vessel.speed_history[-50:],  # Last 50 readings
                    'Optimal': [vessel.optimal_speed] * len(vessel.speed_history[-50:])
                })
                st.line_chart(speed_df)

        # Hidden ML data collection
        self._collect_voyage_data(vessel, voyage)

    def _collect_voyage_data(self, vessel, voyage):
        """Collect data for ML training (not visible in UI)"""
        ml_data = {
            # Metadata
            'imo': getattr(vessel, 'imo', 0),  # Default to 0 if no IMO
            'timestamp': datetime.now(),

            # Visible data
            'voyage_id': voyage.voyage_id,
            'route': (voyage.origin, voyage.destination),
            'costs': vessel.calculate_voyage_costs(voyage),

            # Hidden ML-specific data
            'features': {
                'weather_conditions': vessel.weather_forecasts,
                'engine_parameters': vessel.engine.readings_history,
                'route_specifics': {
                    'traffic_density': self._get_route_traffic(),
                    'seasonal_patterns': self._get_seasonal_data(),
                    'historical_delays': self._get_historical_delays()
                },
                'external_factors': {
                    'fuel_prices': self._get_fuel_prices(),
                    'port_congestion': self._get_port_congestion(),
                    'market_conditions': self._get_market_data()
                }
            },

            # Metadata for ML
            'metadata': {
                'vessel_type': vessel.__class__.__name__,
                'data_version': '1.0',
                'collection_method': 'automated'
            }
        }

        # Store ML data
        self.db_manager.store_ml_data(ml_data)

    def _show_historical_comparison(self, vessel, current_voyage):
        """Compare current voyage with historical data"""
        # Get voyage from same period last year
        last_year_voyage = self._get_voyage_from_last_year(vessel, current_voyage)

        # Get monthly average
        monthly_avg = self._calculate_monthly_averages(vessel)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("Current")
            current_costs = vessel.calculate_voyage_costs(current_voyage)
            st.metric("Cost per Mile", f"${current_costs['cost_per_mile']:.2f}")

        with col2:
            if last_year_voyage:
                st.subheader("Last Year")
                last_year_costs = vessel.calculate_voyage_costs(last_year_voyage)
                delta = ((current_costs['cost_per_mile'] - last_year_costs['cost_per_mile'])
                         / last_year_costs['cost_per_mile'] * 100)
                st.metric("Cost per Mile",
                          f"${last_year_costs['cost_per_mile']:.2f}",
                          f"{delta:+.1f}%")

        with col3:
            st.subheader("Monthly Avg")
            if monthly_avg:
                delta = ((current_costs['cost_per_mile'] - monthly_avg['cost_per_mile'])
                         / monthly_avg['cost_per_mile'] * 100)
                st.metric("Cost per Mile",
                          f"${monthly_avg['cost_per_mile']:.2f}",
                          f"{delta:+.1f}%")

    def _show_monthly_statistics(self, vessel):
        """Show monthly statistics and trends"""
        # Get monthly statistics
        monthly_stats = self._calculate_monthly_statistics(vessel)

        # Show trends
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=monthly_stats['months'],
            y=monthly_stats['cost_per_mile'],
            name='Cost per Mile'
        ))
        fig.update_layout(
            title='Monthly Cost Trends',
            xaxis_title='Month',
            yaxis_title='Cost per Mile ($)'
        )
        st.plotly_chart(fig, use_container_width=True)

        # Show key statistics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Average Cost per Mile",
                      f"${monthly_stats['avg_cost_per_mile']:.2f}")
            st.metric("Total Voyages",
                      monthly_stats['total_voyages'])
        with col2:
            st.metric("On-time Completion Rate",
                      f"{monthly_stats['on_time_rate']:.1f}%")
            st.metric("Average Delay Cost",
                      f"${monthly_stats['avg_delay_cost']:.2f}")

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

            # Cost breakdown
            costs = vessel.calculate_voyage_costs(voyage)
            st.write("💰 **Cost Breakdown**")

            # Cost metrics
            cost_col1, cost_col2, cost_col3 = st.columns(3)
            with cost_col1:
                st.metric("Fuel Cost", f"${costs['fuel_cost']:,.2f}")
                st.metric("Port Fees", f"${costs['port_costs']:,.2f}")
            with cost_col2:
                st.metric("Port Delay Costs", f"${costs['port_delay_costs']:,.2f}")
                st.metric("Schedule Deviation Costs", f"${costs['schedule_deviation_costs']:,.2f}")
            with cost_col3:
                total_delay_costs = costs['port_delay_costs'] + costs['schedule_deviation_costs']
                st.metric("Total Delay Costs", f"${total_delay_costs:,.2f}")
                st.metric("Total Cost", f"${costs['total_cost']:,.2f}")

            # Cost distribution pie chart
            fig = px.pie(
                values=[
                    costs['fuel_cost'],
                    costs['port_costs'],
                    costs['port_delay_costs'],
                    costs['schedule_deviation_costs']
                ],
                names=['Fuel', 'Port Fees', 'Port Delays', 'Schedule Deviation'],
                title='Cost Distribution'
            )
            st.plotly_chart(fig, use_container_width=True)

            # Cost per mile
            st.info(f"Cost per nautical mile: ${costs['cost_per_mile']:.2f}")

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

    def _get_current_voyage(self, vessel):
        """Get the current active voyage"""
        if not vessel.voyage_history:
            return None

        # returns the most recent journey
        current_voyage = vessel.voyage_history[-1]

        # check if the voyage is current
        now = datetime.now()
        if current_voyage.start_date <= now <= current_voyage.end_date:
            return current_voyage

        # if the is not current voyage, it returns the last one
        return current_voyage

    def _get_voyage_from_last_year(self, vessel, current_voyage):
        """Get comparable voyage from last year"""
        if not vessel.voyage_history:
            return None

        # Calculates the date one year ago
        target_date = current_voyage.start_date - timedelta(days=365)

        # Searching for a voyage with similar date and destination
        for voyage in vessel.voyage_history:
            if (voyage.origin == current_voyage.origin and
                    voyage.destination == current_voyage.destination and
                    abs((voyage.start_date - target_date).days) < 30):
                return voyage

        return None

    def _calculate_monthly_averages(self, vessel):
        """Calculate average costs for the current month"""
        if not vessel.voyage_history:
            return None

        current_month = datetime.now().month
        current_year = datetime.now().year

        # filtering current month voyages
        month_voyages = [
            v for v in vessel.voyage_history
            if v.start_date.month == current_month and v.start_date.year == current_year
        ]

        if not month_voyages:
            return None

        # Calculating averages
        total_cost = sum(v.total_cost for v in month_voyages)
        total_distance = sum(v.distance for v in month_voyages)

        return {
            'cost_per_mile': total_cost / total_distance if total_distance > 0 else 0,
            'avg_total_cost': total_cost / len(month_voyages),
            'voyage_count': len(month_voyages)
        }

    def _calculate_monthly_statistics(self, vessel):
        """Calculate detailed monthly statistics"""
        if not vessel.voyage_history:
            return None

        # organizing data per month
        monthly_data = {}
        for voyage in vessel.voyage_history:
            month_key = voyage.start_date.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'voyages': [],
                    'total_cost': 0,
                    'total_distance': 0,
                    'delays': 0,
                    'on_time': 0
                }

            data = monthly_data[month_key]
            data['voyages'].append(voyage)
            data['total_cost'] += voyage.total_cost
            data['total_distance'] += voyage.distance

            if voyage.actual_arrival_time and voyage.actual_arrival_time <= voyage.end_date:
                data['on_time'] += 1
            else:
                data['delays'] += 1

        # calculating statistics
        stats = {
            'months': list(monthly_data.keys()),
            'cost_per_mile': [],
            'total_voyages': [],
            'on_time_rate': [],
            'avg_delay_cost': []
        }

        for month, data in monthly_data.items():
            total_voyages = len(data['voyages'])
            stats['total_voyages'].append(total_voyages)

            cost_per_mile = data['total_cost'] / data['total_distance'] if data['total_distance'] > 0 else 0
            stats['cost_per_mile'].append(cost_per_mile)

            on_time_rate = (data['on_time'] / total_voyages * 100) if total_voyages > 0 else 0
            stats['on_time_rate'].append(on_time_rate)

            total_delay_cost = sum(
                (costs := vessel.calculate_voyage_costs(v))['port_delay_costs'] +
                costs['schedule_deviation_costs']
                for v in data['voyages']
            )
            avg_delay_cost = total_delay_cost / total_voyages if total_voyages > 0 else 0
            stats['avg_delay_cost'].append(avg_delay_cost)

        # Adding sum averages
        stats['avg_cost_per_mile'] = sum(stats['cost_per_mile']) / len(stats['cost_per_mile']) if stats[
            'cost_per_mile'] else 0
        stats['total_voyages'] = sum(stats['total_voyages'])
        stats['on_time_rate'] = sum(stats['on_time_rate']) / len(stats['on_time_rate']) if stats['on_time_rate'] else 0
        stats['avg_delay_cost'] = sum(stats['avg_delay_cost']) / len(stats['avg_delay_cost']) if stats[
            'avg_delay_cost'] else 0

        return stats

    def _calculate_voyage_progress(self, voyage):
        """Calculate voyage progress as a percentage"""
        now = datetime.now()

        # if the trip hasn't started yet
        if now < voyage.start_date:
            return 0.0

        # if the trip is completed
        if now > voyage.end_date:
            return 1.0

        # progress calculation
        total_duration = (voyage.end_date - voyage.start_date).total_seconds()
        elapsed_time = (now - voyage.start_date).total_seconds()

        progress = elapsed_time / total_duration
        return min(max(progress, 0.0), 1.0)  # percentage

    def _show_analytics(self):
        """Display analytics page"""
        st.title("Fleet Analytics")

        try:
            vessels = self.api.get_sample_data()
            if not vessels:
                st.error("No data available for analytics")
                return

            # Performance Trends
            st.subheader("Performance Trends")

            # Create sample trend data
            trend_data = {
                'Month': pd.date_range(start='2023-01-01', periods=6, freq='M'),
                'Fuel Efficiency': [0.85, 0.87, 0.82, 0.88, 0.90, 0.89],
                'Route Efficiency': [0.92, 0.94, 0.91, 0.93, 0.95, 0.94],
                'Cost Efficiency': [0.78, 0.82, 0.80, 0.85, 0.87, 0.86]
            }

            df_trends = pd.DataFrame(trend_data)

            # Line chart for trends
            fig = px.line(
                df_trends.melt(id_vars=['Month'], var_name='Metric', value_name='Value'),
                x='Month',
                y='Value',
                color='Metric',
                title='Fleet Performance Trends'
            )
            st.plotly_chart(fig)

            # Key Performance Indicators
            st.subheader("Fleet KPIs")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Average Fleet Utilization",
                    "87%",
                    "↑ 3%"
                )
            with col2:
                st.metric(
                    "On-Time Delivery Rate",
                    "92%",
                    "↑ 5%"
                )
            with col3:
                st.metric(
                    "Cost per Mile",
                    "$2.34",
                    "↓ $0.12"
                )

        except Exception as e:
            st.error(f"Error loading analytics data: {str(e)}")

    def _sort_vessels(self, vessels: list, sort_by: str) -> list:
        """Sort vessels based on selected criteria"""
        if sort_by == "Name":
            return sorted(vessels, key=lambda x: x.name)
        elif sort_by == "Status":
            return sorted(vessels, key=lambda x: x.status.value)
        elif sort_by == "Delay Time":
            return sorted(vessels, key=lambda x: x.current_delay.total_seconds(), reverse=True)
        elif sort_by == "ETA":
            return sorted(vessels, key=lambda x: x.current_eta)
        else:
            return vessels  # Return unsorted if no valid sort criteria

    def _show_fleet_summary(self, vessels):
        """Display fleet-wide summary metrics"""
        total_vessels = len(vessels)
        delayed_vessels = sum(1 for v in vessels if v.is_delayed())
        total_delay_cost = sum(v.total_delay_cost for v in vessels)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Vessels", total_vessels)
        with col2:
            st.metric("Delayed Vessels", delayed_vessels)
        with col3:
            st.metric("Total Delay Cost", f"${total_delay_cost:,.2f}")

    def _show_vessel_card(self, vessel):
        """Display individual vessel information card"""
        status_info = vessel.get_status_info()
        weather_info = vessel.get_weather_summary()
        engine_status = vessel.check_engine_parameters()

        with st.expander(f"🚢 {vessel.name}"):
            # Status and ETA information
            st.write("📍 **Current Status**")
            status_color = "🟢" if not vessel.is_delayed() else "🔴"
            st.write(f"{status_color} Status: {status_info['status']}")

            # Time Information
            st.write("⏰ **Time Information**")
            original_eta = vessel.original_eta.strftime('%Y-%m-%d %H:%M')
            current_eta = vessel.current_eta.strftime('%Y-%m-%d %H:%M')
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

            # Performance Metrics
            st.write("📊 **Performance**")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Speed", f"{vessel.speed:.1f} knots")
                st.metric("Fuel Level", f"{vessel.fuel_level:.1f}%")
            with col2:

                st.metric("Engine Load", f"{engine_status['current_values']['load']:.1f}%")
                st.metric("Engine Temp", f"{engine_status['current_values']['temperature']:.1f}°C")

            # Speed History
            if vessel.speed_history:
                st.write("📈 **Speed History**")
                st.line_chart(vessel.speed_history)

            # Weather Information
            if weather_info:
                st.write("🌊 **Weather Conditions**")
                st.write(f"Current: {weather_info['current']}")

                if weather_info.get('alerts'):
                    for alert in weather_info['alerts']:
                        st.error(f"""
                            ⚠️ Weather Alert
                            Condition: {alert['condition']}
                            Wind: {alert['wind_speed']:.1f} knots
                            Waves: {alert['wave_height']:.1f}m
                        """)

    def _center_map(self):
        """Center map on fleet average position"""
        # This method will be called when the "Center Map" button is clicked
        pass  # For now, we'll just pass as we need vessel positions to implement

    def _toggle_tracks(self):
        """Toggle visibility of vessel tracks"""
        # This method will be called when the "Show All Tracks" button is clicked
        pass  # For now, we'll just pass as we need to implement track toggling

    def _get_route_traffic(self):
        """Get route traffic data"""
        # Προσωρινή υλοποίηση
        return {
            'density': 'medium',
            'vessels_nearby': 5
        }

    def _get_seasonal_data(self):
        """Get seasonal patterns data"""
        # Προσωρινή υλοποίηση
        return {
            'season': 'winter',
            'typical_delays': 2
        }

    def _get_historical_delays(self):
        """Get historical delay data"""
        # Προσωρινή υλοποίηση
        return {
            'average_delay': 3,
            'common_causes': ['weather', 'port congestion']
        }

    def _get_fuel_prices(self):
        """Get current fuel prices"""
        return {
            'HFO': 500,
            'MGO': 750
        }

    def _get_port_congestion(self):
        """Get port congestion data"""
        # Προσωρινή υλοποίηση
        return {
            'level': 'medium',
            'waiting_time': 2
        }

    def _get_market_data(self):
        """Get market conditions data"""
        # Προσωρινή υλοποίηση
        return {
            'freight_rates': 1200,
            'market_trend': 'stable'
        }


if __name__ == "__main__":
    st.set_page_config(
    page_title="Fleet Monitor",
    page_icon="🚢",
    layout="wide"
        )

    dashboard = Dashboard()
    dashboard.run()
