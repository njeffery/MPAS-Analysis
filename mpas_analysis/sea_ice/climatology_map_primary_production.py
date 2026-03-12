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

import xarray as xr
from pyremap import LatLonGridDescriptor

from mpas_analysis.shared import AnalysisTask

from mpas_analysis.shared.climatology import RemapMpasClimatologySubtask, \
    RemapObservedClimatologySubtask

from mpas_analysis.shared.plot import PlotClimatologyMapSubtask

from mpas_analysis.shared.io.utility import build_obs_path


class ClimatologyMapSeaIcePrimaryProduction(AnalysisTask):
    """
    An analysis task for comparison of sea ice primary production against
    observations
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

        tags = ['climatology', 'horizontalMap', fieldName, 'publicObs', 'BGC']
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

        if controlConfig is None:
            self._add_obs_tasks(seasons, comparisonGridNames, hemisphere,
                                hemisphereLong, remapClimatologySubtask,
                                mpasFieldName)
        else:
            self._add_ref_tasks(seasons, comparisonGridNames, hemisphere,
                                hemisphereLong, remapClimatologySubtask,
                                controlConfig, mpasFieldName)

    def _add_obs_tasks(self, seasons, comparisonGridNames, hemisphere,
                       hemisphereLong, remapClimatologySubtask,
                       mpasFieldName):
        config = self.config
        obsFieldName = 'primaryProduction'
        sectionName = self.taskName

        observationPrefixes = config.getexpression(sectionName,
                                                   'observationPrefixes')
        for prefix in observationPrefixes:
            for season in seasons:
                observationTitleLabel = \
                    'Observations ({})'.format(prefix)

                obsFileName = build_obs_path(
                    config, 'seaIce',
                    relativePathOption='primaryProduction{}{}_{}'.format(
                        prefix, hemisphere, season),
                    relativePathSection=sectionName)

                remapObservationsSubtask = RemapObservedClimatologySubtask(
                    parentTask=self, seasons=[season],
                    fileName=obsFileName,
                    outFilePrefix='{}{}{}_{}'.format(
                        obsFieldName, prefix, hemisphere, season),
                    comparisonGridNames=comparisonGridNames,
                    subtaskName='remapObservations_{}{}'.format(
                        prefix, season))
                self.add_subtask(remapObservationsSubtask)
                for comparisonGridName in comparisonGridNames:

                    imageDescription = \
                        'Climatology Map of {}-Hemisphere Sea-Ice ' \
                        'Primary Production'.format(hemisphereLong)
                    imageCaption = \
                        '{}. <br> Observations: {}'.format(
                            imageDescription, prefix)
                    galleryGroup = \
                        '{}-Hemisphere Sea-Ice Primary Production'.format(
                            hemisphereLong)
                    # make a new subtask for this season and comparison
                    # grid

                    subtaskName = f'plot{season}_{comparisonGridName}_{prefix}'

                    subtask = PlotClimatologyMapSubtask(
                        parentTask=self, season=season,
                        comparisonGridName=comparisonGridName,
                        remapMpasClimatologySubtask=remapClimatologySubtask,
                        remapObsClimatologySubtask=remapObservationsSubtask,
                        subtaskName=subtaskName)

                    subtask.set_plot_info(
                        outFileLabel='primaryProduction{}{}'.format(prefix,
                                                                    hemisphere),
                        fieldNameInTitle='Sea ice primary production',
                        mpasFieldName=mpasFieldName,
                        refFieldName=obsFieldName,
                        refTitleLabel=observationTitleLabel,
                        diffTitleLabel='Model - Observations',
                        unitsLabel=r'mg m$^{-2}$ d$^{-1}$',
                        imageCaption=imageCaption,
                        galleryGroup=galleryGroup,
                        groupSubtitle=None,
                        groupLink='{}_primaryprod'.format(hemisphere.lower()),
                        galleryName='Observations: {}'.format(prefix),
                        extend='both',
                        prependComparisonGrid=False)

                    self.add_subtask(subtask)

    def _add_ref_tasks(self, seasons, comparisonGridNames, hemisphere,
                       hemisphereLong, remapClimatologySubtask,
                       controlConfig, mpasFieldName):

        controlRunName = controlConfig.get('runs', 'mainRunName')
        galleryName = None
        refTitleLabel = 'Control: {}'.format(controlRunName)

        for season in seasons:
            for comparisonGridName in comparisonGridNames:

                imageDescription = \
                    '{} Climatology Map of {}-Hemisphere Sea-Ice ' \
                    'Primary Production'.format(season, hemisphereLong)
                imageCaption = imageDescription
                galleryGroup = \
                    '{}-Hemisphere Sea-Ice Primary Production'.format(
                        hemisphereLong)
                # make a new subtask for this season and comparison
                # grid
                subtask = PlotClimatologyMapSubtask(
                    parentTask=self, season=season,
                    comparisonGridName=comparisonGridName,
                    remapMpasClimatologySubtask=remapClimatologySubtask,
                    controlConfig=controlConfig)

                subtask.set_plot_info(
                    outFileLabel='primaryProduction{}'.format(hemisphere),
                    fieldNameInTitle='Sea ice primary production',
                    mpasFieldName=mpasFieldName,
                    refFieldName=mpasFieldName,
                    refTitleLabel=refTitleLabel,
                    diffTitleLabel='Main - Control',
                    unitsLabel=r'mg m$^{-2}$ d$^{-1}$',
                    imageCaption=imageCaption,
                    galleryGroup=galleryGroup,
                    groupSubtitle=None,
                    groupLink='{}_primaryprod'.format(hemisphere.lower()),
                    galleryName=galleryName,
                    extend='both',
                    prependComparisonGrid=False)

                self.add_subtask(subtask)
