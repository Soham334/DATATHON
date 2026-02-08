# TVSI: Traffic Vital Stability Index

A real-time computer vision system that predicts traffic congestion before it occurs, using a unified stability metric that fuses flow-density dynamics, speed variance, and spatio-temporal coordination signals.

---

## Problem Statement

Traditional traffic monitoring systems fail for two fundamental reasons:

**1. Siloed Metrics**  
Flow and density are typically analyzed in isolation. High flow with moderate density may look acceptable, but masks impending breakdown. By the time density spikes, the system is already in gridlock.

**2. Reactive Alerting**  
Conventional systems trigger alerts after congestion has formed. At that point, intervention options are limited to damage control. Traffic operators need predictive signals that fire while the system can still recover.

TVSI addresses both failures by computing a single, continuous stability score that captures the trajectory of traffic health, not just its current state.

---

## Core Idea: Traffic Vital Stability Index (TVSI)

TVSI is a bounded score in the range `[-1, +1]` that represents traffic system health at any moment.

**Formula:**
```
TVSI = 0.5 × TFSI - 0.25 × SpeedVariance - 0.25 × ST-GCN_Anomaly
```

Where:
```
TFSI = NormalizedFlow - 2 × NormalizedDensity
```

**Component Intuition:**

| Component | What It Captures | Weight |
|-----------|------------------|--------|
| TFSI (Traffic Flow Stability Index) | Balance between throughput and crowding. Positive when flow dominates; negative when density chokes the system. | 50% |
| Speed Variance | Uniformity of vehicle speeds. High variance indicates stop-and-go waves forming. | 25% |
| ST-GCN Anomaly | Coordination loss across space and time. Detects when vehicle movements become chaotic rather than synchronized. | 25% |

**Score Interpretation:**

| TVSI Range | State | Meaning |
|------------|-------|---------|
| > 0.3 | OPTIMAL | Free-flow traffic, no intervention needed |
| 0.0 to 0.3 | NORMAL | Stable conditions with minor fluctuations |
| -0.2 to 0.0 | CAUTION | Early signs of degradation |
| -0.35 to -0.2 | WARNING | Amber Alert zone, intervention recommended |
| -0.5 to -0.35 | SEVERE | Active congestion forming |
| < -0.5 | CRITICAL | Gridlock, emergency response required |

---

## Amber Alert: Predictive Early Warning

Amber Alert is the core innovation of this system. Unlike severity-based alerts that fire when conditions are already bad, Amber Alert fires based on the rate of change of TVSI.

**Trigger Conditions:**

1. TVSI derivative exceeds `-0.15` per 5-second window (rapid decline)
2. Current TVSI is in the warning zone (`-0.3` to `+0.2`)
3. Density is rising AND speed is dropping simultaneously

**Why Rate-of-Change Matters:**

A TVSI of `-0.1` is not alarming on its own. But if TVSI was `+0.3` five seconds ago, that trajectory predicts gridlock within 30-60 seconds. Amber Alert captures this predictive signal.

**Time-to-Congestion Prediction:**

The system extrapolates current decline rate to estimate when TVSI will cross the critical threshold (`-0.5`). This gives operators a countdown for intervention.

**Philosophy:**  
"Intervene while recovery is still possible, not after the system has failed."

---

## System Architecture

The pipeline consists of four layers:

**1. Perception Layer**
- YOLOv8 vehicle detection (classes: car, motorcycle, bus, truck)
- ByteTrack multi-object tracking with 90%+ accuracy
- Per-vehicle speed estimation via centroid displacement

**2. Aggregation Layer**
- 5-second sliding window at 30 FPS
- Flow: unique vehicles crossing ROI per window
- Density: concurrent vehicles in frame
- Speed statistics: mean, variance, distribution shape

**3. Reasoning Layer**
- TFSI computation from normalized flow/density
- Speed variance normalization against baseline
- ST-GCN anomaly signal (simulated from variance + density patterns)
- TVSI fusion with bounded output

