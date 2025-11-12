"""
Quick script to create heatmap visualization like the reference image
Just run: python create_heatmap_visualization.py
"""

from bsit import EDSACrashAnalyzer
import os

def create_enhanced_heatmap():
    """Create a clean heatmap visualization similar to the reference image"""
    
    print("="*70)
    print(" EDSA Crash Heatmap Generator ".center(70))
    print("="*70)
    
    # Check if CSVData directory exists
    if not os.path.exists('CSVData'):
        print("\n❌ Error: CSVData directory not found!")
        print("Please ensure the CSVData folder with crash data exists.")
        return
    
    # Initialize analyzer
    analyzer = EDSACrashAnalyzer()
    
    # Get available years from directory
    print("\n📂 Scanning CSVData directory for available years...")
    available_years = analyzer.get_available_years_from_directory('CSVData')
    
    if not available_years:
        print("\n❌ No CSV files with year information found!")
        return
    
    print(f"✅ Found data for years: {', '.join(map(str, available_years))}")
    print(f"   Range: {min(available_years)} to {max(available_years)}")
    
    # Ask user for year range
    print("\n" + "="*70)
    print(" SELECT YEAR RANGE FOR ANALYSIS ".center(70))
    print("="*70)
    print("\n💡 Tips:")
    print("   - Recent years (2020-2023): Fast, ~30 seconds")
    print("   - All years (2013-2023): Slower, ~2-3 minutes")
    print("   - Press Enter to use all available years")
    
    start_year_input = input(f"\n📅 Start year [{min(available_years)}-{max(available_years)}] (default: {min(available_years)}): ").strip()
    end_year_input = input(f"📅 End year [{min(available_years)}-{max(available_years)}] (default: {max(available_years)}): ").strip()
    
    # Parse user input
    try:
        start_year = int(start_year_input) if start_year_input else min(available_years)
        end_year = int(end_year_input) if end_year_input else max(available_years)
        
        # Validate range
        if start_year < min(available_years) or end_year > max(available_years):
            print(f"\n⚠️  Year range outside available data. Using full range: {min(available_years)}-{max(available_years)}")
            start_year, end_year = min(available_years), max(available_years)
        elif start_year > end_year:
            print("\n⚠️  Start year > End year. Swapping them.")
            start_year, end_year = end_year, start_year
        
        year_range = (start_year, end_year)
        print(f"\n✅ Selected year range: {start_year} to {end_year}")
        
    except ValueError:
        print(f"\n⚠️  Invalid input. Using all years: {min(available_years)}-{max(available_years)}")
        year_range = (min(available_years), max(available_years))
    
    print("\n📂 Loading crash data from CSVData directory...")
    
    # Load CSV files with year filter
    if not analyzer.load_crash_data_from_directory('CSVData', year_range=year_range):
        print("\n❌ Failed to load crash data!")
        return
    
    print(f"✅ Loaded {len(analyzer.crash_data)} crash records")
    
    # Show year distribution
    if 'year' in analyzer.crash_data.columns:
        print("\n📊 Data distribution by year:")
        year_counts = analyzer.crash_data['year'].value_counts().sort_index()
        for year, count in year_counts.items():
            print(f"   {int(year)}: {count} crashes")
    
    # Preprocess data
    print("\n🔄 Preprocessing data...")
    analyzer.preprocess_data()
    
    # Perform KDE analysis
    print("🔍 Performing Kernel Density Estimation...")
    analyzer.perform_kde_analysis(bandwidth=0.010)  # Smooth heatmap
    
    # Identify hotspots
    print("🎯 Identifying crash hotspots...")
    analyzer.identify_hotspots(threshold_percentile=85)
    
    if analyzer.hotspots is not None and len(analyzer.hotspots) > 0:
        print(f"✅ Found {len(analyzer.hotspots)} hotspot(s)")
        print("\nTop hotspot locations:")
        top_hotspots = analyzer.hotspots.nlargest(min(3, len(analyzer.hotspots)), 'crash_count')
        for i, (_, hotspot) in enumerate(top_hotspots.iterrows(), 1):
            print(f"   {i}. ({hotspot['latitude']:.4f}, {hotspot['longitude']:.4f}) - {hotspot['crash_count']} crashes")
    
    # Evaluate performance
    print("\n📈 Evaluating model performance...")
    metrics = analyzer.evaluate_model_performance()
    
    # Create the enhanced heatmap visualization
    print("\n🗺️  Creating interactive heatmap...")
    print("   Style: Clean heatmap-only view (like reference image)")
    
    # Create heatmap-only version (clean view like reference image)
    analyzer.create_interactive_map(
        save_path='edsa_heatmap_visualization.html',
        style='heatmap_only'
    )
    
    # Also create detailed version for comparison
    analyzer.create_interactive_map(
        save_path='edsa_detailed_visualization.html',
        style='detailed'
    )
    
    print("\n" + "="*70)
    print(" ✅ SUCCESS! ".center(70))
    print("="*70)
    print("\n📁 Generated files:")
    print("   1. edsa_heatmap_visualization.html    (Clean heatmap - like reference)")
    print("   2. edsa_detailed_visualization.html   (Detailed map with markers)")
    print("\n💡 How to view:")
    print("   - Double-click the HTML file to open in your browser")
    print("   - Or drag and drop into a browser window")
    print("\n🎨 Features:")
    print("   - Blue → Cyan → Green → Yellow → Orange → Red gradient")
    print("   - Warning triangle markers for hotspots")
    print("   - Layer controls (top right)")
    print("   - Zoom and pan to explore")
    print("   - Click hotspot markers for details")
    print("\n" + "="*70)
    
    return analyzer, metrics

if __name__ == "__main__":
    try:
        analyzer, metrics = create_enhanced_heatmap()
        
        if analyzer and metrics:
            print("\n📊 Quick Statistics:")
            print(f"   Total crashes analyzed: {metrics['total_crashes']}")
            print(f"   Number of clusters: {metrics['n_clusters']}")
            print(f"   Hit rate: {metrics['hit_rate']:.2%}")
            
            # Ask if user wants to see static plots too
            print("\n" + "="*70)
            show_plots = input("\n📊 Generate static plots too? (y/n): ").lower().strip()
            if show_plots in ['y', 'yes']:
                print("\n🎨 Creating static visualizations...")
                analyzer.create_visualizations()
                print("✅ Static plots displayed!")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user.")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        print("\nPlease check:")
        print("  1. CSVData directory exists")
        print("  2. CSV files are properly formatted")
        print("  3. Required packages are installed")

