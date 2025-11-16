## EDSA Crash Analysis – All-in-One Guide

A complete toolkit to analyze and visualize EDSA crash data with multiple high-quality outputs:
- Interactive heatmaps (Folium)
- GIS-style parcel/zone maps (Folium)
- GPU-accelerated MapLibre GL JS maps (via browser)
- Analytical dashboards (Matplotlib)


## What’s in this project

- `bsit.py`: Core analysis engine (data loading, preprocessing, KDE heatmap, DBSCAN hotspots, metrics, dashboards, Folium maps). Also includes quick/fast modes.
- `create_heatmap_visualization.py`: Quick clean heatmap generator (Folium) similar to your reference image.
- `create_gis_style_visualization.py`: GIS-style zone/parcel map (Folium) with labeled crash counts and professional legend.
- `create_maplibre_visualization.py`: High-performance, GPU-accelerated MapLibre GL JS visualizations with optional GIS parcel overlay.
- `install_this.txt`: One-line pip command to install required Python packages.


## Requirements

- Python 3.9+ (3.10/3.11 recommended)
- Internet access when using MapLibre (loads JS/CSS from CDN)
- Crash CSV files in a `CSVData/` folder (see Data Format below)


## Installation

You can install everything with the single command found in `install_this.txt`.

```bash
python -m pip install pandas numpy geopandas matplotlib seaborn scikit-learn scipy folium
```

Optional (only if geopandas wheels fail on your system):
- Use Conda/Mamba: `conda install -c conda-forge geopandas`

Tip (Windows): If you have multiple Python versions, replace `python` with `py` or `python3` as appropriate.


## Dataset Setup

1) Create a folder named `CSVData` in the project root.
2) Place your CSV files inside, ideally with year in the filename (e.g., `edsa_crashes_2020.csv`).
3) Minimum required columns:
   - `latitude`
   - `longitude`

Nice-to-have columns (auto-detected if present):
- `year`, `severity`, `crash_id`, `date`, `vehicle_type`

The loader is tolerant to minor column naming differences and degree symbols in coordinates (they’re cleaned automatically).


## Quick Start – Pick One

All commands are executed from the project root directory.

- Ultra-fast analysis (recommended for quick iteration) – generates Folium maps and dashboard:

```bash
python bsit.py
```

By default, this runs recent years in “ultra fast” mode (see bottom of `bsit.py`). Generated files include:
- `edsa_crash_detailed.html`
- `edsa_crash_heatmap.html`


### Clean Heatmap (like the reference image)

```bash
python create_heatmap_visualization.py
```

Outputs:
- `edsa_heatmap_visualization.html` (clean heatmap)
- `edsa_detailed_visualization.html` (detailed map with markers)

The script will:
- Detect available years in `CSVData/`
- Let you choose a year range (press Enter to use all)
- Run preprocessing, KDE, hotspot detection


### GIS-Style Parcel/Zone Map (Folium)

```bash
python create_gis_style_visualization.py
```

Outputs:
- `edsa_gis_style_map.html` (GIS-like parcels with crash counts, labeled)
- `edsa_heatmap_comparison.html` (standard heatmap for comparison)

Key adjustable parameter:
- `zone_size` (degrees): smaller values → more zones, finer detail. Default in script is `0.008` (~0.9 km).


### GPU-Accelerated MapLibre GL JS (Best performance in browser)

```bash
python create_maplibre_visualization.py
```

Outputs:
- `edsa_maplibre_detailed.html` (heatmap + markers + zones)
- `edsa_maplibre_heatmap.html` (clean heatmap)
- `edsa_maplibre_dark.html` (dark theme)

Features:
- Smooth pan/zoom via WebGL (MapLibre GL JS via CDN)
- Optional GIS parcel overlay with same color scheme as Folium GIS map
- Layer toggle button and keyboard shortcuts:
  - `H`: toggle heatmap
  - `M`: toggle markers/zones


## Typical Workflow

1) Prepare `CSVData/` with your crash CSVs.
2) Install Python packages (see Installation).
3) Run one or more scripts based on your needs:
   - Quick Folium outputs: `python bsit.py` or `python create_heatmap_visualization.py`
   - Presentation-ready GIS-style: `python create_gis_style_visualization.py`
   - High-performance browser maps: `python create_maplibre_visualization.py`
4) Open the generated `.html` files in your browser.


## Performance Tips

- Year range: choose fewer years for faster runs in interactive scripts.
- KDE bandwidth (`bsit.py`): `0.008–0.012` gives smooth heatmaps.
- `fast_mode` in `bsit.py`: uses sampling and coarser grids for speed.
- MapLibre:
  - Handles large datasets better; you can limit points when prompted (for very large sets).
- GIS zone size: `0.005–0.02` degrees; smaller is finer but slower/heavier.


## Outputs Overview

Folium-based:
- `edsa_crash_detailed.html`: Points, hotspots, heatmap, layers
- `edsa_crash_heatmap.html`: Clean heatmap view
- `edsa_heatmap_visualization.html`: Clean heatmap (from heatmap script)
- `edsa_detailed_visualization.html`: Detailed map (from heatmap script)
- `edsa_gis_style_map.html`: GIS-style zones with labels and legend
- `edsa_heatmap_comparison.html`: Heatmap comparison for GIS script

MapLibre-based (GPU-accelerated):
- `edsa_maplibre_detailed.html`
- `edsa_maplibre_heatmap.html`
- `edsa_maplibre_dark.html`

Static (Matplotlib):
- Optional 2×2 analytical dashboard (saved as `edsa_dashboard_overview.png` if chosen in MapLibre script)


## Troubleshooting

- “CSVData directory not found”
  - Create `CSVData/` in the project root and place your CSVs inside.

- “Missing required columns: ['latitude', 'longitude']”
  - Ensure your CSVs have these columns. The loader normalizes common variations, but the fields must exist.

- Geopandas install issues on Windows
  - Try a Conda environment: `conda create -n edsa python=3.11 -y && conda activate edsa && conda install -c conda-forge geopandas`

- Very large datasets cause slow browser rendering
  - Prefer MapLibre scripts; when prompted, limit points for rendering.
  - In Folium scripts, consider reducing points (year range) or increasing `zone_size`.

- Empty or tiny outputs
  - Check your data’s coordinate bounds: the code filters to Metro Manila bounds by default in `preprocess_data()`.


## Advanced Notes

- Coordinate cleaning: degree symbols (°, N/S/E/W) are stripped and parsed automatically.
- Hotspots: DBSCAN with reasonable defaults; severity-weighted scores if `severity` present.
- Metrics: hit rate (vs KDE top-percentile), silhouette score, clusters, noise ratio.


## Suggested Environments

Create and activate a virtual environment (optional but recommended):

```bash
# Windows (CMD/PowerShell)
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

Then run the install command from `install_this.txt`:

```bash
python -m pip install pandas numpy geopandas matplotlib seaborn scikit-learn scipy folium
```

You’re ready to run any of the scripts in this project.


