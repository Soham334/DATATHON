"""
=============================================================================
TVSI TRAFFIC INTELLIGENCE DASHBOARD
Production-Grade Streamlit Application with GSAP Kinetic UI
=============================================================================
Version: 2.0.0
Architecture: YOLO + ST-GCN + TVSI Health Monitoring
Design: Sundown Minimalist Aesthetic with Locomotive Scroll
=============================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(
    page_title="TVSI Intelligence Platform",
    layout="wide",
    page_icon="🚦",
    initial_sidebar_state="collapsed"
)

# =============================================================================
# DATA GENERATION & CACHING SYSTEM
# =============================================================================

@st.cache_data(ttl=3600)
def generate_synthetic_traffic_data(n_rows: int = 1000) -> pd.DataFrame:
    """
    Generate synthetic traffic data for demonstration purposes.
    Uses realistic distributions based on urban traffic patterns.
    
    Parameters:
    -----------
    n_rows : int
        Number of synthetic records to generate
        
    Returns:
    --------
    pd.DataFrame
        Synthetic traffic dataset with realistic patterns
    """
    np.random.seed(42)
    
    # Vehicle type distribution (realistic urban mix)
    vehicle_types = ['Car', 'Motorcycle', 'Bus', 'Truck']
    type_weights = [0.70, 0.15, 0.08, 0.07]
    
    # Generate timestamps over 24 hours
    base_time = datetime.now() - timedelta(hours=24)
    timestamps = [base_time + timedelta(seconds=i*86.4) for i in range(n_rows)]
    
    # Generate vehicle IDs
    vehicle_ids = np.arange(1, n_rows + 1)
    
    # Generate vehicle types with weighted distribution
    types = np.random.choice(vehicle_types, size=n_rows, p=type_weights)
    
    # Generate speeds with realistic patterns
    # Peak hours have lower speeds, off-peak higher
    hours = np.array([t.hour for t in timestamps])
    
    # Base speed varies by vehicle type
    base_speeds = {
        'Car': 55,
        'Motorcycle': 60,
        'Bus': 45,
        'Truck': 50
    }
    
    speeds = []
    for i, vtype in enumerate(types):
        base = base_speeds[vtype]
        hour = hours[i]
        
        # Peak hours (7-9, 17-19) have congestion
        if hour in [7, 8, 9, 17, 18, 19]:
            speed = np.random.normal(base * 0.6, 8)
        else:
            speed = np.random.normal(base, 12)
        
        # Add some extreme cases
        if np.random.random() < 0.05:
            speed *= np.random.uniform(1.3, 2.0)
        
        speeds.append(max(0, min(speed, 120)))
    
    # Generate frame numbers
    frames = np.linspace(1, 50000, n_rows).astype(int)
    
    df = pd.DataFrame({
        'Timestamp': timestamps,
        'Vehicle_ID': vehicle_ids,
        'Type': types,
        'Speed_kmh': speeds,
        'Frame': frames
    })
    
    return df


@st.cache_data(ttl=3600)
def generate_synthetic_tvsi_data(n_windows: int = 200) -> pd.DataFrame:
    """
    Generate synthetic TVSI monitoring data.
    
    Parameters:
    -----------
    n_windows : int
        Number of time windows to generate
        
    Returns:
    --------
    pd.DataFrame
        Synthetic TVSI dataset
    """
    np.random.seed(42)
    
    base_time = datetime.now() - timedelta(hours=24)
    timestamps = [base_time + timedelta(seconds=i*432) for i in range(n_windows)]
    
    # Generate realistic TVSI patterns
    tvsi_scores = []
    states = []
    flows = []
    densities = []
    avg_speeds = []
    
    for i in range(n_windows):
        hour = timestamps[i].hour
        
        # Peak hours have worse TVSI
        if hour in [7, 8, 9, 17, 18, 19]:
            tvsi = np.random.normal(-0.2, 0.3)
            flow = np.random.randint(5, 15)
            density = np.random.randint(8, 20)
            avg_speed = np.random.normal(35, 8)
        else:
            tvsi = np.random.normal(0.4, 0.2)
            flow = np.random.randint(15, 30)
            density = np.random.randint(3, 10)
            avg_speed = np.random.normal(55, 10)
        
        tvsi = np.clip(tvsi, -1, 1)
        
        if tvsi > 0.2:
            state = 'Healthy'
            explanation = 'Traffic flowing smoothly with coordinated movement'
        elif tvsi >= -0.3:
            state = 'Stressed'
            explanation = 'Rising density with reduced throughput detected'
        else:
            state = 'Failing'
            explanation = 'Critical congestion - immediate intervention required'
        
        tvsi_scores.append(tvsi)
        states.append(state)
        flows.append(flow)
        densities.append(density)
        avg_speeds.append(max(0, avg_speed))
    
    df = pd.DataFrame({
        'Timestamp': [t.strftime('%Y-%m-%d %H:%M:%S') for t in timestamps],
        'Frame': np.linspace(1, 50000, n_windows).astype(int),
        'TVSI': tvsi_scores,
        'State': states,
        'Explanation': [
            f"Traffic {s.lower()}: {'high throughput' if s == 'Healthy' else 'reduced flow'}"
            for s in states
        ],
        'Flow': flows,
        'Density': densities,
        'Avg_Speed': avg_speeds
    })
    
    return df


@st.cache_data(ttl=3600)
def load_traffic_data() -> Tuple[pd.DataFrame, pd.DataFrame, bool, bool]:
    """
    Load traffic and TVSI data with automatic fallback to synthetic generation.
    
    Returns:
    --------
    Tuple containing:
        - traffic_df: Vehicle detection data
        - tvsi_df: TVSI monitoring data
        - real_traffic: Boolean indicating if real traffic data was loaded
        - real_tvsi: Boolean indicating if real TVSI data was loaded
    """
    real_traffic = False
    real_tvsi = False
    
    # Try loading real traffic data
    try:
        traffic_df = pd.read_excel("traffic_data.xlsx")
        real_traffic = True
    except:
        traffic_df = generate_synthetic_traffic_data(1000)
    
    # Try loading real TVSI data
    try:
        tvsi_df = pd.read_csv("tvsi_results.csv")
        real_tvsi = True
    except:
        tvsi_df = generate_synthetic_tvsi_data(200)
    
    return traffic_df, tvsi_df, real_traffic, real_tvsi


# =============================================================================
# ANALYTICS FUNCTIONS
# =============================================================================

def calculate_traffic_entropy(speeds: np.ndarray, window_size: int = 50) -> float:
    """
    Calculate Shannon entropy of speed distribution as traffic stability metric.
    Higher entropy indicates more chaotic/unpredictable traffic patterns.
    
    Parameters:
    -----------
    speeds : np.ndarray
        Array of vehicle speeds
    window_size : int
        Rolling window size for calculation
        
    Returns:
    --------
    float
        Entropy value (0 = perfectly uniform, higher = more chaotic)
    """
    if len(speeds) < window_size:
        window_size = len(speeds)
    
    # Create speed bins
    bins = np.linspace(0, 120, 13)
    hist, _ = np.histogram(speeds[-window_size:], bins=bins, density=True)
    
    # Remove zero probabilities
    hist = hist[hist > 0]
    
    # Calculate Shannon entropy
    entropy = -np.sum(hist * np.log2(hist))
    
    return entropy


def calculate_system_health(traffic_df: pd.DataFrame, tvsi_df: pd.DataFrame) -> Dict:
    """
    Calculate comprehensive system health metrics.
    
    Parameters:
    -----------
    traffic_df : pd.DataFrame
        Vehicle detection data
    tvsi_df : pd.DataFrame
        TVSI monitoring data
        
    Returns:
    --------
    Dict
        System health metrics
    """
    metrics = {}
    
    # Traffic entropy
    metrics['entropy'] = calculate_traffic_entropy(traffic_df['Speed_kmh'].values)
    
    # TVSI metrics
    if len(tvsi_df) > 0:
        metrics['avg_tvsi'] = tvsi_df['TVSI'].mean()
        metrics['tvsi_volatility'] = tvsi_df['TVSI'].std()
        metrics['health_score'] = (
            (metrics['avg_tvsi'] + 1) / 2 * 100  # Normalize to 0-100
        )
        
        # State distribution
        state_counts = tvsi_df['State'].value_counts()
        total = len(tvsi_df)
        metrics['healthy_pct'] = (state_counts.get('Healthy', 0) / total) * 100
        metrics['stressed_pct'] = (state_counts.get('Stressed', 0) / total) * 100
        metrics['failing_pct'] = (state_counts.get('Failing', 0) / total) * 100
    else:
        metrics['avg_tvsi'] = 0
        metrics['tvsi_volatility'] = 0
        metrics['health_score'] = 50
        metrics['healthy_pct'] = 0
        metrics['stressed_pct'] = 0
        metrics['failing_pct'] = 0
    
    # Speed metrics
    metrics['avg_speed'] = traffic_df['Speed_kmh'].mean()
    metrics['speed_variance'] = traffic_df['Speed_kmh'].var()
    metrics['violations'] = len(traffic_df[traffic_df['Speed_kmh'] > 60])
    metrics['violation_rate'] = (metrics['violations'] / len(traffic_df)) * 100
    
    return metrics


def analyze_peak_hours(traffic_df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze traffic patterns by hour of day.
    
    Parameters:
    -----------
    traffic_df : pd.DataFrame
        Vehicle detection data with Timestamp column
        
    Returns:
    --------
    pd.DataFrame
        Hourly aggregated statistics
    """
    # Ensure Timestamp is datetime
    if not pd.api.types.is_datetime64_any_dtype(traffic_df['Timestamp']):
        traffic_df['Timestamp'] = pd.to_datetime(traffic_df['Timestamp'])
    
    traffic_df['Hour'] = traffic_df['Timestamp'].dt.hour
    
    hourly = traffic_df.groupby('Hour').agg({
        'Speed_kmh': ['mean', 'std', 'count'],
        'Vehicle_ID': 'count'
    }).round(2)
    
    hourly.columns = ['avg_speed', 'speed_std', 'speed_count', 'vehicle_count']
    hourly = hourly.reset_index()
    
    return hourly


