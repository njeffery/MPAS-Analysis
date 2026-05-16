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

from mpas_analysis.shared import AnalysisTask

from mpas_analysis.shared.climatology import RemapMpasClimatologySubtask

from mpas_analysis.shared.plot import PlotClimatologyMapSubtask


class ClimatologyMapSeaIceTotalChlorophyll(AnalysisTask):
    """
    An analysis task for plotting seasonal climatologies of sea-ice total
    chlorophyll in polar stereographic projections.
    """

    def __init__(self, config, mpas_climatology_task, hemisphere,
                 control_config=None):
        """
        Construct the analysis task.

        Parameters
        ----------
        config : tranche.Tranche
            Configuration options

        mpas_climatology_task : ``MpasClimatologyTask``
            The task that produced the climatology to be remapped and plotted

        hemisphere : {'NH', 'SH'}
            The hemisphere to plot

        control_config : tranche.Tranche, optional
            Configuration options for a control run (if any)
        """

        task_name = f'climatologyMapSeaIceTotalChlorophyll{hemisphere}'

        tags = ['climatology', 'horizontalMap', 'BGC', 'seaiceChlorophyll',
            'seaIceBGC', 'seaiceBGC', 'publicObs',
            'climatologyMapSeaIceBGC', 'climatologyMapSeaiceBGC']
        if hemisphere == 'NH':
            tags.append('arctic')
        else:
            tags.append('antarctic')

        super().__init__(config=config, taskName=task_name,
                         componentName='seaIce', tags=tags)

        section_name = self.taskName
        hemisphere_long = 'Northern' if hemisphere == 'NH' else 'Southern'
        parent_section = 'climatologyMapSeaIceBGC'

        if config.has_option(parent_section, 'seasons'):
            seasons = config.getexpression(parent_section, 'seasons')
        else:
            seasons = config.getexpression(section_name, 'seasons')
        if len(seasons) == 0:
            raise ValueError(f'config section {section_name} does not contain '
                             'valid list of seasons')

        if config.has_option(parent_section, 'comparisonGrids'):
            comparison_grid_names = config.getexpression(
                parent_section, 'comparisonGrids')
        else:
            comparison_grid_names = config.getexpression(
                section_name, 'comparisonGrids')
        if len(comparison_grid_names) == 0:
            raise ValueError(f'config section {section_name} does not contain '
                             'valid list of comparison grids')

        grid_keyword = 'arctic' if hemisphere == 'NH' else 'antarctic'
        comparison_grid_names = [grid_name for grid_name in
                                 comparison_grid_names
                                 if grid_name.lower().startswith(grid_keyword)]
        if len(comparison_grid_names) == 0:
            raise ValueError(f'No valid {grid_keyword} comparison grids '
                             f'found in section {section_name}')

        field_name = 'totalChlorophyll'
        mpas_field_name = f'timeMonthly_avg_{field_name}'

        remap_climatology_subtask = RemapMpasClimatologySubtask(
            mpasClimatologyTask=mpas_climatology_task,
            parentTask=self,
            climatologyName=f'{field_name}{hemisphere}',
            variableList=[mpas_field_name],
            comparisonGridNames=comparison_grid_names,
            seasons=seasons,
            iselValues=None)

        ref_title_label = None
        ref_field_name = None
        diff_title_label = None
        if control_config is not None:
            control_run_name = control_config.get('runs', 'mainRunName')
            ref_title_label = f'Control: {control_run_name}'
            ref_field_name = mpas_field_name
            diff_title_label = 'Main - Control'

        # Season and hemisphere-specific point-data bounds for title strings
        # Whether point obs exist for this season/hemisphere
        # (derived from Jeffery2020 nc file content)
        has_point_obs = {
            'ANN': {'NH': True, 'SH': True},
            'JFM': {'NH': True, 'SH': False},
            'AMJ': {'NH': True, 'SH': True},
            'JAS': {'NH': False, 'SH': True},
            'OND': {'NH': True, 'SH': True},
            'DJF': {'NH': True, 'SH': False},
            'MAM': {'NH': True, 'SH': True},
            'JJA': {'NH': False, 'SH': True},
            'SON': {'NH': True, 'SH': True}
        }

        season_ranges = {
            'ANN': {'NH': None, 'SH': None},
            'JFM': {'NH': '0-38', 'SH': None},
            'AMJ': {'NH': '0-52', 'SH': '0-56'},
            'JAS': {'NH': None, 'SH': '0-18'},
            'OND': {'NH': '0-22', 'SH': '0-32'},
            'DJF': {'NH': None, 'SH': None},
            'MAM': {'NH': None, 'SH': None},
            'JJA': {'NH': None, 'SH': None},
            'SON': {'NH': None, 'SH': None}
        }

        # Observed bounds are reported for JFM/AMJ/JAS/OND; map
        # climatological seasons to those bins when needed.
        season_aliases = {
            'DJF': 'JFM',
            'MAM': 'AMJ',
            'JJA': 'JAS',
            'SON': 'OND'
        }

        for comparison_grid_name in comparison_grid_names:
            for season in seasons:
                season_for_bounds = season
                data_range = season_ranges.get(season, {}).get(hemisphere)
                if data_range is None and season in season_aliases:
                    season_for_bounds = season_aliases[season]
                    data_range = season_ranges.get(season_for_bounds, {}).get(
                        hemisphere)
                subtask_name = \
                    f'plot_{field_name}_{season}_{comparison_grid_name}'
                subtask = PlotClimatologyMapSubtask(
                    parentTask=self, season=season,
                    comparisonGridName=comparison_grid_name,
                    remapMpasClimatologySubtask=remap_climatology_subtask,
                    remapObsClimatologySubtask=None,
                    controlConfig=control_config,
                    subtaskName=subtask_name)

                if data_range:
                    image_description = (
                        f'{season} {hemisphere_long} Sea-Ice Total '
                        f'Chlorophyll ({data_range} mg Chla m$^{{-2}}$)')
                else:
                    image_description = (
                        f'{season} {hemisphere_long} Sea-Ice Total Chlorophyll')
                field_name_in_title = 'Total chlorophyll'

                season_has_obs = (
                    has_point_obs.get(season, {}).get(hemisphere, False))
                if data_range:
                    field_name_in_title = (
                        'Total chlorophyll\n'
                        f'Observed bounds: '
                        f'{data_range} mg Chla m$^{{-2}}$ '
                        '[Jeffery et al. 2020]')
                elif season_has_obs:
                    field_name_in_title = (
                        'Total chlorophyll\n'
                        '[Jeffery et al. 2020]')
                else:
                    field_name_in_title = 'Total chlorophyll'

                if data_range:
                    image_caption = (
                        f'{image_description}. <br> Observed bounds '
                        f'({season_for_bounds}): '
                        f'{data_range} mg Chla m$^{{-2}}$ '
                        '[Jeffery et al. 2020]')
                elif season_has_obs:
                    image_caption = (
                        f'{image_description}. <br> Reference: observed '
                        'range reported in [Jeffery et al. 2020]')
                else:
                    image_caption = image_description

                subtask.set_plot_info(
                    outFileLabel=f'{field_name}{hemisphere}',
                    fieldNameInTitle=field_name_in_title,
                    mpasFieldName=mpas_field_name,
                    refFieldName=ref_field_name,
                    refTitleLabel=ref_title_label,
                    diffTitleLabel=diff_title_label,
                    unitsLabel=r'mg Chla m$^{-2}$',
                    imageCaption=image_caption,
                    galleryGroup=f'BGC - {hemisphere_long}-Hemisphere',
                    groupSubtitle=None,
                    groupLink=f'{hemisphere.lower()}_bgc',
                    galleryName='Total sea ice chlorophyll',
                    configSectionName='seaIceTotalChlorophyll',
                    prependComparisonGrid=False)

                self.add_subtask(subtask)