import json

from PySide2.QtCore import QObject, Signal

# from easyDiffractionApp.Logic.Background import BackgroundLogic
from easyDiffractionApp.Logic.Experiment import ExperimentLogic
# from easyDiffractionApp.Logic.Fitting import FittingLogic
# from easyDiffractionApp.Logic.Parameters import ParametersLogic
from easyDiffractionApp.Logic.Phase import PhaseLogic
from easyDiffractionApp.Logic.Plotting1d import Plotting1dLogic
from easyDiffractionApp.Logic.Plotting3d import Plotting3dLogic
# from easyDiffractionApp.Logic.Project import ProjectLogic
from easyDiffractionApp.Logic.Stack import StackLogic
from easyDiffractionApp.Logic.State import StateLogic
from easyDiffractionLib.interface import InterfaceFactory


class LogicController(QObject):
    parametersChanged = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.proxy = parent
        self.interface = InterfaceFactory()

        # Screen recorder
        self._screen_recorder = self.recorder()

        # instantiate logics
        self.initializeLogics()

        # define signal forwarders
        self.setupSignals()

    def initializeLogics(self):
        self.l_state = StateLogic(self, interface=self.interface)
        self.l_experiment = ExperimentLogic(self)
        self.l_phase = PhaseLogic(self, interface=self.interface)
        self.l_plotting1d = Plotting1dLogic(self)
        self.l_plotting3d = Plotting3dLogic(self)
        # stack logic
        no_history = [self.proxy.parametersChanged]
        with_history = [self.l_phase.phaseAdded, self.parametersChanged]
        self.l_stack = StackLogic(self, self.proxy,
                                  callbacks_no_history=no_history,
                                  callbacks_with_history=with_history)

    def setupSignals(self):
        pass
        # self.parametersChanged.connect(self.l_phase.structureParametersChanged)
        # self.parametersChanged.connect(self.l_experiment._onPatternParametersChanged)
        # self.parametersChanged.connect(self.proxy.parameters.instrumentParametersChanged)
        # self.parametersChanged.connect(self.proxy.parameters._updateCalculatedData)

        # self.parametersChanged.connect(self.l_stack.undoRedoChanged)

        # self.l_phase.updateProjectInfo.connect(self.proxy.project.updateProjectInfo)

    def resetFactory(self):
        self.interface = InterfaceFactory()

    def plotCalculatedData(self, data):
        self.l_plotting1d.setCalculatedData(data[0], data[1])

    def plotBraggData(self, data):
        self.l_plotting1d.setBraggData(data[0], data[1], data[2], data[3])  # noqa: E501

    def initializeBorg(self):
        self.l_stack.initializeBorg()

    def resetState(self):
        self.l_plotting1d.clearBackendState()
        self.l_plotting1d.clearFrontendState()
        self.l_stack.resetUndoRedoStack()
        self.l_stack.undoRedoChanged.emit()

    def removePhase(self, phase_name: str):
        if self.l_phase.removePhase(phase_name):
            self.l_phase.structureParametersChanged.emit()
            self.l_phase.phasesEnabled.emit()

    def recorder(self):
        rec = None
        try:
            from easyDiffractionApp.Logic.ScreenRecorder import ScreenRecorder
            rec = ScreenRecorder()
        except (ImportError, ModuleNotFoundError):
            print('Screen recording disabled')
        return rec