**4. Action Layer**
- State classification (OPTIMAL through CRITICAL)
- Amber Alert detection from TVSI derivative
- Time-to-congestion prediction
- Actionable recommendations (signal timing, ramp metering, lane management)

---

## Dataset and Adaptability

This system is explicitly designed to be dataset-agnostic.

**No Hard-Coded Assumptions:**
- No dependency on METR-LA sensor IDs or LA road topology
- No pre-trained city-specific models
- No fixed camera angles or resolutions

**Adaptation Mechanisms:**

| Input Variation | How System Adapts |
|-----------------|-------------------|
| Different camera feeds | YOLO generalizes across angles; ROI is configurable |
| Different sensor densities | Baseline calibration runs during first N frames |
| Different cities | Flow/density normalization adapts to local capacity |
| Different vehicle mixes | Class-agnostic counting (any detected vehicle contributes) |

**Integration with Forecasting Pipelines:**

TVSI outputs can feed directly into spatio-temporal forecasting models like ST-GCN, DCRNN, or Graph WaveNet. The per-frame TVSI time-series becomes a node feature for graph-based prediction, enabling city-wide congestion forecasting.

---

## How to Run

**Installation:**
```bash
pip install -r requirements.txt
```

**Basic Usage:**
```bash
python hackathon_traffic_system.py
```

**Input Options:**
- `--video path/to/video.mp4` — Process local video file
- `--camera 0` — Use webcam or IP camera
- `--youtube URL` — Download and process YouTube video

**Example:**
```bash
python hackathon_traffic_system.py --video traffic_feed.mp4
```

**Dashboard:**
```bash
streamlit run dashboard.py
```

---

## Outputs

The system generates the following artifacts:

| Output | Description |
|--------|-------------|
| `tvsi_results.csv` | Per-frame TVSI scores with state, severity, flow, density, speed, alerts |
| `traffic_data.csv` | Raw vehicle detections with class, position, speed, track ID |
| `congestion_events.csv` | Logged congestion incidents with timestamps and duration |
| `tvsi_alerts.txt` | Amber Alert log with trigger reasons and recommended actions |
| `overspeed_alerts.txt` | Speeding vehicle detections |
| `tvsi_traffic_analysis.mp4` | Processed video with TVSI overlay, bounding boxes, and state indicator |

---

## Why This Is Novel

**1. TVSI as a Continuous Stability Signal**  
Unlike binary congestion detection, TVSI provides a smooth, differentiable signal that captures the full spectrum from free-flow to gridlock. This enables gradient-based optimization of traffic control.

**2. Amber Alert as Pre-Failure Intervention**  
Rate-of-change alerting is borrowed from medical vital sign monitoring. Just as a dropping heart rate triggers intervention before cardiac arrest, dropping TVSI triggers intervention before gridlock.

**3. Separation of Perception and Reasoning**  
YOLO handles "what vehicles are where." TVSI handles "is the system healthy." This separation means the perception layer can be swapped (radar, lidar, sensor fusion) without changing the reasoning layer.

**4. Explainability**  
Every TVSI score can be decomposed into its three components. Operators can see exactly why the system is degrading (flow imbalance vs. speed chaos vs. coordination loss).

---

## Hackathon Scope Disclaimer

**ST-GCN Simulation:**  
The ST-GCN anomaly signal in this demo is simulated using speed variance and density patterns. The architecture supports integration with a trained ST-GCN model (e.g., from METR-LA or PEMS-BAY datasets) by replacing the simulation function with model inference.

**Focus on Decision Intelligence:**  
This project emphasizes the reasoning layer, not raw detection accuracy. YOLO and ByteTrack are off-the-shelf. The contribution is the TVSI formulation, Amber Alert logic, and the decision framework that transforms perception into actionable intelligence.

**Production Considerations:**  
A production deployment would add: multi-camera fusion, historical baseline learning, integration with traffic signal controllers, and real-time ST-GCN inference. These are out of scope for this hackathon but architecturally supported.

---

## License

MIT License. See LICENSE file for details.