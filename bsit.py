import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, Polygon
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.neighbors import KernelDensity
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score
from scipy.spatial.distance import cdist
import folium
from folium.plugins import HeatMap
import warnings
import os
import glob
import re
import time
warnings.filterwarnings('ignore')

class EDSACrashAnalyzer:
    def __init__(self):
        self.crash_data = None
        self.edsa_boundary = None
        self.kde_model = None
        self.crash_gdf = None
        self.hotspots = None
    
    def _parse_coordinate(self, coord_str):
        """Parse coordinate string that may contain degree symbols and directions"""
        if pd.isna(coord_str):
            return None
        
        coord_str = str(coord_str).strip()
        
        # Remove degree symbol, N, S, E, W, and extra spaces
        coord_str = re.sub(r'[°NSEW\s]', '', coord_str)
        
        try:
            return float(coord_str)
        except ValueError:
            return None
    
    def _standardize_dataframe(self, df):
        """Standardize column names and data formats"""
        # Standardize column names to lowercase
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # Map various column name variations
        column_mapping = {
            'crash_id': 'crash_id',
            'latitude': 'latitude',
            'longitude': 'longitude',
            'year': 'year',
            'severity': 'severity'
        }
        
        # Rename if exact match exists
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns and old_name != new_name:
                df.rename(columns={old_name: new_name}, inplace=True)
        
        # Parse latitude and longitude if they contain degree symbols
        if 'latitude' in df.columns:
            df['latitude'] = df['latitude'].apply(self._parse_coordinate)
        
        if 'longitude' in df.columns:
            df['longitude'] = df['longitude'].apply(self._parse_coordinate)
        
        # Standardize severity values
        if 'severity' in df.columns:
            df['severity'] = df['severity'].str.strip().str.title()
        
        # Create a date column from year if it exists
        if 'year' in df.columns and 'date' not in df.columns:
            df['date'] = pd.to_datetime(df['year'].astype(str) + '-01-01', errors='coerce')
        
        return df
    
    def load_crash_data(self, data_path):
        """Load crash data from a single CSV file"""
        try:
            df = pd.read_csv(data_path)
            df = self._standardize_dataframe(df)
            self.crash_data = df
            print(f"Loaded {len(self.crash_data)} crash records from {data_path}")
        except FileNotFoundError:
            print(f"File not found: {data_path}")
            return False
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            return False
        
        required_columns = ['latitude', 'longitude']
        missing_cols = [col for col in required_columns if col not in self.crash_data.columns]
        if missing_cols:
            print(f"Missing required columns: {missing_cols}")
            return False
        
        # Remove rows with invalid coordinates
        self.crash_data = self.crash_data.dropna(subset=['latitude', 'longitude'])
        
        geometry = [Point(xy) for xy in zip(self.crash_data.longitude, self.crash_data.latitude)]
        self.crash_gdf = gpd.GeoDataFrame(self.crash_data, geometry=geometry, crs='EPSG:4326')
        
        return True
    
    def load_multiple_crash_data(self, data_paths):
        """Load and combine crash data from multiple CSV files"""
        try:
            all_dataframes = []
            
            for data_path in data_paths:
                if not os.path.exists(data_path):
                    print(f"Warning: File not found: {data_path}")
                    continue
                
                try:
                    df = pd.read_csv(data_path)
                    df = self._standardize_dataframe(df)
                    all_dataframes.append(df)
                    print(f"Loaded {len(df)} crash records from {os.path.basename(data_path)}")
                except Exception as e:
                    print(f"Error loading {data_path}: {str(e)}")
                    continue
            
            if not all_dataframes:
                print("No data files were successfully loaded")
                return False
            
            # Combine all dataframes
            self.crash_data = pd.concat(all_dataframes, ignore_index=True)
            print(f"\nTotal combined crash records: {len(self.crash_data)}")
            
            # Remove rows with invalid coordinates
            initial_count = len(self.crash_data)
            self.crash_data = self.crash_data.dropna(subset=['latitude', 'longitude'])
            
            if len(self.crash_data) < initial_count:
                print(f"Removed {initial_count - len(self.crash_data)} records with invalid coordinates")
            
            required_columns = ['latitude', 'longitude']
            missing_cols = [col for col in required_columns if col not in self.crash_data.columns]
            if missing_cols:
                print(f"Missing required columns: {missing_cols}")
                return False
            
            geometry = [Point(xy) for xy in zip(self.crash_data.longitude, self.crash_data.latitude)]
            self.crash_gdf = gpd.GeoDataFrame(self.crash_data, geometry=geometry, crs='EPSG:4326')
            
            return True
            
        except Exception as e:
            print(f"Error combining data: {str(e)}")
            return False
    
    def load_crash_data_from_directory(self, directory_path, pattern='*.csv'):
        """Load all CSV files matching pattern from a directory"""
        try:
            search_path = os.path.join(directory_path, pattern)
            csv_files = sorted(glob.glob(search_path))
            
            if not csv_files:
                print(f"No CSV files found in {directory_path}")
                return False
            
            print(f"Found {len(csv_files)} CSV files")
            return self.load_multiple_crash_data(csv_files)
            
        except Exception as e:
            print(f"Error loading from directory: {str(e)}")
            return False
    
    def filter_by_year_range(self, start_year=None, end_year=None):
        """Filter crash data by year range to reduce dataset size"""
        if 'year' not in self.crash_data.columns:
            print("Warning: 'year' column not found. Cannot filter by year.")
            return
        
        initial_count = len(self.crash_data)
        
        if start_year is not None:
            self.crash_data = self.crash_data[self.crash_data['year'] >= start_year]
        
        if end_year is not None:
            self.crash_data = self.crash_data[self.crash_data['year'] <= end_year]
        
        if initial_count != len(self.crash_data):
            print(f"Filtered by year range ({start_year or 'all'} to {end_year or 'all'}): {initial_count} -> {len(self.crash_data)} records")
            
            # Update geometry
            geometry = [Point(xy) for xy in zip(self.crash_data.longitude, self.crash_data.latitude)]
            self.crash_gdf = gpd.GeoDataFrame(self.crash_data, geometry=geometry, crs='EPSG:4326')
    
    def preprocess_data(self):
        print("Preprocessing crash data...")
        
        initial_count = len(self.crash_data)
        self.crash_data = self.crash_data.dropna(subset=['latitude', 'longitude'])
        
        lat_bounds = (14.4, 14.8)
        lon_bounds = (120.9, 121.2)
        
        coord_filter = (
            (self.crash_data['latitude'].between(*lat_bounds)) & 
            (self.crash_data['longitude'].between(*lon_bounds))
        )
        self.crash_data = self.crash_data[coord_filter]
        
        geometry = [Point(xy) for xy in zip(self.crash_data.longitude, self.crash_data.latitude)]
        self.crash_gdf = gpd.GeoDataFrame(self.crash_data, geometry=geometry, crs='EPSG:4326')
        
        print(f"Data preprocessing complete: {initial_count} -> {len(self.crash_data)} records")
        return self.crash_data
    
    def perform_kde_analysis(self, bandwidth=0.01, max_kde_points=100000, grid_resolution=100):
        print(f"Performing KDE analysis with bandwidth={bandwidth}")
        
        coordinates = self.crash_data[['latitude', 'longitude']].values
        
        # Use sampling for KDE if dataset is too large
        if len(coordinates) > max_kde_points:
            print(f"Sampling {max_kde_points} points for KDE analysis (from {len(coordinates)} total)...")
            sample_indices = np.random.choice(len(coordinates), max_kde_points, replace=False)
            kde_coords = coordinates[sample_indices]
        else:
            kde_coords = coordinates
        
        print(f"Fitting KDE model on {len(kde_coords)} points...")
        self.kde_model = KernelDensity(bandwidth=bandwidth, kernel='gaussian')
        self.kde_model.fit(kde_coords)
        
        lat_min, lat_max = coordinates[:, 0].min(), coordinates[:, 0].max()
        lon_min, lon_max = coordinates[:, 1].min(), coordinates[:, 1].max()
        
        lat_range = lat_max - lat_min
        lon_range = lon_max - lon_min
        lat_min -= lat_range * 0.1
        lat_max += lat_range * 0.1
        lon_min -= lon_range * 0.1
        lon_max += lon_range * 0.1
        
        print(f"Computing density grid ({grid_resolution}x{grid_resolution})...")
        lat_grid = np.linspace(lat_min, lat_max, grid_resolution)
        lon_grid = np.linspace(lon_min, lon_max, grid_resolution)
        lat_mesh, lon_mesh = np.meshgrid(lat_grid, lon_grid)
        
        mesh_points = np.column_stack([lat_mesh.ravel(), lon_mesh.ravel()])
        density_scores = np.exp(self.kde_model.score_samples(mesh_points))
        density_grid = density_scores.reshape(lat_mesh.shape)
        
        self.density_grid = density_grid
        self.lat_mesh = lat_mesh
        self.lon_mesh = lon_mesh
        
        print("KDE analysis completed")
        return density_grid
    
    def identify_hotspots(self, threshold_percentile=90, max_points=50000):
        print(f"Identifying hotspots (threshold: {threshold_percentile}th percentile)")
        
        coordinates = self.crash_data[['latitude', 'longitude']].values
        
        # Handle large datasets by sampling
        use_sample = len(coordinates) > max_points
        if use_sample:
            print(f"Dataset too large ({len(coordinates)} points). Using sample of {max_points} points for clustering...")
            sample_indices = np.random.choice(len(coordinates), max_points, replace=False)
            sample_coords = coordinates[sample_indices]
        else:
            sample_coords = coordinates
        
        eps = 0.005
        min_samples = 5
        
        print(f"Running DBSCAN on {len(sample_coords)} points...")
        clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(sample_coords)
        sample_labels = clustering.labels_
        
        # If we used sampling, assign all points to nearest cluster
        if use_sample:
            print("Assigning all points to nearest clusters...")
            # Get cluster centroids from sample
            unique_labels = set(sample_labels) - {-1}
            cluster_centroids = {}
            for label in unique_labels:
                cluster_points = sample_coords[sample_labels == label]
                cluster_centroids[label] = cluster_points.mean(axis=0)
            
            # Assign all points to nearest cluster
            labels = np.full(len(coordinates), -1)
            if cluster_centroids:
                centroid_array = np.array([cluster_centroids[label] for label in sorted(cluster_centroids.keys())])
                centroid_labels = list(sorted(cluster_centroids.keys()))
                
                # Process in batches to avoid memory issues
                batch_size = 10000
                for i in range(0, len(coordinates), batch_size):
                    batch_end = min(i + batch_size, len(coordinates))
                    batch_coords = coordinates[i:batch_end]
                    
                    # Calculate distances to all centroids
                    distances = cdist(batch_coords, centroid_array)
                    # Assign to nearest cluster if within eps distance
                    min_distances = distances.min(axis=1)
                    nearest_clusters = distances.argmin(axis=1)
                    
                    # Only assign if within threshold distance
                    valid_assignments = min_distances < (eps * 2)  # Use 2*eps as threshold
                    labels[i:batch_end][valid_assignments] = [centroid_labels[idx] for idx in nearest_clusters[valid_assignments]]
        else:
            labels = sample_labels
        
        self.crash_data['cluster'] = labels
        self.crash_gdf['cluster'] = labels
        
        unique_labels = set(labels)
        hotspots = []
        
        for label in unique_labels:
            if label == -1:
                continue
                
            cluster_points = coordinates[labels == label]
            if len(cluster_points) >= min_samples:
                centroid = cluster_points.mean(axis=0)
                crash_count = len(cluster_points)
                
                hotspots.append({
                    'cluster_id': label,
                    'latitude': centroid[0],
                    'longitude': centroid[1],
                    'crash_count': crash_count,
                    'severity_score': self._calculate_severity_score(label)
                })
        
        self.hotspots = pd.DataFrame(hotspots)
        print(f"Identified {len(self.hotspots)} hotspot clusters")
        return self.hotspots
    
    def _calculate_severity_score(self, cluster_label):
        cluster_data = self.crash_data[self.crash_data['cluster'] == cluster_label]
        severity_weights = {'Minor': 1, 'Major': 3, 'Fatal': 5}
        
        if 'severity' in cluster_data.columns:
            scores = cluster_data['severity'].map(severity_weights).fillna(1)
            return scores.mean()
        return 1.0
    
    def evaluate_model_performance(self, calculate_hit_rate=True, max_silhouette_samples=10000):
        print("Evaluating model performance...")
        
        coordinates = self.crash_data[['latitude', 'longitude']].values
        
        # Hit rate can be skipped for speed
        if calculate_hit_rate:
            hit_rate = self._calculate_hit_rate()
        else:
            hit_rate = -1.0  # Indicates not calculated
            print("  Skipping hit rate calculation for speed...")
        
        valid_clusters = self.crash_data['cluster'] != -1
        if valid_clusters.sum() > 1:
            cluster_coords = coordinates[valid_clusters]
            cluster_labels = self.crash_data.loc[valid_clusters, 'cluster']
            
            if len(set(cluster_labels)) > 1:
                # Sample for silhouette score if too large
                if len(cluster_coords) > max_silhouette_samples:
                    print(f"  Sampling {max_silhouette_samples} points for silhouette score...")
                    sample_indices = np.random.choice(len(cluster_coords), max_silhouette_samples, replace=False)
                    cluster_coords_sample = cluster_coords[sample_indices]
                    cluster_labels_sample = cluster_labels.iloc[sample_indices]
                    silhouette_avg = silhouette_score(cluster_coords_sample, cluster_labels_sample)
                else:
                    silhouette_avg = silhouette_score(cluster_coords, cluster_labels)
            else:
                silhouette_avg = 0.0
        else:
            silhouette_avg = 0.0
        
        n_clusters = len(set(self.crash_data['cluster'])) - (1 if -1 in self.crash_data['cluster'].values else 0)
        noise_ratio = (self.crash_data['cluster'] == -1).sum() / len(self.crash_data)
        
        performance_metrics = {
            'hit_rate': hit_rate,
            'silhouette_score': silhouette_avg,
            'n_clusters': n_clusters,
            'noise_ratio': noise_ratio,
            'total_crashes': len(self.crash_data)
        }
        
        print(f"Performance Metrics:")
        if hit_rate >= 0:
            print(f"  Hit Rate: {hit_rate:.3f}")
        else:
            print(f"  Hit Rate: Not calculated (fast mode)")
        print(f"  Silhouette Score: {silhouette_avg:.3f}")
        print(f"  Number of Clusters: {n_clusters}")
        print(f"  Noise Ratio: {noise_ratio:.3f}")
        
        return performance_metrics
    
    def _calculate_hit_rate(self, top_percentile=20, max_sample_points=5000):
        if self.hotspots is None or len(self.hotspots) == 0:
            return 0.0
        
        threshold = np.percentile(self.density_grid, 100 - top_percentile)
        
        # Sample for hit rate calculation if dataset is large (reduced sample size)
        if len(self.crash_data) > max_sample_points:
            print(f"  Sampling {max_sample_points} points for hit rate calculation...")
            sample_data = self.crash_data.sample(n=max_sample_points, random_state=42)
        else:
            sample_data = self.crash_data
        
        # Simplified hit rate calculation - much faster
        coordinates = sample_data[['latitude', 'longitude']].values
        
        # Get grid boundaries
        lat_grid = self.lat_mesh[:, 0]
        lon_grid = self.lon_mesh[0, :]
        
        # Digitize coordinates to grid cells (much faster than argmin)
        lat_indices = np.clip(
            np.digitize(coordinates[:, 0], lat_grid) - 1, 
            0, len(lat_grid) - 1
        )
        lon_indices = np.clip(
            np.digitize(coordinates[:, 1], lon_grid) - 1,
            0, len(lon_grid) - 1
        )
        
        # Vectorized hit counting
        valid_mask = (lat_indices < len(self.density_grid)) & (lon_indices < len(self.density_grid[0]))
        density_values = self.density_grid[lat_indices[valid_mask], lon_indices[valid_mask]]
        hits = np.sum(density_values >= threshold)
        
        return hits / len(sample_data) if len(sample_data) > 0 else 0.0
    
    def create_visualizations(self, max_plot_points=10000):
        print("Creating visualizations...")
        
        # Sample data for plotting if too large
        if len(self.crash_data) > max_plot_points:
            print(f"Sampling {max_plot_points} points for visualization (from {len(self.crash_data)} total)...")
            plot_data = self.crash_data.sample(n=max_plot_points, random_state=42)
        else:
            plot_data = self.crash_data
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        ax1 = axes[0, 0]
        ax1.scatter(plot_data['longitude'], plot_data['latitude'], 
                   alpha=0.6, s=20, c='red', label='Crashes')
        if self.hotspots is not None and len(self.hotspots) > 0:
            ax1.scatter(self.hotspots['longitude'], self.hotspots['latitude'], 
                       s=self.hotspots['crash_count']*10, c='blue', alpha=0.7, 
                       marker='s', label='Hotspots')
        ax1.set_xlabel('Longitude')
        ax1.set_ylabel('Latitude')
        ax1.set_title(f'EDSA Crash Distribution and Identified Hotspots\n(showing {len(plot_data):,} of {len(self.crash_data):,} crashes)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        ax2 = axes[0, 1]
        if hasattr(self, 'density_grid'):
            im = ax2.contourf(self.lon_mesh, self.lat_mesh, self.density_grid, 
                             levels=20, cmap='YlOrRd', alpha=0.7)
            # Sample points for density overlay too
            overlay_data = self.crash_data.sample(n=min(5000, len(self.crash_data)), random_state=42)
            ax2.scatter(overlay_data['longitude'], overlay_data['latitude'], 
                       alpha=0.4, s=5, c='black')
            plt.colorbar(im, ax=ax2, label='Density')
        ax2.set_xlabel('Longitude')
        ax2.set_ylabel('Latitude')
        ax2.set_title('Kernel Density Estimation Heatmap')
        
        ax3 = axes[1, 0]
        if 'date' in self.crash_data.columns:
            self.crash_data['date'] = pd.to_datetime(self.crash_data['date'])
            monthly_crashes = self.crash_data.groupby(self.crash_data['date'].dt.to_period('M')).size()
            monthly_crashes.plot(ax=ax3, kind='line', marker='o')
        ax3.set_xlabel('Time Period')
        ax3.set_ylabel('Number of Crashes')
        ax3.set_title('Temporal Distribution of Crashes')
        ax3.grid(True, alpha=0.3)
        
        ax4 = axes[1, 1]
        if 'cluster' in self.crash_data.columns:
            clusters = plot_data['cluster']
            unique_clusters = set(self.crash_data['cluster']) - {-1}
            colors = plt.cm.tab10(np.linspace(0, 1, min(len(unique_clusters), 10)))
            
            noise_points = plot_data[plot_data['cluster'] == -1]
            if len(noise_points) > 0:
                ax4.scatter(noise_points['longitude'], noise_points['latitude'], 
                           c='gray', alpha=0.5, s=10, label='Noise')
            
            # Only show first 10 clusters in legend
            shown_clusters = list(unique_clusters)[:10]
            for i, cluster_id in enumerate(shown_clusters):
                cluster_points = plot_data[plot_data['cluster'] == cluster_id]
                if len(cluster_points) > 0:
                    color_idx = i % len(colors)
                    ax4.scatter(cluster_points['longitude'], cluster_points['latitude'], 
                               c=[colors[color_idx]], alpha=0.7, s=20, label=f'Cluster {cluster_id}')
            
            ax4.set_xlabel('Longitude')
            ax4.set_ylabel('Latitude')
            ax4.set_title(f'DBSCAN Clustering Results\n({len(unique_clusters)} clusters total, showing sample)')
            if len(shown_clusters) <= 10:
                ax4.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        else:
            ax4.set_xlabel('Longitude')
            ax4.set_ylabel('Latitude')
            ax4.set_title('DBSCAN Clustering Results (No clustering data)')
        
        plt.tight_layout()
        plt.show()
        
        # Create summary statistics
        self._create_summary_report()
    
    def create_interactive_map(self, save_path='edsa_crash_analysis.html', style='detailed', max_markers=5000):
        """
        Create interactive map with enhanced visualization
        
        Parameters:
        -----------
        save_path : str
            Output HTML file path
        style : str
            'detailed' - Shows individual crash markers and heatmap
            'heatmap_only' - Shows only heatmap (cleaner, like reference image)
        max_markers : int
            Maximum number of individual crash markers to show (to avoid browser slowdown)
        """
        print(f"Creating interactive map (style: {style})...")
        
        center_lat = self.crash_data['latitude'].mean()
        center_lon = self.crash_data['longitude'].mean()
        
        # Create map with better tile options
        m = folium.Map(
            location=[center_lat, center_lon], 
            zoom_start=12,
            tiles='OpenStreetMap',  # or 'CartoDB positron' for cleaner look
            control_scale=True
        )
        
        # Add alternative tile layers
        folium.TileLayer('CartoDB positron', name='Light Map').add_to(m)
        folium.TileLayer('CartoDB dark_matter', name='Dark Map').add_to(m)
        
        # Create feature groups for layer control
        crash_layer = folium.FeatureGroup(name='Individual Crashes')
        hotspot_layer = folium.FeatureGroup(name='Hotspot Markers')
        heatmap_layer = folium.FeatureGroup(name='Heatmap', show=True)
        
        # Add individual crash markers (if style is detailed)
        if style == 'detailed':
            # Sample crashes for markers if too many
            if len(self.crash_data) > max_markers:
                print(f"  Sampling {max_markers} crashes for individual markers (from {len(self.crash_data)} total)...")
                crash_sample = self.crash_data.sample(n=max_markers, random_state=42)
            else:
                crash_sample = self.crash_data
            
            print(f"  Adding {len(crash_sample)} crash markers...")
            for idx, crash in crash_sample.iterrows():
                color = 'red' if crash.get('severity') == 'Fatal' else 'orange' if crash.get('severity') == 'Major' else 'yellow'
                folium.CircleMarker(
                    location=[crash['latitude'], crash['longitude']],
                    radius=3,
                    popup=f"Crash ID: {crash.get('crash_id', 'N/A')}<br>Severity: {crash.get('severity', 'Unknown')}",
                    color=color,
                    fillColor=color,
                    fillOpacity=0.6,
                    weight=1
                ).add_to(crash_layer)
        
        # Add hotspot markers with warning triangles
        if self.hotspots is not None and len(self.hotspots) > 0:
            for _, hotspot in self.hotspots.iterrows():
                # Create custom icon with warning symbol
                folium.Marker(
                    location=[hotspot['latitude'], hotspot['longitude']],
                    popup=folium.Popup(
                        f"<b>⚠️ HOTSPOT</b><br>"
                        f"Crashes: {hotspot['crash_count']}<br>"
                        f"Severity Score: {hotspot['severity_score']:.2f}<br>"
                        f"Location: ({hotspot['latitude']:.4f}, {hotspot['longitude']:.4f})",
                        max_width=250
                    ),
                    icon=folium.Icon(
                        color='lightblue',
                        icon='warning-sign',
                        prefix='glyphicon'
                    )
                ).add_to(hotspot_layer)
        
        # Enhanced heatmap with better color gradient
        # Sample heatmap data for better performance
        max_heatmap_points = 50000
        if len(self.crash_data) > max_heatmap_points:
            print(f"  Sampling {max_heatmap_points} points for heatmap (from {len(self.crash_data)} total)...")
            heatmap_sample = self.crash_data.sample(n=max_heatmap_points, random_state=42)
        else:
            heatmap_sample = self.crash_data
        
        print(f"  Generating heatmap with {len(heatmap_sample)} points...")
        heat_data = [[row['latitude'], row['longitude']] for _, row in heatmap_sample.iterrows()]
        
        # Create heatmap with enhanced parameters
        HeatMap(
            heat_data,
            min_opacity=0.2,
            max_opacity=0.8,
            radius=25,  # Increased radius for smoother appearance
            blur=20,    # Increased blur for better gradient
            max_zoom=13,
            gradient={
                0.0: 'blue',
                0.2: 'cyan',
                0.4: 'lime',
                0.6: 'yellow',
                0.8: 'orange',
                1.0: 'red'
            }
        ).add_to(heatmap_layer)
        
        # Add layers to map
        crash_layer.add_to(m)
        hotspot_layer.add_to(m)
        heatmap_layer.add_to(m)
        
        # Add layer control
        folium.LayerControl(position='topright', collapsed=False).add_to(m)
        
        # Add title/legend
        title_html = '''
        <div style="position: fixed; 
                    top: 10px; left: 50px; width: 300px; height: 90px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px; opacity: 0.9;">
        <h4 style="margin:0;">EDSA Crash Analysis</h4>
        <p style="margin:5px 0;"><span style="color:blue;">●</span> Low Density</p>
        <p style="margin:5px 0;"><span style="color:yellow;">●</span> Medium Density</p>
        <p style="margin:5px 0;"><span style="color:red;">●</span> High Density</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(title_html))
        
        m.save(save_path)
        print(f"Interactive map saved to {save_path}")
        print(f"Heatmap style: {style}")
        print(f"Open {save_path} in your browser to view the map")
        return m
    
    def _create_summary_report(self):
        print("\n" + "="*50)
        print("EDSA CRASH ANALYSIS SUMMARY REPORT")
        print("="*50)
        
        print(f"\nDATA OVERVIEW:")
        print(f"Total Crashes Analyzed: {len(self.crash_data)}")
        
        if 'year' in self.crash_data.columns:
            year_min = int(self.crash_data['year'].min())
            year_max = int(self.crash_data['year'].max())
            print(f"Year Range: {year_min} to {year_max}")
            
            print(f"\nCRASHES BY YEAR:")
            year_counts = self.crash_data['year'].value_counts().sort_index()
            for year, count in year_counts.items():
                print(f"  {int(year)}: {count} crashes")
        elif 'date' in self.crash_data.columns:
            print(f"Date Range: {self.crash_data['date'].min()} to {self.crash_data['date'].max()}")
        
        print(f"\nGEOGRAPHIC COVERAGE:")
        print(f"  Latitude:  {self.crash_data['latitude'].min():.4f}° to {self.crash_data['latitude'].max():.4f}° N")
        print(f"  Longitude: {self.crash_data['longitude'].min():.4f}° to {self.crash_data['longitude'].max():.4f}° E")
        
        if 'severity' in self.crash_data.columns:
            print(f"\nSEVERITY BREAKDOWN:")
            severity_counts = self.crash_data['severity'].value_counts()
            for severity, count in severity_counts.items():
                print(f"  {severity}: {count} ({count/len(self.crash_data)*100:.1f}%)")
        
        if self.hotspots is not None and len(self.hotspots) > 0:
            print(f"\nHOTSPOT ANALYSIS:")
            print(f"Number of Hotspots Identified: {len(self.hotspots)}")
            print(f"Average Crashes per Hotspot: {self.hotspots['crash_count'].mean():.1f}")
            print(f"Most Dangerous Hotspot: {self.hotspots['crash_count'].max()} crashes")
            
            print(f"\nTOP 5 HOTSPOTS:")
            top_hotspots = self.hotspots.nlargest(5, 'crash_count')
            for i, (_, hotspot) in enumerate(top_hotspots.iterrows(), 1):
                print(f"  {i}. Location: ({hotspot['latitude']:.4f}, {hotspot['longitude']:.4f}) - {hotspot['crash_count']} crashes")
        
        print(f"\nRECOMMENDATIONS:")
        print("1. Focus safety interventions on identified hotspot locations")
        print("2. Implement traffic calming measures in high-density crash areas")
        print("3. Enhance lighting and signage at critical intersections")
        print("4. Consider temporal patterns for targeted enforcement")
        print("5. Regular monitoring and updating of hotspot analysis")

def create_sample_data():
    """Create sample crash data for testing"""
    np.random.seed(42)
    
    # Define EDSA corridor roughly
    edsa_lat_center = 14.6
    edsa_lon_center = 121.03
    
    # Create sample crash data with clusters
    sample_data = []
    
    # Cluster 1: North EDSA area
    for i in range(15):
        lat = np.random.normal(14.65, 0.005)
        lon = np.random.normal(121.025, 0.005)
        severity = np.random.choice(['Minor', 'Major', 'Fatal'], p=[0.6, 0.3, 0.1])
        vehicle = np.random.choice(['Car', 'Motorcycle', 'Bus', 'Truck'], p=[0.4, 0.3, 0.2, 0.1])
        date = f"1/{np.random.randint(1, 31)}/2024"
        
        sample_data.append({
            'crash_id': f'EDSA_{i+1:03d}',
            'latitude': lat,
            'longitude': lon,
            'date': date,
            'severity': severity,
            'vehicle_type': vehicle
        })
    
    # Cluster 2: Central EDSA area
    for i in range(12):
        lat = np.random.normal(14.58, 0.004)
        lon = np.random.normal(121.03, 0.004)
        severity = np.random.choice(['Minor', 'Major', 'Fatal'], p=[0.5, 0.4, 0.1])
        vehicle = np.random.choice(['Car', 'Motorcycle', 'Bus', 'Truck'], p=[0.3, 0.4, 0.2, 0.1])
        date = f"2/{np.random.randint(1, 29)}/2024"
        
        sample_data.append({
            'crash_id': f'EDSA_{i+16:03d}',
            'latitude': lat,
            'longitude': lon,
            'date': date,
            'severity': severity,
            'vehicle_type': vehicle
        })
    
    # Cluster 3: South EDSA area
    for i in range(10):
        lat = np.random.normal(14.52, 0.003)
        lon = np.random.normal(121.02, 0.003)
        severity = np.random.choice(['Minor', 'Major', 'Fatal'], p=[0.7, 0.2, 0.1])
        vehicle = np.random.choice(['Car', 'Motorcycle', 'Bus', 'Truck'], p=[0.5, 0.2, 0.2, 0.1])
        date = f"3/{np.random.randint(1, 31)}/2024"
        
        sample_data.append({
            'crash_id': f'EDSA_{i+28:03d}',
            'latitude': lat,
            'longitude': lon,
            'date': date,
            'severity': severity,
            'vehicle_type': vehicle
        })
    
    # Add some scattered points
    for i in range(8):
        lat = np.random.uniform(14.45, 14.75)
        lon = np.random.uniform(121.0, 121.1)
        severity = np.random.choice(['Minor', 'Major', 'Fatal'], p=[0.8, 0.15, 0.05])
        vehicle = np.random.choice(['Car', 'Motorcycle', 'Bus', 'Truck'])
        date = f"4/{np.random.randint(1, 30)}/2024"
        
        sample_data.append({
            'crash_id': f'EDSA_{i+38:03d}',
            'latitude': lat,
            'longitude': lon,
            'date': date,
            'severity': severity,
            'vehicle_type': vehicle
        })
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(sample_data)
    df.to_csv('crash_data.csv', index=False)
    print(f"Created sample data with {len(df)} crash records")
    return 'crash_data.csv'

def main():
    start_time = time.time()
    
    print("Starting EDSA Road Crash Spatial Analysis")
    print("="*50)
    
    analyzer = EDSACrashAnalyzer()
    
    # Ask user for data loading option
    print("\nData Loading Options:")
    print("1. Load from CSVData directory (recommended)")
    print("2. Load specific files")
    print("3. Use sample data")
    
    choice = input("\nSelect option (1/2/3): ").strip()
    
    if choice == '1':
        # Load all CSV files from CSVData directory
        directory = 'CSVData'
        if not os.path.exists(directory):
            print(f"Directory '{directory}' not found. Please ensure the CSVData folder exists.")
            return None, None
        
        if not analyzer.load_crash_data_from_directory(directory):
            return None, None
        
        # Ask if user wants to filter by year
        if 'year' in analyzer.crash_data.columns:
            years = sorted(analyzer.crash_data['year'].unique())
            print(f"\nAvailable years: {int(years[0])} to {int(years[-1])}")
            filter_choice = input("Filter by year range? (y/n): ").strip().lower()
            
            if filter_choice == 'y':
                try:
                    start_year = input(f"Start year ({int(years[0])}-{int(years[-1])}, press Enter for all): ").strip()
                    end_year = input(f"End year ({int(years[0])}-{int(years[-1])}, press Enter for all): ").strip()
                    
                    start_year = int(start_year) if start_year else None
                    end_year = int(end_year) if end_year else None
                    
                    analyzer.filter_by_year_range(start_year, end_year)
                except ValueError:
                    print("Invalid year input. Using all years.")
            
    elif choice == '2':
        # Load specific files
        print("\nEnter CSV file paths (comma-separated):")
        file_input = input("Files: ").strip()
        
        if not file_input:
            print("No files specified.")
            return None, None
        
        file_paths = [f.strip() for f in file_input.split(',')]
        
        if not analyzer.load_multiple_crash_data(file_paths):
            return None, None
            
    elif choice == '3':
        # Use sample data
        data_path = create_sample_data()
        print(f"Using sample data: {data_path}")
        
        if not analyzer.load_crash_data(data_path):
            return None, None
    else:
        print("Invalid option selected.")
        return None, None
    
    # Perform analysis
    print("\nStarting analysis...")
    print("="*50)
    
    t0 = time.time()
    analyzer.preprocess_data()
    print(f"[TIME] Preprocessing time: {time.time() - t0:.2f} seconds\n")
    
    t0 = time.time()
    analyzer.perform_kde_analysis(bandwidth=0.008)
    print(f"[TIME] KDE analysis time: {time.time() - t0:.2f} seconds\n")
    
    t0 = time.time()
    analyzer.identify_hotspots(threshold_percentile=85)
    print(f"[TIME] Hotspot identification time: {time.time() - t0:.2f} seconds\n")
    
    t0 = time.time()
    performance_metrics = analyzer.evaluate_model_performance(calculate_hit_rate=True)
    print(f"[TIME] Performance evaluation time: {time.time() - t0:.2f} seconds\n")
    
    # Create visualizations
    print("\nGenerating visualizations...")
    t0 = time.time()
    analyzer.create_visualizations()
    print(f"[TIME] Visualization time: {time.time() - t0:.2f} seconds\n")
    
    # Create interactive maps
    print("\nCreating interactive maps...")
    t0 = time.time()
    analyzer.create_interactive_map('edsa_crash_detailed.html', style='detailed')
    analyzer.create_interactive_map('edsa_crash_heatmap.html', style='heatmap_only')
    print(f"[TIME] Map generation time: {time.time() - t0:.2f} seconds\n")
    
    total_time = time.time() - start_time
    
    print("\n" + "="*50)
    print("Analysis complete! Check the generated files:")
    print("  - Static plots (displayed)")
    print("  - edsa_crash_detailed.html (detailed map with markers)")
    print("  - edsa_crash_heatmap.html (heatmap only - clean view)")
    print(f"\n[TIME] Total execution time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
    print("="*50)
    
    return analyzer, performance_metrics

def quick_analysis_from_csvdata(year_filter=None, fast_mode=False):
    """
    Quick analysis using all CSV files from CSVData directory
    
    Parameters:
    -----------
    year_filter : tuple or None
        (start_year, end_year) to filter data, or None for all years
        Example: (2018, 2023) to analyze only 2018-2023 data
    fast_mode : bool
        If True, uses more aggressive sampling for extra speed (30-50% faster)
    """
    start_time = time.time()
    
    mode_text = "FAST MODE" if fast_mode else "STANDARD MODE"
    print(f"Starting Quick EDSA Road Crash Spatial Analysis ({mode_text})")
    print("="*50)
    
    analyzer = EDSACrashAnalyzer()
    
    directory = 'CSVData'
    if not os.path.exists(directory):
        print(f"Directory '{directory}' not found. Please ensure the CSVData folder exists.")
        return None, None
    
    print(f"\nLoading all CSV files from '{directory}' directory...")
    if not analyzer.load_crash_data_from_directory(directory):
        return None, None
    
    # Apply year filter if specified
    if year_filter is not None and 'year' in analyzer.crash_data.columns:
        start_year, end_year = year_filter
        analyzer.filter_by_year_range(start_year, end_year)
    
    # Perform analysis with timing
    print("\nStarting analysis...")
    print("="*50)
    
    t0 = time.time()
    analyzer.preprocess_data()
    print(f"[TIME] Preprocessing time: {time.time() - t0:.2f} seconds\n")
    
    # Adjust parameters based on fast_mode
    if fast_mode:
        kde_points = 50000  # Reduced from 100000
        cluster_points = 30000  # Reduced from 50000
        plot_points = 5000  # Reduced from 10000
        print("[FAST] Fast mode enabled - using aggressive sampling for speed\n")
    else:
        kde_points = 100000
        cluster_points = 50000
        plot_points = 10000
    
    t0 = time.time()
    analyzer.perform_kde_analysis(bandwidth=0.008, max_kde_points=kde_points, grid_resolution=80 if fast_mode else 100)
    print(f"[TIME] KDE analysis time: {time.time() - t0:.2f} seconds\n")
    
    t0 = time.time()
    analyzer.identify_hotspots(threshold_percentile=85, max_points=cluster_points)
    print(f"[TIME] Hotspot identification time: {time.time() - t0:.2f} seconds\n")
    
    t0 = time.time()
    # Skip hit rate in fast mode for extra speed
    performance_metrics = analyzer.evaluate_model_performance(calculate_hit_rate=not fast_mode)
    print(f"[TIME] Performance evaluation time: {time.time() - t0:.2f} seconds\n")
    
    # Create visualizations
    print("\nGenerating visualizations...")
    t0 = time.time()
    analyzer.create_visualizations(max_plot_points=plot_points)
    print(f"[TIME] Visualization time: {time.time() - t0:.2f} seconds\n")
    
    # Create interactive maps
    print("\nCreating interactive maps...")
    t0 = time.time()
    analyzer.create_interactive_map('edsa_crash_detailed.html', style='detailed', max_markers=3000 if fast_mode else 5000)
    analyzer.create_interactive_map('edsa_crash_heatmap.html', style='heatmap_only', max_markers=0)
    print(f"[TIME] Map generation time: {time.time() - t0:.2f} seconds\n")
    
    total_time = time.time() - start_time
    
    print("\n" + "="*50)
    print("Analysis complete! Check the generated files:")
    print("  - Static plots (displayed)")
    print("  - edsa_crash_detailed.html (detailed map with markers)")
    print("  - edsa_crash_heatmap.html (heatmap only - clean view)")
    print(f"\n[TIME] Total execution time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
    print("="*50)
    
    return analyzer, performance_metrics

def ultra_fast_analysis(year_filter=(2020, 2023)):
    """
    Ultra-fast analysis - optimized for speed with minimal quality loss
    Perfect for quick iterations and testing
    
    Parameters:
    -----------
    year_filter : tuple
        (start_year, end_year) - defaults to recent years (2020-2023)
    """
    return quick_analysis_from_csvdata(year_filter=year_filter, fast_mode=True)

if __name__ == "__main__":
    # ============================================================
    # CHOOSE YOUR ANALYSIS MODE:
    # ============================================================
    
    # 🚀🚀 ULTRA FAST MODE - Recent years with aggressive sampling - RECOMMENDED!
    # Analyzes 2020-2023 (~120k records) with fast mode - completes in ~20 seconds
    analyzer, metrics = ultra_fast_analysis(year_filter=(2020, 2023))
    
    # 🚀 FAST MODE - Recent years only (2020-2023) - completes in ~30 seconds
    # analyzer, metrics = quick_analysis_from_csvdata(year_filter=(2020, 2023))
    
    # 📊 STANDARD MODE - Recent years with full sampling - ~45 seconds
    # analyzer, metrics = quick_analysis_from_csvdata(year_filter=(2020, 2023), fast_mode=False)
    
    # 🐌 FULL MODE - All years (slow with large datasets - ~2-3 minutes)
    # analyzer, metrics = quick_analysis_from_csvdata()
    
    # 🎯 CUSTOM MODE - Interactive menu with year filtering option
    # analyzer, metrics = main()
    
    # 💡 MORE OPTIONS:
    # analyzer, metrics = ultra_fast_analysis(year_filter=(2022, 2023))  # Only very recent (~60k records, ~15 sec)
    # analyzer, metrics = quick_analysis_from_csvdata(year_filter=(2018, 2023), fast_mode=True)  # 2018-2023 fast