# =============================================================================
# VISUALIZATION FUNCTIONS
# =============================================================================

def create_base_layout(title: str) -> Dict:
    """
    Create base Plotly layout with consistent styling.
    
    Parameters:
    -----------
    title : str
        Chart title
        
    Returns:
    --------
    Dict
        Plotly layout configuration
    """
    return {
        'title': {
            'text': f'<b>{title}</b>',
            'font': {'size': 16, 'color': '#ffffff', 'family': 'Space Grotesk'},
            'x': 0,
            'xanchor': 'left'
        },
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'font': {'family': 'Space Grotesk', 'color': '#ffffff'},
        'hovermode': 'closest',
        'margin': {'l': 60, 'r': 20, 't': 60, 'b': 60}
    }


def create_tvsi_timeline(tvsi_df: pd.DataFrame) -> go.Figure:
    """Create TVSI timeline visualization."""
    fig = go.Figure()
    
    colors = {
        'Healthy': '#ffffff',
        'Stressed': '#888888',
        'Failing': '#444444',
        'Initializing': '#666666'
    }
    
    for state in tvsi_df['State'].unique():
        df_state = tvsi_df[tvsi_df['State'] == state]
        fig.add_trace(go.Scatter(
            x=df_state.index,
            y=df_state['TVSI'],
            mode='lines+markers',
            name=state,
            line={'color': colors.get(state, '#ffffff'), 'width': 2},
            marker={'size': 6, 'color': colors.get(state, '#ffffff')},
            hovertemplate=f'<b>{state}</b><br>TVSI: %{{y:.3f}}<br>Window: %{{x}}<extra></extra>'
        ))
    
    fig.add_hline(y=0.2, line_dash="dash", line_color="rgba(255,255,255,0.2)", line_width=1)
    fig.add_hline(y=-0.3, line_dash="dash", line_color="rgba(255,255,255,0.2)", line_width=1)
    
    layout = create_base_layout('TVSI HEALTH SCORE')
    layout.update({
        'xaxis': {
            'title': 'Window Number',
            'gridcolor': 'rgba(255,255,255,0.05)',
            'tickfont': {'color': 'rgba(255,255,255,0.6)'},
            'title_font': {'color': 'rgba(255,255,255,0.5)'}
        },
        'yaxis': {
            'title': 'TVSI Score',
            'gridcolor': 'rgba(255,255,255,0.05)',
            'tickfont': {'color': 'rgba(255,255,255,0.6)'},
            'title_font': {'color': 'rgba(255,255,255,0.5)'},
            'range': [-1.1, 1.1]
        },
        'legend': {
            'font': {'color': 'rgba(255,255,255,0.7)'},
            'bgcolor': 'rgba(0,0,0,0)'
        },
        'height': 450
    })
    
    fig.update_layout(layout)
    return fig


