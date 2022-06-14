# -*- coding: utf-8 -*-

import re


def string_matches(pattern_string, seeking_line):
    pattern = re.compile(pattern_string)
    if pattern.match(seeking_line):
        return True, pattern.match(seeking_line).group(0)
    else:
        return False, None


def parse_geomturbo(gt_file):
    side_seeking = '(\s)*(suction|pressure)'
    section_seeking = "(\s)*(#\s)?section\s*[0-9]+"
    start_row = "(\s)*NI_BEGIN(\s)*NIBLADEGEOMETRY"
    end_row = "(\s)*NI_END(\s)*NIBLADEGEOMETRY"

    airfoil = {}

    with open(gt_file, 'r') as f:
        side = False
        lines = iter(f.readlines())
        start_block = False
        for row in lines:
            line = row.strip()
            if string_matches(end_row, line)[0]:
                break
            elif string_matches(start_row, line)[0]:
                start_block = True
            elif start_block and string_matches(side_seeking, line)[0]:
                side = string_matches(side_seeking, line)[1]
                airfoil[side] = {}
            elif start_block and string_matches(section_seeking, line)[0]:
                section = string_matches(section_seeking, line)[1]
                airfoil[side][section] = []
                next(lines)
                row = next(lines)
                try:
                    num_lines = int(row)
                    points = []
                    for point in range(num_lines):
                        row = next(lines)
                        points.append([float(pt) for pt in row.strip().split()])
                    airfoil[side][section] = points
                except ValueError as ex:
                    msg = f'{ex}'

    return airfoil
