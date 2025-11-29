"""
Example: How to Query and Understand Density of Areas

This script demonstrates how to:
1. Calculate density using KDE analysis
2. Query density at specific locations
3. Identify high-density areas
4. Get density statistics

Run this after running phase3_metrics_analysis.py
"""

from phase3_metrics_analysis import Phase3MetricsAnalyzer

def main():
    print("="*70)
    print(" DENSITY QUERY EXAMPLE ".center(70))
    print("="*70)
    
    # Initialize analyzer
    analyzer = Phase3MetricsAnalyzer()
    
    # Load crash reports
    print("\n[1] Loading crash data...")
    if not analyzer.load_crash_reports_from_directory(
        'CSVData/crashReports', 
        year_range=(2013, 2024)
    ):
        print("Failed to load data!")
        return
    
    # Perform KDE analysis to calculate density
    print("\n[2] Calculating density using KDE...")
    analyzer.perform_kde_analysis(bandwidth=0.008, grid_resolution=100)
    
    # Print comprehensive density information
    print("\n[3] Density Information:")
    analyzer.print_density_info()
    
    # Example: Query density at specific Metro Manila locations
    print("\n" + "="*70)
    print(" EXAMPLE: Querying Density at Specific Locations ".center(70))
    print("="*70)
    
    # Sample locations (Metro Manila cities)
    locations = {
        'Quezon City': (14.6760, 121.0437),
        'Makati': (14.5547, 121.0244),
        'Manila': (14.5995, 120.9842),
        'Pasig': (14.5755, 121.0855),
        'Taguig': (14.5176, 121.0509),
    }
    
    print("\n📍 Density values at various Metro Manila locations:\n")
    for city_name, (lat, lon) in locations.items():
        density = analyzer.get_density_at_location(lat, lon)
        is_high = analyzer.is_high_density_area(lat, lon, percentile=80)
        status = "🔴 HIGH DENSITY" if is_high else "🟢 Normal"
        
        print(f"  {city_name:15s} (lat: {lat:.4f}, lon: {lon:.4f})")
        print(f"    Density: {density:.6f}  {status}")
        print()
    
    # Get density thresholds
    print("\n" + "="*70)
    print(" Density Thresholds for High-Risk Areas ".center(70))
    print("="*70)
    
    percentiles = [75, 80, 85, 90, 95, 99]
    print("\n  Percentile | Threshold Value | Top % of Area")
    print("  " + "-" * 52)
    
    for pct in percentiles:
        threshold = analyzer.get_density_percentile(pct)
        top_pct = 100 - pct
        print(f"     {pct:3d}th    |  {threshold:12.6f}  |  Top {top_pct:2d}%")
    
    # Find which locations are high-density
    print("\n" + "="*70)
    print(" High-Density Area Identification ".center(70))
    print("="*70)
    
    high_density_locations = []
    for city_name, (lat, lon) in locations.items():
        is_high_90 = analyzer.is_high_density_area(lat, lon, percentile=90)
        is_high_80 = analyzer.is_high_density_area(lat, lon, percentile=80)
        
        if is_high_90:
            high_density_locations.append((city_name, "Top 10%"))
        elif is_high_80:
            high_density_locations.append((city_name, "Top 20%"))
    
    if high_density_locations:
        print("\n  🔴 High-Density Locations (Crash Hotspots):")
        for city, level in high_density_locations:
            print(f"    • {city} - {level} of area")
    else:
        print("\n  ⚠ No locations in top 20% density range")
    
    # Get density statistics
    print("\n" + "="*70)
    print(" Detailed Density Statistics ".center(70))
    print("="*70)
    
    stats = analyzer.get_density_statistics()
    if stats:
        print(f"\n  Minimum Density:  {stats['min']:.6f}")
        print(f"  Maximum Density:  {stats['max']:.6f}")
        print(f"  Mean Density:     {stats['mean']:.6f}")
        print(f"  Median Density:   {stats['median']:.6f}")
        print(f"  Standard Dev:     {stats['std']:.6f}")
        
        print("\n  Interpretation (using available percentiles):")
        if '90th' in stats['percentiles']:
            print(f"    • Areas with density > {stats['percentiles']['90th']:.6f} are in top 10%")
        if '80th' in stats['percentiles']:
            print(f"    • Areas with density > {stats['percentiles']['80th']:.6f} are in top 20%")
        if '75th' in stats['percentiles']:
            print(f"    • Areas with density > {stats['percentiles']['75th']:.6f} are in top 25%")
        
        # Use get_density_percentile for any percentile - this method is more flexible
        print(f"\n  Alternative: Use get_density_percentile() for any percentile value:")
        for pct in [75, 80, 85, 90]:
            threshold = analyzer.get_density_percentile(pct)
            top_pct = 100 - pct
            print(f"    • Top {top_pct}% threshold ({pct}th percentile): {threshold:.6f}")
    
    print("\n" + "="*70)
    print(" ✓ Density Analysis Complete! ".center(70))
    print("="*70)
    print("\n💡 Tips:")
    print("   • Higher density = More crash activity in that area")
    print("   • Top 20% of density areas are typically considered 'high-risk'")
    print("   • Use density values to prioritize safety interventions")
    print("   • Density is relative - compare values across locations")
    print()


if __name__ == "__main__":
    main()

