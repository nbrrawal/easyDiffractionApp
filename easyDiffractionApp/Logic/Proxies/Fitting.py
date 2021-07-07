from threading import Thread
from dicttoxml import dicttoxml
from distutils.util import strtobool

from PySide2.QtCore import QObject, Signal, Slot, Property
from easyCore.Utils.UndoRedo import property_stack_deco
from easyCore.Fitting.Constraints import ObjConstraint, NumericConstraint
from easyCore.Fitting.Fitting import Fitter as CoreFitter


def _defaultFitResults():
    return {
        "success": None,
        "nvarys":  None,
        "GOF":     None,
        "redchi2": None
    }


class FittingProxy(QObject):
    """
    A proxy class to interact between the QML plot and Python datasets.
    """
    fitFinishedNotify = Signal()
    fitResultsChanged = Signal()
    dummySignal = Signal()
    currentMinimizerChanged = Signal()
    currentMinimizerMethodChanged = Signal()
    currentCalculatorChanged = Signal()
    fitFinished = Signal()
    fitStarted = Signal()
    finished = Signal(dict)
    constraintsChanged = Signal()

    def __init__(self, parent=None, interface=None):
        super().__init__(parent)

        self.parent = parent
        self.interface = interface
        self.fitter = CoreFitter(self.parent.phase.sample, self.interface.fit_func)

        # Multithreading
        # self._fitter_thread = None
        self._fit_finished = True
        self._fit_results = _defaultFitResults()
        self.data = None
        self.is_fitting_now = False
        self._current_minimizer_method_index = 0
        self._current_minimizer_method_name = self.fitter.available_methods()[0]  # noqa: E501
        self.currentMinimizerChanged.connect(self.onCurrentMinimizerChanged)

        self.fit_thread = Thread(target=self.fit_threading)
        self.finished.connect(self._setFitResults)
        self.fitFinished.emit()

        self.fitStarted.connect(self.fitFinishedNotify)
        self.fitFinished.connect(self.fitFinishedNotify)
        self.fitFinished.connect(self.fitResultsChanged)

    @Slot()
    def fit(self):
        # Currently using python threads from the `threading` module,
        # since QThreads don't seem to properly work under macos
        self.data = self.parent.parameters._data
        if not self.fit_thread.is_alive():
            self.is_fitting_now = True
            self.fit_thread.start()

    @Property('QVariant', notify=fitResultsChanged)
    def fitResults(self):
        return self._fit_results

    @Property(bool, notify=fitFinishedNotify)
    def isFitFinished(self):
        return self._fit_finished

    def fit_threading(self):
        data = self.data
        method = self._current_minimizer_method_name

        self._fit_finished = False
        self.fitStarted.emit()
        exp_data = data.experiments[0]

        x = exp_data.x
        y = exp_data.y
        weights = 1 / exp_data.e

        res = self.fitter.fit(x, y, weights=weights, method=method)
        self.finished.emit(res)

    def _setFitResults(self, res):
        if self.fit_thread.is_alive():
            self.fit_thread.join()
        self._fit_results = {
            "success": res.success,
            "nvarys":  res.n_pars,
            "GOF":     float(res.goodness_of_fit),
            "redchi2": float(res.reduced_chi)
        }
        self._fit_finished = True
        self.fitFinished.emit()
        # must reinstantiate the thread object
        self.fit_thread = Thread(target=self.fit_threading)

    ####################################################################################################################
    # Minimizer
    ####################################################################################################################

    @Property('QVariant', notify=dummySignal)
    def minimizerNames(self):
        return self.fitter.available_engines

    @Property(int, notify=currentMinimizerChanged)
    def currentMinimizerIndex(self):
        current_name = self.fitter.current_engine.name
        index = self.fitter.available_engines.index(current_name)
        return index

    @currentMinimizerIndex.setter
    @property_stack_deco('Minimizer change')
    def currentMinimizerIndex(self, new_index: int):
        if self.currentMinimizerIndex == new_index:
            return
        new_name = self.fitter.available_engines[new_index]
        self.fitter.switch_engine(new_name)
        self.currentMinimizerChanged.emit()

    # Minimizer method
    @Property('QVariant', notify=currentMinimizerChanged)
    def minimizerMethodNames(self):
        current_minimizer = self.fitter.available_engines[self.currentMinimizerIndex]  # noqa: E501
        tested_methods = {
            'lmfit': ['leastsq', 'powell', 'cobyla'],
            'bumps': ['newton', 'lm'],
            'DFO_LS': ['leastsq']
        }
        return tested_methods[current_minimizer]

    @Property(int, notify=currentMinimizerMethodChanged)
    def currentMinimizerMethodIndex(self):
        return self._current_minimizer_method_index

    @currentMinimizerMethodIndex.setter
    @property_stack_deco('Minimizer method change')
    def currentMinimizerMethodIndex(self, new_index: int):
        if self._current_minimizer_method_index == new_index:
            return

        self._current_minimizer_method_index = new_index
        self._current_minimizer_method_name = self.minimizerMethodNames[new_index]  # noqa: E501
        self.currentMinimizerMethodChanged.emit()

    def _onCurrentMinimizerMethodChanged(self):
        print("***** _onCurrentMinimizerMethodChanged")

    def onCurrentMinimizerChanged(self):
        idx = 0
        minimizer_name = self.fitter.current_engine.name
        if minimizer_name == 'lmfit':
            idx = self.minimizerMethodNames.index('leastsq')
        elif minimizer_name == 'bumps':
            idx = self.minimizerMethodNames.index('lm')
        if -1 < idx != self._current_minimizer_method_index:
            # Bypass the property as it would be added to the stack.
            self._current_minimizer_method_index = idx
            self._current_minimizer_method_name = self.minimizerMethodNames[idx]  # noqa: E501
            self.currentMinimizerMethodChanged.emit()
        return

    ####################################################################################################################
    # Calculator
    ####################################################################################################################

    @Property('QVariant', notify=dummySignal)
    def calculatorNames(self):
        return self.interface.available_interfaces

    @Property(int, notify=currentCalculatorChanged)
    def currentCalculatorIndex(self):
        return self.interface.available_interfaces.index(self.interface.current_interface_name)

    @currentCalculatorIndex.setter
    @property_stack_deco('Calculation engine change')
    def currentCalculatorIndex(self, new_index: int):
        if self.currentCalculatorIndex == new_index:
            return
        new_name = self.interface.available_interfaces[new_index]
        self.interface.switch(new_name)
        self.currentCalculatorChanged.emit()
        print("***** _onCurrentCalculatorChanged")
        self._onCurrentCalculatorChanged()
        self.parent.parameters._updateCalculatedData()

    def _onCurrentCalculatorChanged(self):
        data = self.parent.parameters._data.simulations
        data = data[0]
        data.name = f'{self.interface.current_interface_name} engine'

    ####################################################################################################################
    # Constraints
    ####################################################################################################################

    @Slot(int, str, str, str, int)
    def addConstraint(self, dependent_par_idx, relational_operator,
                      value, arithmetic_operator, independent_par_idx):
        if dependent_par_idx == -1 or value == "":
            print("Failed to add constraint: Unsupported type")
            return
        pars = [par for par in self.fitter.fit_object.get_parameters() if par.enabled]
        if arithmetic_operator != "" and independent_par_idx > -1:
            c = ObjConstraint(pars[dependent_par_idx],
                              str(float(value)) + arithmetic_operator,
                              pars[independent_par_idx])
        elif arithmetic_operator == "" and independent_par_idx == -1:
            c = NumericConstraint(pars[dependent_par_idx],
                                  relational_operator.replace("=", "=="),
                                  float(value))
        else:
            print("Failed to add constraint: Unsupported type")
            return
        # print(c)
        c()
        self.fitter.add_fit_constraint(c)
        self.constraintsChanged.emit()

    def constraintsList(self):
        constraint_list = []
        for index, constraint in enumerate(self.fitter.fit_constraints()):
            if type(constraint) is ObjConstraint:
                independent_name = constraint.get_obj(constraint.independent_obj_ids).name
                relational_operator = "="
                value = float(constraint.operator[:-1])
                arithmetic_operator = constraint.operator[-1]
            elif type(constraint) is NumericConstraint:
                independent_name = ""
                relational_operator = constraint.operator.replace("==", "=")
                value = constraint.value
                arithmetic_operator = ""
            else:
                print(f"Failed to get constraint: Unsupported type {type(constraint)}")
                return
            number = index + 1
            dependent_name = constraint.get_obj(constraint.dependent_obj_ids).name
            enabled = int(constraint.enabled)
            constraint_list.append(
                {"number": number,
                 "dependentName": dependent_name,
                 "relationalOperator": relational_operator,
                 "value": value,
                 "arithmeticOperator": arithmetic_operator,
                 "independentName": independent_name,
                 "enabled": enabled}
            )
        return constraint_list

    @Property(str, notify=constraintsChanged)
    def constraintsAsXml(self):
        xml = dicttoxml(self.constraintsList(), attr_type=False)
        xml = xml.decode()
        return xml

    @Slot(int)
    def removeConstraintByIndex(self, index: int):
        self.fitter.remove_fit_constraint(index)
        self.constraintsChanged.emit()

    @Slot(int, str)
    def toggleConstraintByIndex(self, index, enabled):
        constraint = self.fitter.fit_constraints()[index]
        constraint.enabled = bool(strtobool(enabled))
        self.constraintsChanged.emit()

    ####################################################################################################################
    ####################################################################################################################
    # STATUS
    ####################################################################################################################
    ####################################################################################################################

    def statusModelAsObj(self):
        engine_name = self.fitter.current_engine.name
        minimizer_name = self._current_minimizer_method_name
        obj = {
            "calculation":  self.interface.current_interface_name,
            "minimization": f'{engine_name} ({minimizer_name})'  # noqa: E501
        }
        self._status_model = obj
        return obj

    def statusModelAsXml(self):
        engine_name = self.fitter.current_engine.name
        minimizer_name = self._current_minimizer_method_name
        model = [
            {"label": "Calculation", "value": self.interface.current_interface_name},  # noqa: E501
            {"label": "Minimization",
             "value": f'{engine_name} ({minimizer_name})'}  # noqa: E501
        ]
        xml = dicttoxml(model, attr_type=False)
        xml = xml.decode()
        return xml
