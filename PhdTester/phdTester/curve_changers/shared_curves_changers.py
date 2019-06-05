import abc
from typing import Tuple

from phdTester.functions import DataFrameFunctionsDict
from phdTester.model_interfaces import XAxisStatus, IFunctionsDict, ICurvesChanger


class AbstractTransformX(ICurvesChanger, abc.ABC):
    """
    Transform each xaxis of each curve passed to this changes

    In this curve changer, every x value of every function will be put as input inside a mapping function and a new x
    value will be generated.

    For example if you have
    ```
    (0,3) (1,4) (2,5)
    ```

    you can pass x_new = x_old + 3
    to obtain:
    ```
    (3,3) (4,4) (5,5)
    ```
    """

    @abc.abstractmethod
    def _mapping(self, function_name: str, x_value: float, y_value: float) -> float:
        """
        the mapping function used to convert old x values into new ones
        :param function_name: the name of the function
        :param x_value: the x value (that will be replaced)
        :param y_value: the y value the function `name` has at value `x`
        :return: the new x value
        """
        pass

    def require_same_xaxis(self) -> bool:
        return False

    def alter_curves(self, curves: "IFunctionsDict") -> Tuple[XAxisStatus, "IFunctionsDict"]:
        result = DataFrameFunctionsDict.empty(functions=curves.function_names(), size=curves.max_function_length())

        for name in curves.function_names():
            for x, y in curves.get_ordered_xy(name):
                result.update_function_point(name, self._mapping(name, x, y), y)
        return XAxisStatus.UNKNOWN, result


class AbstractTransformY(ICurvesChanger, abc.ABC):
    """
    Curve changer which apply a function  to every point of every function and update only the y values

    For example if you have
    ```
    (0,3) (1,4) (2,5)
    ```

    you can pass y_new = y_old + 3
    to obtain:
    ```
    (0,6) (1,7) (2,8)
    """

    @abc.abstractmethod
    def _mapping(self, name: str, x: float, y: float) -> float:
        """
        the function which
        :param name:
        :param x:
        :param y:
        :return:
        """
        pass

    def alter_curves(self, curves: "IFunctionsDict") -> Tuple["XAxisStatus", "IFunctionsDict"]:
        for name in curves.function_names():
            for x, y in curves.get_ordered_xy(name):
                curves.update_function_point(name, x, self._mapping(name, x, curves.get_function_y(name, x)))
        return XAxisStatus.UNALTERED, curves

    def require_same_xaxis(self) -> bool:
        return False
