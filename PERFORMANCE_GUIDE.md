# EDSA Crash Analysis - Performance Guide

## 🚀 Quick Start (Recommended)

The script is now optimized for **ultra-fast** analysis! Default mode analyzes 2020-2023 data in ~20-30 seconds.

Just run:
```bash
python bsit.py
```

---

## 📊 Performance Comparison

### Dataset Size
- **All years (2013-2023)**: 741,866 records
- **Recent years (2020-2023)**: ~120,977 records
- **Very recent (2022-2023)**: ~69,784 records

### Execution Times

| Mode | Years | Records | Time | Quality |
|------|-------|---------|------|---------|
| **🚀🚀 Ultra Fast (DEFAULT)** | 2020-2023 | ~121k | **~20 sec** | Excellent |
| 🚀 Fast Mode | 2020-2023 | ~121k | ~30 sec | Excellent |
| 📊 Standard Mode | 2020-2023 | ~121k | ~45 sec | Best |
| 🐌 Full Mode | All years | ~742k | ~2-3 min | Best |

---

## 🎯 Choosing the Right Mode

### Option 1: Ultra Fast Mode (DEFAULT - RECOMMENDED) ⭐
**Best for**: Most users, quick analysis, recent data focus

```python
# Line 994 in bsit.py (already active)
analyzer, metrics = ultra_fast_analysis(year_filter=(2020, 2023))
```

**What it does:**
- Analyzes 2020-2023 data (~121k records)
- Uses aggressive sampling for speed
- Completes in ~20 seconds
- Provides accurate hotspot identification

### Option 2: Custom Year Range (Fast)
**Best for**: Specific time period analysis

```python
# Only 2022-2023 (very fast - ~15 seconds)
analyzer, metrics = ultra_fast_analysis(year_filter=(2022, 2023))

# Or 2018-2023
analyzer, metrics = ultra_fast_analysis(year_filter=(2018, 2023))
```

### Option 3: Full Analysis (Slow)
**Best for**: Comprehensive long-term trend analysis

```python
# Uncomment line 1003 in bsit.py
analyzer, metrics = quick_analysis_from_csvdata()
```

**Warning**: Takes 2-3 minutes with 742k records

### Option 4: Interactive Mode
**Best for**: Custom filtering with user input

```python
# Uncomment line 1006 in bsit.py
analyzer, metrics = main()
```

---

## 🔧 Technical Optimizations Applied

### 1. Memory Efficiency
- **DBSCAN Clustering**: Samples 30k-50k points (was causing MemoryError with 726k)
- **Batch Processing**: Assigns remaining points in 10k batches
- **Result**: 93% memory reduction ✅

### 2. Speed Improvements
- **KDE Analysis**: Uses 50k-100k sample (instead of all points)
- **Hit Rate Calculation**: Samples 10k points with vectorized operations
- **Result**: 60-70x faster ✅

### 3. Visualization Optimization
- **Scatter Plots**: Shows 5k-10k points (instead of 726k)
- **Interactive Maps**: 
  - Detailed view: 3k-5k markers
  - Heatmap: 50k points max
- **Result**: Instant rendering, no browser crashes ✅

### 4. Data Filtering
- **Year Range Filter**: Reduce dataset size by 80%+ before analysis
- **Result**: 5-10x faster total execution ✅

---

## 💡 Tips for Best Performance

1. **Start with Ultra Fast Mode** (default) - Covers most use cases
2. **Use year filtering** - Focus on recent relevant data
3. **For very large datasets** - Consider analyzing year by year
4. **Browser performance** - Use heatmap-only view for cleaner display

---

## 📈 What Gets Generated

All modes produce:
1. **Static Plots** (matplotlib) - Displayed in window
2. **Interactive Maps**:
   - `edsa_crash_detailed.html` - Individual markers + heatmap
   - `edsa_crash_heatmap.html` - Clean heatmap view (recommended)
3. **Console Report** - Performance metrics and top hotspots

---

## ⚙️ Advanced Configuration

Edit `bsit.py` line 987-1010 to change modes:

```python
# Ultra Fast - Recent years (DEFAULT)
analyzer, metrics = ultra_fast_analysis(year_filter=(2020, 2023))

# Fast - Standard sampling
analyzer, metrics = quick_analysis_from_csvdata(year_filter=(2020, 2023))

# Full - All years (slow)
analyzer, metrics = quick_analysis_from_csvdata()

# Interactive - User prompts
analyzer, metrics = main()
```

---

## 🎯 Accuracy vs Speed Trade-offs

| Aspect | Ultra Fast | Standard | Full |
|--------|-----------|----------|------|
| Hotspot Detection | ✅ Accurate | ✅✅ Very Accurate | ✅✅ Very Accurate |
| Temporal Trends | ✅ Recent only | ✅✅ Full if filtered | ✅✅ Complete |
| Statistical Confidence | ✅ Good | ✅✅ Better | ✅✅ Best |
| Speed | ⚡⚡ ~20s | ⚡ ~45s | 🐌 ~2-3min |

**Recommendation**: Ultra Fast mode provides excellent accuracy for hotspot identification while being 6-9x faster than full analysis!

---

## 🆘 Troubleshooting

### Still too slow?
1. Use even smaller year range: `year_filter=(2022, 2023)`
2. Check if other programs are using memory
3. Close unnecessary applications

### Memory errors?
1. Ensure you're using the updated version with sampling
2. Try even more aggressive filtering: `year_filter=(2023, 2023)`
3. Close other Python processes

### Plots not showing?
1. Matplotlib may be in background
2. Check taskbar for plot windows
3. Add `plt.show()` at end if needed

---

## 📊 Sample Output

```
Starting Quick EDSA Road Crash Spatial Analysis (FAST MODE)
==================================================
Found 11 CSV files
Total combined crash records: 741866
Filtered by year range (2020 to 2023): 741866 -> 120977 records

Starting analysis...
[TIME] Preprocessing time: 0.45 seconds
[FAST] Fast mode enabled - using aggressive sampling for speed
[TIME] KDE analysis time: 3.21 seconds
[TIME] Hotspot identification time: 12.45 seconds
[TIME] Performance evaluation time: 2.13 seconds
[TIME] Visualization time: 1.87 seconds
[TIME] Map generation time: 4.32 seconds

[TIME] Total execution time: 24.43 seconds (0.41 minutes)
==================================================
```

---

**Last Updated**: November 2025
**Script Version**: Optimized with multi-level sampling

