# noqa: E501
from PySide2.QtCore import QObject, Signal, Property

# from easyDiffractionApp.Logic.LogicController import LogicController
from easyDiffractionApp.Logic.Proxies.Background import BackgroundProxy
from easyDiffractionApp.Logic.Proxies.Experiment import ExperimentProxy
from easyDiffractionApp.Logic.Proxies.Fitting import FittingProxy
from easyDiffractionApp.Logic.Proxies.Parameters import ParametersProxy
from easyDiffractionApp.Logic.Proxies.Phase import PhaseProxy
from easyDiffractionApp.Logic.Proxies.Plotting1d import Plotting1dProxy
from easyDiffractionApp.Logic.Proxies.Plotting3d import Plotting3dProxy
from easyDiffractionApp.Logic.Proxies.Project import ProjectProxy
from easyDiffractionApp.Logic.Proxies.Stack import StackProxy
from easyDiffractionLib.interface import InterfaceFactory


class PyQmlProxy(QObject):
    # SIGNALS
    currentCalculatorChanged = Signal()

    # Status info
    statusInfoChanged = Signal()
    parametersChanged = Signal()

    # Misc
    dummySignal = Signal()

    # METHODS

    def __init__(self, parent=None):
        super().__init__(parent)

        self._screen_recorder = self.recorder()

        ################## proxies #################
        # interface = self.lc.interface
        interface = InterfaceFactory()
        self._plotting_1d_proxy = Plotting1dProxy()
        self._plotting_3d_proxy = Plotting3dProxy()
        self._parameters_proxy = ParametersProxy(self, interface=interface)
        self._project_proxy = ProjectProxy(self, interface=interface)
        self._experiment_proxy = ExperimentProxy(self)
        self._phase_proxy = PhaseProxy(self, interface=interface)
        no_history = [self.parametersChanged]
        with_history = [self.phase.phaseAdded, self.parametersChanged]
        self._stack_proxy = StackProxy(self, callbacks_no_history=no_history,
                                       callbacks_with_history=with_history)
        self._background_proxy = BackgroundProxy(self)
        self._fitting_proxy = FittingProxy(self, interface=interface)

        ################## signals from other proxies #################
        self.currentCalculatorChanged.connect(self.statusInfoChanged)
        self._fitting_proxy.currentMinimizerChanged.connect(self.statusInfoChanged)
        self._fitting_proxy.currentMinimizerMethodChanged.connect(self.statusInfoChanged)
        # Constraints
        self._fitting_proxy.constraintsChanged.connect(self._parameters_proxy._setParametersAsObj)
        self._fitting_proxy.constraintsChanged.connect(self._parameters_proxy._setParametersAsXml)
        self._fitting_proxy.constraintsChanged.connect(self._parameters_proxy._onSimulationParametersChanged)

        self._fitting_proxy.fitFinished.connect(self.parametersChanged)
        self._fitting_proxy.currentCalculatorChanged.connect(self.statusInfoChanged)

        self._background_proxy.asObjChanged.connect(self._parameters_proxy.parametersChanged)
        self._background_proxy.asObjChanged.connect(self.phase._sample.set_background)
        self._background_proxy.asObjChanged.connect(self._parameters_proxy._updateCalculatedData)

        self._project_proxy.phasesEnabled.connect(self._phase_proxy.phasesEnabled)
        self._project_proxy.phasesAsObjChanged.connect(self._phase_proxy.phasesAsObjChanged)
        self._project_proxy.experimentDataAdded.connect(self._experiment_proxy._onExperimentDataAdded)
        self._project_proxy.structureParametersChanged.connect(self._phase_proxy.structureParametersChanged)
        self._project_proxy.removePhaseSignal.connect(self._phase_proxy.removePhase)
        self._project_proxy.experimentLoadedChanged.connect(self._experiment_proxy.experimentLoadedChanged)
        self._phase_proxy.updateProjectInfo.connect(self._project_proxy.updateProjectInfo)

        self.parameters.parametersValuesChanged.connect(self.parametersChanged)
        self.parameters.undoRedoChanged.connect(self._stack_proxy.undoRedoChanged)
        self.parameters.plotCalculatedDataSignal.connect(self._plotting_1d_proxy.plotCalculatedData)
        self.parameters.plotBraggDataSignal.connect(self._plotting_1d_proxy.plotBraggData)
        self.parameters.simulationParametersChanged.connect(self._stack_proxy.undoRedoChanged)

        self.parametersChanged.connect(self.phase.structureParametersChanged)
        self.parametersChanged.connect(self.experiment._onPatternParametersChanged)
        self.parametersChanged.connect(self.parameters.instrumentParametersChanged)
        self.parametersChanged.connect(self.parameters._updateCalculatedData)

        self.parametersChanged.connect(self.stack.undoRedoChanged)

        # start the undo/redo stack
        self.stack.initializeBorg()

    ####################################################################################################################
    ####################################################################################################################
    # Proxies
    ####################################################################################################################
    ####################################################################################################################

    # 1d plotting
    @Property('QVariant', notify=dummySignal)
    def plotting1d(self):
        return self._plotting_1d_proxy

    # 3d plotting
    @Property('QVariant', notify=dummySignal)
    def plotting3d(self):
        return self._plotting_3d_proxy

    # background
    @Property('QVariant', notify=dummySignal)
    def background(self):
        return self._background_proxy

    # experiment
    @Property('QVariant', notify=dummySignal)
    def experiment(self):
        return self._experiment_proxy

    # fitting
    @Property('QVariant', notify=dummySignal)
    def fitting(self):
        return self._fitting_proxy

    # project
    @Property('QVariant', notify=dummySignal)
    def project(self):
        return self._project_proxy

    # stack
    @Property('QVariant', notify=dummySignal)
    def stack(self):
        return self._stack_proxy

    # phase
    @Property('QVariant', notify=dummySignal)
    def phase(self):
        return self._phase_proxy

    # parameters
    @Property('QVariant', notify=dummySignal)
    def parameters(self):
        return self._parameters_proxy

    # status
    @Property('QVariant', notify=statusInfoChanged)
    def statusModelAsObj(self):
        return self.fitting.statusModelAsObj()

    @Property(str, notify=statusInfoChanged)
    def statusModelAsXml(self):
        return self.fitting.statusModelAsXml()

    # screen recorder
    @Property('QVariant', notify=dummySignal)
    def screenRecorder(self):
        return self._screen_recorder

    def recorder(self):
        rec = None
        try:
            from easyDiffractionApp.Logic.ScreenRecorder import ScreenRecorder
            rec = ScreenRecorder()
        except (ImportError, ModuleNotFoundError):
            print('Screen recording disabled')
        return rec
