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

import xarray

from mpas_analysis.shared.climatology import MpasClimatologyTask


class MpasSnapshotTask(MpasClimatologyTask):
    """
    An analysis task for computing snapshot climatologies (single month/date)
    from output from the ``timeSeriesStatsMonthly*`` analysis members.

    Snapshot tasks compute climatologies for a single specified date range
    rather than aggregating over a full year. They always use xarray-based
    computation (never ncclimo) and read dates from the config file directly.

    Attributes
    ----------
    All attributes inherited from ``MpasClimatologyTask``

    """

    # Authors
    # -------
    # Xylar Asay-Davis

    def __init__(self, config, componentName, taskName=None, op='avg'):
        """
        Construct the analysis task.

        Parameters
        ----------
        config : tranche.Tranche
            Contains configuration options

        componentName : {'ocean', 'seaIce'}
            The name of the component (same as the folder where the task
            resides)

        op : {'avg', 'min', 'max'}, optional
             operator for monthly stats

        taskName : str, optional
            the name of the task, defaults to
            mpasSnapshot<ComponentName><Op>
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        if taskName is None:
            suffix = componentName[0].upper() + componentName[1:] + \
                     op[0].upper() + op[1:]
            taskName = 'mpasSnapshot{}'.format(suffix)

        # call the constructor from the base class (MpasClimatologyTask)
        # Note: parent __init__ will call super().__init__() which sets up
        # season subtasks and other attributes
        super(MpasSnapshotTask, self).__init__(
            config=config,
            componentName=componentName,
            taskName=taskName,
            op=op)

        # Override: Snapshot mode always uses xarray (never ncclimo)
        self.useNcclimo = False
        self.subprocessCount = 1

        self.tags.append('snapshot')

    def setup_and_check(self):
        """
        Perform steps to set up the analysis and check for errors in the setup.

        In snapshot mode, dates are read directly from the config file rather
        than computed from start/end years.

        Raises
        ------
        IOError :
            If a restart file is not available from which to read mesh
            information or if no history files are available from which to
            compute the climatology in the desired time range.
        """
        # Authors
        # -------
        # Xylar Asay-Davis

        # Call parent's parent (AnalysisTask) setup to avoid the year-based
        # date logic in MpasClimatologyTask.setup_and_check()
        from mpas_analysis.shared.analysis_task import AnalysisTask
        AnalysisTask.setup_and_check(self)

        self.startYear, self.endYear = self.get_start_and_end()

        # In snapshot mode, use dates from config directly
        self.startDate = self.config.get('climatology', 'startDate')
        self.endDate = self.config.get('climatology', 'endDate')

        if self.op == 'avg':
            self.check_analysis_enabled(
                analysisOptionName='config_am_timeseriesstatsmonthly_enable',
                raiseException=True)
        elif self.op == 'min':
            self.check_analysis_enabled(
                analysisOptionName='config_AM_timeSeriesStatsMonthlyMin_enable',
                raiseException=True)
        elif self.op == 'max':
            self.check_analysis_enabled(
                analysisOptionName='config_AM_timeSeriesStatsMonthlyMax_enable',
                raiseException=True)

        # get a list of timeSeriesSta output files from the streams file,
        # reading only those that are between the start and end dates
        self.inputFiles = self.historyStreams.readpath(
            self.streamName, startDate=self.startDate, endDate=self.endDate,
            calendar=self.calendar)

        if len(self.inputFiles) == 0:
            raise IOError('No files were found in stream {} between {} and '
                          '{}.'.format(self.streamName, self.startDate,
                                       self.endDate))

        self.symlinkDirectory = self._create_symlinks()

        with xarray.open_dataset(self.inputFiles[0],
                                 decode_timedelta=False) as ds:
            self.allVariables = list(ds.data_vars.keys())
