from PySide2.QtCore import QObject, Signal, Property
from easyCore.Utils.UndoRedo import property_stack_deco


class Plotting3dProxy(QObject):
    # Plotting
    current3dPlottingLibChanged = Signal()
    structureViewChanged = Signal()
    dummySignal = Signal()

    def __init__(self):
        super().__init__()
        self.current3dPlottingLibChanged.connect(self.onCurrent3dPlottingLibChanged)
        # Plotting 3D
        self._3d_plotting_libs = ['chemdoodle', 'qtdatavisualization']
        self._current_3d_plotting_lib = self._3d_plotting_libs[0]

        self._show_bonds = True
        self._bonds_max_distance = 2.0

    @Property('QVariant', notify=current3dPlottingLibChanged)
    def current3dPlottingLib(self):
        return self._current_3d_plotting_lib

    @current3dPlottingLib.setter
    @property_stack_deco('Changing 3D library from {old_value} to {new_value}')
    def current3dPlottingLib(self, plotting_lib):
        self._current_3d_plotting_lib = plotting_lib
        self.current3dPlottingLibChanged.emit()

    def onCurrent3dPlottingLibChanged(self):
        self.logic.onCurrent3dPlottingLibChanged()

    @Property('QVariant', notify=dummySignal)
    def plotting3dLibs(self):
        return self._3d_plotting_libs

    @Property(bool, notify=structureViewChanged)
    def showBonds(self):
        return self._show_bonds

    @showBonds.setter
    def showBonds(self, show_bonds: bool):
        if self._show_bonds == show_bonds:
            return
        self._show_bonds = show_bonds
        self.structureViewChanged.emit()

    @Property(float, notify=structureViewChanged)
    def bondsMaxDistance(self):
        return self._bonds_max_distance

    @bondsMaxDistance.setter
    def bondsMaxDistance(self, max_distance: float):
        if self._bonds_max_distance == max_distance:
            return
        self._bonds_max_distance = max_distance
        self.structureViewChanged.emit()
