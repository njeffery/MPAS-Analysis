# This software is open source software available under the BSD-3 license.
#
# Copyright (c) 2022 Triad National Security, LLC. All rights reserved.
# Copyright (c) 2022 Lawrence Livermore National Security, LLC. All rights
# reserved.
# Copyright (c) 2022 UT-Battelle, LLC. All rights reserved.
#
# Additional copyright and license information can be found in the LICENSE file
# distributed with this code, or at
# https://raw.githubusercontent.com/MPAS-Dev/MPAS-Analysis/main/LICENSE

"""
Utilities for reading MPAS restart files for snapshot climatologies
"""
# Authors
# -------
# Xylar Asay-Davis

import os
import glob
import xarray as xr
from datetime import datetime


def find_restart_file(baseDirectory, component, date, runName, archiveMode):
    """
    Find a restart file for a given date and component.

    Parameters
    ----------
    baseDirectory : str
        The base directory for model output

    component : {'ocean', 'seaIce'}
        Component name (used to select mpaso or mpassi)

    date : str
        Date string in format 'YYYY-MM-DD'

    runName : str
        The run name prefix for restart files

    archiveMode : bool
        If True, search in archive/rest/YYYY-MM-DD-SSSSS/
        If False, search in run/

    Returns
    -------
    restartFile : str
        Full path to the restart file, or None if not found

    Raises
    ------
    ValueError
        If date format is invalid or component is unknown
    """
    # Parse the date
    try:
        snapshot_date = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Invalid date format: {date}. Expected YYYY-MM-DD")

    # Map component to file prefix
    component_map = {
        'ocean': 'mpaso',
        'seaIce': 'mpassi'
    }

    if component not in component_map:
        raise ValueError(f"Unknown component: {component}. "
                        f"Must be 'ocean' or 'seaIce'")

    component_prefix = component_map[component]

    # Construct search path
    if archiveMode:
        # archive/rest/YYYY-MM-DD-SSSSS/ subdirectories
        search_pattern = os.path.join(
            baseDirectory, 'archive', 'rest',
            f'{snapshot_date.strftime("%Y-%m-%d")}-*',
            f'{runName}.{component_prefix}.rst.{snapshot_date.strftime("%Y-%m-%d")}_*.nc'
        )
    else:
        # run/ directory
        search_pattern = os.path.join(
            baseDirectory, 'run',
            f'{runName}.{component_prefix}.rst.{snapshot_date.strftime("%Y-%m-%d")}_*.nc'
        )

    # Find matching files
    matching_files = sorted(glob.glob(search_pattern))

    if not matching_files:
        return None

    # Return the first (usually only) match
    return matching_files[0]


def read_restart_file(restartFile, fieldNames=None):
    """
    Read fields from a restart file, stripping timeSeriesStatsMonthly prefix
    if present.

    Parameters
    ----------
    restartFile : str
        Path to the restart file

    fieldNames : list of str, optional
        List of field names to read. If None, all variables are returned.
        Field names should NOT include the 'timeSeriesStatsMonthly_avg_'
        prefix, which will be stripped if present.

    Returns
    -------
    ds : xarray.Dataset
        Dataset with requested fields (prefix already stripped)
    """
    # Open the file
    ds = xr.open_dataset(restartFile)

    if fieldNames is None:
        # Return all variables, stripping prefix
        return _strip_time_series_prefix(ds)

    # Select only requested fields, trying both with and without prefix
    selected_vars = []
    for field in fieldNames:
        # Try without prefix (native restart field name)
        if field in ds.variables:
            selected_vars.append(field)
        # Try with prefix (in case preprocessing added it)
        elif f'timeSeriesStatsMonthly_avg_{field}' in ds.variables:
            selected_vars.append(f'timeSeriesStatsMonthly_avg_{field}')
        else:
            # Field not found - warn but continue
            print(f"Warning: Field '{field}' not found in {restartFile}")

    if selected_vars:
        ds = ds[selected_vars]

    # Strip any remaining prefix
    return _strip_time_series_prefix(ds)


def _strip_time_series_prefix(ds):
    """
    Strip 'timeSeriesStatsMonthly_avg_' prefix from variable names in dataset.

    Parameters
    ----------
    ds : xarray.Dataset
        Input dataset

    Returns
    -------
    ds : xarray.Dataset
        Dataset with prefix stripped from variable names
    """
    rename_map = {}
    for var in ds.data_vars:
        if var.startswith('timeSeriesStatsMonthly_avg_'):
            new_name = var.replace('timeSeriesStatsMonthly_avg_', '', 1)
            rename_map[var] = new_name

    if rename_map:
        ds = ds.rename(rename_map)

    return ds
