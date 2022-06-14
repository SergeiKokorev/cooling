# -*- coding: utf-8 -*-


def factorial(n: int):
    if n == 0:
        return 1
    else:
        return n * factorial(n - 1)


def bernstein_func(n: int, i: int, s: float):
    return (factorial(n) / (factorial(i) * factorial(n - i))) * (s ** i) * (1 - s) ** (n - i)


class Interpolation:
    """
    Parent class Interpolation contains base attributes and methods to
    piecewise interpolation

    Attributes
    __________
    :parameter: points list: a list of curve points
    :parameter: curve_name str: a curve name
    :parameter: length list: a list where the length of pieces will be written
    :parameter: full_length float: a full length of an entire curve
    :parameter: instances list: a list of all instances of the class

    Methods
    _______
    line_length(x: list, y: list, z: list):
        :returns: float a length of a spatial line
    set_lengths(coefficients: list, x_low_bound, x_high_bound, num_points=1000):
        :returns: list a length of a curve by using a polynomial
    get_polynomial_derivative(derivative_degree, polynomial_degree, point):
        :returns: list of coefficients of polynomial by known point
    __get_polynomial_derivative(derivative_degree: int, polynomial_degree, pt):
        :returns: float derivative of x ** n
    get_full_length():
        :returns: float full length of an entire curve
    get_lengths():
        :returns: list of lengths of pieces
    """
    instances = []

    def __init__(self, **kwargs):

        self.__points = kwargs.get('points', [])
        self.__curve_name = kwargs.get('curve_name', None)
        self.lengths = []
        self.full_length = 0.0

        self.instances.append(self)

    @property
    def points(self):
        return self.__points

    @property
    def curve_name(self):
        return self.__curve_name

    def __repr__(self):
        text = f'Class name: {self.__class__.__name__}\nCurve: {self.curve_name}\n'
        x, y, z = 'x', 'y', 'z'
        text += f'{x:<20}{y:^}{z:>17}\n'
        for pt in self.points:
            x, y, z = f'{pt[0]:.4f}', f'{pt[1]:.4f}', f'{pt[2]:.4f}'
            text += f'{x:<10}\t\t{y:^}\t\t{z:>10}\n'
        return text

    @staticmethod
    def line_length(x: list, y: list, z: list):
        return ((x[1] - x[0]) ** 2 + (y[1] - y[0]) ** 2 + (z[1] - z[0]) ** 2) ** 0.5

    @staticmethod
    def __get_polynomial_derivative(derivative_degree: int, polynomial_degree, pt):
        if polynomial_degree > derivative_degree:
            f1 = factorial(polynomial_degree)
            f2 = factorial(polynomial_degree - derivative_degree)
            degree = (polynomial_degree - derivative_degree)
            return (f1 / f2) * pt ** degree
        else:
            return factorial(polynomial_degree) * pt ** 0

    def set_lengths(self, coefficients: list, x_low_bound, x_high_bound, num_points=1000):
        dx = (x_high_bound - x_low_bound) / num_points
        x = [x_low_bound + dx * n for n in range(0, num_points + 1)]
        y = []
        for xi in x:
            y.append(sum([a * xi ** i for i, a in enumerate(coefficients[::-1])]))
        for i, xi in enumerate(x):
            if i != len(x) - 1:
                self.lengths.append(self.line_length([x[i], x[i + 1]], [y[i], y[i + 1]]))

    def get_polynomial_derivative(self, derivative_degree, polynomial_degree, point):
        result = []
        for m in range(polynomial_degree, derivative_degree - 1, -1):
            result.append(self.__get_polynomial_derivative(derivative_degree, m, point))
        return result

    def get_full_length(self):
        if self.lengths:
            return sum(self.lengths)
        else:
            return None

    def get_lengths(self):
        return self.lengths


