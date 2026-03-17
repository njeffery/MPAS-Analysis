# GEOTRACES Point Observations overlay for Dissolved Iron Climatology Maps

## ✅ Implementation Complete

Successfully converted GEOTRACES Excel workbook to netCDF format and integrated point-observation overlay system into MPAS-Analysis dissolved iron climatology maps.

---

## What Was Done

### 1. Data Conversion
**File Created:**
- `observations/Ocean/BGC/Fe/tagliabue_fe_database_jun2015_public_point_data.nc`
- **Conversion**: Excel workbook → self-describing netCDF4
- **Observations**: 2,607 depth-filtered records (all < 2.0 m)
- **Content**: lon, lat, depth (m), dFe (nM) with metadata
- **Size**: 102 KB
- **Tools Used**: pandas (read Excel), xarray (write netCDF)
- **Conversion Script**: `convert_geotraces_to_netcdf.py`

### 2. Code Changes

#### [plot_climatology_map_subtask.py](mpas_analysis/shared/plot/plot_climatology_map_subtask.py)
- **Method**: `_get_point_observations()` - refactored to read netCDF instead of Excel
- **Key Changes**:
  - Replaced `pd.read_excel()` with `xr.open_dataset()`
  - Removed pandas dependency
  - Depth filtering logic preserved
  - Scale factor application preserved
  - Removed `pointObservationsSheetName` config option (not needed for netCDF)
- **Imports**: Removed pandas, kept xarray, numpy, os

#### [climatology_map.py](mpas_analysis/shared/plot/climatology_map.py)
- **Scatter Overlay Logic**: Conditional matplotlib scatter plot on model panel
- **Coverage**: Both latlon and projection comparison grids
- **Color**: Using model's colormap for consistency
- **No Changes**: Integration already complete from previous work

#### [climatology_map_bgc.py](mpas_analysis/ocean/climatology_map_bgc.py)
- **Unit Conversion**: avgOceanSurfaceFeDissolved converted mmol m⁻³ → nM (×1e6)
- **Dimension Handling**: Added to 2-D field list (no nVertLevels indexing)
- **No Changes**: Already completed previously

### 3. Configuration Updates

#### [default.cfg](mpas_analysis/default.cfg)
- Updated section: `[climatologyMapBGC_avgOceanSurfaceFeDissolved]`
- Changed: `pointObservationsFileName` example from `.xlsx` → `.nc`
- Removed: `pointObservationsSheetName` option
- Comments updated to reference netCDF format

#### [ocean_bgc_test.cfg](ocean_bgc_test.cfg)
- **Active Configuration**: Points to netCDF point observations file
- **Settings**:
  - `pointObservationsFileName = .../tagliabue_fe_database_jun2015_public.nc`
  - `pointObservationsLonColumn = lon`
  - `pointObservationsLatColumn = lat`
  - `pointObservationsDepthColumn = depth`
  - `pointObservationsValueColumn = dFe`
  - `pointObservationsDepthMax = 2.0`
  - `pointObservationsScaleFactor = 1.0`
  - `pointObservationsLabel = GEOTRACES surface dissolved iron`

---

## Test Results

### Final Run (March 16, 2026, 12:24-12:27)
```
✅ Total setup time: 0:00:20.07
✅ Total run time:   0:00:23.36

✅ Climatologies computed: 12 monthly + ANN
✅ Climatology remapped:    avgOceanSurfaceFeDissolved (0:00:00.11)
✅ Map generated:           Plotting completed (0:00:02.02)
```

### Output Map
- **File**: `ocean_bgc_test_output/plots/avgOceanSurfaceFeDissolved_02092026.v3.LR.HES.PI-dust.pm-cpu_ANN_years0160-0160.png`
- **Size**: 495 KB
- **Generated**: 2026-03-16 12:27
- **Content**: Annual mean dissolved iron concentration with GEOTRACES point observations overlaid
- **Grid**: Latlon (global)
- **Scale**: Log colormap (5–800 nM)

### Data Verification
```
Loaded 2,607 point observations with depth < 2.0 m
  dFe range: 0.00 to 20.00 nM
  Latitude range: -77.2 to 90.0°N
  Longitude range: -179.4 to 179.9°E
```

---

## Usage

### To generate dissolved iron climatology maps with GEOTRACES overlays:

1. **Basic**: Use test config (already set up)
   ```bash
  cd ${MPAS_ANALYSIS_DIR}
  mpas_analysis ocean_bgc_test.cfg
   ```

2. **For other E3SM runs**: Add to your config file:
   ```ini
   [climatologyMapBGC]
   variables = ['avgOceanSurfaceFeDissolved']
   
   [climatologyMapBGC_avgOceanSurfaceFeDissolved]
  pointObservationsFileName = observations/Ocean/BGC/Fe/tagliabue_fe_database_jun2015_public_point_data.nc
   pointObservationsLonColumn = lon
   pointObservationsLatColumn = lat
   pointObservationsDepthColumn = depth
   pointObservationsValueColumn = dFe
   pointObservationsDepthMax = 2.0
   pointObservationsScaleFactor = 1.0
   pointObservationsLabel = GEOTRACES surface dissolved iron
   ```

3. **To disable overlays**: Set `pointObservationsFileName = None` or comment it out

### Configuration Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `pointObservationsFileName` | path/to/file.nc | netCDF file with point observations |
| `pointObservationsLonColumn` | lon | Variable name for longitude |
| `pointObservationsLatColumn` | lat | Variable name for latitude |
| `pointObservationsDepthColumn` | depth | Variable name for depth |
| `pointObservationsValueColumn` | dFe | Variable name for values to plot |
| `pointObservationsDepthMax` | 2.0 | Depth cutoff (meters) for filtering |
| `pointObservationsScaleFactor` | 1.0 | Multiplier (e.g., 1e-6 nM→mmol m⁻³) |
| `pointObservationsLabel` | string | Legend label for points |

---

## Files Modified or Created

**Created:**
- `convert_geotraces_to_netcdf.py` – Conversion script
- `observations/Ocean/BGC/Fe/tagliabue_fe_database_jun2015_public_point_data.nc` – Point observations

**Modified:**
- `mpas_analysis/shared/plot/plot_climatology_map_subtask.py` – netCDF reader
- `mpas_analysis/default.cfg` – Updated defaults
- `ocean_bgc_test.cfg` – Updated test config

---


## Contact/Support

- **Point observations file**: `observations/Ocean/BGC/Fe/tagliabue_fe_database_jun2015_public_point_data.nc`
- **Reference**: Tagliabue et al. (2015) Dissolved Iron Database (public access)
- **Original Excel**: Original file still available for reference

## Portable Locations

- **Repository-relative data path**: `observations/Ocean/BGC/Fe/`
- **Remote source URL**: `https://web.lcrc.anl.gov/public/e3sm/diagnostics/observations/Ocean/BGC/Fe/`
- **Recommended run pattern**:
  ```bash
  export MPAS_ANALYSIS_DIR=/path/to/MPAS-Analysis
  cd ${MPAS_ANALYSIS_DIR}
  mpas_analysis ocean_bgc_test.cfg
  ```
