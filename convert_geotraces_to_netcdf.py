#!/usr/bin/env python
"""Convert GEOTRACES Excel workbook to netCDF format."""

import pandas as pd
import xarray as xr
import numpy as np

# Read Excel file
excel_file = '/Users/njeffery/Documents/DATA/GEOTRACES/OceanDissolvedIron/tagliabue_fe_database_jun2015_public.xlsx'
sheet_name = 'Dissolved Iron'

print(f"Reading {excel_file}...")
# Headers are in row 4 (skiprows=3 to skip first 3 rows)
df = pd.read_excel(excel_file, sheet_name=sheet_name, skiprows=3)

# Extract columns - note the exact column names from the file
lon = df['long (degE)'].values
lat = df['Lat (degN)'].values
depth = df['depth'].values
dfe = df['dFe (nM)'].values

# Filter to depth < 2 m
mask = depth < 2.0
lon = lon[mask]
lat = lat[mask]
depth = depth[mask]
dfe = dfe[mask]

print(f"Total observations: {len(dfe)}")
print(f"Observations with depth < 2 m: {len(dfe)}")
print(f"dFe range: {np.nanmin(dfe):.2f} to {np.nanmax(dfe):.2f} nM")

# Create xarray Dataset
nobs = len(dfe)
ds = xr.Dataset(
    data_vars={
        'dFe': (['nobs'], dfe),
    },
    coords={
        'lon': (['nobs'], lon),
        'lat': (['nobs'], lat),
        'depth': (['nobs'], depth),
        'nobs': np.arange(nobs),
    },
)

# Add metadata
ds['dFe'].attrs['long_name'] = 'Dissolved Iron'
ds['dFe'].attrs['units'] = 'nM'
ds['lon'].attrs['long_name'] = 'Longitude'
ds['lon'].attrs['units'] = 'degrees_east'
ds['lat'].attrs['long_name'] = 'Latitude'
ds['lat'].attrs['units'] = 'degrees_north'
ds['depth'].attrs['long_name'] = 'Depth'
ds['depth'].attrs['units'] = 'm'

ds.attrs['source'] = 'GEOTRACES Database'
ds.attrs['dataset'] = 'Tagliabue et al. (2015) Dissolved Iron'
ds.attrs['depth_filter'] = 'depth < 2.0 m'

# Write to netCDF
output_file = '/Users/njeffery/Documents/DATA/GEOTRACES/OceanDissolvedIron/tagliabue_fe_database_jun2015_public.nc'
print(f"\nWriting to {output_file}...")
ds.to_netcdf(output_file, encoding={'dFe': {'dtype': 'float32'}})

print("Conversion complete!")
print(f"\nDataset preview:")
print(ds)
