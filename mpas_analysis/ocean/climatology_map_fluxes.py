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
import datetime

from mpas_analysis.shared import AnalysisTask

from mpas_analysis.shared.constants import constants

from mpas_analysis.shared.climatology import RemapMpasClimatologySubtask

from mpas_analysis.shared.plot import PlotClimatologyMapSubtask


class ClimatologyMapFluxes(AnalysisTask):
    """
    An analysis task for plotting sea surface fluxes. Observational comparison
    is not supported because no observational datasets are currently available.
    """
    # Authors
    # -------
    # Carolyn Begeman

    def __init__(self, config, mpasClimatologyTask, controlConfig=None,
                 fluxType='mass'):
        """
        Construct the analysis task.

        Parameters
        ----------
        config : tranche.Tranche
            Configuration options

        mpasClimatologyTask : ``MpasClimatologyTask``
            The task that produced the climatology to be remapped and plotted

        controlconfig : tranche.Tranche, optional
            Configuration options for a control run (if any)

        fluxType : str, optional
            The type of surface fluxes, which corresponds to a different config
            section. One of 'mass' or 'heat'.
        """
        # Authors
        # -------
        # Carolyn Begeman

        taskName = f'climatologyMap{fluxType.title()}Fluxes'
        groupLink = taskName

        # call the constructor from the base class (AnalysisTask)
        # Add BGC tag for dust flux variables so they obey no_BGC
        tags = ['climatology', 'horizontalMap', 'fluxes', fluxType]
        # actual variables not yet read; we will update tags later when
        # looping over the config section if any startswith dust_FLUX_
        super(ClimatologyMapFluxes, self).__init__(
            config=config, taskName=taskName,
            componentName='ocean',
            tags=tags)

        iselValues = None

        # read in what seasons we want to plot
        seasons = config.getexpression(taskName, 'seasons')

        if len(seasons) == 0:
            raise ValueError(f'config section {taskName} does not contain '
                             'valid list of seasons')

        comparisonGridNames = config.getexpression(taskName,
                                                   'comparisonGrids')

        if len(comparisonGridNames) == 0:
            raise ValueError(f'config section {taskName} does not contain '
                             'valid list of comparison grids')

        # the variable mpasFieldName will be added to mpasClimatologyTask
        # along with the seasons.
        variableList = config.getexpression(taskName, 'variables')
        # if any dust or iron fluxes are requested, mark this task as BGC so that
        # generate = no_BGC can skip it
        if any(v.startswith('dust_FLUX_') or v == 'IRON_FLUX_IN'
               for v in variableList):
            self.tags.append('BGC')

        for variable in variableList:

            mpasFieldName = f'timeMonthly_avg_{variable}'

            # TemperatureFlux variables have different units and need to be
            # converted to the units of heat flux variables to be compared
            if 'TemperatureFlux' in variable:
                remapClimatologySubtask = RemapMpasTemperatureFluxClimatology(
                    mpasClimatologyTask=mpasClimatologyTask,
                    parentTask=self,
                    climatologyName=variable,
                    variableList=[mpasFieldName],
                    comparisonGridNames=comparisonGridNames,
                    seasons=seasons,
                    iselValues=iselValues,
                    subtaskName=f'remap_{variable}')
                mpasFieldName = 'timeMonthly_avg_' \
                    f'{variable.replace("TemperatureFlux", "HeatFlux")}'

            # dust flux variables require unit conversion from kg m-2 s-1 to
            # g m-2 yr-1
            elif variable.startswith('dust_FLUX_'):
                remapClimatologySubtask = RemapMpasDustFluxClimatology(
                    mpasClimatologyTask=mpasClimatologyTask,
                    parentTask=self,
                    climatologyName=variable,
                    variableList=[mpasFieldName],
                    comparisonGridNames=comparisonGridNames,
                    seasons=seasons,
                    iselValues=iselValues,
                    subtaskName=f'remap_{variable}')

            # iron flux requires unit conversion from mmol m-2 s-1 to
            # mmol m-2 yr-1
            elif variable == 'IRON_FLUX_IN':
                remapClimatologySubtask = RemapMpasIronFluxClimatology(
                    mpasClimatologyTask=mpasClimatologyTask,
                    parentTask=self,
                    climatologyName=variable,
                    variableList=[mpasFieldName],
                    comparisonGridNames=comparisonGridNames,
                    seasons=seasons,
                    iselValues=iselValues,
                    subtaskName=f'remap_{variable}')
            else:
                remapClimatologySubtask = RemapMpasClimatologySubtask(
                    mpasClimatologyTask=mpasClimatologyTask,
                    parentTask=self,
                    climatologyName=variable,
                    variableList=[mpasFieldName],
                    comparisonGridNames=comparisonGridNames,
                    seasons=seasons,
                    iselValues=iselValues,
                    subtaskName=f'remap_{variable}')

            remapObservationsSubtask = None
            galleryName = variable
            if controlConfig is None:
                refTitleLabel = None
                refFieldName = None
                diffTitleLabel = None
            else:
                control_run_name = controlConfig.get('runs', 'mainRunName')
                refTitleLabel = f'Control: {control_run_name}'
                refFieldName = mpasFieldName
                diffTitleLabel = 'Main - Control'

            for comparisonGridName in comparisonGridNames:
                for season in seasons:
                    # make a new subtask for this season and comparison grid
                    subtaskName = f'plot_{variable}_{season}_{comparisonGridName}'
                    outFileName = f'{variable}_{season}_{comparisonGridName}'
                    subtask = PlotClimatologyMapSubtask(
                        self, season, comparisonGridName, remapClimatologySubtask,
                        remapObservationsSubtask, controlConfig=controlConfig,
                        subtaskName=subtaskName)

                    if 'TemperatureFlux' in variable:
                        fieldNameInTitle = variable.replace('TemperatureFlux', 'HeatFlux')
                    else:
                        fieldNameInTitle = variable

                    if 'HeatFlux' in mpasFieldName:
                        groupSubtitle = 'Heat fluxes'
                        unitsLabel = r'W m$^{-2}$'
                    elif variable.startswith('dust_FLUX_'):
                        groupSubtitle = 'Dust fluxes'
                        unitsLabel = r'g m$^{-2}$ yr$^{-1}$'
                    elif variable == 'IRON_FLUX_IN':
                        groupSubtitle = 'Iron fluxes'
                        unitsLabel = r'mmol m$^{-2}$ yr$^{-1}$'
                    else:
                        groupSubtitle = 'Mass fluxes'
                        unitsLabel = r'kg m$^{-2}$ s$^{-1}$'

                    subtask.set_plot_info(
                        outFileLabel=outFileName,
                        fieldNameInTitle=fieldNameInTitle,
                        mpasFieldName=mpasFieldName,
                        refFieldName=refFieldName,
                        refTitleLabel=refTitleLabel,
                        diffTitleLabel=diffTitleLabel,
                        unitsLabel=unitsLabel,
                        imageCaption=variable,
                        galleryGroup='surface fluxes',
                        groupSubtitle=None,
                        groupLink=groupLink,
                        galleryName=galleryName)

                    self.add_subtask(subtask)

