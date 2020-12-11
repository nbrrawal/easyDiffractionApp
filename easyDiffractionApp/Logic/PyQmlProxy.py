import json
from dicttoxml import dicttoxml

import timeit

from PySide2.QtCore import QObject, Slot, Signal, Property

from easyCore import np
from easyCore import borg
# borg.debug = True

from easyCore.Symmetry.tools import SpacegroupInfo
from easyCore.Fitting.Fitting import Fitter
from easyCore.Fitting.Constraints import ObjConstraint, NumericConstraint
from easyCore.Utils.classTools import generatePath
from easyDiffractionLib.Elements.Backgrounds.Point import PointBackground, BackgroundPoint

from easyDiffractionLib.sample import Sample
from easyDiffractionLib import Phases, Phase, Lattice, Site, Atoms, SpaceGroup
from easyDiffractionLib.interface import InterfaceFactory
from easyDiffractionLib.Elements.Experiments.Experiment import Pars1D
from easyDiffractionLib.Elements.Experiments.Pattern import Pattern1D

from easyAppLogic.Utils.Utils import generalizePath

from easyDiffractionApp.Logic.DataStore import DataSet1D, DataStore
from easyDiffractionApp.Logic.MatplotlibBackend import DisplayBridge


class PyQmlProxy(QObject):
    _borg = borg
    matplotlib_bridge = DisplayBridge()

    # SIGNALS

    # Misc
    projectInfoChanged = Signal()
    constraintsChanged = Signal()
    calculatorChanged = Signal()
    #modelChanged = Signal()
    backgroundChanged = Signal()
    instrumentResolutionChanged = Signal()
    simulationParametersChanged = Signal()
    currentPhaseSitesChanged = Signal()

    # Parameters
    parametersChanged = Signal()
    parametersAsObjChanged = Signal()
    parametersAsXmlChanged = Signal()
    parametersFilterCriteriaChanged = Signal()

    # Phases
    phaseAdded = Signal()
    phaseRemoved = Signal()
    phasesChanged = Signal()
    phasesAsListChanged = Signal()
    phasesAsXmlChanged = Signal()
    phasesAsCifChanged = Signal()
    currentPhaseChanged = Signal()

    # Experiment
    patternParametersChanged = Signal()
    patternParametersAsObjChanged = Signal()

    instrumentParametersChanged = Signal()
    instrumentParametersAsObjChanged = Signal()
    instrumentParametersAsXmlChanged = Signal()

    experimentDataAdded = Signal()
    experimentDataRemoved = Signal()
    experimentDataChanged = Signal()
    experimentDataAsXmlChanged = Signal()

    experimentLoadedChanged = Signal()
    experimentSkippedChanged = Signal()

    # Space Group
    spaceGroupChanged = Signal()

    # Atoms
    atomsChanged = Signal()

    # Structure View
    structureViewChanged = Signal()

    # Calculation
    calculatedDataChanged = Signal()

    # Minimizer
    currentMinimizerChanged = Signal()
    currentMinimizerMethodChanged = Signal()

    # Calculator
    currentCalculatorChanged = Signal()

    # Fitting
    fitFinished = Signal()
    fitResultsChanged = Signal()

    # Status info
    statusInfoChanged = Signal()


    # METHODS

    def __init__(self, parent=None):
        super().__init__(parent)

        # Main
        self._interface = InterfaceFactory()
        self._sample = self.defaultSample()

        # Charts
        self.vtkHandler = None
        self._experiment_figure_obj_name = None
        self._analysis_figure_obj_name = None
        self._difference_figure_obj_name = None

        # Project
        self._project_info = self._defaultProjectInfo()

        # Parameters
        self._parameters_as_obj = []
        self._parameters_as_xml = []

        self.parametersChanged.connect(self._onParametersChanged)
        self.parametersChanged.connect(self.phasesChanged)
        self.parametersChanged.connect(self.patternParametersChanged)
        self.parametersChanged.connect(self.instrumentParametersChanged)

        self._parameters_filter_criteria = ""
        self.parametersFilterCriteriaChanged.connect(self._onParametersFilterCriteriaChanged)

        # Phases
        self._phases_as_list = []
        self._phases_as_xml = ""
        self._phases_as_cif = ""

        self.phaseAdded.connect(self._onPhaseAdded)
        self.phaseRemoved.connect(self._onPhaseRemoved)

        self.phasesChanged.connect(self._onPhasesChanged)
        self.phasesChanged.connect(self.structureViewChanged)
        self.phasesChanged.connect(self.calculatedDataChanged)

        self._current_phase_index = 0
        self.currentPhaseChanged.connect(self._onCurrentPhaseChanged)

        # Simulation
        self._simulation_parameters_as_obj = self.defaultSimulationParameters()
        self._background = self.defaultBackground()
        self._data = self.defaultData()

        self.simulationParametersChanged.connect(self._onSimulationParametersChanged)

        # Experiment
        self._pattern_parameters_as_obj = self.defaultPatternParameters()
        self.patternParametersChanged.connect(self._onPatternParametersChanged)

        self._instrument_parameters_as_obj = self.defaultInstrumentParameters()
        self._instrument_parameters_as_xml = ""
        self.instrumentParametersChanged.connect(self._onInstrumentParametersChanged)

        self._experiment_parameters = None
        self._experiment_data = None
        self._experiment_data_as_xml = ""
        self.experiments = self.defaultExperiments()
        self.experimentDataChanged.connect(self._onExperimentDataChanged)
        self.experimentDataAdded.connect(self._onExperimentDataAdded)
        self.experimentDataRemoved.connect(self._onExperimentDataRemoved)

        self._experiment_loaded = False
        self._experiment_skipped = False
        self.experimentLoadedChanged.connect(self._onParametersChanged)
        self.experimentLoadedChanged.connect(self.patternParametersChanged)
        self.experimentLoadedChanged.connect(self.instrumentParametersChanged)
        self.experimentSkippedChanged.connect(self._onParametersChanged)
        self.experimentSkippedChanged.connect(self.patternParametersChanged)
        self.experimentSkippedChanged.connect(self.instrumentParametersChanged)

        # Space group
        self.spaceGroupChanged.connect(self._onSpaceGroupChanged)

        # Atoms
        self.atomsChanged.connect(self._onAtomsChanged)

        # Structure view
        self.structureViewChanged.connect(self._onStructureViewChanged)

        # Calculation
        self.calculatedDataChanged.connect(self._onCalculatedDataChanged)

        # Fitting
        self._fit_results = self.defaultFitResults()
        self.fitter = Fitter(self._sample, self._interface.fit_func)
        self.fitFinished.connect(self._onFitFinished)

        # Calculator
        self.currentCalculatorChanged.connect(self._onCurrentCalculatorChanged)

        # Minimizer
        self._current_minimizer_method_index = 0
        self._current_minimizer_method_name = self.fitter.available_methods()[0]
        self.currentMinimizerChanged.connect(self._onCurrentMinimizerChanged)
        self.currentMinimizerMethodChanged.connect(self._onCurrentMinimizerMethodChanged)

        # Status info
        self.statusInfoChanged.connect(self._onStatusInfoChanged)
        self.currentCalculatorChanged.connect(self.statusInfoChanged)
        self.currentMinimizerChanged.connect(self.statusInfoChanged)
        self.currentMinimizerMethodChanged.connect(self.statusInfoChanged)

    ####################################################################################################################
    ####################################################################################################################
    # Misc
    ####################################################################################################################
    ####################################################################################################################

    ####################################################################################################################
    # Charts
    ####################################################################################################################

    @Slot(str)
    def setExperimentFigureObjName(self, name):
        if self._experiment_figure_obj_name == name:
            return
        self._experiment_figure_obj_name = name

    @Slot(str)
    def setAnalysisFigureObjName(self, name):
        if self._analysis_figure_obj_name == name:
            return
        self._analysis_figure_obj_name = name

    @Slot(str)
    def setDifferenceFigureObjName(self, name):
        if self._difference_figure_obj_name == name:
            return
        self._difference_figure_obj_name = name

    @Slot(str)
    def updateFigureMargins(self, obj_name: str):
        self.matplotlib_bridge.updateWithCanvas(obj_name)

    ####################################################################################################################
    ####################################################################################################################
    # PROJECT
    ####################################################################################################################
    ####################################################################################################################

    ####################################################################################################################
    # Project
    ####################################################################################################################

    @Property('QVariant', notify=projectInfoChanged)
    def projectInfoAsJson(self):
        return self._project_info

    @projectInfoAsJson.setter
    def projectInfoAsJsonSetter(self, json_str):
        self._project_info = json.loads(json_str)
        self.projectInfoChanged.emit()

    @Slot(str, str)
    def editProjectInfo(self, key, value):
        self._project_info[key] = value
        self.projectInfoChanged.emit()

    def _defaultProjectInfo(self):
        return dict(
            name="Example Project",
            keywords="diffraction, cfml, cryspy",
            samples="samples.cif",
            experiments="experiments.cif",
            calculations="calculation.cif",
            modified="18.09.2020, 09:24"
        )

    ####################################################################################################################
    ####################################################################################################################
    # SAMPLE
    ####################################################################################################################
    ####################################################################################################################

    def defaultSample(self):
        sample = Sample(parameters=Pars1D.default(), pattern=Pattern1D.default(), interface=self._interface)
        sample.pattern.zero_shift = 0.0
        sample.pattern.scale = 1.0
        sample.parameters.wavelength = 1.912
        sample.parameters.resolution_u = 0.14
        sample.parameters.resolution_v = -0.42
        sample.parameters.resolution_w = 0.38
        sample.parameters.resolution_x = 0.0
        sample.parameters.resolution_y = 0.0
        return sample

    ####################################################################################################################
    # Phase models (list, xml, cif)
    ####################################################################################################################

    @Property('QVariant', notify=phasesAsListChanged)
    def phasesAsList(self):
        #print("+ phasesAsList")
        return self._phases_as_list

    @Property(str, notify=phasesAsXmlChanged)
    def phasesAsXml(self):
        #print("+ phasesAsXml")
        return self._phases_as_xml

    @Property(str, notify=phasesAsCifChanged)
    def phasesAsCif(self):
        #print("+ phasesAsCif")
        return self._phases_as_cif

    @phasesAsCif.setter
    def phasesAsCifSetter(self, phases_as_cif):
        print("+ phasesAsCifSetter")
        if self._phases_as_cif == phases_as_cif:
            return

        self._sample.phases = Phases.from_cif_str(phases_as_cif)
        self.phasesChanged.emit()

    def _setPhasesAsList(self):
        print("+ _setPhasesAsList")
        self._phases_as_list = self._sample.phases.as_dict()['data']
        self.phasesAsListChanged.emit()

    def _setPhasesAsXml(self):
        print("+ _setPhasesAsXml")
        self._phases_as_xml = dicttoxml(self._phases_as_list, attr_type=True).decode()
        self.phasesAsXmlChanged.emit()

    def _setPhasesAsCif(self):
        print("+ _setPhasesAsCif")
        self._phases_as_cif = str(self._sample.phases.cif)
        self.phasesAsCifChanged.emit()

    def _onPhasesChanged(self):
        print("***** _onPhasesChanged")
        self._setPhasesAsList()  # 0.025 s
        self._setPhasesAsXml()  # 0.065 s
        self._setPhasesAsCif()  # 0.010 s

    ####################################################################################################################
    # Phase: Add / Remove
    ####################################################################################################################

    @Slot(str)
    def addSampleFromCif(self, cif_path):
        cif_path = generalizePath(cif_path)
        self._sample.phases = Phases.from_cif_file(cif_path)
        self.phaseAdded.emit()

    @Slot()
    def addDefaultPhase(self):
        print("+ addDefaultPhase")
        self._sample.phases = self._defaultPhase()
        self.phaseAdded.emit()

    @Slot(str)
    def removePhase(self, phase_name: str):
        if phase_name in self._sample.phases.phase_names:
            del self._sample.phases[phase_name]
            self.phaseRemoved.emit()

    def _defaultPhase(self):
        space_group = SpaceGroup.from_pars('P 42/n c m')
        cell = Lattice.from_pars(8.56, 8.56, 6.12, 90, 90, 90)
        atom = Site.from_pars(label='Cl1', specie='Cl', fract_x=0.125, fract_y=0.167, fract_z=0.107)
        atom.add_adp('Uiso', Uiso=0.0)
        phase = Phase('Dichlorine', spacegroup=space_group, cell=cell)
        phase.add_atom(atom)
        return phase

    def _onPhaseAdded(self):
        print("***** _onPhaseAdded")
        if self._interface.current_interface_name != 'CrysPy':
            self._interface.generate_sample_binding("filename", self._sample)
        ## self.vtkHandler.plot_system2(self._sample.phases[0])
        self._sample.phases.name = 'Phases'
        #self._sample.set_background(self._background)
        self.phasesChanged.emit()
        #self.currentPhaseChanged.emit()
        #self.currentPhaseSitesChanged.emit()
        #self.spaceGroupChanged.emit()
        #self.parametersChanged.emit()

    def _onPhaseRemoved(self):
        print("***** _onPhaseRemoved")
        ## self.vtkHandler.clearScene()
        self.phasesChanged.emit()
        #self.currentPhaseChanged.emit()
        #self.currentPhaseSitesChanged.emit()
        #self.spaceGroupChanged.emit()

    ####################################################################################################################
    # Phase: Symmetry
    ####################################################################################################################

    # Crystal system

    @Property('QVariant', notify=spaceGroupChanged)
    def crystalSystemList(self):
        systems = [system.capitalize() for system in SpacegroupInfo.get_all_systems()]
        return systems

    @Property(str, notify=spaceGroupChanged)
    def currentCrystalSystem(self):
        phases = self._sample.phases
        if not phases:
            return ''

        current_system = phases[self.currentPhaseIndex].spacegroup.crystal_system
        current_system = current_system.capitalize()
        return current_system

    @currentCrystalSystem.setter
    def currentCrystalSystemSetter(self, new_system: str):
        new_system = new_system.lower()
        space_group_numbers = SpacegroupInfo.get_ints_from_system(new_system)
        top_space_group_number = space_group_numbers[0]
        top_space_group_name = SpacegroupInfo.get_symbol_from_int_number(top_space_group_number)
        self._setCurrentSpaceGroup(top_space_group_name)

    # Space group number and name

    @Property('QVariant', notify=spaceGroupChanged)
    def formattedSpaceGroupList(self):
        def format_display(num):
            name = SpacegroupInfo.get_symbol_from_int_number(num)
            return f"<font color='#999'>{num}</font> {name}"

        space_group_numbers = self._spaceGroupNumbers()
        display_list = [format_display(num) for num in space_group_numbers]
        return display_list

    @Property(int, notify=spaceGroupChanged)
    def currentSpaceGroup(self):
        def space_group_index(number, numbers):
            if number in numbers:
                return numbers.index(number)
            return 0

        phases = self._sample.phases
        if not phases:
            return -1

        space_group_numbers = self._spaceGroupNumbers()
        current_number = self._currentSpaceGroupNumber()
        current_idx = space_group_index(current_number, space_group_numbers)
        return current_idx

    @currentSpaceGroup.setter
    def currentSpaceGroupSetter(self, new_idx: int):
        space_group_numbers = self._spaceGroupNumbers()
        space_group_number = space_group_numbers[new_idx]
        space_group_name = SpacegroupInfo.get_symbol_from_int_number(space_group_number)
        self._setCurrentSpaceGroup(space_group_name)

    def _spaceGroupNumbers(self):
        current_system = self.currentCrystalSystem.lower()
        numbers = SpacegroupInfo.get_ints_from_system(current_system)
        return numbers

    def _currentSpaceGroupNumber(self):
        phases = self._sample.phases
        current_number = phases[self.currentPhaseIndex].spacegroup.int_number
        return current_number

    # Space group setting

    @Property('QVariant', notify=spaceGroupChanged)
    def formattedSpaceGroupSettingList(self):
        def format_display(num, name):
            return f"<font color='#999'>{num}</font> {name}"

        raw_list = self._spaceGroupSettingList()
        formatted_list = [format_display(i+1, name) for i, name in enumerate(raw_list)]
        return formatted_list

    @Property(int, notify=spaceGroupChanged)
    def currentSpaceGroupSetting(self):
        phases = self._sample.phases
        if not phases:
            return 0

        settings = self._spaceGroupSettingList()
        current_setting = phases[self.currentPhaseIndex].spacegroup.space_group_HM_name.raw_value
        current_number = settings.index(current_setting)
        return current_number

    @currentSpaceGroupSetting.setter
    def currentSpaceGroupSettingSetter(self, new_number: int):
        settings = self._spaceGroupSettingList()
        name = settings[new_number]
        self._setCurrentSpaceGroup(name)

    def _spaceGroupSettingList(self):
        phases = self._sample.phases
        if not phases:
            return []

        current_number = self._currentSpaceGroupNumber()
        settings = SpacegroupInfo.get_compatible_HM_from_int(current_number)
        return settings

    # Common

    def _setCurrentSpaceGroup(self, new_name: str):
        phases = self._sample.phases
        if phases[self.currentPhaseIndex].spacegroup.space_group_HM_name == new_name:
            return

        phases[self.currentPhaseIndex].spacegroup.space_group_HM_name = new_name
        self.spaceGroupChanged.emit()

    def _onSpaceGroupChanged(self):
        print("***** _onSpaceGroupChanged")

    ####################################################################################################################
    # Phase: Atoms
    ####################################################################################################################

    @Slot()
    def addAtom(self):
        try:
            atom = Site.default('Label2', 'H')
            atom.add_adp('Uiso', Uiso=0.0)
            self._sample.phases[self.currentPhaseIndex].add_atom(atom)
            self.atomsChanged.emit()
        except AttributeError:
            print("Error: failed to add atom")

    @Slot(str)
    def removeAtom(self, atom_label: str):
        del self._sample.phases[self.currentPhaseIndex].atoms[atom_label]
        self.atomsChanged.emit()

    def _onAtomsChanged(self):
        print("***** _onAtomsChanged")
        self.phasesChanged.emit()

    ####################################################################################################################
    # Current phase
    ####################################################################################################################

    @Property(int, notify=currentPhaseChanged)
    def currentPhaseIndex(self):
        return self._current_phase_index

    @currentPhaseIndex.setter
    def currentPhaseIndexSetter(self, new_index: int):
        if self._current_phase_index == new_index or new_index == -1:
            return

        self._current_phase_index = new_index
        self.currentPhaseChanged.emit()

    def _onCurrentPhaseChanged(self):
        print("***** _onCurrentPhaseChanged")
        self.structureViewChanged.emit()

    ####################################################################################################################
    # Structure view
    ####################################################################################################################

    @Property(bool, notify=False)
    def showBonds(self):
        if self.vtkHandler is None:
            return True
        return self.vtkHandler.show_bonds

    @showBonds.setter
    def showBondsSetter(self, show_bonds: bool):
        if self.vtkHandler is None or self.vtkHandler.show_bonds == show_bonds:
            return
        self.vtkHandler.show_bonds = show_bonds
        self.structureViewChanged.emit()

    @Property(float, notify=False)
    def bondsMaxDistance(self):
        if self.vtkHandler is None:
            return 2.0
        return self.vtkHandler.max_distance

    @bondsMaxDistance.setter
    def bondsMaxDistanceSetter(self, max_distance: float):
        if self.vtkHandler is None or self.vtkHandler.max_distance == max_distance:
            return
        self.vtkHandler.max_distance = max_distance
        self.structureViewChanged.emit()

    def _updateStructureView(self):
        print("+ _updateStructureView")
        if self.vtkHandler is None or not self._sample.phases:
            return
        self.vtkHandler.clearScene()
        self.vtkHandler.plot_system2(self._sample.phases[0])

    def _onStructureViewChanged(self):
        print("***** _onStructureViewChanged")
        self._updateStructureView()

    ####################################################################################################################
    ####################################################################################################################
    # EXPERIMENT
    ####################################################################################################################
    ####################################################################################################################

    def defaultExperiments(self):
        return []

    def defaultData(self):
        x_min = self._simulation_parameters_as_obj['x_min']
        x_max = self._simulation_parameters_as_obj['x_max']
        x_step = self._simulation_parameters_as_obj['x_step']
        num_points = int((x_max - x_min) / x_step + 1)
        x_data = np.linspace(x_min, x_max, num_points)

        data = DataStore()

        data.append(
            DataSet1D(
                name='D1A@ILL data',
                x=x_data, y=np.zeros_like(x_data),
                x_label='2theta (deg)', y_label='Intensity (arb. units)',
                data_type='experiment'
            )
        )
        data.append(
            DataSet1D(
                name='{:s} engine'.format(self._interface.current_interface_name),
                x=x_data, y=np.zeros_like(x_data),
                x_label='2theta (deg)', y_label='Intensity (arb. units)',
                data_type='simulation'
            )
        )
        data.append(
            DataSet1D(
                name='Difference',
                x=x_data, y=np.zeros_like(x_data),
                x_label='2theta (deg)', y_label='Intensity (arb. units)',
                data_type='simulation'
            )
        )
        return data

    ####################################################################################################################
    # Experiment models (list, xml, cif)
    ####################################################################################################################

    @Property(str, notify=experimentDataAsXmlChanged)
    def experimentDataAsXml(self):
        return self._experiment_data_as_xml

    def _setExperimentDataAsXml(self):
        print("+ _setExperimentDataAsXml")
        self._experiment_data_as_xml = dicttoxml(self.experiments, attr_type=True).decode()
        self.experimentDataAsXmlChanged.emit()

    def _onExperimentDataChanged(self):
        print("***** _onExperimentDataChanged")
        self._setExperimentDataAsXml()  # ? s

    ####################################################################################################################
    # Experiment data: Add / Remove
    ####################################################################################################################

    @Slot(str)
    def addExperimentDataFromXye(self, file_url):
        print(f"+ addExperimentDataFromXye: {file_url}")
        self._experiment_data = self._loadExperimentData(file_url)
        self.experimentDataAdded.emit()

    @Slot()
    def removeExperiment(self):
        print("+ removeExperiment")
        self.experiments.clear()
        self.experimentDataRemoved.emit()

    def _defaultExperiment(self):
        return {
            "label": "D1A@ILL",
            "color": "steelblue"
        }

    def _loadExperimentData(self, file_url):
        print("+ _loadExperimentData")
        file_path = generalizePath(file_url)
        data = self._data.experiments[0]
        data.x, data.y, data.e = np.loadtxt(file_path, unpack=True)
        return data

    def _experimentDataParameters(self, data):
        x_min = data.x[0]
        x_max = data.x[-1]
        x_step = (x_max - x_min) / (len(data.x) - 1)
        parameters = {
            "x_min": x_min,
            "x_max": x_max,
            "x_step": x_step
        }
        return parameters

    def _onExperimentDataAdded(self):
        print("***** _onExperimentDataAdded")
        self._experiment_parameters = self._experimentDataParameters(self._experiment_data)
        self.simulationParametersAsObj = json.dumps(self._experiment_parameters)
        self.experiments = [self._defaultExperiment()]
        self.matplotlib_bridge.updateWithCanvas(self._experiment_figure_obj_name, self._experiment_data)
        self.experimentDataChanged.emit()

    def _onExperimentDataRemoved(self):
        print("***** _onExperimentDataRemoved")
        self.experimentDataChanged.emit()

    ####################################################################################################################
    # Experiment loaded and skipped flags
    ####################################################################################################################

    @Property(bool, notify=experimentLoadedChanged)
    def experimentLoaded(self):
        return self._experiment_loaded

    @experimentLoaded.setter
    def experimentLoadedSetter(self, loaded: bool):
        if self._experiment_loaded == loaded:
            return

        self._experiment_loaded = loaded
        self.experimentLoadedChanged.emit()

    @Property(bool, notify=experimentSkippedChanged)
    def experimentSkipped(self):
        return self._experiment_skipped

    @experimentSkipped.setter
    def experimentSkippedSetter(self, skipped: bool):
        if self._experiment_skipped == skipped:
            return

        self._experiment_skipped = skipped
        self.experimentSkippedChanged.emit()

    ####################################################################################################################
    # Simulation parameters
    ####################################################################################################################

    def defaultSimulationParameters(self):
        return {
            "x_min": 10.0,
            "x_max": 150.0,
            "x_step": 0.1
        }

    @Property('QVariant', notify=simulationParametersChanged)
    def simulationParametersAsObj(self):
        return self._simulation_parameters_as_obj

    @simulationParametersAsObj.setter
    def simulationParametersAsObjSetter(self, json_str):
        if self._simulation_parameters_as_obj == json.loads(json_str):
            return

        self._simulation_parameters_as_obj = json.loads(json_str)
        self.simulationParametersChanged.emit()

    def _onSimulationParametersChanged(self):
        x_min = float(self._simulation_parameters_as_obj['x_min'])
        x_max = float(self._simulation_parameters_as_obj['x_max'])
        x_step = float(self._simulation_parameters_as_obj['x_step'])
        num_points = int((x_max - x_min) / x_step + 1)

        sim = self._data.simulations[0]
        sim.x = np.linspace(x_min, x_max, num_points)
        sim.y = self._interface.fit_func(sim.x)

        self.calculatedDataChanged.emit()

    ####################################################################################################################
    # Pattern parameters (scale, zero_shift, backgrounds)
    ####################################################################################################################

    def defaultPatternParameters(self):
        return {
            "scale": 1.0,
            "zero_shift": 0.0
        }

    @Property('QVariant', notify=patternParametersAsObjChanged)
    def patternParametersAsObj(self):
        return self._pattern_parameters_as_obj

    def _setPatternParametersAsObj(self):
        print("+ _setPatternParametersAsObj")
        parameters = self._sample.pattern.as_dict()
        self._pattern_parameters_as_obj = parameters
        self.patternParametersAsObjChanged.emit()

    def _onPatternParametersChanged(self):
        print("***** _onPatternParametersChanged")
        self._setPatternParametersAsObj()

    ####################################################################################################################
    # Instrument parameters (wavelength, resolution_u, ..., resolution_y)
    ####################################################################################################################

    def defaultInstrumentParameters(self):
        return {
            "wavelength": 1.0,
            "resolution_u": 0.01,
            "resolution_v": -0.01,
            "resolution_w": 0.01,
            "resolution_x": 0.0,
            "resolution_y": 0.0
        }

    @Property('QVariant', notify=instrumentParametersAsObjChanged)
    def instrumentParametersAsObj(self):
        return self._instrument_parameters_as_obj

    @Property(str, notify=instrumentParametersAsXmlChanged)
    def instrumentParametersAsXml(self):
        return self._instrument_parameters_as_xml

    def _setInstrumentParametersAsObj(self):
        print("+ _setInstrumentParametersAsObj")
        parameters = self._sample.parameters.as_dict()
        self._instrument_parameters_as_obj = parameters
        self.instrumentParametersAsObjChanged.emit()

    def _setInstrumentParametersAsXml(self):
        print("+ _setInstrumentParametersAsXml")
        parameters = [self._instrument_parameters_as_obj]
        self._instrument_parameters_as_xml = dicttoxml(parameters, attr_type=True).decode()
        self.instrumentParametersAsXmlChanged.emit()

    def _onInstrumentParametersChanged(self):
        print("***** _onInstrumentParametersChanged")
        self._setInstrumentParametersAsObj()
        self._setInstrumentParametersAsXml()

    ####################################################################################################################
    # ---Background
    ####################################################################################################################

    def defaultBackground(self):
        bkg = PointBackground(
            BackgroundPoint.from_pars(0, 200), 
            BackgroundPoint.from_pars(140, 200),
            linked_experiment='NEED_TO_CHANGE'
        )
        return bkg

    @Property(str, notify=backgroundChanged)
    def backgroundAsXml(self):
        background = np.array([item.as_dict() for item in self._background])
        idx = np.array([item.x.raw_value for item in self._background]).argsort()
        xml = dicttoxml(background[idx], attr_type=False)
        xml = xml.decode()
        return xml

    @Slot(str)
    def removeBackgroundPoint(self, background_point_x_name: str):
        print(f"removeBackgroundPoint for background_point_x_name: {background_point_x_name}")
        self._sample.remove_background(self._background)
        names = self._background.names
        del self._background[names.index(background_point_x_name)]
        self._sample.set_background(self._background)
        self._backgroundChanged.emit()
        self._updateCalculatedData()
        self.phasesChanged.emit()
        #self.modelChanged.emit()

    @Slot()
    def addBackgroundPoint(self):
        print(f"addBackgroundPoint")
        self._sample.remove_background(self._background)
        point = BackgroundPoint.from_pars(x=180.0, y=0.0)
        self._background.append(point)
        self._sample.set_background(self._background)
        self._backgroundChanged.emit()
        self._updateCalculatedData()
        self.phasesChanged.emit()
        #self.modelChanged.emit()

    ####################################################################################################################
    ####################################################################################################################
    # ANALYSIS
    ####################################################################################################################
    ####################################################################################################################

    ####################################################################################################################
    # ---Calculated data
    ####################################################################################################################

    def _updateCalculatedData(self):
        print("+ _updateCalculatedData")
        if not self.experimentLoaded and not self.experimentSkipped:
            return

        if self._analysis_figure_obj_name is None:
            return

        self._sample.output_index = self.currentPhaseIndex

        #  THIS IS WHERE WE WOULD LOOK UP CURRENT EXP INDEX
        sim = self._data.simulations[0]

        zeros_sim = DataSet1D(name='', x=[sim.x[0]], y=[sim.y[0]])  # Temp solution to have proper color for sim curve
        zeros_diff = DataSet1D(name='', x=[sim.x[0]])  # Temp solution to have proper color for sim curve

        if self.experimentLoaded:
            exp = self._data.experiments[0]

            sim.x = exp.x
            sim.y = self._interface.fit_func(sim.x)

            diff = self._data.simulations[1]
            diff.x = exp.x
            diff.y = exp.y - sim.y

            zeros_diff.y = [exp.y[0] - sim.y[0]]
            zeros_diff.x_label = diff.x_label
            zeros_diff.y_label = diff.y_label

            data = [exp, sim]

            self.matplotlib_bridge.updateWithCanvas(self._difference_figure_obj_name, [zeros_diff, zeros_diff, diff])

        elif self.experimentSkipped:
            x_min = float(self._simulation_parameters_as_obj['x_min'])
            x_max = float(self._simulation_parameters_as_obj['x_max'])
            x_step = float(self._simulation_parameters_as_obj['x_step'])
            num_points = int((x_max - x_min) / x_step + 1)

            sim.x = np.linspace(x_min, x_max, num_points)
            sim.y = self._interface.fit_func(sim.x)

            zeros_sim.x_label = sim.x_label
            zeros_sim.y_label = sim.y_label

            data = [zeros_sim, sim]

        else:
            print("???")

        self.matplotlib_bridge.updateWithCanvas(self._analysis_figure_obj_name, data)

        #self.modelChanged.emit()

    def _onCalculatedDataChanged(self):
        print("***** _onCalculatedDataChanged")
        self._updateCalculatedData()

    ####################################################################################################################
    # Any parameter (parameters table from analysis tab & ...)
    ####################################################################################################################

    @Property('QVariant', notify=parametersAsObjChanged)
    def parametersAsObj(self):
        #print("+ parametersAsObj")
        return self._parameters_as_obj

    @Property(str, notify=parametersAsXmlChanged)
    def parametersAsXml(self):
        #print("+ parametersAsXml")
        return self._parameters_as_xml

    @Slot(str, 'QVariant')
    def editParameter(self, obj_id: str, new_value: [bool, float, str]):  # covers both parameter and descriptor
        print(f"+ editParameter {new_value}, {type(new_value)}")
        obj = self._parameterObj(obj_id)

        if type(new_value) is bool:
            if obj.fixed == (not new_value):
                return

            obj.fixed = not new_value
            self._onParametersChanged()

        else:
            if obj.raw_value == new_value:
                return

            obj.value = new_value
            self.parametersChanged.emit()

    def _parameterObj(self, obj_id: str):
        print(f"+ _parameterObj {obj_id}")
        if not obj_id:
            return
        obj_id = int(obj_id)
        obj = borg.map.get_item_by_key(obj_id)
        print(f"  _parameterObj {obj_id} {obj.value}")
        return obj

    def _setParametersAsObj(self):
        print("+ _setParametersAsObj")
        self._parameters_as_obj.clear()

        par_ids, par_paths = generatePath(self._sample, True)
        for par_index, par_path in enumerate(par_paths):
            par_id = par_ids[par_index]
            par = borg.map.get_item_by_key(par_id)

            if not par.enabled:
                continue

            if self._parameters_filter_criteria.lower() not in par_path.lower():
                continue

            self._parameters_as_obj.append({
                "id": str(par_id),
                "number": par_index + 1,
                "label": par_path,
                "value": par.raw_value,
                "unit": '{:~P}'.format(par.unit),
                "error": par.error,
                "fit": int(not par.fixed)
            })

        self.parametersAsObjChanged.emit()

    def _setParametersAsXml(self):
        print("+ _setParametersAsXml")
        # print(f" _setParametersAsObj self._parameters_as_obj id C {id(self._parameters_as_obj)}")
        self._parameters_as_xml = dicttoxml(self._parameters_as_obj, attr_type=False).decode()
        self.parametersAsXmlChanged.emit()

    def _onParametersChanged(self):
        print("***** _onParametersChanged")
        self._setParametersAsObj()
        self._setParametersAsXml()

    # Filtering

    @Slot(str)
    def setParametersFilterCriteria(self, new_criteria):
        if self._parameters_filter_criteria == new_criteria:
            return
        self._parameters_filter_criteria = new_criteria
        self.parametersFilterCriteriaChanged.emit()

    def _onParametersFilterCriteriaChanged(self):
        print("***** _onParametersFilterCriteriaChanged")
        #self.modelChanged.emit()

    ####################################################################################################################
    # Minimizer
    ####################################################################################################################

    # Minimizer

    @Property('QVariant', notify=None)
    def minimizerNames(self):
        return self.fitter.available_engines

    @Property(int, notify=currentMinimizerChanged)
    def currentMinimizerIndex(self):
        current_name = self.fitter.current_engine.name
        return self.minimizerNames.index(current_name)

    @Slot(int)
    def changeCurrentMinimizer(self, new_index: int):
        if self.currentMinimizerIndex == new_index:
            return

        new_name = self.minimizerNames[new_index]
        self.fitter.switch_engine(new_name)
        self.currentMinimizerChanged.emit()

    def _onCurrentMinimizerChanged(self):
        print("***** _onCurrentMinimizerChanged")

    # Minimizer method

    @Property('QVariant', notify=None)
    def minimizerMethodNames(self):
        return self.fitter.available_methods()

    @Property(int, notify=currentMinimizerMethodChanged)
    def currentMinimizerMethodIndex(self):
        return self._current_minimizer_method_index

    @Slot(int)
    def changeCurrentMinimizerMethod(self, new_index: int):
        if self._current_minimizer_method_index == new_index:
            return

        self._current_minimizer_method_index = new_index
        self._current_minimizer_method_name = self.minimizerMethodNames[new_index]
        self.currentMinimizerMethodChanged.emit()

    def _onCurrentMinimizerMethodChanged(self):
        print("***** _onCurrentMinimizerMethodChanged")

    ####################################################################################################################
    # Calculator
    ####################################################################################################################

    @Property('QVariant', notify=None)
    def calculatorNames(self):
        return self._interface.available_interfaces

    @Property(int, notify=currentCalculatorChanged)
    def currentCalculatorIndex(self):
        return self.calculatorNames.index(self._interface.current_interface_name)

    @Slot(int)
    def changeCurrentCalculator(self, new_index: int):
        if self.currentCalculatorIndex == new_index:
            return

        new_name = self.calculatorNames[new_index]
        self._interface.switch(new_name)
        self.currentCalculatorChanged.emit()

    def _onCurrentCalculatorChanged(self):
        print("***** _onCurrentCalculatorChanged")
        data = self._data.simulations
        data = data[0]  # THIS IS WHERE WE WOULD LOOK UP CURRENT EXP INDEX
        data.name = f'{self._interface.current_interface_name} engine'
        self._sample._updateInterface()
        self.calculatedDataChanged.emit()

    ####################################################################################################################
    # Fitting
    ####################################################################################################################

    def defaultFitResults(self):
        return {
            "success": None,
            "nvarys": None,
            "GOF": None,
            "redchi": None
        }

    @Slot()
    def fit(self):
        exp_data = self._data.experiments[0]

        x = exp_data.x
        y = exp_data.y
        weights = 1 / exp_data.e
        method = self._current_minimizer_method_name

        res = self.fitter.fit(x, y, weights=weights, method=method)

        self.setFitResults(res)
        self.fitFinished.emit()

    @Property('QVariant', notify=fitResultsChanged)
    def fitResults(self):
        return self._fit_results

    def setFitResults(self, res):
        self._fit_results = {
            "success": res.success,
            "nvarys": res.n_pars,
            "gof": float(res.goodness_of_fit),
            "redchi2": float(res.reduced_chi)
        }
        self.fitResultsChanged.emit()

    def _onFitFinished(self):
        print("***** _onFitFinished")
        self.parametersChanged.emit()

    ####################################################################################################################
    ####################################################################################################################
    # STATUS
    ####################################################################################################################
    ####################################################################################################################

    @Property(str, notify=statusInfoChanged)
    def statusModelAsXml(self):
        model = [
            {"label": "Engine", "value": self._interface.current_interface_name},
            {"label": "Minimizer", "value": self.fitter.current_engine.name},
            {"label": "Method", "value": self._current_minimizer_method_name}
        ]
        xml = dicttoxml(model, attr_type=False)
        xml = xml.decode()
        return xml

    def _onStatusInfoChanged(self):
        print("***** _onStatusInfoChanged")