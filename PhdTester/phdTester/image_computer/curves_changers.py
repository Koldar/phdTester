from typing import Dict, Callable

from phdTester.model_interfaces import ICurvesChanger, Function2D


class Identity(ICurvesChanger):
    """
    A changer that does nothing
    """

    def alter_curves(self, curves: Dict[str, Function2D]) -> Dict[str, Function2D]:
        return curves


class SortCrescentYValues(ICurvesChanger):
    """
    The changer will rearrenge the y values of each curve to ensure they are only monotonic crescent.

    This will have a huge effect! The corrispondance XY value will cease to exist, this mean that you won't know
    which Y is associate to which X
    """

    def __init__(self):
        ICurvesChanger.__init__(self)

    def alter_curves(self, curves: Dict[str, Function2D]) -> Dict[str, Function2D]:
        result = {}
        for name, f in curves.items():
            x = list(f.x_unordered_values())
            y = list(f.y_ordered_value())
            new_f = Function2D.from_xy(x, y)
            result[name] = new_f
        return result



class Multiplexer(ICurvesChanger):
    """
    A changer that sequentially apply contained curves changers
    """

    def __init__(self, *changers: ICurvesChanger):
        self.changers = changers

    def alter_curves(self, curves: Dict[str, Function2D]) -> Dict[str, Function2D]:
        result = curves

        for changer in self.changers:
            result = changer.alter_curves(result)

        return result

class ConditionCurveRemoval(ICurvesChanger):
    """
    A changer that removes curves if the given condition is not satisfied

    Conditions maybe something like:

    lambda

    """

    def __init__(self, condition: Callable[[str, Function2D], bool]):
        """
        initialize the removal

        :param condition: a function of 2 parameters such that the first parameter is the function name while the
        second is the actual function. Generates true if the function should be kept, false otherwise
        """
        self.condition = condition

    def alter_curves(self, curves: Dict[str, Function2D]) -> Dict[str, Function2D]:
        result = {}

        for name, f in map(lambda x: (x, curves[x]), curves):
            if self.condition(name, f):
                # ok, the plot is deemed ok
                result[name] = f

        return result


class LowCurveRemoval(ICurvesChanger):
    """
    A changer that removes curves which maximum never go up a certain value
    """

    def __init__(self, threshold: float, threshold_included: bool = False):
        self.threshold = threshold
        self.threshold_included = threshold_included

    def alter_curves(self, curves: Dict[str, Function2D]) -> Dict[str, Function2D]:
        result = {}

        for name, f in map(lambda x: (x, curves[x]), curves):
            for y in f.y_unordered_value():
                if (y > self.threshold) or (self.threshold_included and y == self.threshold):
                    # ok, the plot is deemed ok
                    result[name] = f
                    break


        return result
