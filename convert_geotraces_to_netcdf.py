#!/usr/bin/env python
"""Convert the GEOTRACES dissolved iron workbook to netCDF."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
from urllib.request import urlretrieve

import numpy as np
import pandas as pd
import xarray as xr


DEFAULT_BASE_URL = (
    'https://web.lcrc.anl.gov/public/e3sm/diagnostics/observations/Ocean/BGC/Fe'
)
DEFAULT_EXCEL_NAME = 'tagliabue_fe_database_jun2015_public.xlsx'
DEFAULT_OUTPUT_NAME = 'tagliabue_fe_database_jun2015_public_point_data.nc'


def _default_fe_dir() -> Path:
    return Path(__file__).resolve().parent / 'observations' / 'Ocean' / 'BGC' / 'Fe'


def _ensure_excel_file(excel_file: Path, base_url: str) -> None:
    if excel_file.exists():
        return

    excel_file.parent.mkdir(parents=True, exist_ok=True)
    remote_url = f'{base_url.rstrip("/")}/{excel_file.name}'
    print(f'Local Excel file not found: {excel_file}')
    print(f'Downloading from {remote_url} ...')
    try:
        urlretrieve(remote_url, excel_file)
        return
    except Exception as error:
        print(f'urllib download failed ({error}). Trying curl fallback...')

    subprocess.run(
        ['curl', '-L', '--fail', '--output', str(excel_file), remote_url],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--excel-file',
        type=Path,
        default=_default_fe_dir() / DEFAULT_EXCEL_NAME,
        help='Path to the GEOTRACES Excel workbook.'
    )
    parser.add_argument(
        '--output-file',
        type=Path,
        default=_default_fe_dir() / DEFAULT_OUTPUT_NAME,
        help='Path to output netCDF file.'
    )
    parser.add_argument(
        '--base-url',
        default=DEFAULT_BASE_URL,
        help='Base URL used to download the workbook when it is missing locally.'
    )
    parser.add_argument(
        '--sheet-name',
        default='Dissolved Iron',
        help='Worksheet name in the Excel workbook.'
    )
    parser.add_argument(
        '--depth-max',
        type=float,
        default=2.0,
        help='Maximum depth (m) for selecting near-surface point observations.'
    )
    args = parser.parse_args()

    excel_file = args.excel_file.resolve()
    output_file = args.output_file.resolve()

    _ensure_excel_file(excel_file, args.base_url)

    print(f'Reading {excel_file}...')
    # Headers are in row 4 (skiprows=3 skips the first 3 rows)
    df = pd.read_excel(excel_file, sheet_name=args.sheet_name, skiprows=3)

    lon = df['long (degE)'].values
    lat = df['Lat (degN)'].values
    depth = df['depth'].values
    dfe = df['dFe (nM)'].values

    mask = depth < args.depth_max
    lon = lon[mask]
    lat = lat[mask]
    depth = depth[mask]
    dfe = dfe[mask]

    print(f'Total observations after depth filter: {len(dfe)}')
    print(f'dFe range: {np.nanmin(dfe):.2f} to {np.nanmax(dfe):.2f} nM')

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
    ds.attrs['depth_filter'] = f'depth < {args.depth_max} m'

    output_file.parent.mkdir(parents=True, exist_ok=True)
    print(f'Writing to {output_file}...')
    ds.to_netcdf(output_file, encoding={'dFe': {'dtype': 'float32'}})

    print('Conversion complete!')
    print('\nDataset preview:')
    print(ds)


if __name__ == '__main__':
    main()