def create_speed_distribution(traffic_df: pd.DataFrame) -> go.Figure:
    """Create speed distribution histogram."""
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=traffic_df['Speed_kmh'],
        nbinsx=30,
        marker={
            'color': '#ffffff',
            'line': {'color': '#0a0a0a', 'width': 1}
        },
        hovertemplate='Speed: %{x:.1f} km/h<br>Count: %{y}<extra></extra>'
    ))
    
    fig.add_vline(
        x=60,
        line_dash="dash",
        line_color="rgba(255,255,255,0.3)",
        line_width=2
    )
    
    layout = create_base_layout('SPEED DISTRIBUTION')
    layout.update({
        'xaxis': {
            'title': 'Speed (km/h)',
            'gridcolor': 'rgba(255,255,255,0.05)',
            'tickfont': {'color': 'rgba(255,255,255,0.6)'},
            'title_font': {'color': 'rgba(255,255,255,0.5)'}
        },
        'yaxis': {
            'title': 'Frequency',
            'gridcolor': 'rgba(255,255,255,0.05)',
            'tickfont': {'color': 'rgba(255,255,255,0.6)'},
            'title_font': {'color': 'rgba(255,255,255,0.5)'}
        },
        'showlegend': False,
        'height': 450
    })
    
    fig.update_layout(layout)
    return fig


