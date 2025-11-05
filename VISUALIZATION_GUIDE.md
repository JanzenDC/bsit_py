# Enhanced Visualization Guide

## Overview
The EDSA Crash Analyzer now creates professional-looking heatmap visualizations similar to your reference image, with enhanced color gradients and interactive features.

## New Features

### 🎨 Enhanced Heatmap Colors
The heatmap now uses a smooth gradient transition:
- **Blue** → Low crash density areas
- **Cyan** → Slightly elevated density
- **Green/Lime** → Moderate density
- **Yellow** → Higher density
- **Orange** → Very high density
- **Red** → Extreme density (hotspots)

### 🗺️ Two Map Styles

#### 1. Detailed Map (`edsa_crash_detailed.html`)
- Shows individual crash markers
- Displays hotspot warning triangles
- Full heatmap overlay
- Layer controls to toggle visibility
- Detailed popups with crash information

#### 2. Heatmap-Only Map (`edsa_crash_heatmap.html`)
- **Clean view similar to your reference image**
- Only shows heatmap and hotspot markers
- No individual crash dots (cleaner appearance)
- Perfect for presentations and reports

### 🎯 Interactive Features

#### Layer Control (Top Right)
Toggle visibility of:
- Individual Crashes
- Hotspot Markers
- Heatmap layer

#### Multiple Base Maps
Switch between:
- OpenStreetMap (default)
- Light Map (CartoDB Positron) - cleaner look
- Dark Map (CartoDB Dark Matter) - high contrast

#### Legend (Top Left)
Shows color coding:
- Blue ● = Low Density
- Yellow ● = Medium Density
- Red ● = High Density

#### Hotspot Markers
- Light blue warning triangle icons
- Click for detailed information:
  - Number of crashes
  - Severity score
  - Exact coordinates

## How to Use

### Basic Usage
```python
from bsit import EDSACrashAnalyzer

analyzer = EDSACrashAnalyzer()
analyzer.load_crash_data_from_directory('CSVData')
analyzer.preprocess_data()
analyzer.perform_kde_analysis(bandwidth=0.008)
analyzer.identify_hotspots(threshold_percentile=85)

# Create both map styles
analyzer.create_interactive_map('detailed_map.html', style='detailed')
analyzer.create_interactive_map('heatmap_only.html', style='heatmap_only')
```

### Quick Analysis
```bash
python bsit.py
# Select option 1 to load from CSVData
# Two HTML files will be generated automatically
```

### Custom Parameters

#### Adjust Heatmap Appearance
```python
# For smoother, more continuous heatmap
analyzer.perform_kde_analysis(bandwidth=0.012)

# For more detailed, granular heatmap
analyzer.perform_kde_analysis(bandwidth=0.005)
```

#### Adjust Hotspot Sensitivity
```python
# Find more hotspots (lower threshold)
analyzer.identify_hotspots(threshold_percentile=75)

# Find fewer, more critical hotspots (higher threshold)
analyzer.identify_hotspots(threshold_percentile=90)
```

## Output Files

When you run the analysis, you'll get:

1. **edsa_crash_detailed.html**
   - Full-featured interactive map
   - All layers visible by default
   - Good for detailed analysis

2. **edsa_crash_heatmap.html**
   - Clean heatmap view
   - **Similar to your reference image**
   - Only heatmap + hotspot markers
   - Perfect for presentations

3. **Static plots window**
   - 4-panel matplotlib visualization
   - Shows distribution, KDE, temporal patterns, and clusters

## Customization Options

### Change Map Center and Zoom
```python
# In the create_interactive_map method, modify:
m = folium.Map(
    location=[14.6, 121.03],  # Custom center [lat, lon]
    zoom_start=13,             # Higher = more zoomed in
    tiles='CartoDB positron'   # Clean base map
)
```

### Modify Heatmap Parameters
The heatmap is configured with:
- `min_opacity=0.2` - Minimum visibility (0-1)
- `max_opacity=0.8` - Maximum visibility (0-1)
- `radius=25` - Size of heat influence
- `blur=20` - Smoothness of gradient
- Custom gradient colors (blue to red)

### Change Hotspot Icons
```python
# In create_interactive_map, modify the icon:
icon=folium.Icon(
    color='red',           # Background color
    icon='exclamation-sign', # Different icon
    prefix='glyphicon'
)
```

## Tips for Best Results

### For Your Metro Manila Data:

1. **Optimal KDE Bandwidth**: 0.008 - 0.012
   - Good balance between detail and smoothness

2. **Recommended Threshold**: 80-85 percentile
   - Identifies significant hotspots without too much noise

3. **Best Map Style for Presentations**: `heatmap_only`
   - Clean, professional appearance
   - Focuses on the heatmap visualization
   - Similar to traffic congestion maps

4. **For Detailed Analysis**: `detailed`
   - See individual crash locations
   - Identify specific problem intersections

## Viewing the Maps

1. Run the analysis:
   ```bash
   python bsit.py
   ```

2. Open the generated HTML files in any web browser:
   ```bash
   # Windows
   start edsa_crash_heatmap.html
   
   # Mac/Linux
   open edsa_crash_heatmap.html
   ```

3. **Interactive Controls**:
   - **Zoom**: Mouse wheel or +/- buttons
   - **Pan**: Click and drag
   - **Layers**: Use control panel (top right)
   - **Info**: Click on hotspot markers
   - **Base Map**: Switch between map styles

## Comparison with Reference Image

Your reference image shows:
✅ Smooth color gradient (blue→red) - **Implemented**
✅ Warning triangle markers for hotspots - **Implemented**
✅ Clean map appearance - **Available in heatmap_only style**
✅ Overlay on street map - **Implemented**
✅ Good color contrast - **Implemented with enhanced gradient**

## Example Output

After running the analysis, your heatmap will show:

- **High-density areas** (red/orange): Major crash hotspots along EDSA
- **Medium-density areas** (yellow/green): Moderate risk zones
- **Low-density areas** (blue/cyan): Lower risk areas
- **Warning markers**: Identified hotspots with crash counts

## Troubleshooting

### Map looks too smooth
```python
# Reduce bandwidth for more detail
analyzer.perform_kde_analysis(bandwidth=0.005)
```

### Too many hotspot markers
```python
# Increase threshold to show only critical hotspots
analyzer.identify_hotspots(threshold_percentile=90)
```

### Heatmap too faint
```python
# Modify in create_interactive_map (line ~476):
min_opacity=0.3,  # Increase from 0.2
max_opacity=0.9,  # Increase from 0.8
```

### Want different colors
```python
# Modify gradient in create_interactive_map (line ~481):
gradient={
    0.0: 'navy',      # Darkest blue
    0.3: 'blue',
    0.5: 'yellow',
    0.7: 'orange',
    1.0: 'darkred'    # Darkest red
}
```

## Next Steps

1. Run your analysis with all CSV files
2. Open `edsa_crash_heatmap.html` for the clean view
3. Share the HTML file - it's fully self-contained
4. Adjust parameters if needed for better visualization
5. Export screenshots for reports/presentations

## Questions?

The enhanced visualization is now ready to use! Just run:
```bash
python bsit.py
```

Select option 1, and you'll get both map styles automatically.

