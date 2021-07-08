import timeit
from dicttoxml import dicttoxml

from easyCore import np, borg
from easyDiffractionLib import Phases, Phase, Lattice, Site, SpaceGroup
from easyCore.Symmetry.tools import SpacegroupInfo
from easyApp.Logic.Utils.Utils import generalizePath
from easyDiffractionLib.sample import Sample
from easyDiffractionLib.Elements.Experiments.Experiment import Pars1D
from easyDiffractionLib.Elements.Experiments.Pattern import Pattern1D
from PySide2.QtCore import QObject, Signal, Slot, Property
from easyCore.Utils.UndoRedo import property_stack_deco


class PhaseProxy(QObject):

    dummySignal = Signal()

    phasesAsObjChanged = Signal()
    phasesAsXmlChanged = Signal()
    phasesAsCifChanged = Signal()
    currentPhaseChanged = Signal()
    phasesEnabled = Signal()
    structureParametersChanged = Signal()
    structureViewChanged = Signal()
    phaseAdded = Signal()
    updateProjectInfo = Signal(tuple)

    def __init__(self, parent=None, interface=None):
        super().__init__(parent)
        self.parent = parent

        self._interface = interface
        self.phases = None
        self._phases_as_obj = []
        self._phases_as_xml = ""
        self._phases_as_cif = ""
        self._sample = self._defaultSample()
        self._current_phase_index = 0

        self.structureParametersChanged.connect(self._onStructureParametersChanged)

        self.phaseAdded.connect(self._onPhaseAdded)
        self.phaseAdded.connect(self.phasesEnabled)
        self.currentPhaseChanged.connect(self._onCurrentPhaseChanged)

    ####################################################################################################################
    # SAMPLE
    ####################################################################################################################

    def _defaultSample(self):
        sample = Sample(parameters=Pars1D.default(),
                        pattern=Pattern1D.default(),
                        interface=self._interface)
        sample.pattern.zero_shift = 0.0
        sample.pattern.scale = 100.0
        sample.parameters.wavelength = 1.912
        sample.parameters.resolution_u = 0.1447
        sample.parameters.resolution_v = -0.4252
        sample.parameters.resolution_w = 0.3864
        sample.parameters.resolution_x = 0.0
        sample.parameters.resolution_y = 0.0  # 0.0961
        return sample

    ####################################################################################################################
    # Phase models (list, xml, cif)
    ####################################################################################################################

    @Property('QVariant', notify=phasesAsObjChanged)
    def phasesAsObj(self):
        return self._phases_as_obj

    @Property(str, notify=phasesAsXmlChanged)
    def phasesAsXml(self):
        return self._phases_as_xml

    @Property(str, notify=phasesAsCifChanged)
    def phasesAsCif(self):
        return self._phases_as_cif

    @Property(str, notify=phasesAsCifChanged)
    def phasesAsExtendedCif(self):
        if len(self._sample.phases) == 0:
            return

        symm_ops = self._sample.phases[0].spacegroup.symmetry_opts
        symm_ops_cif_loop = "loop_\n _symmetry_equiv_pos_as_xyz\n"
        for symm_op in symm_ops:
            symm_ops_cif_loop += f' {symm_op.as_xyz_string()}\n'
        return self._phases_as_cif + symm_ops_cif_loop

    @phasesAsCif.setter
    @property_stack_deco
    def phasesAsCif(self, phases_as_cif):
        if self._phases_as_cif == phases_as_cif:
            return
        self._sample.phases = Phases.from_cif_str(phases_as_cif)
        self.parent.parametersChanged.emit()

    def sample(self):
        return self._sample

    def _setPhasesAsObj(self):
        start_time = timeit.default_timer()
        self._phases_as_obj = self._sample.phases.as_dict(skip=['interface'])['data']
        print("+ _setPhasesAsObj: {0:.3f} s".format(timeit.default_timer() - start_time))
        self.phasesAsObjChanged.emit()

    def _setPhasesAsXml(self):
        start_time = timeit.default_timer()
        self._phases_as_xml = dicttoxml(self._phases_as_obj, attr_type=True).decode()  # noqa: E501
        print("+ _setPhasesAsXml: {0:.3f} s".format(timeit.default_timer() - start_time))
        self.phasesAsXmlChanged.emit()

    def _setPhasesAsCif(self):
        start_time = timeit.default_timer()
        self._phases_as_cif = str(self._sample.phases.cif)
        print("+ _setPhasesAsCif: {0:.3f} s".format(timeit.default_timer() - start_time))
        self.phasesAsCifChanged.emit()

    def _onStructureParametersChanged(self):
        print("***** _onStructureParametersChanged")
        self._setPhasesAsObj()  # 0.025 s
        self._setPhasesAsXml()  # 0.065 s
        self._setPhasesAsCif()  # 0.010 s
        self.parent._project_proxy.stateChanged.emit(True)
        self._updateCalculatedData()

    def _updateCalculatedData(self):
        self.parent.parameters._updateCalculatedData()

    ####################################################################################################################
    # Phase: Add / Remove
    ####################################################################################################################

    @Slot(str)
    def addSampleFromCif(self, cif_url):
        cif_path = generalizePath(cif_url)
        borg.stack.enabled = False
        self._sample.phases = Phases.from_cif_file(cif_path)
        borg.stack.enabled = True
        self._onPhaseAdded()

    @Slot()
    def addDefaultPhase(self):
        print("+ addDefaultPhase")
        borg.stack.enabled = False
        self._sample.phases.append(self._defaultPhase())
        borg.stack.enabled = True
        self._onPhaseAdded()

    @Slot(str)
    def removePhase(self, phase_name: str):
        if phase_name not in self._sample.phases.phase_names:
            return
        del self._sample.phases[phase_name]
        self.structureParametersChanged.emit()
        self.phasesEnabled.emit()

    def _onPhaseAdded(self):
        print("***** _onPhaseAdded")
        if self._interface.current_interface_name != 'CrysPy':
            self._interface.generate_sample_binding("filename", self._sample)
        self._sample.phases.name = 'Phases'
        name = self._sample.phases[self._current_phase_index].name
        self.updateProjectInfo.emit(('samples', name))
        self.phasesEnabled.emit()
        self.phasesAsObjChanged.emit()
        self.structureParametersChanged.emit()
        self.parent._project_proxy.projectInfoChanged.emit()

    @Property(bool, notify=phasesEnabled)
    def samplesPresent(self) -> bool:
        result = len(self._sample.phases) > 0
        return result

    def _defaultPhase(self):
        space_group = SpaceGroup.from_pars('P 42/n c m')
        cell = Lattice.from_pars(8.56, 8.56, 6.12, 90, 90, 90)
        atom = Site.from_pars(label='Cl1', specie='Cl', fract_x=0.125, fract_y=0.167, fract_z=0.107)  # noqa: E501
        atom.add_adp('Uiso', Uiso=0.0)
        phase = Phase('Dichlorine', spacegroup=space_group, cell=cell)
        phase.add_atom(atom)
        return phase

    ####################################################################################################################
    # Phase: Symmetry
    ####################################################################################################################

    # Crystal system

    @Property('QVariant', notify=structureParametersChanged)
    def crystalSystemList(self):
        systems = [system.capitalize() for system in SpacegroupInfo.get_all_systems()]  # noqa: E501
        return systems

    @Property(str, notify=structureParametersChanged)
    def currentCrystalSystem(self):
        phases = self._sample.phases
        if not phases:
            return ''
        current_system = phases[self._current_phase_index].spacegroup.crystal_system  # noqa: E501
        current_system = current_system.capitalize()
        return current_system

    @currentCrystalSystem.setter
    def currentCrystalSystem(self, new_system: str):
        new_system = new_system.lower()
        space_group_numbers = SpacegroupInfo.get_ints_from_system(new_system)
        top_space_group_number = space_group_numbers[0]
        top_space_group_name = SpacegroupInfo.get_symbol_from_int_number(top_space_group_number)  # noqa: E501
        self._setCurrentSpaceGroup(top_space_group_name)
        self.structureParametersChanged.emit()

    @Property('QVariant', notify=structureParametersChanged)
    def formattedSpaceGroupList(self):
        def format_display(num):
            name = SpacegroupInfo.get_symbol_from_int_number(num)
            return f"<font color='#999'>{num}</font> {name}"

        space_group_numbers = self._spaceGroupNumbers()
        display_list = [format_display(num) for num in space_group_numbers]
        return display_list

    @Property(int, notify=structureParametersChanged)
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
    def currentSpaceGroup(self, new_idx: int):
        space_group_numbers = self._spaceGroupNumbers()
        space_group_number = space_group_numbers[new_idx]
        space_group_name = SpacegroupInfo.get_symbol_from_int_number(space_group_number)  # noqa: E501
        self._setCurrentSpaceGroup(space_group_name)
        self.structureParametersChanged.emit()

    @Property('QVariant', notify=structureParametersChanged)
    def formattedSpaceGroupSettingList(self):
        def format_display(num, name):
            return f"<font color='#999'>{num}</font> {name}"

        raw_list = self._spaceGroupSettingList()
        formatted_list = [format_display(i + 1, name) for i, name in enumerate(raw_list)]  # noqa: E501
        return formatted_list

    @Property(int, notify=structureParametersChanged)
    def currentSpaceGroupSetting(self):
        phases = self._sample.phases
        if not phases:
            return 0

        settings = self._spaceGroupSettingList()
        # current_setting = phases[self._current_phase_index].spacegroup.space_group_HM_name.raw_value  # noqa: E501
        current_setting = phases[self._current_phase_index].spacegroup.hermann_mauguin  # noqa: E501
        current_number = settings.index(current_setting)
        return current_number

    @currentSpaceGroupSetting.setter
    def currentSpaceGroupSetting(self, new_number: int):
        settings = self._spaceGroupSettingList()
        name = settings[new_number]
        self._setCurrentSpaceGroup(name)
        self.structureParametersChanged.emit()

    def _setCurrentSpaceGroup(self, new_name: str):
        phases = self._sample.phases
        if phases[self._current_phase_index].spacegroup.space_group_HM_name == new_name:  # noqa: E501
            return
        phases[self._current_phase_index].spacegroup.space_group_HM_name = new_name  # noqa: E501

    def setCurrentExperimentDatasetName(self, name):
        if self.parent.parameters._data.experiments[0].name == name:
            return
        self.parent.parameters._data.experiments[0].name = name
        self.updateProjectInfo.emit(('experiments', name))

    def _spaceGroupNumbers(self):
        current_system = self.currentCrystalSystem.lower()
        numbers = SpacegroupInfo.get_ints_from_system(current_system)
        return numbers

    def _currentSpaceGroupNumber(self):
        phases = self._sample.phases
        current_number = phases[self._current_phase_index].spacegroup.int_number  # noqa: E501
        return current_number

    def _spaceGroupSettingList(self):
        phases = self._sample.phases
        if not phases:
            return []

        current_number = self._currentSpaceGroupNumber()
        settings = SpacegroupInfo.get_compatible_HM_from_int(current_number)
        return settings

    ####################################################################################################################
    # Phase: Atoms
    ####################################################################################################################

    @Slot()
    def addDefaultAtom(self):
        try:
            index = len(self._sample.phases[0].atoms.atom_labels) + 1
            label = f'Label{index}'
            atom = Site.from_pars(label=label,
                                specie='O',
                                fract_x=0.05,
                                fract_y=0.05,
                                fract_z=0.05)
            atom.add_adp('Uiso', Uiso=0.0)
            self._sample.phases[self._current_phase_index].add_atom(atom)
            self.structureParametersChanged.emit()
        except AttributeError:
            print("Error: failed to add atom")

    @Slot(str)
    def removeAtom(self, atom_label: str):
        self._sample.phases[self._current_phase_index].remove_atom(atom_label)
        self.structureParametersChanged.emit()

    ####################################################################################################################
    # Current phase
    ####################################################################################################################

    @Property(int, notify=currentPhaseChanged)
    def currentPhaseIndex(self):
        return self._current_phase_index

    @currentPhaseIndex.setter
    def currentPhaseIndex(self, new_index: int):
        if self._current_phase_index == new_index or new_index == -1:
            return
        self._current_phase_index = new_index
        self.currentPhaseChanged.emit()

    def _onCurrentPhaseChanged(self):
        print("***** _onCurrentPhaseChanged")
        self.structureViewChanged.emit()

    @Slot(str)
    def setCurrentPhaseName(self, name):
        if self._sample.phases[self._current_phase_index].name == name:
            return
        self._sample.phases[self._current_phase_index].name = name
        # self._project_info['samples'] = name
        self.updateProjectInfo.emit(('samples', name))
        self.parent.parametersChanged.emit()
        self.parent._project_proxy.projectInfoChanged.emit()