def create_vehicle_distribution(traffic_df: pd.DataFrame) -> go.Figure:
    """Create vehicle type distribution pie chart."""
    type_counts = traffic_df['Type'].value_counts()
    
    fig = go.Figure(data=[go.Pie(
        labels=type_counts.index,
        values=type_counts.values,
        hole=0.65,
        marker={
            'colors': ['#ffffff', '#cccccc', '#999999', '#666666'],
            'line': {'color': '#0a0a0a', 'width': 2}
        },
        textfont={'size': 13, 'color': '#ffffff', 'family': 'Space Grotesk'},
        textposition='outside',
        textinfo='label+percent',
        hovertemplate='<b>%{label}</b><br>%{value} vehicles<br>%{percent}<extra></extra>'
    )])
    
    layout = create_base_layout('VEHICLE DISTRIBUTION')
    layout.update({
        'showlegend': False,
        'height': 450,
        'annotations': [{
            'text': f'<b>{len(traffic_df)}</b>',
            'x': 0.5,
            'y': 0.5,
            'font': {'size': 48, 'color': '#ffffff', 'family': 'Space Grotesk'},
            'showarrow': False
        }]
    })
    
    fig.update_layout(layout)
    return fig


def create_hourly_heatmap(hourly_df: pd.DataFrame) -> go.Figure:
    """Create hourly traffic heatmap."""
    fig = go.Figure(data=go.Heatmap(
        x=hourly_df['Hour'],
        y=['Traffic Volume'],
        z=[hourly_df['vehicle_count'].values],
        colorscale=[
            [0, '#000000'],
            [0.5, '#666666'],
            [1, '#ffffff']
        ],
        hovertemplate='Hour: %{x}<br>Vehicles: %{z}<extra></extra>',
        showscale=True,
        colorbar={
            'tickfont': {'color': '#ffffff'},
            'title': {'text': 'Volume', 'font': {'color': '#ffffff'}}
        }
    ))
    
    layout = create_base_layout('HOURLY TRAFFIC VOLUME')
    layout.update({
        'xaxis': {
            'title': 'Hour of Day',
            'tickmode': 'linear',
            'tick0': 0,
            'dtick': 2,
            'tickfont': {'color': 'rgba(255,255,255,0.6)'},
            'title_font': {'color': 'rgba(255,255,255,0.5)'}
        },
        'yaxis': {
            'tickfont': {'color': 'rgba(255,255,255,0.6)'}
        },
        'height': 300
    })
    
    fig.update_layout(layout)
    return fig


def create_speed_violin(traffic_df: pd.DataFrame) -> go.Figure:
    """Create violin plot for speed distribution by vehicle type."""
    fig = go.Figure()
    
    colors = {
        'Car': '#ffffff',
        'Motorcycle': '#cccccc',
        'Bus': '#999999',
        'Truck': '#666666'
    }
    
    for vtype in traffic_df['Type'].unique():
        df_type = traffic_df[traffic_df['Type'] == vtype]
        fig.add_trace(go.Violin(
            y=df_type['Speed_kmh'],
            name=vtype,
            box_visible=True,
            meanline_visible=True,
            fillcolor=colors.get(vtype, '#ffffff'),
            line_color=colors.get(vtype, '#ffffff'),
            opacity=0.6,
            hovertemplate='<b>%{fullData.name}</b><br>Speed: %{y:.1f} km/h<extra></extra>'
        ))
    
    layout = create_base_layout('SPEED DISTRIBUTION BY VEHICLE TYPE')
    layout.update({
        'xaxis': {
            'tickfont': {'color': 'rgba(255,255,255,0.6)'}
        },
        'yaxis': {
            'title': 'Speed (km/h)',
            'gridcolor': 'rgba(255,255,255,0.05)',
            'tickfont': {'color': 'rgba(255,255,255,0.6)'},
            'title_font': {'color': 'rgba(255,255,255,0.5)'}
        },
        'height': 450
    })
    
    fig.update_layout(layout)
    return fig


