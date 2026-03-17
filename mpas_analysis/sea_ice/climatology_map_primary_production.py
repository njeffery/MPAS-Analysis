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


class ClimatologyMapSeaIcePrimaryProduction(AnalysisTask):
    """An analysis task for plotting sea ice primary production climatologies
    """
    # Authors
    # -------

    def __init__(self, config, mpasClimatologyTask, hemisphere,
                 controlConfig=None):
        """
        Construct the analysis task.

        Parameters
        ----------
        config : tranche.Tranche
            Configuration options

        mpasClimatologyTask : ``MpasClimatologyTask``
            The task that produced the climatology to be remapped and plotted

        hemisphere : {'NH', 'SH'}
            The hemisphere to plot

        controlconfig : tranche.Tranche, optional
            Configuration options for a control run (if any)
        """

        taskName = 'climatologyMapSeaIcePrimaryProduction{}'.format(hemisphere)

        fieldName = 'seaIcePrimaryProduction'

        tags = ['climatology', 'horizontalMap', fieldName, 'BGC']
        if hemisphere == 'NH':
            tags = tags + ['arctic']
        else:
            tags = tags + ['antarctic']

        # call the constructor from the base class (AnalysisTask)
        super(ClimatologyMapSeaIcePrimaryProduction, self).__init__(
            config=config, taskName=taskName,
            componentName='seaIce',
            tags=tags)

        mpasFieldName = 'timeMonthly_avg_primaryProduction'
        iselValues = None

        sectionName = taskName

        if hemisphere == 'NH':
            hemisphereLong = 'Northern'
        else:
            hemisphereLong = 'Southern'

        # read in what seasons we want to plot
        seasons = config.getexpression(sectionName, 'seasons')

        if len(seasons) == 0:
            raise ValueError('config section {} does not contain valid list '
                             'of seasons'.format(sectionName))

        comparisonGridNames = config.getexpression(sectionName,
                                                   'comparisonGrids')

        if len(comparisonGridNames) == 0:
            raise ValueError('config section {} does not contain valid list '
                             'of comparison grids'.format(sectionName))

        # the variable self.mpasFieldName will be added to mpasClimatologyTask
        # along with the seasons.
        remapClimatologySubtask = RemapMpasClimatologySubtask(
            mpasClimatologyTask=mpasClimatologyTask,
            parentTask=self,
            climatologyName='{}{}'.format(fieldName, hemisphere),
            variableList=[mpasFieldName],
            comparisonGridNames=comparisonGridNames,
            seasons=seasons,
            iselValues=iselValues)

        # Season and hemisphere-specific observed-range annotations
        season_ranges = {
            'ANN': {'NH': None, 'SH': None},
            'JFM': {'NH': '0-58', 'SH': '0-12'},
            'AMJ': {'NH': '0-30', 'SH': '0-5'},
            'JAS': {'NH': '0-28', 'SH': '0-60'},
            'OND': {'NH': None, 'SH': '0-140'},
            'DJF': {'NH': None, 'SH': None},
            'MAM': {'NH': None, 'SH': None},
            'JJA': {'NH': None, 'SH': None},
            'SON': {'NH': None, 'SH': None},
        }

        if hemisphere == 'NH':
            obsCitation = 'Leu et al. 2015'
        else:
            obsCitation = 'Arrigo et al. 2010'

        ref_title_label = None
        ref_field_name = None
        diff_title_label = None
        if controlConfig is not None:
            controlRunName = controlConfig.get('runs', 'mainRunName')
            ref_title_label = 'Control: {}'.format(controlRunName)
            ref_field_name = mpasFieldName
            diff_title_label = 'Main - Control'

        for comparisonGridName in comparisonGridNames:
            for season in seasons:
                dataRange = season_ranges.get(season, {}).get(hemisphere)

                if dataRange:
                    imageDescription = (
                        '{} {} Sea-Ice Primary Production '
                        '({} mg m$^{{-2}}$ d$^{{-1}}$)'.format(
                            season, hemisphereLong, dataRange))
                else:
                    imageDescription = (
                        '{} {} Sea-Ice Primary Production'.format(
                            season, hemisphereLong))

                fieldNameInTitle = 'Sea ice primary production'
                if dataRange:
                    fieldNameInTitle = (
                        'Sea ice primary production\n'
                        'Observed bounds: {} mg m$^{{-2}}$ d$^{{-1}}$ [{}]'.format(
                            dataRange, obsCitation))

                if dataRange:
                    imageCaption = (
                        '{}. <br> Observed bounds: {} mg m$^{{-2}}$ '
                        'd$^{{-1}}$ [{}]'.format(
                            imageDescription, dataRange, obsCitation))
                else:
                    imageCaption = (
                        '{}. <br> Reference: observed range reported '
                        'in [{}]'.format(imageDescription, obsCitation))

                subtaskName = 'plot_seaIcePrimaryProduction_{}_{}'.format(
                    season, comparisonGridName)

                subtask = PlotClimatologyMapSubtask(
                    parentTask=self, season=season,
                    comparisonGridName=comparisonGridName,
                    remapMpasClimatologySubtask=remapClimatologySubtask,
                    remapObsClimatologySubtask=None,
                    controlConfig=controlConfig,
                    subtaskName=subtaskName)

                subtask.set_plot_info(
                    outFileLabel='primaryProduction{}'.format(hemisphere),
                    fieldNameInTitle=fieldNameInTitle,
                    mpasFieldName=mpasFieldName,
                    refFieldName=ref_field_name,
                    refTitleLabel=ref_title_label,
                    diffTitleLabel=diff_title_label,
                    unitsLabel=r'mg m$^{-2}$ d$^{-1}$',
                    imageCaption=imageCaption,
                    galleryGroup='BGC - {}-Hemisphere Sea-Ice Primary Production'.format(
                        hemisphereLong),
                    groupSubtitle=None,
                    groupLink='{}_primaryprod'.format(hemisphere.lower()),
                    galleryName='Sea ice primary production',
                    extend='both',
                    prependComparisonGrid=False)

                self.add_subtask(subtask)