class PiecewiseLinearInterpolation(Interpolation):

    """
    A children class to operate piecewise linear interpolation

    Methods
    _______
    set_piece_lengths():
        :returns: list of length of each linear pieces
    get_abs_coordinates(s: float = 0.0)
        :returns: list of coordinates according to relative length s
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_piece_lengths(self):
        for i, pnt in enumerate(self.points):
            if i != len(self.points) - 1:
                self.lengths.append(self.line_length(
                    [self.points[i][0], self.points[i + 1][0]],
                    [self.points[i][1], self.points[i + 1][1]],
                    [self.points[i][2], self.points[i + 1][2]])
                )

    def get_abs_coordinates(self, s: float = 0.0):
        abs_length = s * self.get_full_length()
        current_length = 0
        index = 0

        for length in self.lengths:
            current_length += length
            if current_length >= abs_length:
                index = self.lengths.index(length)
                break

        if index == 0:
            si = abs_length / self.lengths[index]
            xi = self.points[index][0] + si * (self.points[index + 1][0] - self.points[index][0])
            yi = self.points[index][1] + si * (self.points[index + 1][1] - self.points[index][1])
            zi = self.points[index][2] + si * (self.points[index + 1][2] - self.points[index][2])
        else:
            current_length = sum(self.lengths[i] for i in range(0, index))
            si = (abs_length - current_length) / self.lengths[index]
            xi = self.points[index][0] + si * (self.points[index + 1][0] - self.points[index][0])
            yi = self.points[index][1] + si * (self.points[index + 1][1] - self.points[index][1])
            zi = self.points[index][2] + si * (self.points[index + 1][2] - self.points[index][2])

        return xi, yi, zi


class BladeCurves(PiecewiseLinearInterpolation):

    """
    A class contains attributes and methods to describe and operate
    blade airfoil curves

    Attributes
    __________
    :parameter: radius float: a section radius
    :parameter: side str: a side of curve (pressure or suction)
    :parameter: blade str: a name of a blade
    :parameter: section str: a name of a section

    Methods
    _______
    get_obj(**kwargs):
        :returns: tuple of objects between which lies an object
        with a given radius
    return_index(obj):
        :returns: index of an object in the instances list
    """

    injection_sections = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.__radius = kwargs.get('radius', None)
        self.__side = kwargs.get('side', None)
        self.__blade = kwargs.get('blade', None)
        self.__section = kwargs.get('section', None)

    @property
    def radius(self):
        return self.__radius

    @property
    def side(self):
        return self.__side

    @property
    def blade(self):
        return self.__blade

    @property
    def section(self):
        return self.__section

    def __repr__(self):
        text = f'Class name: {self.__class__.__name__}\nBlade: {self.blade};\t'
        text += f'Side: {self.side};\tSection: {self.section}\n'
        text += f'Radius: {self.radius}\n'
        x, y, z = 'x', 'y', 'z'
        text += f'{x:<20}{y:^}{z:>17}\n'
        for pt in self.points:
            x, y, z = f'{pt[0]:.4f}', f'{pt[1]:.4f}', f'{pt[2]:.4f}'
            text += f'{x:<10}\t\t{y:^}\t\t{z:>10}\n'
        return text

    @classmethod
    def get_obj(cls, **kwargs):

        """
        Attributes
        __________
        :param: blade str: a name of blade
        :param: side str: a name of side
        :param: radius float: a radius lies between returned objects
        """

        blade = kwargs.get('blade', None)
        side = kwargs.get('side', None)
        radius = kwargs.get('radius', -1)

        objects = [i for i in cls.instances
                   if (i.blade, i.side) == (blade, side)]

        for i, obj in enumerate(objects):
            if obj.radius > radius:
                if i == 0:
                    return objects[i + 1], obj
                else:
                    return objects[i - 1], obj
        return objects[len(objects) - 1], objects[len(objects) - 2]

    @classmethod
    def return_index(cls, obj):
        try:
            index = cls.instances.index(obj)
            return index
        except ValueError as er:
            return None