def create_speed_timeline(traffic_df: pd.DataFrame) -> go.Figure:
    """Create speed timeline scatter plot."""
    fig = go.Figure()
    
    colors = {
        'Car': 'rgba(255,255,255,0.8)',
        'Motorcycle': 'rgba(204,204,204,0.8)',
        'Bus': 'rgba(153,153,153,0.8)',
        'Truck': 'rgba(102,102,102,0.8)'
    }
    
    for vtype in traffic_df['Type'].unique():
        df_type = traffic_df[traffic_df['Type'] == vtype]
        fig.add_trace(go.Scatter(
            x=df_type['Frame'],
            y=df_type['Speed_kmh'],
            mode='markers',
            name=vtype,
            marker={
                'size': 8,
                'color': colors.get(vtype, 'rgba(255,255,255,0.8)'),
                'line': {'color': '#0a0a0a', 'width': 1}
            },
            hovertemplate='<b>%{fullData.name}</b><br>Frame: %{x}<br>Speed: %{y:.1f} km/h<extra></extra>'
        ))
    
    fig.add_hline(y=60, line_dash="dash", line_color="rgba(255,255,255,0.2)", line_width=1)
    
    layout = create_base_layout('SPEED OVER TIME')
    layout.update({
        'xaxis': {
            'title': 'Frame Number',
            'gridcolor': 'rgba(255,255,255,0.05)',
            'tickfont': {'color': 'rgba(255,255,255,0.6)'},
            'title_font': {'color': 'rgba(255,255,255,0.5)'}
        },
        'yaxis': {
            'title': 'Speed (km/h)',
            'gridcolor': 'rgba(255,255,255,0.05)',
            'tickfont': {'color': 'rgba(255,255,255,0.6)'},
            'title_font': {'color': 'rgba(255,255,255,0.5)'}
        },
        'legend': {
            'font': {'color': 'rgba(255,255,255,0.7)'},
            'orientation': 'h',
            'y': 1.15,
            'bgcolor': 'rgba(0,0,0,0)'
        },
        'height': 450
    })
    
    fig.update_layout(layout)
    return fig


def create_correlation_heatmap(traffic_df: pd.DataFrame) -> go.Figure:
    """Create correlation heatmap for numerical features."""
    # Select numerical columns
    numerical_cols = ['Speed_kmh', 'Frame']
    
    # Add hour if available
    if 'Hour' in traffic_df.columns:
        numerical_cols.append('Hour')
    
    corr_matrix = traffic_df[numerical_cols].corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.columns,
        colorscale=[
            [0, '#000000'],
            [0.5, '#666666'],
            [1, '#ffffff']
        ],
        text=corr_matrix.values,
        texttemplate='%{text:.2f}',
        textfont={'color': '#ffffff'},
        hovertemplate='%{x} vs %{y}<br>Correlation: %{z:.3f}<extra></extra>',
        showscale=True,
        colorbar={
            'tickfont': {'color': '#ffffff'},
            'title': {'text': 'Correlation', 'font': {'color': '#ffffff'}}
        }
    ))
    
    layout = create_base_layout('FEATURE CORRELATION MATRIX')
    layout.update({
        'xaxis': {'tickfont': {'color': 'rgba(255,255,255,0.6)'}},
        'yaxis': {'tickfont': {'color': 'rgba(255,255,255,0.6)'}},
        'height': 450
    })
    
    fig.update_layout(layout)
    return fig


# =============================================================================
# CUSTOM CSS WITH GSAP-INSPIRED ANIMATIONS
# =============================================================================