# adds to the functionality of RemapMpasClimatology
class RemapMpasDustFluxClimatology(RemapMpasClimatologySubtask):
    """
    A subtask for converting dust flux variables from kg m-2 s-1 to
    g m-2 yr-1 before plotting.

    MPs variable units are assumed kg m$^{-2}$ s$^{-1}$.  The conversion
    factor is 1000 (kg to g) * seconds per year (365.25*24*3600).
    """
    # Authors
    # -------
    # Generated by Copilot adaptation

    def customize_masked_climatology(self, climatology, season):
        """
        Multiply the field by conversion factor and update metadata.
        """
        climatology = super(RemapMpasDustFluxClimatology,
                            self).customize_masked_climatology(climatology,
                                                              season)
        variable = self.variableList[0]
        factor = 1000.0 * 365.25 * 24 * 3600  # kg->g and s->yr
        climatology[variable] = climatology[variable] * factor
        climatology[variable].attrs['units'] = 'g m$^{-2}$ yr$^{-1}$'
        climatology[variable].attrs['description'] = \
            climatology[variable].attrs.get('description', '') + \
            ' (converted from kg m-2 s-1)'
        return climatology


class RemapMpasIronFluxClimatology(RemapMpasClimatologySubtask):
    """
    A subtask for converting iron flux variables from mmol m-2 s-1 to
    mmol m-2 yr-1 before plotting.

    MPAS variable units are assumed mmol m$^{-2}$ s$^{-1}$.  The conversion
    factor is seconds per year (365.25*24*3600).  The molecular weight of
    iron (55.845 g/mol) is noted for reference but not applied in the unit
    conversion.
    """
    # Authors
    # -------
    # Generated by Copilot adaptation

    def customize_masked_climatology(self, climatology, season):
        """
        Multiply the field by conversion factor and update metadata.
        """
        climatology = super(RemapMpasIronFluxClimatology,
                            self).customize_masked_climatology(climatology,
                                                               season)
        variable = self.variableList[0]
        factor = 365.25 * 24 * 3600  # s->yr
        climatology[variable] = climatology[variable] * factor
        climatology[variable].attrs['units'] = 'mmol m$^{-2}$ yr$^{-1}$'
        climatology[variable].attrs['description'] = \
            climatology[variable].attrs.get('description', '') + \
            ' (converted from mmol m-2 s-1)'
        return climatology


class RemapMpasTemperatureFluxClimatology(RemapMpasClimatologySubtask):
    """
    A subtask for computing climatologies of heat flux from temperature flux
    """
    # Authors
    # -------
    # Carolyn Begeman

    def customize_masked_climatology(self, climatology, season):
        """
        Construct velocity magnitude as part of the climatology

        Parameters
        ----------
        climatology : ``xarray.Dataset`` object
            the climatology data set

        season : str
            The name of the season to be masked

        Returns
        -------
        climatology : ``xarray.Dataset`` object
            the modified climatology data set
        """
        # Authors
        # -------
        # Carolyn Begeman

        # first, call the base class's version of this function so we extract
        # the desired slices.
        variable = self.variableList[0]
        climatology = super(RemapMpasTemperatureFluxClimatology,
                            self).customize_masked_climatology(climatology,
                                                               season)

        # calculate heat flux from temperature flux
        scaleFactor = constants.rho_sw * constants.cp_sw  # C m s^-1 to W m^-2
        heatFlux = 0.5 * scaleFactor * climatology[variable]
        # drop unnecessary fields before re-mapping
        climatology.drop_vars([variable])

        # this creates a variable with heat flux units in climatology (like netcdf)
        variable = variable.replace('TemperatureFlux', 'HeatFlux')
        climatology[variable] = heatFlux
        climatology[variable].attrs['units'] = 'W m$^[-2]$'
        climatology[variable].attrs['description'] = \
            f'{variable} converted to heat flux'

        return climatology
