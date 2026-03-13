"""Test: sea-ice primary production and total chlorophyll NH/SH with new colormaps."""
import os
import sys

os.environ['PATH'] = '/Applications/anaconda3/envs/mpas-py311/bin:' + os.environ.get('PATH', '')
sys.path.insert(0, '/Users/njeffery/MPAS-Analysis')

from tranche import Tranche
from mpas_analysis.shared.climatology import MpasClimatologyTask
from mpas_analysis.shared.time_series import MpasTimeSeriesTask
from mpas_analysis.sea_ice.climatology_map_primary_production import (
    ClimatologyMapSeaIcePrimaryProduction)
from mpas_analysis.sea_ice.climatology_map_total_chlorophyll import (
    ClimatologyMapSeaIceTotalChlorophyll)
from mpas_analysis.sea_ice.climatology_map_aerosol_impurities import (
    ClimatologyMapSeaIceAerosolImpurities)
from mpas_analysis.sea_ice.time_series_primary_production import (
    TimeSeriesSeaIcePrimaryProduction)

config = Tranche()
config.add_from_package('mpas_analysis', 'default.cfg')
config.add_user_config('/Users/njeffery/MPAS-Analysis/seaice_sample_test.cfg')

sea_ice_climo = MpasClimatologyTask(config=config, componentName='seaIce')
sea_ice_time_series = MpasTimeSeriesTask(config=config, componentName='seaIce')
tasks = [
    sea_ice_climo,
    sea_ice_time_series,
    ClimatologyMapSeaIcePrimaryProduction(
        config=config, mpasClimatologyTask=sea_ice_climo,
        hemisphere='NH', controlConfig=None),  # JFM + JAS
    ClimatologyMapSeaIcePrimaryProduction(
        config=config, mpasClimatologyTask=sea_ice_climo,
        hemisphere='SH', controlConfig=None),  # JJA + DJF
    ClimatologyMapSeaIceTotalChlorophyll(
        config=config, mpas_climatology_task=sea_ice_climo,
        hemisphere='NH', control_config=None),
    ClimatologyMapSeaIceTotalChlorophyll(
        config=config, mpas_climatology_task=sea_ice_climo,
        hemisphere='SH', control_config=None),
    ClimatologyMapSeaIceAerosolImpurities(
        config=config, mpas_climatology_task=sea_ice_climo,
        hemisphere='NH', control_config=None),
    ClimatologyMapSeaIceAerosolImpurities(
        config=config, mpas_climatology_task=sea_ice_climo,
        hemisphere='SH', control_config=None),
    TimeSeriesSeaIcePrimaryProduction(
        config=config, mpasTimeSeriesTask=sea_ice_time_series,
        controlConfig=None),
]


def gather(task, ordered, seen):
    if task.fullTaskName in seen:
        return
    seen.add(task.fullTaskName)
    ordered.append(task)
    for subtask in task.subtasks:
        gather(subtask, ordered, seen)


ordered, seen = [], set()
for task in tasks:
    gather(task, ordered, seen)

print(f'Total tasks/subtasks: {len(ordered)}')
for task in ordered:
    print(f'  SETTING UP {task.fullTaskName}')
    task.setup_and_check()

by_name = {task.fullTaskName: task for task in ordered}
deps = {}
for task in ordered:
    task_deps = {dep.fullTaskName for dep in task.runAfterTasks}
    task_deps.update(subtask.fullTaskName for subtask in task.subtasks)
    deps[task.fullTaskName] = task_deps

remaining, done = set(by_name), set()
while remaining:
    ready = sorted(name for name in remaining if deps[name].issubset(done))
    if not ready:
        raise RuntimeError(f'No runnable tasks. Pending: {sorted(remaining)}')
    name = ready[0]
    task = by_name[name]
    print(f'RUNNING {name}')
    task.run(writeLogFile=False)
    if task._runStatus.value != task.SUCCESS:
        raise RuntimeError(f'Task failed: {name}\n{task._stackTrace}')
    done.add(name)
    remaining.remove(name)

import glob
pngs = sorted(glob.glob('/Users/njeffery/MPAS-Analysis/seaice_sample_test_output/plots/*.png'))
print(f'\nOutput plots ({len(pngs)}):')
for p in pngs:
    print(f'  {os.path.basename(p)}')

print('\nAll tasks completed successfully.')
