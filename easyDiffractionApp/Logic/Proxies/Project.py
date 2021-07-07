import os
import datetime

from dicttoxml import dicttoxml
import json

from easyCore import np, borg

from easyDiffractionLib.sample import Sample
from easyApp.Logic.Utils.Utils import generalizePath
from PySide2.QtCore import QObject, Signal, Slot, Property


class ProjectProxy(QObject):
    projectCreatedChanged = Signal()
    projectInfoChanged = Signal()
    dummySignal = Signal()
    stateChanged = Signal(bool)
    htmlExportingFinished = Signal(bool, str)

    reset = Signal()
    phasesEnabled = Signal()
    phasesAsObjChanged = Signal()
    structureParametersChanged = Signal()
    removePhaseSignal = Signal(str)
    experimentDataAdded = Signal()
    experimentLoadedChanged = Signal()

    def __init__(self, parent=None, interface=None):
        super().__init__(parent)
        self.parent = parent
        self._interface = interface
        self._interface_name = interface.current_interface_name
        self.project_save_filepath = ""
        self.project_load_filepath = ""
        self._project_info = self._defaultProjectInfo()
        self._project_created = False
        self._state_changed = False

        self._report = ""
        self._currentProjectPath = os.path.expanduser("~")

        self.stateChanged.connect(self._onStateChanged)

    ####################################################################################################################
    ####################################################################################################################
    # project
    ####################################################################################################################
    ####################################################################################################################

    def _defaultProjectInfo(self):
        return dict(
            name="Example Project",
            short_description="diffraction, powder, 1D",
            samples="Not loaded",
            experiments="Not loaded",
            modified=datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        )

    @Property('QVariant', notify=projectInfoChanged)
    def projectInfoAsJson(self):
        return self._project_info

    @projectInfoAsJson.setter
    def projectInfoAsJson(self, json_str):
        self._project_info = json.loads(json_str)
        self.projectInfoChanged.emit()

    @Property(str, notify=projectInfoChanged)
    def projectInfoAsCif(self):
        cif_list = []
        for key, value in self._project_info.items():
            if ' ' in value:
                value = f"'{value}'"
            cif_list.append(f'_{key} {value}')
        cif_str = '\n'.join(cif_list)
        return cif_str

    @Slot(str, str)
    def editProjectInfo(self, key, value):
        if key == 'location':
            self._currentProjectPath = value
            return
        else:
            if self._project_info[key] == value:
                return
            self._project_info[key] = value
        self.projectInfoChanged.emit()

    @Property(str, notify=projectInfoChanged)
    def currentProjectPath(self):
        return self._currentProjectPath

    @currentProjectPath.setter
    def currentProjectPath(self, new_path):
        if self._currentProjectPath == new_path:
            return
        self._currentProjectPath = new_path
        self.projectInfoChanged.emit()

    @Slot()
    def createProject(self):
        projectPath = self._currentProjectPath
        mainCif = os.path.join(projectPath, 'project.cif')
        samplesPath = os.path.join(projectPath, 'samples')
        experimentsPath = os.path.join(projectPath, 'experiments')
        calculationsPath = os.path.join(projectPath, 'calculations')
        if not os.path.exists(projectPath):
            os.makedirs(projectPath)
            os.makedirs(samplesPath)
            os.makedirs(experimentsPath)
            os.makedirs(calculationsPath)
            with open(mainCif, 'w') as file:
                file.write(self.projectInfoAsCif())
        else:
            print(f"ERROR: Directory {projectPath} already exists")

    @Property(str, notify=dummySignal)
    def projectExamplesAsXml(self):
        model = [
            {"name": "PbSO4", "description": "neutrons, powder, 1D, D1A@ILL",
             "path": "../Resources/Examples/PbSO4/project.json"},
            {"name": "Co2SiO4", "description": "neutrons, powder, 1D, D20@ILL",
             "path": "../Resources/Examples/Co2SiO4/project.json"},
            {"name": "Dy3Al5O12", "description": "neutrons, powder, 1D, G41@LLB",
             "path": "../Resources/Examples/Dy3Al5O12/project.json"}
        ]
        xml = dicttoxml(model, attr_type=False)
        xml = xml.decode()
        return xml

    def updateProjectInfo(self, key_value):
        if len(key_value) == 2:
            self._project_info[key_value[0]] = key_value[1]
            self.projectInfoChanged.emit()

    ####################################################################################################################
    ####################################################################################################################
    # State save/load
    ####################################################################################################################
    ####################################################################################################################

    @Slot()
    def saveProject(self):
        projectPath = self._currentProjectPath
        project_save_filepath = os.path.join(projectPath, 'project.json')
        descr = {
            'sample': self.parent.phase.logic._sample.as_dict(skip=['interface'])
        }
        if self.parent.parameters.logic._data.experiments:
            experiments_x = self.parent.parameters.logic._data.experiments[0].x
            experiments_y = self.parent.parameters.logic._data.experiments[0].y
            experiments_e = self.parent.parameters.logic._data.experiments[0].e
            descr['experiments'] = [experiments_x, experiments_y, experiments_e]

        descr['experiment_skipped'] = self.parent.experiment.logic._experiment_skipped
        descr['project_info'] = self._project_info

        descr['interface'] = self._interface.current_interface_name

        descr['minimizer'] = {
            'engine': self.parent.fitting.fitter.current_engine.name,
            'method': self.parent.fitting._current_minimizer_method_name
        }
        content_json = json.dumps(descr, indent=4, default=self.default)
        path = generalizePath(project_save_filepath)
        createFile(path, content_json)
        self.stateChanged.emit(False)

    def setProjectCreated(self, created: bool):
        if self._project_created == created:
            return
        self._project_created = created
        self.projectCreatedChanged.emit()

    def _loadProjectAs(self, filepath):
        """
        """
        self.project_load_filepath = filepath
        print("LoadProjectAs " + filepath)
        self._loadProject()

    @Slot(str)
    def loadProjectAs(self, filepath):
        self.project_load_filepath = filepath
        print("LoadProjectAs " + filepath)
        self._loadProject()
        self.stateChanged.emit(False)

    @Slot()
    def _loadProject(self):
        path = generalizePath(self.project_load_filepath)
        if not os.path.isfile(path):
            print("Failed to find project: '{0}'".format(path))
            return
        with open(path, 'r') as xml_file:
            descr: dict = json.load(xml_file)

        interface_name = descr.get('interface', None)
        if interface_name is not None:
            old_interface_name = self._interface.current_interface_name
            if old_interface_name != interface_name:
                self._interface.switch(interface_name)

        self.parent.phase.logic._sample = Sample.from_dict(descr['sample'])
        self.parent.phase.logic._sample.interface = self._interface

        # send signal to tell the proxy we changed phases
        self.phasesEnabled.emit()
        self.phasesAsObjChanged.emit()
        self.structureParametersChanged.emit()
        self.parent.background._setAsXml()

        # experiment
        if 'experiments' in descr:
            self.parent.experiment.logic.experimentLoaded(True)
            self.parent.experiment.logic.experimentSkipped(False)
            self.parent.parameters.logic._data.experiments[0].x = np.array(descr['experiments'][0])
            self.parent.parameters.logic._data.experiments[0].y = np.array(descr['experiments'][1])
            self.parent.parameters.logic._data.experiments[0].e = np.array(descr['experiments'][2])
            self.parent.experiment.logic._experiment_data = self.parent.parameters.logic._data.experiments[0]
            self.parent.experiment.logic.experiments = [{'name': descr['project_info']['experiments']}]
            self.parent.experiment.logic.setCurrentExperimentDatasetName(descr['project_info']['experiments'])

            # send signal to tell the proxy we changed experiment
            self.experimentDataAdded.emit()
            self.parent.lc.parametersChanged.emit()
            self.experimentLoadedChanged.emit()

        else:
            # delete existing experiment
            self.parent.experiment.logic.removeExperiment()
            self.parent.experiment.logic.experimentLoaded(False)
            if descr['experiment_skipped']:
                self.parent.experiment.logic.experimentSkipped(True)
                self.parent.experiment.logic.experimentSkippedChanged.emit()

        # project info
        self._project_info = descr['project_info']

        new_minimizer_settings = descr.get('minimizer', None)
        if new_minimizer_settings is not None:
            new_engine = new_minimizer_settings['engine']
            new_method = new_minimizer_settings['method']

            new_engine_index = self.parent.fitting.fitter.available_engines.index(new_engine)
            self.parent.fitting.currentMinimizerIndex = new_engine_index
            new_method_index = self.parent.fitting.minimizerMethodNames.index(new_method)
            self.parent.fitting.currentMinimizerMethodIndex = new_method_index

        self.parent.fitting.fitter.fit_object = self.parent.phase.logic._sample
        self.parent.stack.logic.resetUndoRedoStack()
        self.parent.stack.logic.undoRedoChanged.emit()
        self.setProjectCreated(True)
        self.stateChanged.emit(False)

    @Slot(str)
    def loadExampleProject(self, filepath):
        self.project_load_filepath = filepath
        print("LoadProjectAs " + filepath)
        self._loadProject()
        self.currentProjectPath = '--- EXAMPLE ---'
        self.stateChanged.emit(False)

    @Property(str, notify=dummySignal)
    def projectFilePath(self):
        return self.project_save_filepath

    @Property(bool, notify=projectCreatedChanged)
    def projectCreated(self):
        return self._project_created

    @projectCreated.setter
    def projectCreated(self, created: bool):
        if self._project_created == created:
            return
        self._project_created = created
        self.projectCreatedChanged.emit()

    @Slot()
    def resetState(self):
        self._project_info = self._defaultProjectInfo()
        self.setProjectCreated(False)
        self.projectInfoChanged.emit()
        self.project_save_filepath = ""
        self.parent.experiment.logic.removeExperiment()
        if self.parent.phase.logic.samplesPresent():
            self.removePhaseSignal.emit(self.parent.phase.logic._sample.phases[self.parent.phase.logic._current_phase_index].name)
        self.reset.emit()
        self.stateHasChanged = False
        self.stateChanged.emit(False)

    @Property(bool, notify=stateChanged)
    def stateHasChanged(self):
        return self._state_changed

    def _onStateChanged(self, changed=True):
        self.stateHasChanged = changed

    @stateHasChanged.setter
    def stateHasChanged(self, changed: bool):
        if self._state_changed == changed:
            return
        self._state_changed = changed

    @Slot(str)
    def setReport(self, report):
        """
        Keep the QML generated HTML report for saving
        """
        self._report = report

    @Slot(str)
    def saveReport(self, filepath):
        """
        Save the generated report to the specified file
        Currently only html
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self._report)
            success = True
        except IOError:
            success = False
        self.htmlExportingFinished.emit(success, filepath)


def createFile(path, content):
    if os.path.exists(path):
        print(f'File already exists {path}. Overwriting...')
        os.unlink(path)
    try:
        message = f'create file {path}'
        with open(path, "w") as file:
            file.write(content)
    except Exception as exception:
        print(message, exception)
