# -*- coding: utf-8 -*-

import os
import platform
import logging
import re
import csv
import subprocess
import sys


from parse_geom import parse_geomturbo
from interpolation import BladeCurves


def get_os():
    return platform.system(), platform.release()


def find_directory(dir_pattern, directory):
    for dir_ in os.listdir(directory):
        if re.search(dir_pattern, dir_):
            return True, re.search(dir_pattern, dir_).group()
    return False, None


def radius_generator(points: list):
    i = 0
    while i < len(points):
        yield ((points[i][0] ** 2 + points[i][1] ** 2) ** 0.5) / len(points)
        i += 1


def get_radius(point: list):
    return (point[0] ** 2 + point[1] ** 2) ** 0.5


def get_index(val, iterator):
    for i in iterator:
        if i > val:
            return iterator.index(i)
    return len(iterator) - 1


def line_equation(p1: list, p2: list, x: float):
    return [
        x,
        p1[1] + (x - p1[0]) * (p2[1] - p1[1]) / (p2[0] - p1[0]),
        p1[2] + (x - p1[0]) * (p2[2] - p1[2]) / (p2[0] - p1[0])
    ]


def get_coordinates(pt1: list, pt2: list, value: float, n: int = 100):

    pm = line_equation(pt1, pt2, (pt2[0] + pt1[0]) / 2)
    current_value = get_radius(pm)
    eps = 10 ** -6

    if current_value > get_radius(pt2):
        x = pt2[0] + (pt2[0] - pt1[0])
        point1 = pt2
        point2 = line_equation(pt1, pt2, x)
        return get_coordinates(point1, point2, value, n)
    elif current_value < get_radius(pt1):
        x = pt1[0] - (pt2[0] - pt1[0])
        point1 = line_equation(pt1, pt2, x)
        point2 = pt1
        return get_coordinates(point1, point2, value, n)

    if abs(current_value - value) <= eps:
        return pm
    # Go to right side
    elif current_value > value:
        return get_coordinates(pt1, pm, value, n)
    # Go to left side
    elif current_value < value:
        return get_coordinates(pm, pt2, value, n)
    elif current_value == value:
        return pm


