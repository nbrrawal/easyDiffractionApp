# noqa: E501
from PySide2.QtCore import QObject, Signal, Property

from easyDiffractionApp.Logic.LogicController import LogicController
from easyDiffractionApp.Logic.Proxies.Background import BackgroundProxy
from easyDiffractionApp.Logic.Proxies.Experiment import ExperimentProxy
from easyDiffractionApp.Logic.Proxies.Fitting import FittingProxy
from easyDiffractionApp.Logic.Proxies.Parameters import ParametersProxy
from easyDiffractionApp.Logic.Proxies.Phase import PhaseProxy
from easyDiffractionApp.Logic.Proxies.Plotting1d import Plotting1dProxy
from easyDiffractionApp.Logic.Proxies.Plotting3d import Plotting3dProxy
from easyDiffractionApp.Logic.Proxies.Project import ProjectProxy
from easyDiffractionApp.Logic.Proxies.Stack import StackProxy


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

        # Initialize logics
        self.lc = LogicController(self)

        ################## proxies #################
        interface = self.lc.interface
        self._plotting_1d_proxy = Plotting1dProxy()
        self._plotting_3d_proxy = Plotting3dProxy()
        self._stack_proxy = StackProxy(self, logic=self.lc)
        self._parameters_proxy = ParametersProxy(self, interface=interface)
        self._project_proxy = ProjectProxy(self, interface=interface)
        self._experiment_proxy = ExperimentProxy(self, logic=self.lc)
        self._phase_proxy = PhaseProxy(self, logic=self.lc)
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
        self._background_proxy.asObjChanged.connect(self.lc.l_phase._sample.set_background)
        self._background_proxy.asObjChanged.connect(self._parameters_proxy._updateCalculatedData)

        self._project_proxy.reset.connect(self.lc.resetState)
        self._project_proxy.phasesEnabled.connect(self._phase_proxy.logic.phasesEnabled)
        self._project_proxy.phasesAsObjChanged.connect(self._phase_proxy.logic.phasesAsObjChanged)
        self._project_proxy.experimentDataAdded.connect(self._experiment_proxy.logic._onExperimentDataAdded)
        self._project_proxy.structureParametersChanged.connect(self._phase_proxy.logic.structureParametersChanged)
        self._project_proxy.removePhaseSignal.connect(self.lc.removePhase)
        self._project_proxy.experimentLoadedChanged.connect(self._experiment_proxy.logic.experimentLoadedChanged)
        self._phase_proxy.logic.updateProjectInfo.connect(self._project_proxy.updateProjectInfo)

        self.parameters.parametersValuesChanged.connect(self.lc.parametersChanged)
        self.parameters.undoRedoChanged.connect(self._stack_proxy.logic.undoRedoChanged)
        self.parameters.plotCalculatedDataSignal.connect(self.plotCalculatedData)
        self.parameters.plotBraggDataSignal.connect(self.plotBraggData)
        # self.parameters.plotCalculatedDataSignal.connect(self._plotting_1d_proxy.setCalculatedData)
        # self.parameters.plotBraggDataSignal.connect(self._plotting_1d_proxy.setBraggData)

        self.parametersChanged.connect(self.lc.l_phase.structureParametersChanged)
        self.parametersChanged.connect(self.lc.l_experiment._onPatternParametersChanged)
        self.parametersChanged.connect(self.parameters.instrumentParametersChanged)
        self.parametersChanged.connect(self.parameters._updateCalculatedData)

        self.parametersChanged.connect(self.lc.l_stack.undoRedoChanged)

        # start the undo/redo stack
        self.lc.initializeBorg()

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

    def plotCalculatedData(self, data):
        self.plotting1d.setCalculatedData(data[0], data[1])

    def plotBraggData(self, data):
        self.plotting1d.setBraggData(data[0], data[1], data[2], data[3])  # noqa: E501

    # status
    @Property('QVariant', notify=statusInfoChanged)
    def statusModelAsObj(self):
        engine_name = self.fitting.fitter.current_engine.name
        minimizer_name = self.fitting._current_minimizer_method_name
        return self.lc.l_state.statusModelAsObj(engine_name, minimizer_name)

        # return self.lc.statusModelAsObj()

    @Property(str, notify=statusInfoChanged)
    def statusModelAsXml(self):
        #return self.lc.statusModelAsXml()
        engine_name = self.fitting.fitter.current_engine.name
        minimizer_name = self.fitting._current_minimizer_method_name
        return self.lc.l_state.statusModelAsXml(engine_name, minimizer_name)

    # screen recorder
    @Property('QVariant', notify=dummySignal)
    def screenRecorder(self):
        return self.lc._screen_recorder
