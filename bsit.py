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
warnings.filterwarnings('ignore')

class EDSACrashAnalyzer:
    def __init__(self):
        self.crash_data = None
        self.edsa_boundary = None
        self.kde_model = None
        self.crash_gdf = None
        self.hotspots = None
        
    def load_crash_data(self, data_path):
        try:
            self.crash_data = pd.read_csv(data_path)
            print(f"Loaded {len(self.crash_data)} crash records from {data_path}")
        except FileNotFoundError:
            print(f"File not found: {data_path}")
            print("Please ensure the CSV file exists with columns: latitude, longitude, date, severity, vehicle_type")
            return False
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            return False
        
        required_columns = ['latitude', 'longitude']
        missing_cols = [col for col in required_columns if col not in self.crash_data.columns]
        if missing_cols:
            print(f"Missing required columns: {missing_cols}")
            return False
        
        geometry = [Point(xy) for xy in zip(self.crash_data.longitude, self.crash_data.latitude)]
        self.crash_gdf = gpd.GeoDataFrame(self.crash_data, geometry=geometry, crs='EPSG:4326')
        
        return True
    
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
    
    def perform_kde_analysis(self, bandwidth=0.01):
        print(f"Performing KDE analysis with bandwidth={bandwidth}")
        
        coordinates = self.crash_data[['latitude', 'longitude']].values
        
        self.kde_model = KernelDensity(bandwidth=bandwidth, kernel='gaussian')
        self.kde_model.fit(coordinates)
        
        lat_min, lat_max = coordinates[:, 0].min(), coordinates[:, 0].max()
        lon_min, lon_max = coordinates[:, 1].min(), coordinates[:, 1].max()
        
        lat_range = lat_max - lat_min
        lon_range = lon_max - lon_min
        lat_min -= lat_range * 0.1
        lat_max += lat_range * 0.1
        lon_min -= lon_range * 0.1
        lon_max += lon_range * 0.1
        
        lat_grid = np.linspace(lat_min, lat_max, 100)
        lon_grid = np.linspace(lon_min, lon_max, 100)
        lat_mesh, lon_mesh = np.meshgrid(lat_grid, lon_grid)
        
        mesh_points = np.column_stack([lat_mesh.ravel(), lon_mesh.ravel()])
        density_scores = np.exp(self.kde_model.score_samples(mesh_points))
        density_grid = density_scores.reshape(lat_mesh.shape)
        
        self.density_grid = density_grid
        self.lat_mesh = lat_mesh
        self.lon_mesh = lon_mesh
        
        print("KDE analysis completed")
        return density_grid
    
    def identify_hotspots(self, threshold_percentile=90):
        print(f"Identifying hotspots (threshold: {threshold_percentile}th percentile)")
        
        coordinates = self.crash_data[['latitude', 'longitude']].values
        
        eps = 0.005
        min_samples = 5
        
        clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(coordinates)
        labels = clustering.labels_
        
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
    
    def evaluate_model_performance(self):
        print("Evaluating model performance...")
        
        coordinates = self.crash_data[['latitude', 'longitude']].values
        
        hit_rate = self._calculate_hit_rate()
        
        valid_clusters = self.crash_data['cluster'] != -1
        if valid_clusters.sum() > 1:
            cluster_coords = coordinates[valid_clusters]
            cluster_labels = self.crash_data.loc[valid_clusters, 'cluster']
            
            if len(set(cluster_labels)) > 1:
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
        print(f"  Hit Rate: {hit_rate:.3f}")
        print(f"  Silhouette Score: {silhouette_avg:.3f}")
        print(f"  Number of Clusters: {n_clusters}")
        print(f"  Noise Ratio: {noise_ratio:.3f}")
        
        return performance_metrics
    
    def _calculate_hit_rate(self, top_percentile=20):
        if self.hotspots is None or len(self.hotspots) == 0:
            return 0.0
        
        threshold = np.percentile(self.density_grid, 100 - top_percentile)
        
        hits = 0
        total_crashes = len(self.crash_data)
        
        for _, crash in self.crash_data.iterrows():
            lat_idx = np.argmin(np.abs(self.lat_mesh[:, 0] - crash['latitude']))
            lon_idx = np.argmin(np.abs(self.lon_mesh[0, :] - crash['longitude']))
            
            if lat_idx < len(self.density_grid) and lon_idx < len(self.density_grid[0]):
                if self.density_grid[lat_idx, lon_idx] >= threshold:
                    hits += 1
        
        return hits / total_crashes if total_crashes > 0 else 0.0
    
    def create_visualizations(self):
        print("Creating visualizations...")
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        ax1 = axes[0, 0]
        ax1.scatter(self.crash_data['longitude'], self.crash_data['latitude'], 
                   alpha=0.6, s=20, c='red', label='Crashes')
        if self.hotspots is not None and len(self.hotspots) > 0:
            ax1.scatter(self.hotspots['longitude'], self.hotspots['latitude'], 
                       s=self.hotspots['crash_count']*10, c='blue', alpha=0.7, 
                       marker='s', label='Hotspots')
        ax1.set_xlabel('Longitude')
        ax1.set_ylabel('Latitude')
        ax1.set_title('EDSA Crash Distribution and Identified Hotspots')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        ax2 = axes[0, 1]
        if hasattr(self, 'density_grid'):
            im = ax2.contourf(self.lon_mesh, self.lat_mesh, self.density_grid, 
                             levels=20, cmap='YlOrRd', alpha=0.7)
            ax2.scatter(self.crash_data['longitude'], self.crash_data['latitude'], 
                       alpha=0.4, s=10, c='black')
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
            clusters = self.crash_data['cluster']
            unique_clusters = set(clusters) - {-1}
            colors = plt.cm.tab10(np.linspace(0, 1, len(unique_clusters)))
            
            noise_points = self.crash_data[clusters == -1]
            if len(noise_points) > 0:
                ax4.scatter(noise_points['longitude'], noise_points['latitude'], 
                           c='gray', alpha=0.5, s=10, label='Noise')
            
            for i, cluster_id in enumerate(unique_clusters):
                cluster_points = self.crash_data[clusters == cluster_id]
                ax4.scatter(cluster_points['longitude'], cluster_points['latitude'], 
                           c=[colors[i]], alpha=0.7, s=20, label=f'Cluster {cluster_id}')
            
            ax4.set_xlabel('Longitude')
            ax4.set_ylabel('Latitude')
            ax4.set_title('DBSCAN Clustering Results')
            if len(unique_clusters) <= 10:
                ax4.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        else:
            ax4.set_xlabel('Longitude')
            ax4.set_ylabel('Latitude')
            ax4.set_title('DBSCAN Clustering Results (No clustering data)')
        
        plt.tight_layout()
        plt.show()
        
        # Create summary statistics
        self._create_summary_report()
    
    def create_interactive_map(self, save_path='edsa_crash_analysis.html'):
        print("Creating interactive map...")
        
        center_lat = self.crash_data['latitude'].mean()
        center_lon = self.crash_data['longitude'].mean()
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=11)
        
        for _, crash in self.crash_data.iterrows():
            color = 'red' if crash.get('severity') == 'Fatal' else 'orange' if crash.get('severity') == 'Major' else 'yellow'
            folium.CircleMarker(
                location=[crash['latitude'], crash['longitude']],
                radius=3,
                popup=f"Crash ID: {crash.get('crash_id', 'N/A')}<br>Severity: {crash.get('severity', 'Unknown')}",
                color=color,
                fillColor=color,
                fillOpacity=0.7
            ).add_to(m)
        
        if self.hotspots is not None and len(self.hotspots) > 0:
            for _, hotspot in self.hotspots.iterrows():
                folium.Marker(
                    location=[hotspot['latitude'], hotspot['longitude']],
                    popup=f"Hotspot: {hotspot['crash_count']} crashes<br>Severity Score: {hotspot['severity_score']:.2f}",
                    icon=folium.Icon(color='blue', icon='warning-sign')
                ).add_to(m)
        
        heat_data = [[row['latitude'], row['longitude']] for _, row in self.crash_data.iterrows()]
        HeatMap(heat_data, radius=15, blur=10, max_zoom=1).add_to(m)
        
        m.save(save_path)
        print(f"Interactive map saved to {save_path}")
        return m
    
    def _create_summary_report(self):
        print("\n" + "="*50)
        print("EDSA CRASH ANALYSIS SUMMARY REPORT")
        print("="*50)
        
        print(f"\nDATA OVERVIEW:")
        print(f"Total Crashes Analyzed: {len(self.crash_data)}")
        if 'date' in self.crash_data.columns:
            print(f"Date Range: {self.crash_data['date'].min()} to {self.crash_data['date'].max()}")
        print(f"Geographic Coverage: {self.crash_data['latitude'].min():.4f}° to {self.crash_data['latitude'].max():.4f}° N")
        print(f"                    {self.crash_data['longitude'].min():.4f}° to {self.crash_data['longitude'].max():.4f}° E")
        
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
    print("Starting EDSA Road Crash Spatial Analysis")
    print("="*50)
    
    analyzer = EDSACrashAnalyzer()
    
    # Ask user for data path or create sample data
    use_sample = input("Use sample data? (y/n): ").lower().strip()
    
    if use_sample == 'y' or use_sample == 'yes':
        data_path = create_sample_data()
        print(f"Using sample data: {data_path}")
    else:
        data_path = input("Enter path to crash data CSV file: ")
    
    if not analyzer.load_crash_data(data_path):
        return None, None
    
    analyzer.preprocess_data()
    analyzer.perform_kde_analysis(bandwidth=0.008)
    analyzer.identify_hotspots(threshold_percentile=85)
    performance_metrics = analyzer.evaluate_model_performance()
    analyzer.create_visualizations()
    analyzer.create_interactive_map()
    
    print("\nAnalysis complete! Check the generated visualizations and interactive map.")
    return analyzer, performance_metrics

if __name__ == "__main__":
    analyzer, metrics = main()