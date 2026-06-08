# This software is open source software available under the BSD-3 license.

import os
from pathlib import PurePosixPath

import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from mpas_analysis.shared import AnalysisTask
from mpas_analysis.shared.html import write_image_xml
from mpas_analysis.shared.io import open_mpas_dataset
from mpas_analysis.shared.io.download import download_files
from mpas_analysis.shared.io.utility import build_config_full_path, \
    build_obs_path, make_directories
from mpas_analysis.shared.plot import savefig


# mmol C s^-1 -> GtC yr^-1
# (1e-3 mol/mmol) * (12.011 g/mol) * (1e-15 Gt/g) * (365.25*24*3600 s/yr)
MMOLC_PER_S_TO_GTC_PER_YR = 1.0e-3 * 12.011 * 1.0e-15 * 365.25 * 24.0 * 3600.0
OVERLAY_YEAR_DIFF_THRESHOLD = 50.0


class TimeSeriesOceanBGCFlux(AnalysisTask):
    """Plot global ocean BGC CO2-flux model time series against observations."""

    def __init__(self, config, mpasTimeSeriesTask, controlConfig=None):
        super().__init__(
            config=config,
            taskName='timeSeriesOceanBGCFlux',
            componentName='ocean',
            tags=['timeSeries', 'BGC', 'publicObs'])

        self.mpasTimeSeriesTask = mpasTimeSeriesTask
        self.controlConfig = controlConfig
        self.run_after(mpasTimeSeriesTask)

    def check_generate(self):
        if not super().check_generate():
            return False

        generateList = self.config.getexpression('output', 'generate')
        if self.taskName in generateList or 'all' in generateList:
            return True

        for element in generateList:
            if element == 'BGC':
                return True
            if '_' in element:
                prefix, suffix = element.split('_', 1)
                if prefix in ['all', 'only'] and suffix == 'BGC':
                    return True

        return False

    def _download_obs_file(self, relativePath, outFileName):
        section = self.taskName
        if not self.config.has_option(section, 'remoteObservationsBaseUrl'):
            return

        remoteBaseUrl = self.config.get(section, 'remoteObservationsBaseUrl')
        relativePosix = PurePosixPath(relativePath)
        urlBase = remoteBaseUrl.rstrip('/')
        if str(relativePosix.parent) != '.':
            urlBase = f"{urlBase}/{relativePosix.parent.as_posix()}"

        download_files([relativePosix.name], urlBase, os.path.dirname(outFileName))

    def setup_and_check(self):
        super().setup_and_check()

        config = self.config
        section = self.taskName

        self.startDate = config.get('timeSeries', 'startDate')
        self.endDate = config.get('timeSeries', 'endDate')

        self.modelFieldName = config.get(section, 'modelFieldName')
        self.modelLegendLabel = config.get('runs', 'mainRunName')
        self.obsLegendLabel = config.get(section, 'obsLegendLabel')

        self.variableList = [self.modelFieldName]
        self.mpasTimeSeriesTask.add_variables(variableList=self.variableList)
        self.inputFile = self.mpasTimeSeriesTask.outputFile
        self.meshFilename = self.get_mesh_filename()

        obsPath = config.get(section, 'obsFileName')
        self.obsFileName = build_obs_path(
            config, component='ocean', relativePath=obsPath)

        if not os.path.exists(self.obsFileName):
            self._download_obs_file(obsPath, self.obsFileName)

        if not os.path.exists(self.obsFileName):
            raise OSError(f'Observation file not found: {self.obsFileName}')

        self.xmlFileNames = [
            f'{self.plotsDirectory}/timeSeriesOceanBGCFlux.xml']

    def _compute_model_global_flux(self, config):
        dsMesh = xr.open_dataset(self.meshFilename)
        areaCell = dsMesh.areaCell

        dsModel = open_mpas_dataset(
            fileName=self.inputFile,
            calendar=self.calendar,
            variableList=[self.modelFieldName],
            startDate=self.startDate,
            endDate=self.endDate)

        modelField = dsModel[self.modelFieldName]

        # The field is a surface flux with units equivalent to mmol C m^-2 s^-1.
        # Multiply by cell area to get mmol C s^-1 per cell, sum globally,
        # then convert to GtC yr^-1.
        modelGlobal = (modelField * areaCell).sum(dim='nCells')
        modelGlobal = modelGlobal * MMOLC_PER_S_TO_GTC_PER_YR
        modelGlobal.attrs['units'] = 'GtC yr-1'
        return modelGlobal

    def _load_obs(self, config):
        section = self.taskName
        dsObs = xr.open_dataset(self.obsFileName)

        obsTimeVar = config.get(section, 'obsTimeVariable')
        obsYearVar = config.get(section, 'obsYearVariable')
        obsMeanVar = config.get(section, 'obsMeanVariable')
        obsLowVar = config.get(section, 'obsLowVariable')
        obsHighVar = config.get(section, 'obsHighVariable')

        obsTime = dsObs[obsTimeVar]
        obsYear = dsObs[obsYearVar] if obsYearVar in dsObs.variables else None
        obsMean = dsObs[obsMeanVar]
        obsLow = dsObs[obsLowVar]
        obsHigh = dsObs[obsHighVar]

        return obsTime, obsYear, obsMean, obsLow, obsHigh

    @staticmethod
    def _to_decimal_year_axis(timeCoord, preferredYears=None):
        """Convert time values to decimal years for robust mixed-type plotting."""

        if preferredYears is not None:
            return np.asarray(preferredYears.values, dtype=float)

        values = np.asarray(timeCoord.values)

        def _from_date_like(dateValues):
            out = []
            for value in dateValues:
                year = float(getattr(value, 'year'))
                month = float(getattr(value, 'month', 7))
                out.append(year + (month - 0.5) / 12.0)
            return np.asarray(out, dtype=float)

        if np.issubdtype(values.dtype, np.datetime64):
            years = values.astype('datetime64[Y]').astype(int) + 1970
            months = values.astype('datetime64[M]').astype(int) % 12 + 1
            return years + (months - 0.5) / 12.0

        if np.issubdtype(values.dtype, np.number):
            units = timeCoord.attrs.get('units', '')
            if 'since' in units:
                calendar = timeCoord.attrs.get('calendar', 'standard')
                try:
                    import cftime
                    dateValues = cftime.num2date(values, units, calendar)
                    return _from_date_like(dateValues)
                except Exception:
                    pass

            out = values.astype(float)
            maxAbs = np.nanmax(np.abs(out)) if out.size > 0 else 0.0

            # Fallback for MPAS numeric time that can arrive without usable
            # units after preprocessing: interpret very large values as
            # elapsed days or seconds and map approximately to years.
            if maxAbs > 1.0e7:
                out = out / (365.25 * 24.0 * 3600.0) + 1.0
            elif maxAbs > 1.0e4:
                out = out / 365.25 + 1.0

            return out

        # Fall back to cftime-like objects with year/month attributes.
        return _from_date_like(values)

    def run_task(self):
        self.logger.info('\nPlotting ocean BGC CO2-flux time series...')

        config = self.config
        section = self.taskName

        movingAveragePoints = config.getint(section, 'movingAveragePoints')
        title = config.get(section, 'title')
        xLabel = 'Time [years]'
        yLabel = config.get(section, 'plotUnitsLabel')

        outputDirectory = os.path.join(self.plotsDirectory)
        make_directories(outputDirectory)

        modelGlobal = self._compute_model_global_flux(config)

        if movingAveragePoints > 1:
            modelGlobal = (
                modelGlobal.to_series()
                .rolling(movingAveragePoints, center=True)
                .mean()
                .to_xarray()
            )

        controlGlobal = None
        controlRunName = None
        if self.controlConfig is not None:
            controlSection = section
            controlFieldName = self.controlConfig.get(controlSection,
                                                      'modelFieldName')

            baseDirectory = build_config_full_path(
                self.controlConfig, 'output', 'timeSeriesSubdirectory')
            controlFileName = (
                f'{baseDirectory}/{self.mpasTimeSeriesTask.fullTaskName}.nc')

            dsControl = open_mpas_dataset(
                fileName=controlFileName,
                calendar=self.calendar,
                variableList=[controlFieldName],
                startDate=self.controlConfig.get('timeSeries', 'startDate'),
                endDate=self.controlConfig.get('timeSeries', 'endDate'))
            dsMesh = xr.open_dataset(self.meshFilename)
            controlGlobal = (
                dsControl[controlFieldName] * dsMesh.areaCell
            ).sum(dim='nCells') * MMOLC_PER_S_TO_GTC_PER_YR
            controlRunName = self.controlConfig.get('runs', 'mainRunName')

        obsTime, obsYear, obsMean, obsLow, obsHigh = self._load_obs(config)
        obsTimeValues = self._to_decimal_year_axis(obsTime, preferredYears=obsYear)
        modelTimeValues = self._to_decimal_year_axis(modelGlobal.Time)

        fig = plt.figure(figsize=(12, 6))
        ax = fig.add_subplot(111)

        # Always show the full observation record, independent of model bounds.
        ax.fill_between(
            obsTimeValues,
            obsLow.values,
            obsHigh.values,
            alpha=0.25,
            color='gray',
            linewidth=0,
            label=f'{self.obsLegendLabel} range')
        ax.plot(
            obsTimeValues,
            obsMean.values,
            color=config.get('timeSeries', 'obsColor1'),
            linewidth=2.0,
            label=self.obsLegendLabel)

        obsYearMin = float(np.nanmin(obsTimeValues))
        obsYearMax = float(np.nanmax(obsTimeValues))
        modelYearMin = float(np.nanmin(modelTimeValues))
        modelYearMax = float(np.nanmax(modelTimeValues))

        # If model years are fully outside obs range, compute distance to the
        # nearest obs bound and hide original model curve when too far away.
        if modelYearMax < obsYearMin:
            nearestBoundGap = obsYearMin - modelYearMax
        elif modelYearMin > obsYearMax:
            nearestBoundGap = modelYearMin - obsYearMax
        else:
            nearestBoundGap = 0.0

        showOriginalModel = nearestBoundGap <= OVERLAY_YEAR_DIFF_THRESHOLD

        xMinCandidates = [obsYearMin]
        xMaxCandidates = [obsYearMax + 1.0]

        if showOriginalModel:
            ax.plot(
                modelTimeValues,
                modelGlobal.values,
                color='black',
                linestyle='--',
                linewidth=1.0,
                marker='o',
                markersize=4.5,
                markerfacecolor='black',
                markeredgecolor='black',
                label=self.modelLegendLabel)
            xMinCandidates.append(modelYearMin)
            xMaxCandidates.append(modelYearMax)

        modelYearCenter = float(np.nanmean(modelTimeValues))
        obsYearCenter = float(np.nanmean(obsTimeValues))
        yearCenterDiff = abs(obsYearCenter - modelYearCenter)

        # If model and observations are far apart in absolute year, overlay a
        # shifted model curve for visual shape comparison.
        if yearCenterDiff > OVERLAY_YEAR_DIFF_THRESHOLD:
            yearShift = obsYearCenter - modelYearCenter
            yearsOverlay = np.array(modelTimeValues, dtype=float) + yearShift
            shiftLabel = (
                f'{self.modelLegendLabel} overlay '
                f'(shift {yearShift:+.1f} y)')
            ax.plot(
                yearsOverlay,
                modelGlobal.values,
                color='black',
                linestyle='--',
                linewidth=1.0,
                marker='o',
                markersize=4.5,
                markerfacecolor='black',
                markeredgecolor='black',
                alpha=0.8,
                label=shiftLabel)
            xMinCandidates.append(float(np.nanmin(yearsOverlay)))
            xMaxCandidates.append(float(np.nanmax(yearsOverlay)))

        self.logger.info(
            f'Model/obs center-year difference: {yearCenterDiff:.1f} years')
        self.logger.info(
            f'Model distance outside nearest obs bound: {nearestBoundGap:.1f} '
            f'years')
        self.logger.info(
            f'Original model curve shown: {showOriginalModel}')
        self.logger.info(
            f'Overlay mode enabled: '
            f'{yearCenterDiff > OVERLAY_YEAR_DIFF_THRESHOLD}')

        if controlGlobal is not None:
            ax.plot(
                self._to_decimal_year_axis(controlGlobal.Time),
                controlGlobal.values,
                color=config.get('timeSeries', 'controlColor'),
                linewidth=1.8,
                label=controlRunName)

        ax.set_xlim(min(xMinCandidates), max(xMaxCandidates))
        ax.set_xlabel(xLabel)
        ax.set_ylabel(yLabel)
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best')

        outFileName = f'{self.plotsDirectory}/timeSeriesOceanBGCFlux.png'
        savefig(outFileName, config)
        plt.close(fig)

        caption = 'Running Mean of Global Ocean CO2 Flux'
        write_image_xml(
            config=config,
            filePrefix='timeSeriesOceanBGCFlux',
            componentName='Ocean',
            componentSubdirectory='ocean',
            galleryGroup='BGC Timeseries',
            groupLink='bgc_timeseries',
            thumbnailDescription='Global Ocean CO2 Flux',
            imageDescription=caption,
            imageCaption=caption)
