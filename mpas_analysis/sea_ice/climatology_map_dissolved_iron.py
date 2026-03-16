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


class ClimatologyMapSeaIceDissolvedIron(AnalysisTask):
    """
    An analysis task for plotting seasonal climatologies of sea-ice dissolved
    iron burden fields in polar stereographic projections.
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

        task_name = f'climatologyMapSeaIceDissolvedIron{hemisphere}'

        tags = ['climatology', 'horizontalMap', 'BGC', 'seaiceDissolvedIron']
        if hemisphere == 'NH':
            tags.append('arctic')
        else:
            tags.append('antarctic')

        super().__init__(config=config, taskName=task_name,
                         componentName='seaIce', tags=tags)

        section_name = self.taskName
        hemisphere_long = 'Northern' if hemisphere == 'NH' else 'Southern'

        seasons = config.getexpression(section_name, 'seasons')
        if len(seasons) == 0:
            raise ValueError(f'config section {section_name} does not contain '
                             'valid list of seasons')

        comparison_grid_names = config.getexpression(section_name,
                                                     'comparisonGrids')
        if len(comparison_grid_names) == 0:
            raise ValueError(f'config section {section_name} does not contain '
                             'valid list of comparison grids')

        variable_specs = [
            {'field': 'totalVerticalDissolvedIronSnow',
               'title': 'Total vertical dissolved iron in snow',
               'config_section': 'seaIceDissolvedIronSnow'},
            {'field': 'totalVerticalDissolvedIronIce',
               'title': 'Total vertical dissolved iron in ice',
               'config_section': 'seaIceDissolvedIron'}
        ]

        for spec in variable_specs:
            field_name = spec['field']
            mpas_field_name = f'timeMonthly_avg_{field_name}'

            remap_climatology_subtask = RemapMpasClimatologySubtask(
                mpasClimatologyTask=mpas_climatology_task,
                parentTask=self,
                climatologyName=f'{field_name}{hemisphere}',
                variableList=[mpas_field_name],
                comparisonGridNames=comparison_grid_names,
                seasons=seasons,
                iselValues=None,
                subtaskName=f'remap_{field_name}_{hemisphere}')

            ref_title_label = None
            ref_field_name = None
            diff_title_label = None
            if control_config is not None:
                control_run_name = control_config.get('runs', 'mainRunName')
                ref_title_label = f'Control: {control_run_name}'
                ref_field_name = mpas_field_name
                diff_title_label = 'Main - Control'

            for comparison_grid_name in comparison_grid_names:
                for season in seasons:
                    subtask_name = \
                        f'plot_{field_name}_{season}_{comparison_grid_name}'
                    subtask = PlotClimatologyMapSubtask(
                        parentTask=self, season=season,
                        comparisonGridName=comparison_grid_name,
                        remapMpasClimatologySubtask=remap_climatology_subtask,
                        remapObsClimatologySubtask=None,
                        controlConfig=control_config,
                        subtaskName=subtask_name)

                    image_caption = (
                        f'Climatology map of {hemisphere_long}-hemisphere '
                        f'{spec["title"].lower()}')

                    field_name_in_title = spec['title']
                    if (hemisphere == 'NH' and
                            field_name == 'totalVerticalDissolvedIronIce'):
                        field_name_in_title = (
                            'Total vertical dissolved iron in ice\n'
                            'Observed bounds: 0.1-16 nM '
                            '(Evans et al. 2018)')
                    elif (hemisphere == 'SH' and
                            field_name == 'totalVerticalDissolvedIronIce'):
                        field_name_in_title = (
                            'Total vertical dissolved iron in ice\n'
                            'Observed bounds: 0.7-37 nM '
                            '(Lannuzel et al. 2010)')

                    subtask.set_plot_info(
                        outFileLabel=f'{field_name}{hemisphere}',
                        fieldNameInTitle=field_name_in_title,
                        mpasFieldName=mpas_field_name,
                        refFieldName=ref_field_name,
                        refTitleLabel=ref_title_label,
                        diffTitleLabel=diff_title_label,
                        unitsLabel=r'$\mu$mol Iron m$^{-2}$',
                        imageCaption=image_caption,
                        galleryGroup=f'{hemisphere_long}-Hemisphere '
                                     'Sea-Ice Dissolved Iron',
                        groupSubtitle=None,
                        groupLink=f'{hemisphere.lower()}_dissolved_iron',
                        galleryName=spec['title'],
                        configSectionName=spec['config_section'],
                        prependComparisonGrid=False)

                    self.add_subtask(subtask)