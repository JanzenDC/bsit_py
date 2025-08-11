# EDSA Road Crash Spatial Analysis

A comprehensive Python tool for analyzing road crash patterns along EDSA (Epifanio de los Santos Avenue) in Metro Manila, Philippines. This project uses advanced spatial analysis techniques including Kernel Density Estimation (KDE) and DBSCAN clustering to identify crash hotspots and provide actionable insights for road safety improvements.

## Features

### 🔍 Spatial Analysis
- **Kernel Density Estimation (KDE)**: Creates density heatmaps to visualize crash concentration areas
- **DBSCAN Clustering**: Automatically identifies crash hotspots using density-based clustering
- **Geographic Filtering**: Focuses analysis on EDSA corridor coordinates
- **Performance Evaluation**: Calculates hit rates, silhouette scores, and clustering metrics

### 📊 Visualizations
- **Static Plots**: Four-panel matplotlib visualizations including scatter plots, heatmaps, and temporal analysis
- **Interactive Maps**: Folium-based web maps with crash markers, hotspots, and heatmap overlays
- **Temporal Analysis**: Time-series plots showing crash patterns over time
- **Cluster Visualization**: Color-coded display of identified crash clusters

### 📈 Reporting
- **Performance Metrics**: Comprehensive model evaluation with multiple statistical measures
- **Summary Reports**: Detailed analysis reports with key findings and recommendations
- **Hotspot Ranking**: Identification and ranking of the most dangerous locations

## Installation

### Prerequisites
- Python 3.7 or higher
- pip package manager

### Required Dependencies

```bash
pip install pandas numpy geopandas shapely matplotlib seaborn scikit-learn scipy folium
```

### Individual Package Installation
```bash
pip install pandas>=1.3.0
pip install numpy>=1.20.0
pip install geopandas>=0.10.0
pip install shapely>=1.8.0
pip install matplotlib>=3.5.0
pip install seaborn>=0.11.0
pip install scikit-learn>=1.0.0
pip install scipy>=1.7.0
pip install folium>=0.12.0
```

## Usage

### Quick Start

1. **Clone or download** the script file
2. **Run the main script**:
   ```bash
   python edsa_crash_analyzer.py
   ```
3. **Choose data source**:
   - Type `y` to use sample data (for testing)
   - Type `n` to provide your own CSV file path

### Using Your Own Data

Prepare a CSV file with the following required columns:
- `latitude`: Crash location latitude (decimal degrees)
- `longitude`: Crash location longitude (decimal degrees)

Optional columns for enhanced analysis:
- `date`: Crash date (MM/DD/YYYY format)
- `severity`: Crash severity (`Minor`, `Major`, `Fatal`)
- `vehicle_type`: Type of vehicle involved
- `crash_id`: Unique identifier for each crash

### Example Usage

```python
from edsa_crash_analyzer import EDSACrashAnalyzer

# Initialize analyzer
analyzer = EDSACrashAnalyzer()

# Load your data
analyzer.load_crash_data('your_crash_data.csv')

# Run complete analysis
analyzer.preprocess_data()
analyzer.perform_kde_analysis(bandwidth=0.008)
analyzer.identify_hotspots(threshold_percentile=85)
analyzer.evaluate_model_performance()

# Generate visualizations
analyzer.create_visualizations()
analyzer.create_interactive_map('crash_map.html')
```

## Configuration Options

### KDE Analysis Parameters
- `bandwidth`: Controls smoothing level (default: 0.008)
  - Smaller values: More detailed, localized patterns
  - Larger values: Broader, smoother patterns

### Hotspot Detection Parameters
- `threshold_percentile`: Percentile for hotspot identification (default: 85)
- `eps`: DBSCAN clustering radius (default: 0.005)
- `min_samples`: Minimum points per cluster (default: 5)

### Geographic Bounds
The analysis is pre-configured for the EDSA corridor:
- Latitude: 14.4° to 14.8° N
- Longitude: 120.9° to 121.2° E

Modify these bounds in the `preprocess_data()` method for other areas.

## Output Files

### Generated Visualizations
1. **Four-panel static plot**: Comprehensive analysis overview
2. **Interactive HTML map**: `edsa_crash_analysis.html` (or custom filename)
3. **Console output**: Detailed performance metrics and summary report

### Sample Output Structure
```
📊 Analysis Results:
├── Static visualization (matplotlib plot)
├── Interactive map (HTML file)
├── Performance metrics (console)
└── Summary report (console)
```

## Methodology

### 1. Data Preprocessing
- Removes records with missing coordinates
- Filters data to EDSA corridor geographic bounds
- Creates GeoDataFrame with proper coordinate reference system

### 2. Kernel Density Estimation
- Applies Gaussian kernel to crash coordinates
- Creates continuous density surface
- Generates probability distribution of crash likelihood

### 3. Hotspot Identification
- Uses DBSCAN clustering algorithm
- Groups nearby crashes into clusters
- Calculates severity scores for each hotspot
- Ranks hotspots by crash frequency and severity

### 4. Performance Evaluation
- **Hit Rate**: Percentage of crashes within high-density areas
- **Silhouette Score**: Quality of clustering results
- **Cluster Metrics**: Number of clusters and noise ratio

## Sample Data

The tool includes a sample data generator that creates realistic crash data for testing:
- 45 total crash records
- 3 main cluster areas (North, Central, South EDSA)
- Mixed severity levels and vehicle types
- Temporal distribution across multiple months

## Limitations

- Designed specifically for EDSA corridor coordinates
- Requires minimum data density for effective clustering
- Performance depends on data quality and completeness
- Geographic bounds may need adjustment for other highways

## Contributing

Contributions are welcome! Areas for improvement:
- Additional clustering algorithms
- Enhanced temporal analysis features
- Integration with real-time traffic data
- Support for multiple highway corridors
- Advanced severity weighting schemes

## Use Cases

### Traffic Management
- Identify high-risk intersections requiring traffic signals
- Plan speed reduction zones and safety barriers
- Optimize emergency response station locations

### Urban Planning
- Inform infrastructure development decisions
- Guide pedestrian overpass/underpass placement
- Support evidence-based road safety policies

### Research Applications
- Academic studies on urban traffic safety
- Transportation engineering analysis
- Public health research on road safety

## Performance Tips

### For Large Datasets (>10,000 records):
- Increase KDE bandwidth (0.01-0.02) for faster processing
- Consider data sampling for initial analysis
- Use higher `min_samples` parameter for clustering

### For Small Datasets (<100 records):
- Decrease KDE bandwidth (0.005-0.008) for better resolution
- Lower `min_samples` parameter (3-5) for clustering
- Reduce `threshold_percentile` (70-80) for hotspot detection

## Troubleshooting

### Common Issues

**"File not found" Error**
- Ensure CSV file path is correct
- Check file permissions
- Verify file format (CSV with proper encoding)

**"Missing required columns" Error**
- Ensure CSV contains `latitude` and `longitude` columns
- Check column name spelling and capitalization
- Remove any special characters from column names

**Empty Visualization Results**
- Verify data falls within EDSA coordinate bounds
- Check for valid coordinate formats (decimal degrees)
- Ensure sufficient data points for clustering

**Poor Clustering Results**
- Adjust DBSCAN parameters (`eps`, `min_samples`)
- Try different KDE bandwidth values
- Verify data quality and coordinate accuracy

## License

This project is open source. Feel free to modify and distribute according to your needs.

## Acknowledgments

- Built using Python's scientific computing ecosystem
- Leverages GeoPandas for spatial data handling
- Uses Folium for interactive web mapping
- Implements scikit-learn algorithms for machine learning analysis