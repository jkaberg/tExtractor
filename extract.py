#!/usr/bin/python3

import os
import logging
import tempfile
import argparse
import subprocess
import shutil

EXTRACT_DIR = '__extracted'
EXTRACTED_FILES = []
COMMANDS = {'.rar': 'unrar -r -o- e',
            '.001': 'unrar -r -o- e',
            '.zip': 'unzip -u -d'
            }


def find_files(path):
    found_files = []

    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            filename, ext = os.path.splitext(file_path)

            if ext in COMMANDS.keys() and file_path not in EXTRACTED_FILES:
                logger.debug('Accepted: {0}'.format(os.path.basename(file_path)))
                EXTRACTED_FILES.append(file_path)
                found_files.append(file_path)

    return found_files


def extract(paths, out_dir):
    for p in paths:
        logger.info('Extracting: {0}'.format(p))

        filename, ext = os.path.splitext(p)
        cmd = COMMANDS.get(ext)

        util = cmd.split()[0]
        exec_path = shutil.which(util)
        if not exec_path:
            logger.error('Cant find executable {0}, not extracting {1}'.format(util, p))
            continue

        cmd = cmd.replace(util, exec_path)

        command = '{0} {1} {2}'.format(cmd, p, out_dir)
        logger.debug('Command: {0}'.format(command))

        subprocess.run(command.split())


def find_path(path, name):
    path = os.path.join(path, name)

    if os.path.isdir(path):
        return os.path.join(path, EXTRACT_DIR)

    return False


def main(args):
    orig_dir = os.path.join(args.path, args.name)
    logger.debug('Processing directory: {0}'.format(orig_dir))
    out_dir = find_path(args.path, args.name)
    if args.tmp:
        try:
            temp_dir = tempfile.mkdtemp(dir=args.tmp)
        except:
            logger.warn('Failed to create temporary extraction directory in specified location. Falling back to system default.')
            temp_dir = tempfile.mkdtemp()
    else:
        temp_dir = tempfile.mkdtemp()

    logger.debug('Using temporary extraction directory: {0}'.format(temp_dir))

    # no out_dir means this is a single file torrent
    if out_dir:
        logger.info('Output directory: {0}'.format(out_dir))

        files = find_files(orig_dir)

        # extact compressed archives found in the original path
        if files:
            logger.debug('Files in original path: {0}'.format(files))

            extract(files, temp_dir)

            # extract (also nested) archives found in the output path, if we found files in the original path
            while files:
                files = find_files(temp_dir)

                if files:
                    logger.debug('Files in output path: {0}'.format(files))
                    extract(files, temp_dir)
                else:
                    logger.info('Finished processing directory: {0}'.format(orig_dir))

            if not os.path.exists(out_dir):
                os.mkdir(out_dir)

            logger.debug('Moving files from temporary directory: {0} to: {1}'.format(temp_dir, out_dir))

            for f in os.listdir(temp_dir):
                logger.debug('Moving file: {0} to: {1}'.format(f, out_dir))
                shutil.move(os.path.join(temp_dir, f), out_dir)

    else:
        logger.warn('This must be a single file torrent, exiting!')

    if temp_dir:
        logger.debug('Removing temporary directory: {0}'.format(temp_dir))
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            logger.warn('Failed to remove temporary extraction directory: {0}'.format(temp_dir))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('id', type=str, help="The HASH/ID of the torrent")
    parser.add_argument('name', type=str, help="The name of the torrent")
    parser.add_argument('path', type=str, help="Absolute path to the root download location")
    parser.add_argument("-t", "--tmp", help="Absolute path to temp extraction directory (must exist)")
    parser.add_argument("-v", "--verbose", help="Set loglevel to debug", action="store_true")
    args = parser.parse_args()


    logger = logging.getLogger()
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    main(args)
