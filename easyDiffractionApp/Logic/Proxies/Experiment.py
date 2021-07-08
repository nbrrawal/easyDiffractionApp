
from dicttoxml import dicttoxml
import pathlib
import json

from easyCore import np
from easyApp.Logic.Utils.Utils import generalizePath
from PySide2.QtCore import QObject, Signal, Slot, Property


class ExperimentProxy(QObject):

    dummySignal = Signal()
    experimentDataChanged = Signal()
    projectInfoChanged = Signal()
    stateChanged = Signal()
    experimentDataAsXmlChanged = Signal()
    experimentLoadedChanged = Signal()
    experimentSkippedChanged = Signal()
    patternParametersAsObjChanged = Signal()
    clearFrontendState = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.experimentDataChanged.connect(self._onExperimentDataChanged)
        self.experimentSkippedChanged.connect(self._onExperimentSkippedChanged)
        self.experimentLoadedChanged.connect(self._onExperimentLoadedChanged)
        self.patternParametersAsObjChanged.connect(self.parent.parameters.patternParametersAsObjChanged)

        self._experiment_parameters = None
        self._experiment_data_as_xml = ""
        self.experiment_data = None
        self._experiment_data = None
        self._experiment_loaded = False
        self._experiment_skipped = False
        self.experiments = self._defaultExperiments()
        self.clearFrontendState.connect(self.onClearFrontendState)

    @Property('QVariant', notify=experimentDataChanged)
    def experimentDataAsObj(self):
        return [{'name': experiment.name} for experiment in self.parent._parameters_proxy._data.experiments]

    @Slot(str)
    def setCurrentExperimentDatasetName(self, name):
        self.parent.phase.setCurrentExperimentDatasetName(name)
        self.experimentDataChanged.emit()
        self.parent.project.projectInfoChanged.emit()

    ####################################################################################################################
    ####################################################################################################################
    # EXPERIMENT
    ####################################################################################################################
    ####################################################################################################################

    def _defaultExperiment(self):
        return {
            "label": "D1A@ILL",
            "color": "#00a3e3"
        }

    @Property(str, notify=experimentDataAsXmlChanged)
    def experimentDataAsXml(self):
        return self._experiment_data_as_xml

    def _setExperimentDataAsXml(self):
        print("+ _setExperimentDataAsXml")
        self._experiment_data_as_xml = dicttoxml(self.experiments, attr_type=True).decode()  # noqa: E501
        self.experimentDataAsXmlChanged.emit()

    def _onExperimentDataChanged(self):
        print("***** _onExperimentDataChanged")
        self._setExperimentDataAsXml()
        self.parent.project.stateChanged.emit(True)

    ####################################################################################################################
    # Experiment data: Add / Remove
    ####################################################################################################################

    @Slot(str)
    def addExperimentDataFromXye(self, file_url):
        self._experiment_data = self._loadExperimentData(file_url)
        self.parent._parameters_proxy._data.experiments[0].name = pathlib.Path(file_url).stem
        self.experiments = [{'name': experiment.name} for experiment in self.parent._parameters_proxy._data.experiments]
        self.experimentLoaded = True
        self.experimentSkipped = False
        self._onExperimentDataAdded()
        self.experimentLoadedChanged.emit()

    @Slot()
    def removeExperiment(self):
        print("+ removeExperiment")
        self.experiments.clear()
        self.experimentLoaded = False
        self.experimentSkipped = False
        self._onExperimentDataRemoved()
        self.experimentLoadedChanged.emit()

    def _loadExperimentData(self, file_url):
        print("+ _loadExperimentData")
        file_path = generalizePath(file_url)
        data = self.parent._parameters_proxy._data.experiments[0]
        data.x, data.y, data.e = np.loadtxt(file_path, unpack=True)
        return data

    def _onExperimentDataRemoved(self):
        print("***** _onExperimentDataRemoved")
        self.clearFrontendState.emit()
        self.experimentDataChanged.emit()

    @Property(bool, notify=experimentLoadedChanged)
    def experimentLoaded(self):
        return self._experiment_loaded

    @experimentLoaded.setter
    def experimentLoaded(self, loaded: bool):
        if self._experiment_loaded == loaded:
            return
        self._experiment_loaded = loaded
        self.experimentLoadedChanged.emit()

    @Property(bool, notify=experimentSkippedChanged)
    def experimentSkipped(self):
        return self._experiment_skipped

    @experimentSkipped.setter
    def experimentSkipped(self, skipped: bool):
        if self._experiment_skipped == skipped:
            return
        self._experiment_skipped = skipped
        self.experimentSkippedChanged.emit()

    def _onExperimentLoadedChanged(self):
        print("***** _onExperimentLoadedChanged")
        if self.experimentLoaded:
            self.parent.parameters._onParametersChanged()
            self.parent.parameters._onInstrumentParametersChanged()
            self._setPatternParametersAsObj()

    def _onExperimentSkippedChanged(self):
        print("***** _onExperimentSkippedChanged")
        if self.experimentSkipped:
            self.parent.parameters._onParametersChanged()
            self.parent.parameters._onInstrumentParametersChanged()
            self._setPatternParametersAsObj()
            self.parent._parameters_proxy._updateCalculatedData()

    def _setPatternParametersAsObj(self):
        self.parent._parameters_proxy._setPatternParametersAsObj()
        self.patternParametersAsObjChanged.emit()

    def _onExperimentDataAdded(self):
        print("***** _onExperimentDataAdded")
        self.parent.plotting1d.setMeasuredData(
                                          self._experiment_data.x,
                                          self._experiment_data.y,
                                          self._experiment_data.e)
        self._experiment_parameters = \
            self._experimentDataParameters(self._experiment_data)

        self.parent.parameters.simulationParametersAsObj = \
            json.dumps(self._experiment_parameters)

        if len(self.parent.phase._sample.pattern.backgrounds) == 0:
            self.parent.background.initializeContainer()

        self.experimentDataChanged.emit()
        self.parent.project._project_info['experiments'] = \
            self.parent.parameters._data.experiments[0].name

        self.parent.project.projectInfoChanged.emit()

    def onClearFrontendState(self):
        self.parent.plotting1d.clearFrontendState()

    def _experimentDataParameters(self, data):
        x_min = data.x[0]
        x_max = data.x[-1]
        x_step = (x_max - x_min) / (len(data.x) - 1)
        parameters = {
            "x_min":  x_min,
            "x_max":  x_max,
            "x_step": x_step
        }
        return parameters

    def _onPatternParametersChanged(self):
        self.parent._parameters_proxy._setPatternParametersAsObj()
        self.patternParametersAsObjChanged.emit()

    def experimentDataXYZ(self):
        return (self._experiment_data.x, self._experiment_data.y, self._experiment_data.e)  # noqa: E501

    def _defaultExperiments(self):
        return []