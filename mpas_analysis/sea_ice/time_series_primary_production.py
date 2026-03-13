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

import numpy as np
import os
import xarray as xr

from mpas_analysis.shared import AnalysisTask

from mpas_analysis.shared.plot import timeseries_analysis_plot, savefig

from mpas_analysis.shared.io.utility import build_config_full_path, \
    check_path_exists, make_directories

from mpas_analysis.shared.timekeeping.utility import date_to_days, \
    days_to_datetime, datetime_to_days, get_simulation_start_time
from mpas_analysis.shared.timekeeping.MpasRelativeDelta import \
    MpasRelativeDelta

from mpas_analysis.shared.time_series import combine_time_series_with_ncrcat
from mpas_analysis.shared.io import open_mpas_dataset, write_netcdf_with_fill

from mpas_analysis.shared.html import write_image_xml

import matplotlib.pyplot as plt


class TimeSeriesSeaIcePrimaryProduction(AnalysisTask):
    """
    Performs analysis of time series of sea-ice primary production,
    computed as hemispherically-integrated values using grid cell areas,
    with results in Tg yr-1.

    Attributes
    ----------

    mpasTimeSeriesTask : ``MpasTimeSeriesTask``
        The task that extracts the time series from MPAS monthly output

    controlconfig : tranche.Tranche
        Configuration options for a control run (if any)

    """
    # Authors
    # -------

    def __init__(self, config, mpasTimeSeriesTask,
                 controlConfig=None):
        """
        Construct the analysis task.

        Parameters
        ----------
        config : tranche.Tranche
            Configuration options

        mpasTimeSeriesTask : ``MpasTimeSeriesTask``
            The task that extracts the time series from MPAS monthly output

        controlconfig : tranche.Tranche, optional
            Configuration options for a control run (if any)
        """
        # Authors
        # -------

        # first, call the constructor from the base class (AnalysisTask)
        super(TimeSeriesSeaIcePrimaryProduction, self).__init__(
            config=config,
            taskName='timeSeriesSeaIcePrimaryProduction',
            componentName='seaIce',
            tags=['timeSeries', 'publicObs', 'arctic', 'antarctic', 'BGC'])

        self.mpasTimeSeriesTask = mpasTimeSeriesTask
        self.controlConfig = controlConfig

        self.run_after(mpasTimeSeriesTask)

    def setup_and_check(self):
        """
        Perform steps to set up the analysis and check for errors in the setup.

        Raises
        ------
        OSError
            If files are not present
        """
        # Authors
        # -------

        # first, call setup_and_check from the base class (AnalysisTask),
        # which will perform some common setup, including storing:
        #     self.runDirectory , self.historyDirectory, self.plotsDirectory,
        #     self.namelist, self.runStreams, self.historyStreams,
        #     self.calendar
        super(TimeSeriesSeaIcePrimaryProduction, self).setup_and_check()

        config = self.config

        self.startDate = self.config.get('timeSeries', 'startDate')
        self.endDate = self.config.get('timeSeries', 'endDate')

        self.variableList = ['timeMonthly_avg_primaryProduction']
        self.mpasTimeSeriesTask.add_variables(variableList=self.variableList)

        self.inputFile = self.mpasTimeSeriesTask.outputFile

        # get a list of timeSeriesStatsMonthly output files from the streams
        # file, reading only those that are between the start and end dates
        streamName = 'timeSeriesStatsMonthlyOutput'
        self.startDate = config.get('timeSeries', 'startDate')
        self.endDate = config.get('timeSeries', 'endDate')
        self.inputFiles = \
            self.historyStreams.readpath(streamName,
                                         startDate=self.startDate,
                                         endDate=self.endDate,
                                         calendar=self.calendar)

        if len(self.inputFiles) == 0:
            raise IOError('No files were found in stream {} between {} and '
                          '{}.'.format(streamName, self.startDate,
                                       self.endDate))

        self.simulationStartTime = get_simulation_start_time(self.runStreams)

        self.meshFilename = self.get_mesh_filename()

        mainRunName = config.get('runs', 'mainRunName')

        self.xmlFileNames = []
        for hemisphere in ['NH', 'SH']:
            filePrefix = 'timeSeriesPrimaryProduction{}'.format(hemisphere)
            self.xmlFileNames.append('{}/{}.xml'.format(
                self.plotsDirectory, filePrefix))

    def run_task(self):
        """
        Performs analysis of time series of sea-ice primary production.
        """
        # Authors
        # -------

        self.logger.info(
            "\nPlotting time series of hemispherically-integrated sea-ice primary production...")

        config = self.config
        calendar = self.calendar

        sectionName = self.taskName

        plotTitle = 'Hemispherically-Integrated Sea-Ice Primary Production'
        units = 'Tg yr$^{-1}$'

        mainRunName = config.get('runs', 'mainRunName')

        movingAveragePoints = config.getint(sectionName,
                                            'movingAveragePoints')
        titleFontSize = config.getint(sectionName, 'titleFontSize')

        outputDirectory = build_config_full_path(config, 'output',
                                                 'timeseriesSubdirectory')

        make_directories(outputDirectory)

        self.logger.info('  Load sea-ice primary production data...')

        # Compute hemispheric primary production
        dsTimeSeries = self._compute_primary_production()

        if self.controlConfig is not None:

            dsTimeSeriesRef = {}
            baseDirectory = build_config_full_path(
                self.controlConfig, 'output', 'timeSeriesSubdirectory')

            controlRunName = self.controlConfig.get('runs', 'mainRunName')

            for hemisphere in ['NH', 'SH']:
                inFileName = \
                    '{}/timeSeriesPrimaryProduction{}.nc'.format(
                        baseDirectory, hemisphere)

                dsTimeSeriesRef[hemisphere] = xr.open_dataset(inFileName)

        xLabel = 'Time [years]'
        startYear = config.getint('timeSeries', 'startYear')
        endYear = config.getint('timeSeries', 'endYear')

        galleryGroup = 'Time Series'
        groupLink = 'timeseries'

        for hemisphere in ['NH', 'SH']:

            filePrefix = 'timeSeriesPrimaryProduction{}'.format(hemisphere)
            outFileName = '{}/{}.nc'.format(outputDirectory, filePrefix)

            dsRegional = dsTimeSeries[hemisphere]

            title = '{} {}-Hemisphere'.format(plotTitle, hemisphere)

            figureNameStd = '{}/{}.png'.format(self.plotsDirectory,
                                              filePrefix)

            self.logger.info('   Load primary production data from {}'.format(
                outFileName))

            # Plot monthly means at month midpoints on a decimal-year axis.
            nTime = dsRegional.sizes['Time']
            timeYears = startYear + (np.arange(nTime) + 0.5) / 12.
            xArrays = [timeYears]
            yArrays = [dsRegional.primaryProduction.values]
            lineStyles = ['-']
            lineWidths = [2.5]
            colors = ['black']
            legends = [mainRunName]

            if self.controlConfig is not None:
                yArrays.append(
                    dsTimeSeriesRef[hemisphere].primaryProduction.values)
                colors.append('red')
                lineStyles.append('-')
                lineWidths.append(2.5)
                legends.append(controlRunName)

            if movingAveragePoints > 1:
                self.logger.info(
                    '   Compute {} points moving average...'.format(
                        movingAveragePoints))
                for i in range(len(yArrays)):
                    yArrays[i] = \
                        self._compute_moving_average(yArrays[i],
                                                    movingAveragePoints)

            # Compute and plot observational bounds as semi-transparent shading
            self.logger.info('   Adding observational range shading...')
            
            obsMin = config.getfloat(sectionName, f'obsMin{hemisphere}')
            obsMax = config.getfloat(sectionName, f'obsMax{hemisphere}')
            obsRef = config.get(sectionName, 'obsReference')

            # Create figure with custom plotting to add shading
            fig = plt.figure(figsize=(12, 5))
            ax = fig.add_subplot(111)
            
            timeData = xArrays[0]
            obsLower = obsMin * np.ones_like(timeData)
            obsUpper = obsMax * np.ones_like(timeData)

            ax.fill_between(timeData, obsLower, obsUpper, alpha=0.3,
                           color='gray', label=f'Observations ({obsRef})')
            
            # Plot main data lines
            for i, (xArray, yArray, lineStyle, lineWidth, color, legend) \
                    in enumerate(zip(xArrays, yArrays, lineStyles, 
                                    lineWidths, colors, legends)):
                ax.plot(xArray, yArray, linestyle=lineStyle, 
                       linewidth=lineWidth, color=color, 
                       label=legend, marker='.')
            
            ax.set_xlabel(xLabel, fontsize=12)
            ax.set_ylabel(units, fontsize=12)
            ax.set_title(title, fontsize=titleFontSize)
            ax.set_xlim(startYear, endYear + 1)
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)
            
            savefig(figureNameStd, config)
            plt.close(fig)
            
            self.logger.info('   plotted {} to {}'.format(title,
                                                          figureNameStd))

            caption = 'Time series of {}'.format(title)
            write_image_xml(
                config, filePrefix, componentName='Sea Ice',
                componentSubdirectory='sea_ice',
                tagDict=None,
                imageDescription=caption,
                imageCaption=caption,
                galleryGroup=galleryGroup,
                groupLink=groupLink,
                downloadFileName='primaryProduction.nc')

    def _compute_primary_production(self):
        """
        Computes hemispherically-integrated time series of primary production,
        using grid cell areas for integration and converting to Tg yr-1.
        """
        # Authors
        # -------

        config = self.config
        calendar = self.calendar

        dsMesh = xr.open_dataset(self.meshFilename)

        dsTimeSeries = {}

        # Conversion factor from mg d-1 to Tg yr-1:
        # mg d-1 * (365.25 days/year) * (10^-15 Tg/mg) = Tg yr-1
        conversion_factor = 365.25e-15

        for hemisphere in ['NH', 'SH']:
            self.logger.info(
                '   Compute primary production for {} hemisphere...'.format(
                    hemisphere))

            outputDirectory = build_config_full_path(
                config, 'output', 'timeseriesSubdirectory')
            outFileName = '{}/timeSeriesPrimaryProduction{}.nc'.format(
                outputDirectory, hemisphere)

            if hemisphere == 'NH':
                mask = dsMesh.latCell > 0
            else:
                mask = dsMesh.latCell < 0

            # Only compute if file doesn't exist or needs updating
            if os.path.exists(outFileName):
                dsTimeSeries[hemisphere] = xr.open_dataset(outFileName)
                continue

            # Open combined monthly time series produced by MpasTimeSeriesTask
            ds = open_mpas_dataset(fileName=self.inputFile,
                                   calendar=calendar,
                                   timeVariableNames=['xtime_startMonthly',
                                                      'xtime_endMonthly'])

            # Compute total hemispheric integrated primary production
            # in mg d-1, then convert to Tg yr-1
            dsPrimaryProd = (
                ds.timeMonthly_avg_primaryProduction.where(mask) * 
                dsMesh.areaCell
            ).sum('nCells') * conversion_factor

            # Create dataset with primary production
            dsOut = xr.Dataset(
                {'primaryProduction': dsPrimaryProd},
                coords={'Time': ds.Time}
            )

            dsOut['primaryProduction'].attrs['units'] = 'Tg yr$^{-1}$'
            dsOut['primaryProduction'].attrs['description'] = \
                f'Integrated {hemisphere} sea-ice primary production'
            dsOut['primaryProduction'].attrs['long_name'] = \
                f'{hemisphere} Hemispherically-Integrated Primary Production'

            write_netcdf_with_fill(dsOut, outFileName)
            dsTimeSeries[hemisphere] = dsOut

        return dsTimeSeries

    def _compute_moving_average(self, array, windowSize):
        """Compute moving average of an array"""
        # Authors
        # -------

        weights = np.ones(windowSize) / windowSize
        return np.convolve(array, weights, mode='same')
