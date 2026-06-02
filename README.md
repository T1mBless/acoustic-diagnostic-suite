# 🎛️ Acoustic Diagnostic Suite

A desktop application for architectural acoustics analysis and treatment design, built for recording studios, control rooms, and critical listening spaces.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python) ![License](https://img.shields.io/badge/License-MIT-green) ![Status](https://img.shields.io/badge/Status-Active-brightgreen)

---

## Screenshots

<!-- Add a screenshot of the app here: assets/screenshot.png -->
![App Screenshot](assets/screenshot.png)

---

## Features

- **RT60 Prediction (Eyring-Norris)** — Full reverb time calculation across 6 octave bands (125 Hz – 4 kHz), with air absorption coefficient per band. Compares empty room vs. treated room in real time.
- **Room Mode Analysis** — Computes axial, tangential, and oblique modes up to 200 Hz. Visualizes pressure maps per mode on a 2D floor plan.
- **Bolt & Bonello Criteria** — Graphical evaluation of room proportions (Bolt chart) and modal density distribution (Bonello criterion).
- **Interactive Floor Plan** — Drag-and-drop placement of monitors and sweet spot. Real-time readout of listening angle and left/right asymmetry.
- **Panel Calculator** — Add acoustic treatment panels per surface, with automatic Sabine unit accounting and area deduction from the target wall.
- **Inverse Absorption Predictor** — Given a target RT60 and frequency band, calculates the exact m² of absorber required using Eyring in reverse.
- **Material Library** — CSV-based material database with absorption coefficients per octave band. Easily extendable.
- **Session Save / Load** — Export and restore full room configurations as JSON.

---

## Technical Stack

| Layer | Technology |
|---|---|
| GUI | CustomTkinter + ttk |
| Numerics | NumPy |
| Visualization | Matplotlib (embedded via FigureCanvasTkAgg) |
| Persistence | CSV (materials), JSON (sessions) |
| Language | Python 3.10+ |

---

## Acoustic Models

- **Reverberation**: Eyring-Norris equation with air absorption term `4mV`
- **Modal frequencies**: `f = (c/2) * sqrt((p/L)² + (q/W)² + (r/H)²)`
- **Bonello criterion**: Mode count monotonicity across 1/3-octave bands from 16 to 200 Hz
- **Bolt chart**: Room proportion ratios W/H vs L/H plotted against the Bolt optimal region
- **Inverse predictor**: Solves for required absorber area `A = ΔS_Eyring / (α_new − α_base)`

---

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/acoustic-diagnostic-suite.git
cd acoustic-diagnostic-suite
pip install -r requirements.txt
python Modulo1.py
```

**Requirements**: Python 3.10+, see `requirements.txt`.

---

## Usage

1. Enter room dimensions (L × W × H in meters)
2. Assign structural materials to each surface from the dropdown menus
3. Click **▶ Calcular Diagnóstico** to run the full analysis
4. Navigate tabs: **Geometría** (floor plan + modes), **Criterios** (Bolt/Bonello), **Absorción** (RT60 + treatment)
5. In the Absorción tab, select a material, set panel dimensions, and click **Agregar Paneles** to simulate treatment
6. Use the **Predicción Inversa** panel to calculate exactly how much absorber you need for a target RT60

---

## Extending the Material Library

Edit `materiales.csv` directly. Each row follows this format:

```
Material Name,α_125Hz,α_250Hz,α_500Hz,α_1kHz,α_2kHz,α_4kHz
Rockwool 50mm,0.15,0.40,0.85,0.99,0.99,0.99
```

The app loads the CSV on startup. No code changes required.

---

## Roadmap

- [ ] Export RT60 report as PDF
- [ ] 3D room mode visualization (axial cross-sections)
- [ ] Schroeder frequency indicator
- [ ] JUCE/C++ plugin version for DAW integration

---

## Author

**Tim Bless / Reder** — Sound Engineer & Software Developer  
Universidad de San Buenaventura · SENA · CBFK  
Bogotá, Colombia

---

## License

MIT License — free to use, modify, and distribute with attribution.
