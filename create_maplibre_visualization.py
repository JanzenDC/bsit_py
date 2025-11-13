"""
Enhanced MapLibre GL JS Visualization for EDSA Crash Analysis
Uses GPU-accelerated rendering for better performance with large datasets
Run: python create_maplibre_visualization.py
"""

from bsit import EDSACrashAnalyzer
import os
import json
import pandas as pd

# Note: We don't need maplibre Python package!
# This script generates HTML that uses MapLibre GL JS via CDN


class MapLibreCrashAnalyzer(EDSACrashAnalyzer):
    """Enhanced analyzer with MapLibre GL JS visualization"""
    
    def create_maplibre_heatmap(self, save_path='edsa_maplibre_heatmap.html', 
                                style='detailed', max_points=None):
        """
        Create high-performance MapLibre GL JS heatmap
        
        Parameters:
        -----------
        save_path : str
            Output HTML file path
        style : str
            'detailed' - Heatmap with markers and layers
            'heatmap_only' - Clean heatmap view
            'dark' - Dark theme heatmap
        max_points : int or None
            Maximum points to render (None = all points)
        """
        print("\n" + "="*70)
        print(" Creating MapLibre GL JS High-Performance Map ".center(70))
        print("="*70)
        
        # Prepare data
        if max_points and len(self.crash_data) > max_points:
            print(f"[INFO] Using {max_points} points (sampled from {len(self.crash_data)})...")
            plot_data = self.crash_data.sample(n=max_points, random_state=42)
        else:
            plot_data = self.crash_data
            print(f"[INFO] Rendering all {len(plot_data)} crash points...")
        
        # Convert crash data to GeoJSON
        features = []
        for idx, row in plot_data.iterrows():
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [row['longitude'], row['latitude']]
                },
                "properties": {
                    "crash_id": str(row.get('crash_id', idx)),
                    "severity": str(row.get('severity', 'Unknown')),
                    "year": int(row.get('year', 0)) if 'year' in row and not pd.isna(row['year']) else None
                }
            }
            features.append(feature)
        
        geojson_data = {
            "type": "FeatureCollection",
            "features": features
        }
        
        # Calculate center
        center_lat = self.crash_data['latitude'].mean()
        center_lon = self.crash_data['longitude'].mean()
        
        # Choose style based on theme
        if style == 'dark':
            base_style = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'
        else:
            base_style = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'
        
        # Create MapLibre HTML with custom styling
        html_content = self._generate_maplibre_html(
            geojson_data, 
            center_lat, 
            center_lon, 
            base_style,
            style,
            len(plot_data),
            len(self.crash_data)
        )
        
        # Save HTML file
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"\n[SUCCESS] MapLibre map saved to: {save_path}")
        print(f"[INFO] Map style: {style}")
        print(f"[INFO] Data points: {len(plot_data):,}")
        print(f"[INFO] GPU acceleration: Enabled")
        print(f"\n[USAGE] Open {save_path} in your browser to view")
        
        return save_path
    
    def _generate_maplibre_html(self, geojson_data, center_lat, center_lon, 
                                base_style, style, rendered_points, total_points):
        """Generate complete MapLibre GL JS HTML"""
        
        # Convert GeoJSON to JSON string
        geojson_str = json.dumps(geojson_data, indent=2)
        
        # Hotspot markers GeoJSON
        hotspot_features = []
        if self.hotspots is not None and len(self.hotspots) > 0:
            for idx, hotspot in self.hotspots.iterrows():
                hotspot_features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [hotspot['longitude'], hotspot['latitude']]
                    },
                    "properties": {
                        "crash_count": int(hotspot['crash_count']),
                        "severity_score": float(hotspot['severity_score']),
                        "cluster_id": int(hotspot['cluster_id'])
                    }
                })
        
        hotspot_geojson_str = json.dumps({
            "type": "FeatureCollection",
            "features": hotspot_features
        }, indent=2)
        
        # Determine layer visibility based on style
        show_circles = 'visible' if style == 'detailed' else 'none'
        show_hotspots = 'visible' if self.hotspots is not None and len(self.hotspots) > 0 else 'none'
        
        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>EDSA Crash Analysis - MapLibre GL JS</title>
    <meta name="viewport" content="initial-scale=1,maximum-scale=1,user-scalable=no">
    <script src="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js"></script>
    <link href="https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css" rel="stylesheet">
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }}
        #map {{
            position: absolute;
            top: 0;
            bottom: 0;
            width: 100%;
        }}
        
        .info-panel {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            max-width: 350px;
            z-index: 1;
        }}
        
        .info-panel h3 {{
            margin: 0 0 10px 0;
            font-size: 18px;
            color: #333;
        }}
        
        .info-panel p {{
            margin: 5px 0;
            font-size: 13px;
            color: #666;
        }}
        
        .info-panel .stat {{
            display: inline-block;
            background: #f0f0f0;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-right: 5px;
            margin-top: 5px;
        }}
        
        .legend {{
            position: absolute;
            bottom: 30px;
            right: 10px;
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            z-index: 1;
        }}
        
        .legend h4 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            color: #333;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 5px 0;
            font-size: 12px;
        }}
        
        .legend-color {{
            width: 20px;
            height: 12px;
            margin-right: 8px;
            border-radius: 2px;
        }}
        
        .maplibregl-popup-content {{
            padding: 12px;
            border-radius: 6px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }}
        
        .maplibregl-popup-content h4 {{
            margin: 0 0 8px 0;
            font-size: 14px;
            color: #333;
        }}
        
        .maplibregl-popup-content p {{
            margin: 4px 0;
            font-size: 12px;
            color: #666;
        }}
        
        .toggle-btn {{
            position: absolute;
            top: 90px;
            right: 10px;
            background: white;
            border: none;
            padding: 10px 15px;
            border-radius: 6px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            cursor: pointer;
            font-size: 13px;
            font-weight: 500;
            z-index: 1;
            transition: background 0.2s;
        }}
        
        .toggle-btn:hover {{
            background: #f5f5f5;
        }}
        
        .toggle-btn:active {{
            background: #e0e0e0;
        }}
        
        .powered-by {{
            position: absolute;
            bottom: 5px;
            left: 10px;
            font-size: 11px;
            color: #888;
            background: rgba(255,255,255,0.9);
            padding: 3px 8px;
            border-radius: 4px;
            z-index: 1;
        }}
        
        .powered-by a {{
            color: #0066cc;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    <div class="info-panel">
        <h3>🗺️ EDSA Crash Analysis</h3>
        <p style="margin-bottom: 10px; color: #333; font-weight: 500;">GPU-Accelerated Visualization</p>
        <div>
            <span class="stat">📊 {rendered_points:,} points</span>
            <span class="stat">🎯 {len(hotspot_features)} hotspots</span>
        </div>
        <p style="margin-top: 10px; font-size: 11px; color: #888;">
            Click map for details • Zoom to explore • GPU-powered rendering
        </p>
    </div>
    
    <div class="legend">
        <h4>Heat Intensity</h4>
        <div class="legend-item">
            <div class="legend-color" style="background: rgba(0, 0, 255, 0.6);"></div>
            <span>Low</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: rgba(0, 255, 0, 0.6);"></div>
            <span>Moderate</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: rgba(255, 255, 0, 0.6);"></div>
            <span>High</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: rgba(255, 0, 0, 0.6);"></div>
            <span>Very High</span>
        </div>
    </div>
    
    <button class="toggle-btn" id="toggleBtn">Toggle Layers</button>
    
    <div class="powered-by">
        Powered by <a href="https://maplibre.org/" target="_blank">MapLibre GL JS</a>
    </div>

    <script>
        // Initialize map
        const map = new maplibregl.Map({{
            container: 'map',
            style: '{base_style}',
            center: [{center_lon}, {center_lat}],
            zoom: 11.5,
            pitch: 0,
            bearing: 0,
            antialias: true
        }});

        // Add navigation controls
        map.addControl(new maplibregl.NavigationControl({{
            visualizePitch: true
        }}), 'top-right');

        // Add scale control
        map.addControl(new maplibregl.ScaleControl({{
            maxWidth: 100,
            unit: 'metric'
        }}), 'bottom-left');

        // Crash data
        const crashData = {geojson_str};
        
        // Hotspot data
        const hotspotData = {hotspot_geojson_str};

        // Load data when map is ready
        map.on('load', () => {{
            // Add crash data source
            map.addSource('crashes', {{
                type: 'geojson',
                data: crashData
            }});
            
            // Add hotspot source
            map.addSource('hotspots', {{
                type: 'geojson',
                data: hotspotData
            }});

            // Add heatmap layer
            map.addLayer({{
                id: 'crashes-heat',
                type: 'heatmap',
                source: 'crashes',
                maxzoom: 15,
                paint: {{
                    // Increase intensity as zoom level increases
                    'heatmap-intensity': [
                        'interpolate',
                        ['linear'],
                        ['zoom'],
                        0, 1,
                        15, 3
                    ],
                    // Assign color values be applied to points depending on their density
                    'heatmap-color': [
                        'interpolate',
                        ['linear'],
                        ['heatmap-density'],
                        0, 'rgba(33,102,172,0)',
                        0.2, 'rgb(103,169,207)',
                        0.4, 'rgb(209,229,240)',
                        0.6, 'rgb(253,219,199)',
                        0.8, 'rgb(239,138,98)',
                        1, 'rgb(178,24,43)'
                    ],
                    // Increase radius as zoom increases
                    'heatmap-radius': [
                        'interpolate',
                        ['linear'],
                        ['zoom'],
                        0, 2,
                        15, 20
                    ],
                    // Decrease opacity to transition into the circle layer
                    'heatmap-opacity': [
                        'interpolate',
                        ['linear'],
                        ['zoom'],
                        7, 0.8,
                        15, 0.4
                    ]
                }}
            }});

            // Add circle layer for individual points (visible when zoomed in)
            map.addLayer({{
                id: 'crashes-circle',
                type: 'circle',
                source: 'crashes',
                minzoom: 12,
                layout: {{
                    'visibility': '{show_circles}'
                }},
                paint: {{
                    'circle-radius': [
                        'interpolate',
                        ['linear'],
                        ['zoom'],
                        12, 3,
                        16, 8
                    ],
                    'circle-color': [
                        'match',
                        ['get', 'severity'],
                        'Fatal', '#DC143C',
                        'Major', '#FF6347',
                        'Minor', '#FFA500',
                        '#FFD700'
                    ],
                    'circle-opacity': 0.7,
                    'circle-stroke-color': '#fff',
                    'circle-stroke-width': 1
                }}
            }});
            
            // Add hotspot markers layer
            map.addLayer({{
                id: 'hotspots-circle',
                type: 'circle',
                source: 'hotspots',
                layout: {{
                    'visibility': '{show_hotspots}'
                }},
                paint: {{
                    'circle-radius': [
                        'interpolate',
                        ['linear'],
                        ['get', 'crash_count'],
                        5, 12,
                        50, 25,
                        100, 35
                    ],
                    'circle-color': '#4169E1',
                    'circle-opacity': 0.6,
                    'circle-stroke-color': '#fff',
                    'circle-stroke-width': 2
                }}
            }});
            
            // Add hotspot labels
            map.addLayer({{
                id: 'hotspots-label',
                type: 'symbol',
                source: 'hotspots',
                layout: {{
                    'visibility': '{show_hotspots}',
                    'text-field': ['concat', '⚠️ ', ['get', 'crash_count']],
                    'text-font': ['Open Sans Bold', 'Arial Unicode MS Bold'],
                    'text-size': 12,
                    'text-offset': [0, 0],
                    'text-anchor': 'center'
                }},
                paint: {{
                    'text-color': '#FFFFFF',
                    'text-halo-color': '#000000',
                    'text-halo-width': 1
                }}
            }});

            // Add click handlers
            map.on('click', 'crashes-circle', (e) => {{
                const coordinates = e.features[0].geometry.coordinates.slice();
                const props = e.features[0].properties;
                
                new maplibregl.Popup()
                    .setLngLat(coordinates)
                    .setHTML(`
                        <h4>🚗 Crash Details</h4>
                        <p><strong>ID:</strong> ${{props.crash_id}}</p>
                        <p><strong>Severity:</strong> ${{props.severity}}</p>
                        ${{props.year ? `<p><strong>Year:</strong> ${{props.year}}</p>` : ''}}
                        <p><strong>Location:</strong> ${{coordinates[1].toFixed(4)}}, ${{coordinates[0].toFixed(4)}}</p>
                    `)
                    .addTo(map);
            }});
            
            map.on('click', 'hotspots-circle', (e) => {{
                const coordinates = e.features[0].geometry.coordinates.slice();
                const props = e.features[0].properties;
                
                new maplibregl.Popup()
                    .setLngLat(coordinates)
                    .setHTML(`
                        <h4>⚠️ Crash Hotspot</h4>
                        <p><strong>Cluster ID:</strong> ${{props.cluster_id}}</p>
                        <p><strong>Total Crashes:</strong> ${{props.crash_count}}</p>
                        <p><strong>Severity Score:</strong> ${{props.severity_score.toFixed(2)}}</p>
                        <p><strong>Location:</strong> ${{coordinates[1].toFixed(4)}}, ${{coordinates[0].toFixed(4)}}</p>
                    `)
                    .addTo(map);
            }});

            // Change cursor on hover
            map.on('mouseenter', 'crashes-circle', () => {{
                map.getCanvas().style.cursor = 'pointer';
            }});
            map.on('mouseleave', 'crashes-circle', () => {{
                map.getCanvas().style.cursor = '';
            }});
            
            map.on('mouseenter', 'hotspots-circle', () => {{
                map.getCanvas().style.cursor = 'pointer';
            }});
            map.on('mouseleave', 'hotspots-circle', () => {{
                map.getCanvas().style.cursor = '';
            }});

            console.log('✅ MapLibre GL JS map loaded successfully');
            console.log(`📊 Rendering ${{crashData.features.length}} crash points`);
            console.log(`🎯 ${{hotspotData.features.length}} hotspots identified`);
        }});
        
        // Layer toggle functionality
        let layersVisible = true;
        document.getElementById('toggleBtn').addEventListener('click', () => {{
            layersVisible = !layersVisible;
            const visibility = layersVisible ? 'visible' : 'none';
            
            if (map.getLayer('crashes-circle')) {{
                map.setLayoutProperty('crashes-circle', 'visibility', visibility);
            }}
            if (map.getLayer('hotspots-circle')) {{
                map.setLayoutProperty('hotspots-circle', 'visibility', visibility);
            }}
            if (map.getLayer('hotspots-label')) {{
                map.setLayoutProperty('hotspots-label', 'visibility', visibility);
            }}
        }});
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {{
            // Press 'H' to toggle heatmap only
            if (e.key === 'h' || e.key === 'H') {{
                const currentVis = map.getLayoutProperty('crashes-heat', 'visibility');
                map.setLayoutProperty('crashes-heat', 'visibility', 
                    currentVis === 'visible' ? 'none' : 'visible');
            }}
            // Press 'M' to toggle markers
            if (e.key === 'm' || e.key === 'M') {{
                document.getElementById('toggleBtn').click();
            }}
        }});
    </script>
</body>
</html>'''
        
        return html


def main():
    """Main function to create MapLibre visualization"""
    
    print("="*70)
    print(" EDSA MapLibre GL JS Crash Visualization Generator ".center(70))
    print("="*70)
    print("\n>> Using GPU-accelerated MapLibre GL JS for high performance!")
    
    # Check if CSVData directory exists
    if not os.path.exists('CSVData'):
        print("\n[ERROR] CSVData directory not found!")
        print("Please ensure the CSVData folder with crash data exists.")
        return None
    
    # Initialize enhanced analyzer
    analyzer = MapLibreCrashAnalyzer()
    
    # Get available years from directory
    print("\n[INFO] Scanning CSVData directory for available years...")
    available_years = analyzer.get_available_years_from_directory('CSVData')
    
    if not available_years:
        print("\n[ERROR] No CSV files with year information found!")
        return None
    
    print(f"[OK] Found data for years: {', '.join(map(str, available_years))}")
    print(f"     Range: {min(available_years)} to {max(available_years)}")
    
    # Ask user for year range
    print("\n" + "="*70)
    print(" SELECT YEAR RANGE FOR ANALYSIS ".center(70))
    print("="*70)
    print("\n[TIP] Performance guide:")
    print("      - Recent years (2020-2023): Fast, ~30 seconds")
    print("      - All years (2013-2023): Slower, ~2-3 minutes")
    print("      - MapLibre handles large datasets better than Folium!")
    print("      - Press Enter to use all available years")
    
    start_year_input = input(f"\n[INPUT] Start year [{min(available_years)}-{max(available_years)}] (default: {min(available_years)}): ").strip()
    end_year_input = input(f"[INPUT] End year [{min(available_years)}-{max(available_years)}] (default: {max(available_years)}): ").strip()
    
    # Parse user input
    try:
        start_year = int(start_year_input) if start_year_input else min(available_years)
        end_year = int(end_year_input) if end_year_input else max(available_years)
        
        # Validate range
        if start_year < min(available_years) or end_year > max(available_years):
            print(f"\n[WARNING] Year range outside available data. Using full range: {min(available_years)}-{max(available_years)}")
            start_year, end_year = min(available_years), max(available_years)
        elif start_year > end_year:
            print("\n[WARNING] Start year > End year. Swapping them.")
            start_year, end_year = end_year, start_year
        
        year_range = (start_year, end_year)
        print(f"\n[OK] Selected year range: {start_year} to {end_year}")
        
    except ValueError:
        print(f"\n[WARNING] Invalid input. Using all years: {min(available_years)}-{max(available_years)}")
        year_range = (min(available_years), max(available_years))
    
    print("\n[INFO] Loading crash data from CSVData directory...")
    
    # Load CSV files with year filter
    if not analyzer.load_crash_data_from_directory('CSVData', year_range=year_range):
        print("\n[ERROR] Failed to load crash data!")
        return None
    
    print(f"[OK] Loaded {len(analyzer.crash_data)} crash records")
    
    # Show year distribution
    if 'year' in analyzer.crash_data.columns:
        print("\n[INFO] Data distribution by year:")
        year_counts = analyzer.crash_data['year'].value_counts().sort_index()
        for year, count in year_counts.items():
            print(f"   {int(year)}: {count} crashes")
    
    # Preprocess data
    print("\n[INFO] Preprocessing data...")
    analyzer.preprocess_data()
    
    # Perform KDE analysis
    print("[INFO] Performing Kernel Density Estimation...")
    analyzer.perform_kde_analysis(bandwidth=0.010)
    
    # Identify hotspots
    print("[INFO] Identifying crash hotspots...")
    analyzer.identify_hotspots(threshold_percentile=85)
    
    if analyzer.hotspots is not None and len(analyzer.hotspots) > 0:
        print(f"[OK] Found {len(analyzer.hotspots)} hotspot(s)")
        print("\nTop hotspot locations:")
        top_hotspots = analyzer.hotspots.nlargest(min(3, len(analyzer.hotspots)), 'crash_count')
        for i, (_, hotspot) in enumerate(top_hotspots.iterrows(), 1):
            print(f"   {i}. ({hotspot['latitude']:.4f}, {hotspot['longitude']:.4f}) - {hotspot['crash_count']} crashes")
    
    # Evaluate performance
    print("\n[INFO] Evaluating model performance...")
    metrics = analyzer.evaluate_model_performance()
    
    # Create MapLibre visualizations
    print("\n[INFO] Creating MapLibre GL JS visualizations...")
    
    # Option to limit points for browser performance
    data_size = len(analyzer.crash_data)
    if data_size > 100000:
        print(f"\n[WARNING] Large dataset detected ({data_size:,} points)")
        print("          For best browser performance, you can limit rendered points.")
        limit_input = input(f"          Limit to how many points? (Enter = use all {data_size:,}): ").strip()
        
        try:
            max_points = int(limit_input) if limit_input else None
        except ValueError:
            max_points = None
    else:
        max_points = None
    
    # Create different styles
    print("\n[INFO] Creating multiple map styles...")
    
    # 1. Detailed heatmap with markers
    analyzer.create_maplibre_heatmap(
        save_path='edsa_maplibre_detailed.html',
        style='detailed',
        max_points=max_points
    )
    
    # 2. Clean heatmap only
    analyzer.create_maplibre_heatmap(
        save_path='edsa_maplibre_heatmap.html',
        style='heatmap_only',
        max_points=max_points
    )
    
    # 3. Dark theme
    analyzer.create_maplibre_heatmap(
        save_path='edsa_maplibre_dark.html',
        style='dark',
        max_points=max_points
    )
    
    print("\n" + "="*70)
    print(" SUCCESS! ".center(70))
    print("="*70)
    print("\n[FILES] Generated MapLibre GL JS files:")
    print("        1. edsa_maplibre_detailed.html   (Full details with markers)")
    print("        2. edsa_maplibre_heatmap.html    (Clean heatmap view)")
    print("        3. edsa_maplibre_dark.html       (Dark theme)")
    print("\n[USAGE] How to view:")
    print("        - Double-click any HTML file to open in your browser")
    print("        - Or drag and drop into a browser window")
    print("\n[FEATURES] MapLibre Advantages:")
    print("           + GPU-accelerated rendering (WebGL)")
    print("           + Smooth pan and zoom")
    print("           + Interactive heatmap with dynamic intensity")
    print("           + Click markers for crash details")
    print("           + Layer toggle button (top right)")
    print("           + Keyboard shortcuts: H (toggle heatmap), M (toggle markers)")
    print("           + Better performance than Folium with large datasets")
    print("\n[POWERED BY] MapLibre GL JS: https://maplibre.org/")
    print("="*70)
    
    return analyzer, metrics


if __name__ == "__main__":
    try:
        analyzer, metrics = main()
        
        if analyzer and metrics:
            print("\n[STATS] Quick Statistics:")
            print(f"        Total crashes analyzed: {metrics['total_crashes']}")
            print(f"        Number of clusters: {metrics['n_clusters']}")
            print(f"        Hit rate: {metrics['hit_rate']:.2%}")
            print("\n[SUCCESS] MapLibre visualization complete!")
            
    except KeyboardInterrupt:
        print("\n\n[WARNING] Process interrupted by user.")
    except Exception as e:
        print(f"\n\n[ERROR] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\nPlease check:")
        print("  1. CSVData directory exists")
        print("  2. CSV files are properly formatted")
        print("  3. Required packages are installed")
        print("\n[NOTE] This script uses MapLibre GL JS (loaded from CDN)")
        print("       No additional Python packages needed!")