def inject_custom_css():
    """Inject custom CSS with Sundown minimalist aesthetic."""
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        html, body, [data-testid="stAppViewContainer"] {
            background: #000000;
            overflow-x: hidden;
            scroll-behavior: smooth;
        }
        
        .main {
            background: #000000;
            padding: 0;
            max-width: 100%;
        }
        
        /* Hero Section */
        .hero-section {
            position: relative;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 4rem 2rem;
            margin: -2rem -3rem 0 -3rem;
            background: #000000;
            overflow: hidden;
        }
        
        .grid-bg {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: 
                linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
            background-size: 50px 50px;
            z-index: 0;
            animation: gridFade 10s ease-in-out infinite alternate;
        }
        
        @keyframes gridFade {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 0.5; }
        }
        
        .hero-title {
            position: relative;
            z-index: 10;
            font-family: 'Space Grotesk', sans-serif;
            /* Larger, responsive headline */
            font-size: clamp(4rem, 14vw, 12rem);
            font-weight: 800;
            text-align: center;
            line-height: 0.85;
            letter-spacing: -0.02em;
            margin-bottom: 1.5rem;
            /* Gradient text with animated sweep */
            background: linear-gradient(90deg, #ffffff 0%, #a8fff0 25%, #ffd6a5 50%, #ff9aa2 75%, #ffffff 100%);
            background-size: 200% 200%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            color: transparent;
            text-shadow: 0 6px 30px rgba(0,0,0,0.6);
            transform-origin: center;
            animation: gradientShift 6s linear infinite, titleReveal 1.2s cubic-bezier(0.19, 1, 0.22, 1) forwards;
        }
        
        @keyframes titleReveal {
            from {
                opacity: 0;
                transform: translateY(50px);
                filter: blur(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
                filter: blur(0);
            }
        }

        /* Animated gradient sweep for the hero title */
        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        .hero-subtitle {
            position: relative;
            z-index: 10;
            font-family: 'Space Grotesk', sans-serif;
            font-size: clamp(0.9rem, 2vw, 1.3rem);
            font-weight: 300;
            color: rgba(255,255,255,0.5);
            text-align: center;
            max-width: 700px;
            line-height: 1.6;
            letter-spacing: 0.02em;
            margin-bottom: 3rem;
            animation: subtitleReveal 1.5s cubic-bezier(0.19, 1, 0.22, 1) 0.2s forwards;
            opacity: 0;
        }
        
        @keyframes subtitleReveal {
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .hero-divider {
            width: 100%;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            margin: 4rem 0;
            animation: dividerExpand 1.2s cubic-bezier(0.19, 1, 0.22, 1) 0.5s forwards;
            transform: scaleX(0);
        }
        
        @keyframes dividerExpand {
            to { transform: scaleX(1); }
        }
        
        /* Content Sections */
        .content-section {
            padding: 6rem 3rem;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .section-header {
            font-family: 'Space Grotesk', sans-serif;
            font-size: clamp(2rem, 5vw, 4rem);
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 1rem;
            letter-spacing: -0.02em;
            text-transform: uppercase;
            opacity: 0;
            animation: fadeInUp 0.8s cubic-bezier(0.19, 1, 0.22, 1) forwards;
        }
        
        .section-description {
            font-family: 'Space Grotesk', sans-serif;
            font-size: 1rem;
            font-weight: 300;
            color: rgba(255,255,255,0.5);
            margin-bottom: 3rem;
            max-width: 600px;
            opacity: 0;
            animation: fadeInUp 0.8s cubic-bezier(0.19, 1, 0.22, 1) 0.1s forwards;
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        /* Glass Morphism Cards */
        div[data-testid="stMetric"] {
            background: rgba(255,255,255,0.03);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 0;
            padding: 2rem 1.5rem;
            transition: all 0.3s cubic-bezier(0.19, 1, 0.22, 1);
            position: relative;
            overflow: hidden;
        }
        
        div[data-testid="stMetric"]::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 2px;
            background: #ffffff;
            transform: scaleX(0);
            transform-origin: left;
            transition: transform 0.3s cubic-bezier(0.19, 1, 0.22, 1);
        }
        
        div[data-testid="stMetric"]:hover::before {
            transform: scaleX(1);
        }
        
        div[data-testid="stMetric"]:hover {
            background: rgba(255,255,255,0.05);
            border-color: rgba(255,255,255,0.2);
            transform: translateY(-5px);
        }
        
        div[data-testid="stMetric"] label {
            font-family: 'Space Grotesk', sans-serif !important;
            font-size: 0.75rem !important;
            font-weight: 500 !important;
            color: rgba(255,255,255,0.5) !important;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }
        
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
            font-family: 'Space Grotesk', sans-serif !important;
            font-size: 2.5rem !important;
            font-weight: 300 !important;
            color: #ffffff !important;
            letter-spacing: -0.02em;
        }
        
        /* Charts */
        div[data-testid="stPlotlyChart"] {
            background: rgba(255,255,255,0.02);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 0;
            padding: 1.5rem;
            margin-bottom: 2rem;
            transition: all 0.3s cubic-bezier(0.19, 1, 0.22, 1);
        }
        
        div[data-testid="stPlotlyChart"]:hover {
            background: rgba(255,255,255,0.03);
            border-color: rgba(255,255,255,0.15);
        }
        
        /* Alert Boxes */
        .alert-box, .info-box, .warning-box {
            font-family: 'Space Grotesk', sans-serif;
            background: rgba(255,255,255,0.03);
            backdrop-filter: blur(10px);
            border-left: 2px solid;
            padding: 1.5rem;
            margin: 2rem 0;
            font-size: 0.95rem;
            font-weight: 400;
            color: rgba(255,255,255,0.8);
            line-height: 1.6;
            transition: all 0.3s cubic-bezier(0.19, 1, 0.22, 1);
        }
        
        .alert-box {
            border-left-color: #ffffff;
        }
        
        .info-box {
            border-left-color: rgba(255,255,255,0.5);
        }
        
        .warning-box {
            border-left-color: rgba(255,255,255,0.3);
        }
        
        .alert-box:hover, .info-box:hover, .warning-box:hover {
            background: rgba(255,255,255,0.05);
            transform: translateX(5px);
        }
        
        /* Data Frames */
        div[data-testid="stDataFrame"] {
            background: rgba(255,255,255,0.02);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 0;
        }
        
        /* Buttons */
        div.stDownloadButton > button {
            font-family: 'Space Grotesk', sans-serif;
            background: #ffffff;
            color: #000000;
            font-weight: 500;
            border: none;
            padding: 1rem 3rem;
            font-size: 0.85rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            transition: all 0.3s cubic-bezier(0.19, 1, 0.22, 1);
            border-radius: 0;
        }
        
        div.stDownloadButton > button:hover {
            background: rgba(255,255,255,0.9);
            transform: translateY(-2px);
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: #000000;
            border-right: 1px solid rgba(255,255,255,0.1);
        }
        
        section[data-testid="stSidebar"] > div {
            background: #000000;
        }
        
        /* Sidebar widgets */
        .stSelectbox, .stMultiSelect, .stSlider {
            font-family: 'Space Grotesk', sans-serif;
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #000000;
        }
        
        ::-webkit-scrollbar-thumb {
            background: rgba(255,255,255,0.2);
            border-radius: 0;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255,255,255,0.3);
        }
        
        /* Remove default Streamlit padding */
        .block-container {
            padding-top: 0;
            padding-bottom: 0;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .hero-section {
                padding: 3rem 1.5rem;
            }
            
            .content-section {
                padding: 3rem 1.5rem;
            }
            
            .hero-title {
                font-size: clamp(2rem, 10vw, 5rem);
            }
        }
    </style>
    """, unsafe_allow_html=True)


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Main application entry point."""
    
    # Inject custom CSS
    inject_custom_css()
    
    # Load data
    traffic_df, tvsi_df, real_traffic, real_tvsi = load_traffic_data()
    
    # Calculate system health
    health_metrics = calculate_system_health(traffic_df, tvsi_df)
    
    # Analyze peak hours
    hourly_df = analyze_peak_hours(traffic_df)
    
    # =============================================================================
    # HERO SECTION
    # =============================================================================
    
    st.markdown("""
    <div class="hero-section">
        <div class="grid-bg"></div>
        <h1 class="hero-title">TVSI</h1>
        <p class="hero-subtitle">
            Traffic Vital Stability Index — Real-time health monitoring 
            powered by computer vision and spatio-temporal graph learning
        </p>
        <div class="hero-divider"></div>
    </div>
    """, unsafe_allow_html=True)
    
    # =============================================================================
    # SIDEBAR FILTERS
    # =============================================================================
    
    with st.sidebar:
        st.markdown("### FILTERS")
        st.markdown("---")
        
        # Vehicle type filter
        vehicle_types = ['All'] + list(traffic_df['Type'].unique())
        selected_types = st.multiselect(
            "Vehicle Types",
            vehicle_types,
            default=['All']
        )
        
        # Speed range filter
        min_speed, max_speed = st.slider(
            "Speed Range (km/h)",
            0, 120,
            (0, 120)
        )
        
        # Data source indicator
        st.markdown("---")
        st.markdown("### DATA SOURCE")
        if real_traffic:
            st.markdown("✓ Live Traffic Data")
        else:
            st.markdown("⚠ Synthetic Data")
        
        if real_tvsi:
            st.markdown("✓ Live TVSI Data")
        else:
            st.markdown("⚠ Synthetic TVSI")
    
    # Apply filters
    filtered_df = traffic_df.copy()
    
    if 'All' not in selected_types and len(selected_types) > 0:
        filtered_df = filtered_df[filtered_df['Type'].isin(selected_types)]
    
    filtered_df = filtered_df[
        (filtered_df['Speed_kmh'] >= min_speed) &
        (filtered_df['Speed_kmh'] <= max_speed)
    ]
    
    # =============================================================================
    # SYSTEM HEALTH SECTION
    # =============================================================================
    
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<h2 class="section-header">SYSTEM HEALTH</h2>', unsafe_allow_html=True)
    st.markdown('<p class="section-description">Real-time traffic stability metrics</p>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Health Score",
            f"{health_metrics['health_score']:.1f}%"
        )
    
    with col2:
        st.metric(
            "Traffic Entropy",
            f"{health_metrics['entropy']:.3f}"
        )
    
    with col3:
        st.metric(
            "Avg TVSI",
            f"{health_metrics['avg_tvsi']:.3f}"
        )
    
    with col4:
        st.metric(
            "Volatility",
            f"{health_metrics['tvsi_volatility']:.3f}"
        )
    
    # Health status alert
    if health_metrics['health_score'] >= 70:
        st.markdown(
            f'<div class="info-box">✓ System operating normally — {health_metrics["healthy_pct"]:.1f}% of time in healthy state</div>',
            unsafe_allow_html=True
        )
    elif health_metrics['health_score'] >= 40:
        st.markdown(
            f'<div class="warning-box">⚠ System experiencing stress — {health_metrics["stressed_pct"]:.1f}% of time in stressed state</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="alert-box">✗ Critical system failure — {health_metrics["failing_pct"]:.1f}% of time in failing state</div>',
            unsafe_allow_html=True
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # =============================================================================
    # METRICS OVERVIEW
    # =============================================================================
    
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<h2 class="section-header">OVERVIEW</h2>', unsafe_allow_html=True)
    st.markdown('<p class="section-description">Key performance indicators</p>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Vehicles", f"{len(filtered_df):,}")
    
    with col2:
        st.metric("Avg Speed", f"{filtered_df['Speed_kmh'].mean():.1f} km/h")
    
    with col3:
        violations = len(filtered_df[filtered_df['Speed_kmh'] > 60])
        st.metric("Violations", f"{violations:,}")
    
    with col4:
        st.metric("Violation Rate", f"{health_metrics['violation_rate']:.1f}%")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # =============================================================================
    # TVSI ANALYSIS
    # =============================================================================
    
    if len(tvsi_df) > 0:
        st.markdown('<div class="content-section">', unsafe_allow_html=True)
        st.markdown('<h2 class="section-header">TVSI ANALYSIS</h2>', unsafe_allow_html=True)
        st.markdown('<p class="section-description">Traffic health evolution over time</p>', unsafe_allow_html=True)
        
        fig_tvsi = create_tvsi_timeline(tvsi_df)
        st.plotly_chart(fig_tvsi, use_container_width=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # =============================================================================
    # TRAFFIC ANALYTICS
    # =============================================================================
    
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<h2 class="section-header">TRAFFIC ANALYTICS</h2>', unsafe_allow_html=True)
    st.markdown('<p class="section-description">Comprehensive traffic pattern analysis</p>', unsafe_allow_html=True)
    
    # Row 1: Distribution charts
    col1, col2 = st.columns(2)
    
    with col1:
        fig_dist = create_vehicle_distribution(filtered_df)
        st.plotly_chart(fig_dist, use_container_width=True)
    
    with col2:
        fig_speed = create_speed_distribution(filtered_df)
        st.plotly_chart(fig_speed, use_container_width=True)
    
    # Row 2: Violin and Timeline
    col1, col2 = st.columns(2)
    
    with col1:
        fig_violin = create_speed_violin(filtered_df)
        st.plotly_chart(fig_violin, use_container_width=True)
    
    with col2:
        fig_timeline = create_speed_timeline(filtered_df)
        st.plotly_chart(fig_timeline, use_container_width=True)
    
    # Row 3: Heatmap and Correlation
    fig_heatmap = create_hourly_heatmap(hourly_df)
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    fig_corr = create_correlation_heatmap(filtered_df)
    st.plotly_chart(fig_corr, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # =============================================================================
    # TECHNICAL DOCUMENTATION
    # =============================================================================
    
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<h2 class="section-header">ARCHITECTURE</h2>', unsafe_allow_html=True)
    st.markdown('<p class="section-description">System design and methodology</p>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <strong>YOLO (You Only Look Once) Object Detection</strong><br>
        Real-time object detection system that processes video frames at 30+ FPS. 
        Uses YOLOv8n architecture for vehicle detection and classification across 
        four categories: Cars, Motorcycles, Buses, and Trucks.
    </div>
    
    <div class="info-box">
        <strong>ByteTrack Multi-Object Tracking</strong><br>
        State-of-the-art tracking algorithm that maintains vehicle identities across 
        frames with 90%+ accuracy. Enables speed calculation and trajectory analysis 
        through temporal correlation of detections.
    </div>
    
    <div class="info-box">
        <strong>ST-GCN (Spatio-Temporal Graph Convolutional Network)</strong><br>
        Advanced graph neural network that models traffic flow as a dynamic graph. 
        Captures spatial relationships between vehicles and temporal evolution of 
        traffic patterns to detect coordination breakdown.
    </div>
    
    <div class="info-box">
        <strong>TVSI (Traffic Vital Stability Index)</strong><br>
        Novel health metric that fuses spatial (flow, density), temporal (speed variance), 
        and graph-based (ST-GCN anomaly) signals into a single interpretable score in 
        the range [-1, 1]. Provides early warning of congestion before visible breakdown.
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # =============================================================================
    # DATA TABLE
    # =============================================================================
    
    st.markdown('<div class="content-section">', unsafe_allow_html=True)
    st.markdown('<h2 class="section-header">RAW DATA</h2>', unsafe_allow_html=True)
    st.markdown('<p class="section-description">Complete vehicle detection records</p>', unsafe_allow_html=True)
    
    df_display = filtered_df.sort_values('Speed_kmh', ascending=False).reset_index(drop=True)
    st.dataframe(df_display, use_container_width=True, height=400)
    
    # Download button
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        csv_data = df_display.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="DOWNLOAD REPORT",
            data=csv_data,
            file_name=f'tvsi_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            mime='text/csv'
        )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # =============================================================================
    # FOOTER
    # =============================================================================
    
    st.markdown("""
    <div class="content-section" style="text-align: center; padding: 3rem;">
        <p style="color: rgba(255,255,255,0.3); font-family: 'Space Grotesk', sans-serif; font-size: 0.85rem; letter-spacing: 0.1em;">
            TVSI INTELLIGENCE PLATFORM — 2026
        </p>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()