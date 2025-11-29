"""
Phase 3 Metrics Analysis - Hit Rate and Silhouette Analysis
============================================================

This module focuses on calculating two key performance metrics:

1. HIT RATE (Capture Rate)
   Formula: Hit Rate = ( # of Crash Accidents within high density areas / Total # of Crash accidents ) x 100%
   
   Measures how well the density model identifies high-risk areas by calculating
   the percentage of crashes that fall within high-density regions.

2. SILHOUETTE SCORE
   Formula: s(i) = (b(i) - a(i)) / max{a(i), b(i)}
   
   Where:
   - s(i) = Silhouette score for point i
   - a(i) = Average distance from point i to the points in the same cluster
   - b(i) = Average distance from point i to the points from closest surrounding clusters
   
   Source: Firdose, T. (2023, December 8). Understanding the silhouette Score.
   
   Measures the quality of clustering by evaluating cohesion and separation.

Based on the EDSA Crash Analysis framework from bsit.py
"""

import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from sklearn.neighbors import KernelDensity
from sklearn.cluster import DBSCAN
from sklearn.metrics import silhouette_score
from scipy.spatial.distance import cdist
import warnings
import os
import glob
import re
import time
import json

warnings.filterwarnings('ignore')


class Phase3MetricsAnalyzer:
    """
    Analyzer class for Phase 3 metrics: Hit Rate and Silhouette Analysis
    """
    
    def __init__(self):
        self.crash_data = None
        self.crash_gdf = None
        self.kde_model = None
        self.density_grid = None
        self.lat_mesh = None
        self.lon_mesh = None
        self.cluster_labels = None
        self.metrics_results = {}
    
    def _parse_coordinate(self, coord_str):
        """Parse coordinate string that may contain degree symbols and directions"""
        if pd.isna(coord_str):
            return None
        
        coord_str = str(coord_str).strip()
        coord_str = re.sub(r'[°NSEW\s]', '', coord_str)
        
        try:
            return float(coord_str)
        except ValueError:
            return None
    
    def _standardize_dataframe(self, df):
        """Standardize column names and data formats"""
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
        
        # Parse latitude and longitude if they contain degree symbols
        if 'latitude' in df.columns:
            df['latitude'] = df['latitude'].apply(self._parse_coordinate)
        
        if 'longitude' in df.columns:
            df['longitude'] = df['longitude'].apply(self._parse_coordinate)
        
        return df
    
    def load_crash_data_from_directory(self, directory_path, pattern='*.csv', year_range=None):
        """
        Load all CSV files matching pattern from a directory
        
        Parameters:
        -----------
        directory_path : str
            Path to directory containing CSV files
        pattern : str
            File pattern to match (default: '*.csv')
        year_range : tuple or None
            (start_year, end_year) to filter files by year in filename
        """
        try:
            search_path = os.path.join(directory_path, pattern)
            csv_files = sorted(glob.glob(search_path))
            
            if not csv_files:
                print(f"No CSV files found in {directory_path}")
                return False
            
            # Filter by year range if specified
            if year_range is not None:
                start_year, end_year = year_range
                filtered_files = []
                
                for file_path in csv_files:
                    filename = os.path.basename(file_path)
                    year_match = re.search(r'(\d{4})', filename)
                    
                    if year_match:
                        file_year = int(year_match.group(1))
                        if start_year <= file_year <= end_year:
                            filtered_files.append(file_path)
                
                if not filtered_files:
                    print(f"No CSV files found for year range {start_year}-{end_year}")
                    return False
                
                csv_files = filtered_files
                print(f"Found {len(csv_files)} CSV files for years {start_year}-{end_year}")
            else:
                print(f"Found {len(csv_files)} CSV files")
            
            # Load and combine all files
            all_dataframes = []
            
            for data_path in csv_files:
                try:
                    df = pd.read_csv(data_path)
                    df = self._standardize_dataframe(df)
                    all_dataframes.append(df)
                    print(f"  Loaded {len(df)} records from {os.path.basename(data_path)}")
                except Exception as e:
                    print(f"  Error loading {data_path}: {str(e)}")
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
            
            # Filter to EDSA area (approximate bounds)
            lat_bounds = (14.4, 14.8)
            lon_bounds = (120.9, 121.2)
            
            coord_filter = (
                (self.crash_data['latitude'].between(*lat_bounds)) & 
                (self.crash_data['longitude'].between(*lon_bounds))
            )
            self.crash_data = self.crash_data[coord_filter]
            
            # Create GeoDataFrame
            geometry = [Point(xy) for xy in zip(self.crash_data.longitude, self.crash_data.latitude)]
            self.crash_gdf = gpd.GeoDataFrame(self.crash_data, geometry=geometry, crs='EPSG:4326')
            
            print(f"Final dataset: {len(self.crash_data)} records after filtering")
            return True
            
        except Exception as e:
            print(f"Error loading from directory: {str(e)}")
            return False
    
    def load_crash_reports_from_directory(self, directory_path='CSVData/crashReports', pattern='damage_*.csv', year_range=None):
        """
        Load aggregated crash reports from CSVData/crashReports directory
        
        This method reads aggregated city-level crash data and expands it into
        individual crash points for analysis.
        
        Parameters:
        -----------
        directory_path : str
            Path to directory containing damage report CSV files (default: 'CSVData/crashReports')
        pattern : str
            File pattern to match (default: 'damage_*.csv')
        year_range : tuple or None
            (start_year, end_year) to filter files by year in filename
        
        Returns:
        --------
        bool
            True if successful, False otherwise
        """
        try:
            search_path = os.path.join(directory_path, pattern)
            csv_files = sorted(glob.glob(search_path))
            
            if not csv_files:
                print(f"No crash report CSV files found in {directory_path}")
                return False
            
            # Filter by year range if specified
            if year_range is not None:
                start_year, end_year = year_range
                filtered_files = []
                
                for file_path in csv_files:
                    filename = os.path.basename(file_path)
                    year_match = re.search(r'(\d{4})', filename)
                    
                    if year_match:
                        file_year = int(year_match.group(1))
                        if start_year <= file_year <= end_year:
                            filtered_files.append(file_path)
                
                if not filtered_files:
                    print(f"No crash report files found for year range {start_year}-{end_year}")
                    return False
                
                csv_files = filtered_files
                print(f"Found {len(csv_files)} crash report files for years {start_year}-{end_year}")
            else:
                print(f"Found {len(csv_files)} crash report files")
            
            # Load and expand all files
            all_expanded_records = []
            
            for data_path in csv_files:
                try:
                    # Extract year from filename
                    filename = os.path.basename(data_path)
                    year_match = re.search(r'(\d{4})', filename)
                    year = int(year_match.group(1)) if year_match else None
                    
                    # Load aggregated data
                    df = pd.read_csv(data_path)
                    df = self._standardize_dataframe(df)
                    
                    # Remove Grand Total summary row if present (last row with aggregate values)
                    # Check if last row has coordinates matching typical Grand Total location
                    if len(df) > 0:
                        last_row = df.iloc[-1]
                        # Typical Grand Total row has central Metro Manila coordinates (14.6042, 121.0182)
                        # and very high values. Check if it looks like a summary row.
                        if (abs(last_row.get('latitude', 0) - 14.6042) < 0.01 and 
                            abs(last_row.get('longitude', 0) - 121.0182) < 0.01):
                            # Likely a Grand Total row, remove it
                            df = df.iloc[:-1].copy()
                            print(f"    Removed Grand Total summary row")
                    
                    # Skip rows with Grand Total = 0 or invalid data
                    df = df[df['grand_total'] > 0].copy()
                    
                    print(f"  Processing {os.path.basename(data_path)}: {len(df)} cities")
                    
                    # Expand aggregated data into individual crash points
                    expanded_records = []
                    for _, row in df.iterrows():
                        lat = row.get('latitude', None)
                        lon = row.get('longitude', None)
                        grand_total = int(row.get('grand_total', 0))
                        
                        # Skip if missing coordinates or Grand Total is 0
                        if pd.isna(lat) or pd.isna(lon) or grand_total <= 0:
                            continue
                        
                        # Expand into individual crash points
                        # Distribute points around the city center with small random offsets
                        np.random.seed(int(lat * 1000 + lon * 1000) % 2**31)  # Deterministic seed per city
                        
                        for i in range(grand_total):
                            # Add small random offset (approximately 0.01 degrees ~ 1km)
                            offset_lat = np.random.normal(0, 0.003)
                            offset_lon = np.random.normal(0, 0.003)
                            
                            # Determine severity based on proportions
                            fatal = int(row.get('fatal', 0))
                            non_fatal_injury = int(row.get('non_fatal_injury', 0))
                            damage = int(row.get('damage', 0))
                            
                            # Assign severity based on position in the total
                            if i < fatal:
                                severity = 'FATAL'
                            elif i < fatal + non_fatal_injury:
                                severity = 'NON FATAL INJURY'
                            else:
                                severity = 'DAMAGE'
                            
                            expanded_records.append({
                                'crash_id': f'REPORT-{year}-{lat:.4f}-{lon:.4f}-{i}',
                                'latitude': lat + offset_lat,
                                'longitude': lon + offset_lon,
                                'year': year,
                                'severity': severity
                            })
                    
                    all_expanded_records.extend(expanded_records)
                    print(f"    Expanded to {len(expanded_records)} crash points")
                    
                except Exception as e:
                    print(f"  Error processing {data_path}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            if not all_expanded_records:
                print("No crash records were successfully expanded")
                return False
            
            # Create DataFrame from expanded records
            self.crash_data = pd.DataFrame(all_expanded_records)
            print(f"\nTotal expanded crash records: {len(self.crash_data)}")
            
            # Remove rows with invalid coordinates
            initial_count = len(self.crash_data)
            self.crash_data = self.crash_data.dropna(subset=['latitude', 'longitude'])
            
            if len(self.crash_data) < initial_count:
                print(f"Removed {initial_count - len(self.crash_data)} records with invalid coordinates")
            
            # Filter to EDSA area (approximate bounds)
            lat_bounds = (14.4, 14.8)
            lon_bounds = (120.9, 121.2)
            
            coord_filter = (
                (self.crash_data['latitude'].between(*lat_bounds)) & 
                (self.crash_data['longitude'].between(*lon_bounds))
            )
            self.crash_data = self.crash_data[coord_filter]
            
            # Create GeoDataFrame
            geometry = [Point(xy) for xy in zip(self.crash_data.longitude, self.crash_data.latitude)]
            self.crash_gdf = gpd.GeoDataFrame(self.crash_data, geometry=geometry, crs='EPSG:4326')
            
            print(f"Final dataset: {len(self.crash_data)} records after filtering")
            return True
            
        except Exception as e:
            print(f"Error loading crash reports from directory: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def perform_kde_analysis(self, bandwidth=0.008, max_kde_points=100000, grid_resolution=100):
        """
        Perform Kernel Density Estimation (KDE) analysis
        
        This is required for Hit Rate calculation as it creates the density grid
        that identifies high-risk areas.
        
        Parameters:
        -----------
        bandwidth : float
            Bandwidth parameter for KDE (default: 0.008)
        max_kde_points : int
            Maximum points to use for KDE fitting (for performance)
        grid_resolution : int
            Resolution of the density grid (default: 100x100)
        
        Returns:
        --------
        density_grid : numpy.ndarray
            2D array of density values
        """
        print("\n" + "="*60)
        print("PERFORMING KDE ANALYSIS (Required for Hit Rate)")
        print("="*60)
        
        coordinates = self.crash_data[['latitude', 'longitude']].values
        
        # Use sampling for KDE if dataset is too large
        if len(coordinates) > max_kde_points:
            print(f"Sampling {max_kde_points} points for KDE analysis (from {len(coordinates)} total)...")
            sample_indices = np.random.choice(len(coordinates), max_kde_points, replace=False)
            kde_coords = coordinates[sample_indices]
        else:
            kde_coords = coordinates
        
        print(f"Fitting KDE model on {len(kde_coords)} points with bandwidth={bandwidth}...")
        self.kde_model = KernelDensity(bandwidth=bandwidth, kernel='gaussian')
        self.kde_model.fit(kde_coords)
        
        # Create grid for density estimation
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
        
        print("✓ KDE analysis completed")
        return density_grid
    
    def get_density_at_location(self, latitude, longitude):
        """
        Get density value at a specific location (latitude, longitude)
        
        This method allows you to query the density value at any specific
        coordinate point after KDE analysis has been performed.
        
        Parameters:
        -----------
        latitude : float
            Latitude coordinate
        longitude : float
            Longitude coordinate
        
        Returns:
        --------
        density_value : float or None
            Density value at the specified location, or None if KDE not performed
        """
        if self.kde_model is None:
            print("ERROR: KDE analysis must be performed first!")
            print("Call perform_kde_analysis() before querying density values")
            return None
        
        # Query density at the specified point
        point = np.array([[latitude, longitude]])
        log_density = self.kde_model.score_samples(point)
        density_value = np.exp(log_density)[0]
        
        return density_value
    
    def get_density_percentile(self, percentile=90):
        """
        Get the density threshold value for a given percentile
        
        This helps identify high-density areas. For example:
        - 90th percentile = threshold where 10% of area has higher density
        - 80th percentile = threshold where 20% of area has higher density
        
        Parameters:
        -----------
        percentile : float
            Percentile value (0-100). Default: 90
        
        Returns:
        --------
        threshold : float or None
            Density threshold value, or None if KDE not performed
        """
        if self.density_grid is None:
            print("ERROR: KDE analysis must be performed first!")
            return None
        
        threshold = np.percentile(self.density_grid, percentile)
        return threshold
    
    def is_high_density_area(self, latitude, longitude, percentile=80):
        """
        Check if a location is in a high-density area
        
        Parameters:
        -----------
        latitude : float
            Latitude coordinate
        longitude : float
            Longitude coordinate
        percentile : float
            Percentile threshold (default: 80 = top 20% are high-density)
        
        Returns:
        --------
        bool or None
            True if location is in high-density area, False otherwise, None if error
        """
        if self.density_grid is None:
            print("ERROR: KDE analysis must be performed first!")
            return None
        
        density_value = self.get_density_at_location(latitude, longitude)
        if density_value is None:
            return None
        
        threshold = self.get_density_percentile(percentile)
        return density_value >= threshold
    
    def get_density_statistics(self):
        """
        Get summary statistics about the density distribution
        
        Returns:
        --------
        stats : dict or None
            Dictionary with density statistics, or None if KDE not performed
        """
        if self.density_grid is None:
            print("ERROR: KDE analysis must be performed first!")
            return None
        
        stats = {
            'min': float(np.min(self.density_grid)),
            'max': float(np.max(self.density_grid)),
            'mean': float(np.mean(self.density_grid)),
            'median': float(np.percentile(self.density_grid, 50)),
            'std': float(np.std(self.density_grid)),
            'percentiles': {
                '10th': float(np.percentile(self.density_grid, 10)),
                '25th': float(np.percentile(self.density_grid, 25)),
                '50th': float(np.percentile(self.density_grid, 50)),
                '75th': float(np.percentile(self.density_grid, 75)),
                '80th': float(np.percentile(self.density_grid, 80)),
                '85th': float(np.percentile(self.density_grid, 85)),
                '90th': float(np.percentile(self.density_grid, 90)),
                '95th': float(np.percentile(self.density_grid, 95)),
                '99th': float(np.percentile(self.density_grid, 99))
            }
        }
        
        return stats
    
    def print_density_info(self):
        """
        Print comprehensive information about density calculation and values
        
        This provides an overview of:
        - How density is calculated
        - Current density statistics
        - How to interpret density values
        """
        print("\n" + "="*60)
        print("DENSITY INFORMATION & STATISTICS")
        print("="*60)
        
        if self.density_grid is None:
            print("\n⚠ KDE analysis has not been performed yet.")
            print("   Call perform_kde_analysis() first to calculate density values.")
            return
        
        print("\n📊 HOW DENSITY IS CALCULATED:")
        print("   • Method: Kernel Density Estimation (KDE)")
        print("   • Technique: Gaussian kernel smoothing")
        print("   • Grid Resolution: {}x{} points".format(
            self.density_grid.shape[0], self.density_grid.shape[1]
        ))
        print("   • Density represents: Relative likelihood of crash occurrence")
        print("     (Higher values = More crash activity in the area)")
        
        stats = self.get_density_statistics()
        if stats:
            print("\n📈 DENSITY STATISTICS:")
            print(f"   Minimum:     {stats['min']:.6f}")
            print(f"   Maximum:     {stats['max']:.6f}")
            print(f"   Mean:        {stats['mean']:.6f}")
            print(f"   Median:      {stats['median']:.6f}")
            print(f"   Std Dev:     {stats['std']:.6f}")
            
            print("\n📊 DENSITY PERCENTILES (for threshold identification):")
            for pct_name, value in stats['percentiles'].items():
                percentile_num = int(pct_name.replace('th', '').replace('rd', '').replace('st', '').replace('nd', ''))
                top_pct = 100 - percentile_num
                print(f"   {pct_name:6s} percentile: {value:10.6f}  (Top {top_pct:2d}% of area)")
        
        print("\n💡 HOW TO USE DENSITY VALUES:")
        print("   1. Query density at a location:")
        print("      density = analyzer.get_density_at_location(lat, lon)")
        print("   2. Check if location is high-density:")
        print("      is_high = analyzer.is_high_density_area(lat, lon, percentile=80)")
        print("   3. Get density threshold for top X%:")
        print("      threshold = analyzer.get_density_percentile(90)  # Top 10%")
        print("   4. Get all statistics:")
        print("      stats = analyzer.get_density_statistics()")
        
        print("\n🎯 HIGH-DENSITY AREA IDENTIFICATION:")
        print("   High-density areas = Locations where crashes are more concentrated")
        print("   • Top 10% of area: 90th percentile threshold")
        print("   • Top 20% of area: 80th percentile threshold")
        print("   • Top 25% of area: 75th percentile threshold")
        print("\n   These areas indicate crash 'hotspots' that need attention.")
        print("="*60)
    
    def perform_clustering(self, eps=0.005, min_samples=5, max_points=50000):
        """
        Perform DBSCAN clustering analysis
        
        This is required for Silhouette Score calculation as it assigns
        cluster labels to each crash point.
        
        Parameters:
        -----------
        eps : float
            Maximum distance between samples in the same cluster (default: 0.005)
        min_samples : int
            Minimum number of samples in a cluster (default: 5)
        max_points : int
            Maximum points to use for clustering (for performance)
        
        Returns:
        --------
        cluster_labels : numpy.ndarray
            Array of cluster labels (-1 indicates noise/outliers)
        """
        print("\n" + "="*60)
        print("PERFORMING CLUSTERING ANALYSIS (Required for Silhouette Score)")
        print("="*60)
        
        coordinates = self.crash_data[['latitude', 'longitude']].values
        
        # Handle large datasets by sampling
        use_sample = len(coordinates) > max_points
        if use_sample:
            print(f"Dataset too large ({len(coordinates)} points). Using sample of {max_points} points...")
            sample_indices = np.random.choice(len(coordinates), max_points, replace=False)
            sample_coords = coordinates[sample_indices]
        else:
            sample_coords = coordinates
        
        print(f"Running DBSCAN clustering on {len(sample_coords)} points...")
        print(f"  Parameters: eps={eps}, min_samples={min_samples}")
        
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
                    min_distances = distances.min(axis=1)
                    nearest_clusters = distances.argmin(axis=1)
                    
                    # Only assign if within threshold distance
                    valid_assignments = min_distances < (eps * 2)
                    labels[i:batch_end][valid_assignments] = [centroid_labels[idx] for idx in nearest_clusters[valid_assignments]]
        else:
            labels = sample_labels
        
        self.cluster_labels = labels
        self.crash_data['cluster'] = labels
        
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise = (labels == -1).sum()
        
        print(f"✓ Clustering completed")
        print(f"  Number of clusters: {n_clusters}")
        print(f"  Noise points: {n_noise} ({n_noise/len(labels)*100:.1f}%)")
        
        return labels
    
    def calculate_hit_rate(self, top_percentile=20, max_sample_points=5000):
        """
        Calculate Hit Rate metric (Capture Rate)
        
        Hit Rate measures the percentage of crash points that fall within
        the top X percentile of the density grid (high-risk areas).
        
        Formula (from research):
        Hit Rate = ( # of Crash Accidents within high density areas / Total # of Crash accidents ) x 100%
        
        Where:
        - High density areas = Top X percentile of the KDE density grid
        - Total # of Crash accidents = All crash points in the dataset
        
        Parameters:
        -----------
        top_percentile : int
            Top percentile to consider as "high-risk" area (default: 20)
            This means we're looking at the top 20% of density values
        max_sample_points : int
            Maximum points to sample for calculation (for performance)
        
        Returns:
        --------
        hit_rate : float
            Hit rate value between 0.0 and 1.0 (multiply by 100 for percentage)
            Higher values indicate better model performance
        """
        print("\n" + "="*60)
        print("CALCULATING HIT RATE")
        print("="*60)
        
        if self.density_grid is None:
            print("ERROR: KDE analysis must be performed first!")
            print("Call perform_kde_analysis() before calculate_hit_rate()")
            return None
        
        # Calculate threshold (top X percentile of density values)
        # If top_percentile=20, we want top 20%, which is 80th-100th percentile
        # So threshold = value at (100 - top_percentile) percentile
        percentile_value = 100 - top_percentile
        threshold = np.percentile(self.density_grid, percentile_value)
        
        # Also get statistics about the density grid
        grid_min = np.min(self.density_grid)
        grid_max = np.max(self.density_grid)
        grid_mean = np.mean(self.density_grid)
        
        print(f"Using top {top_percentile}% of density values as threshold")
        print(f"  Density grid statistics:")
        print(f"    Min: {grid_min:.6f}, Max: {grid_max:.6f}, Mean: {grid_mean:.6f}")
        print(f"  Threshold ({percentile_value}th percentile): {threshold:.6f}")
        print(f"  This means areas with density >= {threshold:.6f} are in top {top_percentile}%")
        
        # Sample for hit rate calculation if dataset is large
        if len(self.crash_data) > max_sample_points:
            print(f"Sampling {max_sample_points} points for hit rate calculation...")
            sample_data = self.crash_data.sample(n=max_sample_points, random_state=42)
        else:
            sample_data = self.crash_data
        
        coordinates = sample_data[['latitude', 'longitude']].values
        
        # Use KDE model to directly query density at each crash point
        # This is more accurate than trying to match grid indices
        print(f"Querying density for {len(coordinates)} crash points...")
        
        # Query density values for all crash points using the KDE model
        # Process in batches to avoid memory issues
        batch_size = 5000
        density_values = np.zeros(len(coordinates))
        
        for i in range(0, len(coordinates), batch_size):
            batch_end = min(i + batch_size, len(coordinates))
            batch_coords = coordinates[i:batch_end]
            
            # Get log density scores and convert to density values
            log_density = self.kde_model.score_samples(batch_coords)
            batch_density = np.exp(log_density)
            density_values[i:batch_end] = batch_density
        
        # Count hits: crashes in high-density areas (above threshold)
        hits = np.sum(density_values >= threshold)
        
        # Debug information
        print(f"  Density range at crash points: {density_values.min():.6f} to {density_values.max():.6f}")
        print(f"  Threshold for top {top_percentile}%: {threshold:.6f}")
        print(f"  Crashes above threshold: {hits} / {len(coordinates)}")
        
        # Calculate Hit Rate according to formula:
        # Hit Rate = ( # of Crash Accidents within high density areas / Total # of Crash accidents ) x 100%
        hit_rate = (hits / len(sample_data)) * 100.0 if len(sample_data) > 0 else 0.0
        
        print(f"\nHit Rate Results (Formula: Hit Rate = (Crashes in high density / Total crashes) x 100%):")
        print(f"  Total # of Crash accidents: {len(sample_data)}")
        print(f"  # of Crash Accidents within high density areas: {hits}")
        print(f"  Hit Rate: {hit_rate:.2f}%")
        
        # Store results (hit_rate is in percentage form)
        self.metrics_results['hit_rate'] = {
            'value': hit_rate,  # Percentage value
            'value_decimal': hit_rate / 100.0,  # Decimal form (0.0 to 1.0)
            'top_percentile': top_percentile,
            'threshold': float(threshold),
            'crashes_in_high_density': int(hits),
            'total_crashes': len(sample_data),
            'formula': 'Hit Rate = ( # of Crash Accidents within high density areas / Total # of Crash accidents ) x 100%'
        }
        
        return hit_rate
    
    def calculate_silhouette_score(self, max_silhouette_samples=10000):
        """
        Calculate Silhouette Score metric
        
        Silhouette Score measures the quality of clustering by evaluating:
        - Cohesion: How similar points are within their cluster
        - Separation: How different clusters are from each other
        
        Formula (from research):
        s(i) = (b(i) - a(i)) / max{a(i), b(i)}
        
        Where:
        - s(i) = Silhouette score for point i
        - a(i) = Average distance from point i to the points in the same cluster
        - b(i) = Average distance from point i to the points from closest surrounding clusters
        
        Range: -1 to +1
        - +1: Perfect clustering (points are well-separated and cohesive)
        - 0: Overlapping clusters
        - -1: Poor clustering (points may be assigned to wrong clusters)
        
        Source: Firdose, T. (2023, December 8). Understanding the silhouette Score.
        
        Parameters:
        -----------
        max_silhouette_samples : int
            Maximum points to sample for calculation (for performance)
        
        Returns:
        --------
        silhouette_score : float
            Average silhouette score between -1.0 and 1.0 (higher is better)
        """
        print("\n" + "="*60)
        print("CALCULATING SILHOUETTE SCORE")
        print("="*60)
        
        if self.cluster_labels is None:
            print("ERROR: Clustering must be performed first!")
            print("Call perform_clustering() before calculate_silhouette_score()")
            return None
        
        coordinates = self.crash_data[['latitude', 'longitude']].values
        
        # Only consider points that are in clusters (not noise)
        valid_clusters = self.cluster_labels != -1
        
        if valid_clusters.sum() < 2:
            print("ERROR: Need at least 2 clustered points for silhouette score")
            print(f"  Clustered points: {valid_clusters.sum()}")
            return None
        
        cluster_coords = coordinates[valid_clusters]
        cluster_labels = self.cluster_labels[valid_clusters]
        
        # Check if we have multiple clusters
        unique_labels = set(cluster_labels)
        if len(unique_labels) < 2:
            print("WARNING: Only one cluster found. Silhouette score will be 0.0")
            silhouette_avg = 0.0
        else:
            # Sample for silhouette score if too large
            if len(cluster_coords) > max_silhouette_samples:
                print(f"Sampling {max_silhouette_samples} points for silhouette score calculation...")
                sample_indices = np.random.choice(len(cluster_coords), max_silhouette_samples, replace=False)
                cluster_coords_sample = cluster_coords[sample_indices]
                cluster_labels_sample = cluster_labels[sample_indices]
                silhouette_avg = silhouette_score(cluster_coords_sample, cluster_labels_sample)
            else:
                silhouette_avg = silhouette_score(cluster_coords, cluster_labels)
        
        print(f"\nSilhouette Score Results (Formula: s(i) = (b(i) - a(i)) / max{{a(i), b(i)}}):")
        print(f"  Total clustered points: {len(cluster_coords)}")
        print(f"  Number of clusters: {len(unique_labels)}")
        print(f"  Average Silhouette Score: {silhouette_avg:.4f}")
        print(f"  Where:")
        print(f"    - a(i) = Average distance from point i to points in same cluster")
        print(f"    - b(i) = Average distance from point i to closest surrounding cluster")
        
        # Interpretation
        if silhouette_avg > 0.5:
            interpretation = "Excellent clustering"
        elif silhouette_avg > 0.25:
            interpretation = "Good clustering"
        elif silhouette_avg > 0:
            interpretation = "Fair clustering"
        else:
            interpretation = "Poor clustering (may need parameter adjustment)"
        
        print(f"  Interpretation: {interpretation}")
        
        # Store results
        self.metrics_results['silhouette_score'] = {
            'value': float(silhouette_avg),
            'n_clusters': len(unique_labels),
            'n_clustered_points': len(cluster_coords),
            'interpretation': interpretation,
            'formula': 's(i) = (b(i) - a(i)) / max{a(i), b(i)}',
            'formula_components': {
                's(i)': 'Silhouette score for point i',
                'a(i)': 'Average distance from point i to points in same cluster',
                'b(i)': 'Average distance from point i to closest surrounding cluster'
            },
            'source': 'Firdose, T. (2023, December 8). Understanding the silhouette Score'
        }
        
        return silhouette_avg
    
    def calculate_silhouette_score_manual(self, max_samples=5000):
        """
        Manual implementation of Silhouette Score formula
        
        This implements the exact formula from research:
        s(i) = (b(i) - a(i)) / max{a(i), b(i)}
        
        This is provided for verification and educational purposes.
        For production use, sklearn's silhouette_score is recommended (faster).
        
        Parameters:
        -----------
        max_samples : int
            Maximum points to sample for calculation (for performance)
        
        Returns:
        --------
        silhouette_score : float
            Average silhouette score between -1.0 and 1.0
        """
        if self.cluster_labels is None:
            print("ERROR: Clustering must be performed first!")
            return None
        
        from scipy.spatial.distance import euclidean
        
        coordinates = self.crash_data[['latitude', 'longitude']].values
        labels = self.cluster_labels
        
        # Only consider clustered points (not noise)
        valid_mask = labels != -1
        coords = coordinates[valid_mask]
        labels_valid = labels[valid_mask]
        
        if len(coords) < 2:
            return None
        
        # Sample if too large
        if len(coords) > max_samples:
            indices = np.random.choice(len(coords), max_samples, replace=False)
            coords = coords[indices]
            labels_valid = labels_valid[indices]
        
        silhouette_scores = []
        
        print(f"Calculating silhouette score manually for {len(coords)} points...")
        print("  Formula: s(i) = (b(i) - a(i)) / max{a(i), b(i)}")
        
        for i in range(len(coords)):
            point = coords[i]
            cluster_id = labels_valid[i]
            
            # a(i): Average distance to points in same cluster
            same_cluster_points = coords[labels_valid == cluster_id]
            if len(same_cluster_points) > 1:
                distances_same = [euclidean(point, other) for other in same_cluster_points if not np.array_equal(point, other)]
                a_i = np.mean(distances_same) if distances_same else 0
            else:
                a_i = 0
            
            # b(i): Average distance to closest surrounding cluster
            other_clusters = set(labels_valid) - {cluster_id}
            if other_clusters:
                min_avg_distances = []
                for other_cluster_id in other_clusters:
                    other_cluster_points = coords[labels_valid == other_cluster_id]
                    distances_other = [euclidean(point, other) for other in other_cluster_points]
                    min_avg_distances.append(np.mean(distances_other))
                b_i = min(min_avg_distances) if min_avg_distances else 0
            else:
                b_i = 0
            
            # Calculate s(i) = (b(i) - a(i)) / max{a(i), b(i)}
            if max(a_i, b_i) > 0:
                s_i = (b_i - a_i) / max(a_i, b_i)
            else:
                s_i = 0
            
            silhouette_scores.append(s_i)
        
        silhouette_avg = np.mean(silhouette_scores)
        
        print(f"  Manual calculation complete: {silhouette_avg:.4f}")
        return silhouette_avg
    
    def run_full_analysis(self, year_range=(2013, 2023), kde_params=None, cluster_params=None, 
                          hit_rate_params=None, silhouette_params=None, use_crash_reports=True):
        """
        Run complete Phase 3 metrics analysis
        
        This method performs all necessary steps:
        1. Load data from CSVData/crashReports (aggregated damage reports)
        2. Perform KDE analysis (for Hit Rate)
        3. Perform clustering (for Silhouette Score)
        4. Calculate Hit Rate
        5. Calculate Silhouette Score
        
        Parameters:
        -----------
        year_range : tuple or None
            (start_year, end_year) to filter data. Default: (2013, 2023)
            If None, loads all available years
        kde_params : dict or None
            Parameters for KDE analysis (bandwidth, max_kde_points, grid_resolution)
        cluster_params : dict or None
            Parameters for clustering (eps, min_samples, max_points)
        hit_rate_params : dict or None
            Parameters for hit rate (top_percentile, max_sample_points)
        silhouette_params : dict or None
            Parameters for silhouette (max_silhouette_samples)
        use_crash_reports : bool
            If True (default), loads from CSVData/crashReports directory.
            If False, loads from CSVData directory using original method.
        
        Returns:
        --------
        results : dict
            Dictionary containing all metrics and results
        """
        start_time = time.time()
        
        print("\n" + "="*60)
        print("PHASE 3 METRICS ANALYSIS - HIT RATE & SILHOUETTE SCORE")
        print("="*60)
        
        # Default parameters
        if year_range is None:
            print("No year range specified - will load all available years")
        else:
            print(f"Year range: {year_range[0]} to {year_range[1]}")
        
        if kde_params is None:
            kde_params = {'bandwidth': 0.008, 'max_kde_points': 100000, 'grid_resolution': 100}
        if cluster_params is None:
            cluster_params = {'eps': 0.005, 'min_samples': 5, 'max_points': 50000}
        if hit_rate_params is None:
            hit_rate_params = {'top_percentile': 20, 'max_sample_points': 5000}
        if silhouette_params is None:
            silhouette_params = {'max_silhouette_samples': 10000}
        
        # Step 1: Load data
        if use_crash_reports:
            print("\n[STEP 1] Loading crash data from crash reports (CSVData/crashReports)...")
            reports_directory = 'CSVData/crashReports'
            if not os.path.exists(reports_directory):
                print(f"ERROR: Directory '{reports_directory}' not found!")
                return None
            
            if not self.load_crash_reports_from_directory(reports_directory, year_range=year_range):
                return None
        else:
            print("\n[STEP 1] Loading crash data from CSVData directory...")
            directory = 'CSVData'
            if not os.path.exists(directory):
                print(f"ERROR: Directory '{directory}' not found!")
                return None
            
            if not self.load_crash_data_from_directory(directory, year_range=year_range):
                return None
        
        # Step 2: KDE Analysis
        print("\n[STEP 2] Performing KDE analysis...")
        t0 = time.time()
        self.perform_kde_analysis(**kde_params)
        print(f"  Time: {time.time() - t0:.2f} seconds")
        
        # Print density information
        self.print_density_info()
        
        # Step 3: Clustering
        print("\n[STEP 3] Performing clustering...")
        t0 = time.time()
        self.perform_clustering(**cluster_params)
        print(f"  Time: {time.time() - t0:.2f} seconds")
        
        # Step 4: Hit Rate
        print("\n[STEP 4] Calculating Hit Rate...")
        t0 = time.time()
        hit_rate = self.calculate_hit_rate(**hit_rate_params)
        print(f"  Time: {time.time() - t0:.2f} seconds")
        
        # Step 5: Silhouette Score
        print("\n[STEP 5] Calculating Silhouette Score...")
        t0 = time.time()
        silhouette_score = self.calculate_silhouette_score(**silhouette_params)
        print(f"  Time: {time.time() - t0:.2f} seconds")
        
        total_time = time.time() - start_time
        
        # Summary
        print("\n" + "="*60)
        print("PHASE 3 ANALYSIS COMPLETE")
        print("="*60)
        print(f"\nFINAL METRICS:")
        if hit_rate is not None:
            print(f"  Hit Rate: {hit_rate:.2f}%")
            print(f"    Formula: (Crashes in high density / Total crashes) x 100%")
        else:
            print(f"  Hit Rate: N/A")
        
        if silhouette_score is not None:
            print(f"  Silhouette Score: {silhouette_score:.4f}")
            print(f"    Formula: s(i) = (b(i) - a(i)) / max{{a(i), b(i)}}")
        else:
            print(f"  Silhouette Score: N/A")
        print(f"\nTotal execution time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
        print("="*60)
        
        # Generate HTML report
        print("\nGenerating HTML report...")
        self.generate_html_report('phase3_metrics_report.html')
        
        return self.metrics_results
    
    def save_results(self, filename='phase3_metrics_results.json'):
        """Save metrics results to JSON file"""
        if not self.metrics_results:
            print("No results to save. Run analysis first.")
            return False
        
        with open(filename, 'w') as f:
            json.dump(self.metrics_results, f, indent=2)
        
        print(f"\nResults saved to {filename}")
        return True
    
    def generate_html_report(self, filename='phase3_metrics_report.html'):
        """
        Generate an HTML report with Phase 3 metrics results
        
        Parameters:
        -----------
        filename : str
            Output HTML filename (default: 'phase3_metrics_report.html')
        
        Returns:
        --------
        bool
            True if successful, False otherwise
        """
        if not self.metrics_results:
            print("No results to save. Run analysis first.")
            return False
        
        # Get metrics data
        hit_rate_data = self.metrics_results.get('hit_rate', {})
        silhouette_data = self.metrics_results.get('silhouette_score', {})
        
        # Prepare data for display
        hit_rate_value = hit_rate_data.get('value', 0.0)
        # Handle both percentage (0-100) and decimal (0-1) formats
        if hit_rate_value <= 1.0 and hit_rate_data.get('value_decimal') is None:
            # Likely stored as decimal, convert to percentage
            hit_rate_value = hit_rate_value * 100.0
        hit_rate_decimal = hit_rate_data.get('value_decimal', hit_rate_value / 100.0)
        crashes_in_high_density = hit_rate_data.get('crashes_in_high_density', hit_rate_data.get('hits', 0))
        total_crashes = hit_rate_data.get('total_crashes', hit_rate_data.get('total_points', 0))
        top_percentile = hit_rate_data.get('top_percentile', 20)
        
        silhouette_value = silhouette_data.get('value', 0.0)
        n_clusters = silhouette_data.get('n_clusters', 0)
        n_clustered_points = silhouette_data.get('n_clustered_points', 0)
        interpretation = silhouette_data.get('interpretation', 'N/A')
        
        # Get dataset info
        dataset_size = len(self.crash_data) if self.crash_data is not None else 0
        year_range = ""
        if self.crash_data is not None and 'year' in self.crash_data.columns:
            years = sorted(self.crash_data['year'].unique())
            if len(years) > 0:
                year_range = f"{int(years[0])} - {int(years[-1])}"
        
        # Generate HTML
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phase 3 Metrics Analysis Report - Hit Rate & Silhouette Score</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 10px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 1.5em;
            margin-bottom: 5px;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
        }}
        
        .header p {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 15px 20px;
        }}
        
        .dataset-info {{
            background: #f8f9fa;
            padding: 10px 15px;
            border-radius: 6px;
            margin-bottom: 15px;
            border-left: 3px solid #667eea;
        }}
        
        .dataset-info h2 {{
            color: #667eea;
            margin-bottom: 8px;
            font-size: 1.1em;
        }}
        
        .dataset-info table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .dataset-info td {{
            padding: 5px 8px;
            border-bottom: 1px solid #e0e0e0;
            font-size: 0.9em;
        }}
        
        .dataset-info td:first-child {{
            font-weight: bold;
            color: #555;
            width: 40%;
        }}
        
        .metrics-section {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 15px;
        }}
        
        @media (max-width: 768px) {{
            .metrics-section {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .metric-card {{
            background: white;
            border-radius: 6px;
            padding: 12px 15px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            border-top: 3px solid;
        }}
        
        .metric-card.hit-rate {{
            border-top-color: #e74c3c;
        }}
        
        .metric-card.silhouette {{
            border-top-color: #3498db;
        }}
        
        .metric-title {{
            font-size: 1.1em;
            margin-bottom: 8px;
            color: #333;
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            margin: 8px 0;
            text-align: center;
        }}
        
        .metric-card.hit-rate .metric-value {{
            color: #e74c3c;
        }}
        
        .metric-card.silhouette .metric-value {{
            color: #3498db;
        }}
        
        .formula-box {{
            background: #f8f9fa;
            padding: 10px 12px;
            border-radius: 6px;
            margin: 10px 0;
            border-left: 3px solid #667eea;
        }}
        
        .formula-box h3 {{
            color: #667eea;
            margin-bottom: 6px;
            font-size: 0.95em;
        }}
        
        .formula {{
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
            background: white;
            padding: 8px 10px;
            border-radius: 4px;
            margin: 6px 0;
            text-align: center;
            border: 1px solid #e0e0e0;
        }}
        
        .formula-explanation {{
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px solid #e0e0e0;
        }}
        
        .formula-explanation p {{
            margin: 3px 0;
            color: #555;
            font-size: 0.85em;
        }}
        
        .formula-explanation strong {{
            color: #333;
        }}
        
        .details-table {{
            width: 100%;
            margin-top: 10px;
            border-collapse: collapse;
            font-size: 0.85em;
        }}
        
        .details-table th {{
            background: #667eea;
            color: white;
            padding: 6px 8px;
            text-align: left;
        }}
        
        .details-table td {{
            padding: 6px 8px;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .details-table tr:hover {{
            background: #f8f9fa;
        }}
        
        .interpretation {{
            background: #e8f5e9;
            padding: 8px 10px;
            border-radius: 4px;
            margin-top: 10px;
            border-left: 3px solid #4caf50;
            font-size: 0.85em;
        }}
        
        .interpretation strong {{
            color: #2e7d32;
        }}
        
        .footer {{
            background: #2c3e50;
            color: white;
            padding: 10px;
            text-align: center;
            font-size: 0.8em;
        }}
        
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.75em;
            font-weight: bold;
            margin-left: 5px;
        }}
        
        .badge.excellent {{
            background: #4caf50;
            color: white;
        }}
        
        .badge.good {{
            background: #8bc34a;
            color: white;
        }}
        
        .badge.fair {{
            background: #ffc107;
            color: #333;
        }}
        
        .badge.poor {{
            background: #f44336;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Phase 3 Metrics Analysis Report</h1>
            <p>Hit Rate & Silhouette Score Evaluation</p>
        </div>
        
        <div class="content">
            <div class="dataset-info">
                <h2>📋 Dataset Information</h2>
                <table>
                    <tr>
                        <td>Total Crash Records</td>
                        <td>{dataset_size:,}</td>
                    </tr>
                    <tr>
                        <td>Year Range</td>
                        <td>{year_range if year_range else 'N/A'}</td>
                    </tr>
                    <tr>
                        <td>Analysis Date</td>
                        <td>{time.strftime('%Y-%m-%d %H:%M:%S')}</td>
                    </tr>
                </table>
            </div>
            
            <div class="metrics-section">
                <!-- Hit Rate Card -->
                <div class="metric-card hit-rate">
                    <div class="metric-title">
                        🎯 Hit Rate (Capture Rate)
                    </div>
                    <div class="metric-value">{hit_rate_value:.2f}%</div>
                    
                    <div class="formula-box">
                        <h3>Formula</h3>
                        <div class="formula">
                            Hit Rate = ( # of Crash Accidents within high density areas / Total # of Crash accidents ) × 100%
                        </div>
                        <div class="formula-explanation">
                            <p><strong>Where:</strong></p>
                            <p>• High density areas = Top {top_percentile}% of the KDE density grid</p>
                            <p>• Total # of Crash accidents = All crash points in the dataset</p>
                        </div>
                    </div>
                    
                    <table class="details-table">
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                        </tr>
                        <tr>
                            <td>Total # of Crash accidents</td>
                            <td>{total_crashes:,}</td>
                        </tr>
                        <tr>
                            <td># of Crash Accidents within high density areas</td>
                            <td>{crashes_in_high_density:,}</td>
                        </tr>
                        <tr>
                            <td>Hit Rate (Percentage)</td>
                            <td><strong>{hit_rate_value:.2f}%</strong></td>
                        </tr>
                        <tr>
                            <td>Hit Rate (Decimal)</td>
                            <td>{hit_rate_decimal:.4f}</td>
                        </tr>
                        <tr>
                            <td>Top Percentile Used</td>
                            <td>{top_percentile}%</td>
                        </tr>
                    </table>
                </div>
                
                <!-- Silhouette Score Card -->
                <div class="metric-card silhouette">
                    <div class="metric-title">
                        📈 Silhouette Score
                    </div>
                    <div class="metric-value">{silhouette_value:.4f}</div>
                    
                    <div class="formula-box">
                        <h3>Formula</h3>
                        <div class="formula">
                            s(i) = (b(i) - a(i)) / max{{a(i), b(i)}}
                        </div>
                        <div class="formula-explanation">
                            <p><strong>Where:</strong></p>
                            <p>• <strong>s(i)</strong> = Silhouette score for point i</p>
                            <p>• <strong>a(i)</strong> = Average distance from point i to the points in the same cluster</p>
                            <p>• <strong>b(i)</strong> = Average distance from point i to the points from closest surrounding clusters</p>
                            <p style="margin-top: 10px; font-size: 0.9em; color: #777;">
                                <em>Source: Firdose, T. (2023, December 8). Understanding the silhouette Score.</em>
                            </p>
                        </div>
                    </div>
                    
                    <table class="details-table">
                        <tr>
                            <th>Metric</th>
                            <th>Value</th>
                        </tr>
                        <tr>
                            <td>Average Silhouette Score</td>
                            <td><strong>{silhouette_value:.4f}</strong></td>
                        </tr>
                        <tr>
                            <td>Number of Clusters</td>
                            <td>{n_clusters}</td>
                        </tr>
                        <tr>
                            <td>Clustered Points</td>
                            <td>{n_clustered_points:,}</td>
                        </tr>
                        <tr>
                            <td>Score Range</td>
                            <td>-1.0 to +1.0</td>
                        </tr>
                    </table>
                    
                    <div class="interpretation">
                        <strong>Interpretation:</strong> {interpretation}
                        <span class="badge {'excellent' if silhouette_value > 0.5 else 'good' if silhouette_value > 0.25 else 'fair' if silhouette_value > 0 else 'poor'}">
                            {'Excellent' if silhouette_value > 0.5 else 'Good' if silhouette_value > 0.25 else 'Fair' if silhouette_value > 0 else 'Poor'}
                        </span>
                    </div>
                </div>
            </div>
            
            <!-- Summary Section -->
            <div class="formula-box" style="margin-top: 10px;">
                <h3>📊 Summary</h3>
                <p style="margin: 6px 0; line-height: 1.4; color: #555; font-size: 0.85em;">
                    This analysis evaluated the performance of the crash hotspot identification model using two key metrics:
                </p>
                <ul style="margin: 6px 0; padding-left: 20px; line-height: 1.5; color: #555; font-size: 0.85em;">
                    <li><strong>Hit Rate ({hit_rate_value:.2f}%):</strong> Measures how effectively the density model identifies high-risk areas. 
                    A higher hit rate indicates that more crashes occur in the predicted high-density regions.</li>
                    <li><strong>Silhouette Score ({silhouette_value:.4f}):</strong> Measures the quality of clustering by evaluating both 
                    cohesion (how similar points are within clusters) and separation (how distinct clusters are from each other). 
                    The score of {silhouette_value:.4f} indicates <strong>{interpretation.lower()}</strong> clustering quality.</li>
                </ul>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by Phase 3 Metrics Analysis Tool | EDSA Crash Analysis System</p>
            <p style="margin-top: 3px; font-size: 0.75em; opacity: 0.8;">© {time.strftime('%Y')} Research Project</p>
        </div>
    </div>
</body>
</html>"""
        
        # Write HTML file
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"\n✓ HTML report saved to {filename}")
            print(f"  Open {filename} in your browser to view the report")
            return True
        except Exception as e:
            print(f"\n✗ Error saving HTML report: {str(e)}")
            return False


def main():
    """Main function for Phase 3 metrics analysis"""
    
    print("\n" + "="*60)
    print("PHASE 3 METRICS ANALYSIS")
    print("Hit Rate & Silhouette Score Calculator")
    print("="*60)
    
    analyzer = Phase3MetricsAnalyzer()
    
    # Run analysis with default parameters
    # You can customize parameters here:
    results = analyzer.run_full_analysis(
        year_range=(2013, 2023),  # Analyze all years from 2013 to 2023
        # kde_params={'bandwidth': 0.008, 'max_kde_points': 100000, 'grid_resolution': 100},
        # cluster_params={'eps': 0.005, 'min_samples': 5, 'max_points': 50000},
        # hit_rate_params={'top_percentile': 20, 'max_sample_points': 5000},
        # silhouette_params={'max_silhouette_samples': 10000}
    )
    
    if results:
        # Save results to JSON file
        analyzer.save_results('phase3_metrics_results.json')
        
        # HTML report is already generated by run_full_analysis()
        print("\n✓ Analysis complete!")
        print("  Generated files:")
        print("    - phase3_metrics_results.json (JSON data)")
        print("    - phase3_metrics_report.html (HTML report)")
        return analyzer, results
    else:
        print("\n✗ Analysis failed!")
        return None, None


if __name__ == "__main__":
    analyzer, results = main()

