from easyCore import borg
from easyCore.Objects.Groups import BaseCollection
from easyCore.Objects.Base import BaseObj
from easyDiffractionLib import Phases, Phase
from PySide2.QtCore import QObject, Property, Signal, Slot


class StackProxy(QObject):

    undoRedoChanged = Signal()
    dummySignal = Signal()

    def __init__(self, parent,
                 callbacks_no_history=None,
                 callbacks_with_history=None):
        super().__init__(parent)
        self.parent = parent
        self.callbacks_no_history = callbacks_no_history
        self.callbacks_with_history = callbacks_with_history

    def initializeBorg(self):
        # Start the undo/redo stack
        borg.stack.enabled = True
        borg.stack.clear()

    @Property(bool, notify=undoRedoChanged)
    def canUndo(self) -> bool:
        return borg.stack.canUndo()

    @Property(bool, notify=undoRedoChanged)
    def canRedo(self) -> bool:
        return borg.stack.canRedo()

    @Slot()
    def undo(self):
        if self.canUndo:
            callback = self.callbacks(borg.stack.history[0])
            borg.stack.undo()
            _ = [call.emit() for call in callback]

    @Slot()
    def redo(self):
        if self.canRedo:
            callback = self.callbacks(borg.stack.future[0])
            borg.stack.redo()
            _ = [call.emit() for call in callback]

    @Property(str, notify=undoRedoChanged)
    def undoText(self):
        return borg.stack.undoText()

    @Property(str, notify=undoRedoChanged)
    def redoText(self):
        return borg.stack.redoText()

    @Slot()
    def resetUndoRedoStack(self):
        if borg.stack.enabled:
            borg.stack.clear()
        self.undoRedoChanged.emit()

    def callbacks(self, frame=None):
        """
        """
        callback = self.callbacks_no_history
        if len(frame) > 1:
            callback = self.callbacks_with_history
        else:
            element = frame.current._parent
            if isinstance(element, (BaseObj, BaseCollection)):
                if isinstance(element, (Phase, Phases)):
                    callback = self.callbacks_with_history
                else:
                    callback = self.callbacks_no_history
            elif element is self.parent:
                # This is a property of the proxy.
                # I.e. minimizer, minimizer method, name or something boring.
                # Signals should be sent by triggering the set method.
                callback = []
            else:
                print(f'Unknown undo thing: {element}')
        return callback

