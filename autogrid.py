# -*- coding: utf-8 -*-
import os
import logging
import re
import sys


def get_row_name(gt_file):
    in_row_block = re.compile(r'(\s*NI_BEGIN\s*NIROW)')
    in_blade_block = re.compile(r'(\s*NI_BEGIN\s*NIBLADE\s*)')
    end_block = re.compile(r'(\s*NI_END\s*NIROW)')
    name_block = re.compile(r'(\s*NAME\s*)')

    with open(gt_file, 'r') as f:
        start_row_block = False
        lines = iter(f.readlines())
        row_name = ''
        for line in lines:
            if re.search(in_blade_block, line):
                start_row_block = False
            elif re.search(in_row_block, line):
                start_row_block = True
            elif start_row_block and re.search(name_block, line):
                row_name = line.split()[1]

        return gt_file, row_name


if __name__ == '__main__':
    log_file = os.path.join('.', 'optimization.log')
    formatter = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        filename=log_file, level=logging.INFO, format=formatter
    )
    logger = logging.getLogger(__name__)

    autogrid_file_name = 'hpt.trb'
    autogrid_template = os.path.join('.', 'autogrid_template', autogrid_file_name)
    geomturbo_dir = os.path.join('.', 'geomturbo')
    geomturbo_files = []

    try:
        for item in os.listdir(geomturbo_dir):
            if (os.path.isfile(os.path.join(geomturbo_dir, item))
                    and os.path.splitext(item)[1] == '.geomTurbo'):
                geomturbo_files.append(os.path.join(geomturbo_dir, item))
    except OSError as er:
        logger.error('Autogrid. File processing error. {error}'.format(error=er))

    gt_row_files = {}
    for gt_file in geomturbo_files:
        get_row = get_row_name(gt_file)
        gt_row_files[get_row[1]] = get_row[0]

    try:
        a5_open_template(autogrid_template)
    except Exception as ex:
        logger.error('While opening file {prj} an error occurred. {exception}'.format(
            prj=autogrid_template, exception=ex
        ))

    row_names = {row(i).get_name(): i for i in range(1, a5_get_row_number()+1)}

    for row_name, i in row_names.items():
        try:
            row(i).load_geometry(gt_row_files[row_name])
            msg = 'geomTurbo file {gt} has been loaded successfully at the row {row}'
            logger.info(msg.format(gt=gt_row_files[row_name], row=row_name))
        except KeyError:
            msg = 'There is no row with name {row_name}'
            logger.warning(msg.format(row_name=row_name))
        except Exception as ex:
            msg = 'The geomTurbo file {gt} has not been loaded. An error occurred: {ex}'
            logger.error(msg.format(gt=gt_row_files[row_name], ex=ex))
            sys.exit(-1)

    autogrid_prj = os.path.join('.', 'autogrid')
    try:
        if not os.path.exists(autogrid_prj):
            os.mkdir(autogrid_prj)
            autogrid_prj = os.path.join(autogrid_prj, autogrid_file_name)
    except Exception as ex:
        logger.error(
            'While creating directory {dir} an error occurred {ex}'.format(dir=autogrid_prj, ex=ex)
        )
        sys.exit(-1)

    try:
        logger.info('Starting mesh generates...')
        rows = [row for row in row_names.keys()]
        select_all_rows()
        a5_generate_b2b_rows(rows, 0)
        a5_generate_b2b_rows(rows, 100)
        a5_generate_3d()
        logger.info('Mesh has been generated successfully.')
    except Exception as ex:
        logger.error('While mesh generating an error occurred {ex}'.format(ex=ex))

    try:
        logger.info('Trying to save project {prj}'.format(prj=autogrid_prj))
        a5_save_project(autogrid_prj)
        logger.info('The project {prj} has been saved successfully'.format(prj=autogrid_prj))
    except Exception as ex:
        logger.error('File has not been saved. An error occurred {ex}'.format(ex=ex))
        sys.exit(-1)
