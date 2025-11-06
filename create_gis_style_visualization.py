"""
Enhanced GIS-Style Visualization for EDSA Crash Analysis
Creates professional parcel/zone-based maps similar to GIS software
Run: python create_gis_style_visualization.py
"""

from bsit import EDSACrashAnalyzer
import folium
from folium import plugins
import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon, box
import geopandas as gpd
import os

class GISStyleCrashAnalyzer(EDSACrashAnalyzer):
    """Enhanced analyzer with GIS-style zone visualization"""
    
    def create_zone_grid(self, zone_size=0.01):
        """
        Divide the area into grid zones/parcels like GIS parcels
        
        Parameters:
        -----------
        zone_size : float
            Size of each zone in degrees (approximately 1km = 0.01 degrees)
        """
        print(f"Creating zone grid (zone size: {zone_size} degrees)...")
        
        # Get bounds of crash data
        lat_min, lat_max = self.crash_data['latitude'].min(), self.crash_data['latitude'].max()
        lon_min, lon_max = self.crash_data['longitude'].min(), self.crash_data['longitude'].max()
        
        # Add padding
        padding = zone_size * 0.5
        lat_min -= padding
        lat_max += padding
        lon_min -= padding
        lon_max += padding
        
        # Create grid
        lat_zones = np.arange(lat_min, lat_max, zone_size)
        lon_zones = np.arange(lon_min, lon_max, zone_size)
        
        zones = []
        zone_id = 0
        
        for i, lat in enumerate(lat_zones[:-1]):
            for j, lon in enumerate(lon_zones[:-1]):
                # Create polygon for this zone (parcel)
                zone_polygon = box(lon, lat, lon + zone_size, lat + zone_size)
                
                # Count crashes in this zone
                crashes_in_zone = 0
                for _, crash in self.crash_data.iterrows():
                    point = Point(crash['longitude'], crash['latitude'])
                    if zone_polygon.contains(point):
                        crashes_in_zone += 1
                
                # Calculate center for label
                center_lat = lat + zone_size/2
                center_lon = lon + zone_size/2
                
                # Calculate crash density (crashes per sq km, approximately)
                area_sq_km = (zone_size * 111) ** 2  # Rough conversion
                density = crashes_in_zone / area_sq_km if area_sq_km > 0 else 0
                
                zones.append({
                    'zone_id': zone_id,
                    'geometry': zone_polygon,
                    'crash_count': crashes_in_zone,
                    'density': density,
                    'center_lat': center_lat,
                    'center_lon': center_lon,
                    'bounds': [[lat, lon], [lat + zone_size, lon + zone_size]]
                })
                
                zone_id += 1
        
        self.zones_gdf = gpd.GeoDataFrame(zones, crs='EPSG:4326')
        print(f"[OK] Created {len(self.zones_gdf)} zones")
        print(f"   Zones with crashes: {(self.zones_gdf['crash_count'] > 0).sum()}")
        
        return self.zones_gdf
    
    def get_zone_color(self, crash_count):
        """
        Get color based on crash count - mimicking GIS parcel colors
        Green (low) -> Yellow -> Orange -> Red (high)
        """
        if crash_count == 0:
            return '#90EE90'  # Light green - no crashes
        elif crash_count <= 2:
            return '#98FB98'  # Pale green - very low
        elif crash_count <= 5:
            return '#ADFF2F'  # Green-yellow - low
        elif crash_count <= 10:
            return '#FFFF00'  # Yellow - moderate
        elif crash_count <= 20:
            return '#FFA500'  # Orange - high
        elif crash_count <= 30:
            return '#FF6347'  # Tomato - very high
        else:
            return '#DC143C'  # Crimson - extreme
    
    def create_gis_style_map(self, save_path='edsa_gis_style_map.html', 
                             zone_size=0.01, show_labels=True):
        """
        Create GIS-style map with zone parcels, boundaries, and labels
        
        Parameters:
        -----------
        save_path : str
            Output HTML file path
        zone_size : float
            Size of each zone/parcel in degrees
        show_labels : bool
            Whether to show crash count labels on zones
        """
        print("\n" + "="*70)
        print(" Creating GIS-Style Professional Map ".center(70))
        print("="*70)
        
        # Create zones
        self.create_zone_grid(zone_size=zone_size)
        
        # Calculate center
        center_lat = self.crash_data['latitude'].mean()
        center_lon = self.crash_data['longitude'].mean()
        
        # Create map with clean background
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13,
            tiles='CartoDB positron',  # Clean white background like GIS
            control_scale=True
        )
        
        # Add zone polygons with boundaries
        print("[INFO] Adding zone parcels and boundaries...")
        for idx, zone in self.zones_gdf.iterrows():
            crash_count = zone['crash_count']
            
            # Get color for this zone
            fill_color = self.get_zone_color(crash_count)
            
            # Create polygon
            coords = list(zone['geometry'].exterior.coords)
            coords_folium = [[lat, lon] for lon, lat in coords]
            
            # Add polygon with boundary
            folium.Polygon(
                locations=coords_folium,
                color='#333333',  # Dark gray boundary
                weight=1.5,
                fill=True,
                fillColor=fill_color,
                fillOpacity=0.7,
                popup=f"<b>Zone {zone['zone_id']}</b><br>"
                      f"Crashes: <b>{crash_count}</b><br>"
                      f"Density: {zone['density']:.2f} crashes/km²",
                tooltip=f"Zone {zone['zone_id']}: {crash_count} crashes"
            ).add_to(m)
            
            # Add label with crash count (like acreage labels in reference image)
            if show_labels and crash_count > 0:
                folium.Marker(
                    location=[zone['center_lat'], zone['center_lon']],
                    icon=folium.DivIcon(
                        html=f'''
                        <div style="font-family: Arial; 
                                    font-size: 11px; 
                                    font-weight: bold; 
                                    color: #000000;
                                    text-align: center;
                                    text-shadow: 1px 1px 2px white, -1px -1px 2px white;">
                            {crash_count}
                        </div>
                        '''
                    )
                ).add_to(m)
        
        # Add professional legend
        print("[INFO] Adding professional legend...")
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; right: 20px; 
                    width: 220px; 
                    background-color: white; 
                    border: 2px solid #333333; 
                    z-index: 9999; 
                    font-size: 13px; 
                    padding: 15px;
                    box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
            <h4 style="margin: 0 0 10px 0; 
                       font-family: Arial; 
                       border-bottom: 2px solid #333333; 
                       padding-bottom: 5px;">
                Crash Density Zones
            </h4>
            <div style="font-family: Arial;">
                <div style="margin: 5px 0;">
                    <span style="background-color: #90EE90; 
                                 padding: 3px 10px; 
                                 border: 1px solid #333; 
                                 display: inline-block; 
                                 width: 15px;"></span>
                    <span style="margin-left: 10px;">No crashes</span>
                </div>
                <div style="margin: 5px 0;">
                    <span style="background-color: #98FB98; 
                                 padding: 3px 10px; 
                                 border: 1px solid #333; 
                                 display: inline-block; 
                                 width: 15px;"></span>
                    <span style="margin-left: 10px;">1-2 crashes</span>
                </div>
                <div style="margin: 5px 0;">
                    <span style="background-color: #ADFF2F; 
                                 padding: 3px 10px; 
                                 border: 1px solid #333; 
                                 display: inline-block; 
                                 width: 15px;"></span>
                    <span style="margin-left: 10px;">3-5 crashes</span>
                </div>
                <div style="margin: 5px 0;">
                    <span style="background-color: #FFFF00; 
                                 padding: 3px 10px; 
                                 border: 1px solid #333; 
                                 display: inline-block; 
                                 width: 15px;"></span>
                    <span style="margin-left: 10px;">6-10 crashes</span>
                </div>
                <div style="margin: 5px 0;">
                    <span style="background-color: #FFA500; 
                                 padding: 3px 10px; 
                                 border: 1px solid #333; 
                                 display: inline-block; 
                                 width: 15px;"></span>
                    <span style="margin-left: 10px;">11-20 crashes</span>
                </div>
                <div style="margin: 5px 0;">
                    <span style="background-color: #FF6347; 
                                 padding: 3px 10px; 
                                 border: 1px solid #333; 
                                 display: inline-block; 
                                 width: 15px;"></span>
                    <span style="margin-left: 10px;">21-30 crashes</span>
                </div>
                <div style="margin: 5px 0;">
                    <span style="background-color: #DC143C; 
                                 padding: 3px 10px; 
                                 border: 1px solid #333; 
                                 display: inline-block; 
                                 width: 15px;"></span>
                    <span style="margin-left: 10px;">30+ crashes</span>
                </div>
            </div>
            <div style="margin-top: 10px; 
                        padding-top: 10px; 
                        border-top: 1px solid #ccc; 
                        font-size: 10px; 
                        color: #666;">
                Numbers show crash count per zone
            </div>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Add title
        title_html = '''
        <div style="position: fixed; 
                    top: 10px; left: 50px; 
                    width: 350px; 
                    background-color: white; 
                    border: 2px solid #333333; 
                    z-index: 9999; 
                    font-size: 14px; 
                    padding: 15px;
                    box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
            <h3 style="margin: 0; font-family: Arial; color: #333;">
                EDSA Crash Analysis - GIS Style
            </h3>
            <p style="margin: 5px 0 0 0; font-size: 12px; color: #666;">
                Professional zone-based crash density visualization
            </p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(title_html))
        
        # Save map
        m.save(save_path)
        
        # Print statistics
        print("\n" + "="*70)
        print(" SUCCESS! ".center(70))
        print("="*70)
        print(f"\n[FILE] Generated file: {save_path}")
        print("\n[STATS] Zone Statistics:")
        print(f"   Total zones created: {len(self.zones_gdf)}")
        print(f"   Zones with crashes: {(self.zones_gdf['crash_count'] > 0).sum()}")
        print(f"   Max crashes in a zone: {self.zones_gdf['crash_count'].max()}")
        print(f"   Average crashes per active zone: {self.zones_gdf[self.zones_gdf['crash_count'] > 0]['crash_count'].mean():.1f}")
        
        print("\n[FEATURES] Map Features:")
        print("   + GIS-style parcel/zone boundaries")
        print("   + Color-coded by crash density (green -> yellow -> red)")
        print("   + Crash count labels on each zone")
        print("   + Professional legend with categories")
        print("   + Click zones for detailed information")
        print("   + Clean, professional appearance")
        
        print("\n[USAGE] How to view:")
        print("   - Double-click the HTML file to open in browser")
        print("   - Zoom and pan to explore different areas")
        print("   - Hover over zones to see quick info")
        print("   - Click zones for detailed popup")
        
        print("\n" + "="*70)
        
        return m

def main():
    """Main function to create GIS-style visualization"""
    
    print("="*70)
    print(" EDSA GIS-Style Crash Visualization Generator ".center(70))
    print("="*70)
    print("\n>> Creating professional GIS-style map like your reference image!")
    
    # Check if CSVData directory exists
    if not os.path.exists('CSVData'):
        print("\n[ERROR] CSVData directory not found!")
        print("Please ensure the CSVData folder with crash data exists.")
        return None
    
    print("\n[INFO] Loading crash data from CSVData directory...")
    
    # Initialize enhanced analyzer
    analyzer = GISStyleCrashAnalyzer()
    
    # Load all CSV files
    if not analyzer.load_crash_data_from_directory('CSVData'):
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
    
    # Perform KDE analysis (still useful for background)
    print("[INFO] Performing density analysis...")
    analyzer.perform_kde_analysis(bandwidth=0.010)
    
    # Identify hotspots
    print("[INFO] Identifying crash hotspots...")
    analyzer.identify_hotspots(threshold_percentile=85)
    
    if analyzer.hotspots is not None and len(analyzer.hotspots) > 0:
        print(f"[OK] Found {len(analyzer.hotspots)} hotspot(s)")
    
    # Create GIS-style map
    print("\n[INFO] Creating GIS-style zoned map...")
    
    # You can adjust zone_size here:
    # - Smaller value (e.g., 0.005) = more zones, finer detail
    # - Larger value (e.g., 0.02) = fewer zones, broader view
    zone_size = 0.008  # Good balance for EDSA corridor
    
    analyzer.create_gis_style_map(
        save_path='edsa_gis_style_map.html',
        zone_size=zone_size,
        show_labels=True
    )
    
    # Also create the original heatmap for comparison
    print("\n[INFO] Creating comparison maps...")
    analyzer.create_interactive_map(
        save_path='edsa_heatmap_comparison.html',
        style='heatmap_only'
    )
    
    print("\n" + "="*70)
    print(" ALL VISUALIZATIONS COMPLETE! ".center(70))
    print("="*70)
    print("\n[FILES] Generated files:")
    print("   1. edsa_gis_style_map.html         ** GIS-style (like your reference)")
    print("   2. edsa_heatmap_comparison.html    ** Original heatmap style")
    print("\n[FEATURES] The GIS-style map includes:")
    print("   - Zone/parcel boundaries like the reference image")
    print("   - Color coding from green (safe) to red (dangerous)")
    print("   - Crash count numbers on each zone")
    print("   - Professional legend and layout")
    print("\n" + "="*70)
    
    return analyzer

if __name__ == "__main__":
    try:
        analyzer = main()
        
        if analyzer:
            print("\n[SUCCESS] Ready to present to your client!")
            print("   Open 'edsa_gis_style_map.html' to see the professional GIS-style visualization.")
            
    except KeyboardInterrupt:
        print("\n\n[WARNING] Process interrupted by user.")
    except Exception as e:
        print(f"\n\n[ERROR] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\nPlease check:")
        print("  1. CSVData directory exists")
        print("  2. CSV files are properly formatted")
        print("  3. Required packages are installed (folium, geopandas, shapely)")