if __name__ == "__main__":

    coef = 1000  # Units conversion
    units = {
        'm': 1000, 'dm': 100, 'cm': 10, 'mm': 1
    }

    # Patterns to search units, section radius and injection hole diameters
    unit_pattern = re.compile(
        r'(\bm{1,2}\b)|(\bcm\b)|(\bdm\b)|(\bC\b)|(\bK\b)|(\bkg\s+s-1\b)'
    )
    radius_pattern = re.compile(r'(\br\s+\[\w+\])')
    hole_diameter_pattern = re.compile(r'(\bDiameter\s+\[\w+\])')

    # Logger configuration
    log_file = os.path.join('.', 'optimization.log')
    formatter = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        filename=log_file, level=logging.ERROR, format=formatter
    )
    logger = logging.getLogger(__name__)

    # geomTurbo directory reading, geomTurbo file searching
    geomturbo_dir = os.path.join('.', 'geomturbo')
    try:
        gt_files = [os.path.join(geomturbo_dir, f)
                    for f in os.listdir(geomturbo_dir)
                    if os.path.splitext(f)[1] == '.geomTurbo']
    except FileNotFoundError:
        gt_files = []
        log_msg = f'System could not find the specified path {geomturbo_dir}'
        logger.error(log_msg)

    # Injection configuration
    injections = []
    injection_cfg_file = os.path.join('.', 'injections.cfg')
    # Reading the injection configuration file and writing it into dictionary
    try:
        with open(injection_cfg_file, newline='') as inj_cfg:
            cfg = csv.DictReader(inj_cfg)
            for row in cfg:
                injections.append(row)
    except FileNotFoundError:
        logger.error(f'Injection configuration file {injection_cfg_file} has not been found.')
        injections = None

    # Generating list of cooling blade and side
    if injections:
        items = [f'{b["blade"]}_{b["side"]}' for b in injections]

        pattern = re.compile(r'(rb_?\d+)|(gv_?\d+)')
        radii = {}
        xyz = {}

        # Reading geomTurbo file and writing coordinates into dictionary
        for gtf in gt_files:
            points_dict = parse_geomturbo(gtf)
            blade = re.search(pattern, os.path.split(gtf)[1]).group()

            for side, section_dict in points_dict.items():
                if f'{blade}_{side}' in items:
                    for section, pts in section_dict.items():
                        section_name = f'{section.split(" ")[1]}_{section.split(" ")[2]}'
                        radius = sum([r for r in radius_generator(pts)])
                        xyz[f'{blade}_{side}_{section_name}'] = pts
                        BladeCurves(
                            points=pts, curve_name=f'{blade}_{side}_{section_name}',
                            radius=radius,
                            side=side, blade=blade, section=section_name
                        )

        injections_dir = os.path.join('.', 'injections')
        try:
            os.mkdir(injections_dir)
        except PermissionError as er:
            logger.warning(f'Failed to create directory {injections_dir}. An error occurs {er}')
        except FileNotFoundError as er:
            logger.error(f'Failed to create directory {injections_dir}. An error occurs {er}')
            sys.exit(1)
        except FileExistsError as er:
            logger.warning(f'Failed to create directory {injections_dir}. An error occurs {er}')

        # Find section embracing an injection radius
        keys_pattern = [
            r'(\br\s+\[\w+\])', r'(\bDiameter\s+\[\w+\])',
            r'(\bTemperature\s+\[\w+\])',
            r'(\bMass\sFlow\sRate\s+\[\w+\s+\])'
        ]

        for i, inj in enumerate(injections, 1):
            try:
                radius_key = [k for k in inj.keys() if re.search(radius_pattern, k)][0]
                radius_unit = re.search(unit_pattern, radius_key).group()
                unit = units[radius_unit]
                radii = [float(r) * unit for r in inj[radius_key].split(' ')]
                for radius in radii:
                    section = []
                    sections = BladeCurves.get_obj(blade=inj['blade'], side=inj['side'], radius=radius)
                    for p1, p2 in zip(sections[0].points, sections[1].points):
                        section.append(get_coordinates(p1, p2, radius))
                    BladeCurves(
                        points=section,
                        curve_name=f'{inj["blade"]}_{inj["side"]}_radius_{radius}_injection_{i}',
                        radius=radius, side=inj['side'], blade=inj['blade'],
                        section=f'injection_{i}_radius_{radius}'
                    )
            except ValueError as er:
                logger.error(f'An error occurred {er}. Tried to convert '
                             f'Injection radius to float: {inj["r"].split(" ")[0]}')
                sys.exit(1)
            except KeyError as er:
                logger.error(f'Key error occurs while '
                             f'trying to read injection '
                             f'configuration dictionary.\n'
                             f'There is no such key in the dictionary: {er}')
                sys.exit(1)
            except TypeError as er:
                logger.error(f'An error occurred while reading injection data.')
                sys.exit(-1)

        # Writing Ansys csv injection region file
        # Finding injection region sections
        injection_pattern = re.compile(r'(injection_\d+)')
        injection_regions = [
            obj for obj in BladeCurves.instances if re.search(injection_pattern, obj.section)
        ]

        for i, inj in enumerate(injections, 1):

            # Getting radius, diameter of injection holes dict key and their units
            radius_key = [k for k in inj.keys() if re.search(radius_pattern, k)][0]
            radius_unit = re.search(unit_pattern, radius_key).group()
            hole_diameter_key = [k for k in inj.keys() if re.search(hole_diameter_pattern, k)][0]
            radii = [float(r) for r in inj[radius_key].split(' ')]

            # Setting Ansys csv injection file name
            injection_file_name = f"{inj['blade']}_{inj['side']}_injection_{i}.csv"
            injection_file = os.path.join(injections_dir, injection_file_name)
            injection_name = f"Injection {inj['blade']} {inj['side']} {i}"

            with open(injection_file, 'w', newline='') as f:
                # Writing file header with injection name and parameters
                f.write('[Name]\n')
                f.write(f'{injection_name}\n\n')
                f.write(f'[Parameters]\n')
                # Writing injection parameters
                for key, val in inj.items():
                    if key not in ['blade', 'side', 's', hole_diameter_key, radius_key]:
                        key_parameter = key.split(' ')[0]
                        key_unit = re.search(unit_pattern, key).group()
                        f.write(f'{key_parameter} = {val} [{key_unit}]\n')
                f.write('\n\n')
                f.write('[Spatial Fields]\n')
                f.write('x, y, z\n\n')
                f.write('[Data]\n')
                f.write('x [ m ], y[ m ], z [ m ], Direction u [], Direction v [], Direction w []\n')

                # Writing absolute coordinates of the injection points
                # for each radius and relative length s
                for radius in radii:
                    injection_section = [
                       obj for obj in injection_regions if (
                                obj.radius == radius * units[radius_unit] and
                                obj.blade == inj['blade'] and
                                obj.side == inj['side']
                        )
                    ][0]
                    injection_section.set_piece_lengths()
                    try:
                        s = [float(si) for si in inj['s'].split(' ')]
                        d = float(inj[hole_diameter_key])
                    except ValueError as er:
                        logger.error(f'Trying to convert {inj["s"]} to float. An error occurs {er}')
                        sys.exit(-1)
                    for si in s:
                        x, y, z = injection_section.get_abs_coordinates(si)
                        zdir = -1 if re.search(r'(rb\d+)', inj['blade']) else 1
                        f.write(f'{x / coef}, {y / coef}, {z / coef}, 0, 0, {zdir}, {d}\n')

    # Running AutoGrid
    os_name = get_os()
    igg_run_file = ''
    if 'Windows' in os_name:
        pattern = re.compile('(NUMECA\w+)')
        numeca = find_directory(pattern, 'C:\\')
        if numeca[0]:
            pattern = re.compile('(fine\d+)')
            numeca_version = find_directory(pattern, f'C:\\{numeca[1]}')
            if numeca_version[0]:
                igg_run_file = f'C:\\{numeca[1]}\\{numeca_version[1]}\\bin64\\iggx86_64.exe'
    elif 'Linux' in os_name:
        igg_run_file = 'igg'
    else:
        logger.error(f'Unknown os system {os_name[0]}')
        sys.exit(-1)

    autogrid_python_file = os.path.join('.', 'autogrid.py')

    try:
        subprocess.run([
            igg_run_file, '-autogrid5', '-batch', '-script', autogrid_python_file
        ])
    except OSError as er:
        logger.error(f'While starting {igg_run_file} an error occurs. {er}.\n'
                     f'The parameter has been set incorrectly or file {igg_run_file}'
                     f' has not been found.')
        sys.exit(-1)
