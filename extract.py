#!/usr/bin/python3

import os
import logging
import argparse
import subprocess


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

            if ext in COMMANDS.keys():
                if file_path not in EXTRACTED_FILES:
                    logger.debug('File {0} accepted'.format(filename))
                    EXTRACTED_FILES.append(file_path)
                    found_files.append(file_path)

    return found_files


def extract(paths, out_dir):
    for p in paths:
        logger.info('Extracting: {0}'.format(p))

        filename, ext = os.path.splitext(p)
        cmd = COMMANDS.get(ext)
        command = '{0} {1} {2}'.format(cmd, p, out_dir)

        logger.debug('Recived command: {0}'.format(command))

        subprocess.run(command.split())


def find_path(rootdir, name):
    r = os.path.join(rootdir, name)

    if not os.path.isdir(r):
        r = rootdir
    extract_dir = os.path.join(r, EXTRACT_DIR)

    logger.info('Output directory is {0}'.format(extract_dir))
    
    return extract_dir


def main(args):
    orig_dir = os.path.join(args.path, args.name)
    out_dir = find_path(args.path, args.name)
    found_files = False

    orig_files = find_files(orig_dir)

    if orig_files:
        logger.debug('Files in orginal path {0}'.format(orig_files))

        if not os.path.exists(out_dir):
            os.mkdir(out_dir)

        extract(orig_files, out_dir)
        found_files = True 

    while found_files:
        found_files = find_files(out_dir)

        if not found_files:
            logger.info('Finished processing directory {0}'.format(orig_dir))
        else:
            logger.debug('Files in output path {0}'.format(found_files))

            extract(found_files, out_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('id', type=str, help="The HASH/ID of the torrent")
    parser.add_argument('name', type=str, help="The name of the torrent")
    parser.add_argument('path', type=str, help="Absolute path to the root download location")
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
