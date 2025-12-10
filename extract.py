#!/usr/bin/python3

import os
import re
import logging
import tempfile
import argparse
import subprocess
import shutil

EXTRACT_DIR = '__extracted'

# Ordered for specific suffix matching first
COMMAND_PATTERNS = [
    ('.tar.gz', ('tar', lambda exe, archive, out_dir: [exe, '-xzf', archive, '-C', out_dir])),
    ('.tgz', ('tar', lambda exe, archive, out_dir: [exe, '-xzf', archive, '-C', out_dir])),
    ('.tar.bz2', ('tar', lambda exe, archive, out_dir: [exe, '-xjf', archive, '-C', out_dir])),
    ('.tbz2', ('tar', lambda exe, archive, out_dir: [exe, '-xjf', archive, '-C', out_dir])),
    ('.tar.xz', ('tar', lambda exe, archive, out_dir: [exe, '-xJf', archive, '-C', out_dir])),
    ('.txz', ('tar', lambda exe, archive, out_dir: [exe, '-xJf', archive, '-C', out_dir])),
    ('.tar', ('tar', lambda exe, archive, out_dir: [exe, '-xf', archive, '-C', out_dir])),
    ('.7z', ('7z', lambda exe, archive, out_dir: [exe, 'x', '-y', f'-o{out_dir}', archive])),
    ('.zip', ('unzip', lambda exe, archive, out_dir: [exe, '-u', archive, '-d', out_dir])),
    ('.001', ('unrar', lambda exe, archive, out_dir: [exe, '-r', '-o-', 'e', archive, out_dir])),
    ('.rar', ('unrar', lambda exe, archive, out_dir: [exe, '-r', '-o-', 'e', archive, out_dir])),
]


def _spec_for_suffix(suffix):
    for suf, spec in COMMAND_PATTERNS:
        if suf == suffix:
            return spec
    return None


def _is_primary_part(part_str):
    return int(part_str.lstrip("0") or "0") == 1


def _detect_7z_split(file_path):
    """Return spec for primary 7z split volumes (.7z.001 or .part1.7z)."""
    lower_name = os.path.basename(file_path).lower()

    if lower_name.endswith('.7z.001'):
        return _spec_for_suffix('.7z')

    part_match = re.search(r'\.part(\d+)\.7z$', lower_name)
    if part_match:
        return _spec_for_suffix('.7z') if _is_primary_part(part_match.group(1)) else None
    return None


def _detect_zip_split(file_path):
    """
    Return spec for zip or split-zip primary.
    - Prefer the .zip if present.
    - If only split parts (.zip.001/.z01) exist, use 7z to extract.
    """
    lower_name = os.path.basename(file_path).lower()
    dir_path = os.path.dirname(file_path)
    base_name = os.path.basename(file_path)

    if lower_name.endswith('.zip'):
        return _spec_for_suffix('.zip')

    if lower_name.endswith('.zip.001') or lower_name.endswith('.z01'):
        base = re.sub(r'\.(zip\.001|z01)$', '', base_name, flags=re.IGNORECASE)
        zip_candidate = os.path.join(dir_path, f"{base}.zip")
        if os.path.exists(zip_candidate):
            return None
        return _spec_for_suffix('.7z')
    return None


def _detect_tar_split(file_path):
    """Return spec for tar-like splits; handled via 7z."""
    lower_name = os.path.basename(file_path).lower()
    dir_path = os.path.dirname(file_path)
    tar_split_suffixes = [
        '.tar.gz.001', '.tgz.001',
        '.tar.bz2.001', '.tbz2.001',
        '.tar.xz.001', '.txz.001',
        '.tar.001',
    ]
    for suf in tar_split_suffixes:
        if lower_name.endswith(suf):
            base = lower_name[:-len(suf)]
            existing_candidates = [
                os.path.join(dir_path, f"{base}.tar.gz"),
                os.path.join(dir_path, f"{base}.tgz"),
                os.path.join(dir_path, f"{base}.tar.bz2"),
                os.path.join(dir_path, f"{base}.tbz2"),
                os.path.join(dir_path, f"{base}.tar.xz"),
                os.path.join(dir_path, f"{base}.txz"),
                os.path.join(dir_path, f"{base}.tar"),
            ]
            if any(os.path.exists(c) for c in existing_candidates):
                return None
            return _spec_for_suffix('.7z')
    return None


def _detect_rar_split(file_path):
    """
    Return spec for RAR primary volume.
    - .rar
    - .part1/.part01.rar
    - .001 only if no sibling .rar/.part1.rar exists
    - .r00 only if no sibling .rar/.part1.rar exists
    """
    lower_name = os.path.basename(file_path).lower()
    dir_path = os.path.dirname(file_path)
    base_name = os.path.basename(file_path)

    # Avoid misclassifying split 7z parts
    if lower_name.endswith('.7z.001') or re.search(r'\.part\d+\.7z$', lower_name):
        return None

    if lower_name.endswith('.001'):
        base = base_name[:-4]
        rar_candidate = os.path.join(dir_path, f"{base}.rar")
        part1_candidate = os.path.join(dir_path, f"{base}.part1.rar")
        if os.path.exists(rar_candidate) or os.path.exists(part1_candidate):
            return None
        return _spec_for_suffix('.rar')

    part_rar = re.search(r'\.part(\d+)\.rar$', lower_name)
    if part_rar:
        base = re.sub(r'\.part\d+\.rar$', '', base_name)
        rar_candidate = os.path.join(dir_path, f"{base}.rar")
        if os.path.exists(rar_candidate):
            return None  # prefer .rar over part1
        return _spec_for_suffix('.rar') if _is_primary_part(part_rar.group(1)) else None

    r_match = re.search(r'\.r(\d{2})$', lower_name)
    if r_match and int(r_match.group(1)) == 0:
        base = re.sub(r'\.r\d{2}$', '', base_name)
        rar_candidate = os.path.join(dir_path, f"{base}.rar")
        part1_candidate = os.path.join(dir_path, f"{base}.part1.rar")
        if os.path.exists(rar_candidate) or os.path.exists(part1_candidate):
            return None
        return _spec_for_suffix('.rar')

    if lower_name.endswith('.rar'):
        base = lower_name[:-4]
        part1_candidate = os.path.join(dir_path, f"{base}.part1.rar")
        if os.path.exists(part1_candidate):
            return None  # prefer part1 over bare .rar of same base
        return _spec_for_suffix('.rar')
    return None


def multipart_command_spec(file_path):
    """
    Return a command spec for multi-part archives if this file is the primary volume.
    """
    detectors = (
        _detect_7z_split,
        _detect_zip_split,
        _detect_tar_split,
        _detect_rar_split,
    )
    for detector in detectors:
        spec = detector(file_path)
        if spec:
            return spec
    return None


def command_spec_for(file_path):
    """Return (util, builder) for supported archive, or None if not extractable or not primary part."""
    lower_name = os.path.basename(file_path).lower()

    multipart_spec = multipart_command_spec(file_path)
    if multipart_spec:
        return multipart_spec

    for suffix, spec in COMMAND_PATTERNS:
        if lower_name.endswith(suffix):
            return spec
    return None


def find_files(path, seen):
    found_files = []

    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)

            if file_path in seen:
                continue

            if command_spec_for(file_path):
                logger.debug('Accepted: {0}'.format(os.path.basename(file_path)))
                seen.add(file_path)
                found_files.append(file_path)

    return found_files


def extract(paths, out_dir):
    for p in paths:
        logger.info('Extracting %s to %s', p, out_dir)

        command_spec = command_spec_for(p)
        if not command_spec:
            logger.error('Unknown extension, not extracting {0}'.format(p))
            continue

        util, builder = command_spec

        exec_path = shutil.which(util)
        if not exec_path:
            logger.error('Cant find executable {0}, not extracting {1}'.format(util, p))
            continue

        command = builder(exec_path, p, out_dir)
        logger.debug('Command argv: {0}'.format(command))

        try:
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            logger.error('Extraction failed (%s): %s', p, e)


def find_path(path, name):
    path = os.path.join(path, name)

    if os.path.isdir(path):
        return os.path.join(path, EXTRACT_DIR)

    return False


def safe_move(src, dst_dir, remove_src=False):
    """Move a file, optionally deleting source only when allowed."""
    os.makedirs(dst_dir, exist_ok=True)
    try:
        shutil.move(src, dst_dir)
        return
    except OSError as e:
        logger.warning('Move failed (%s), falling back to copy: %s -> %s', e, src, dst_dir)

    dst_path = os.path.join(dst_dir, os.path.basename(src))
    try:
        shutil.copy2(src, dst_path)
        if remove_src:
            os.remove(src)
    except Exception as e:
        logger.error('Copy fallback failed: %s -> %s (%s)', src, dst_dir, e)


def main(args):
    orig_dir = os.path.join(args.path, args.name)
    logger.debug('Processing directory: {0}'.format(orig_dir))
    out_dir = find_path(args.path, args.name)
    seen = set()

    if not out_dir:
        logger.debug('This must be a single file torrent, exiting!')
        return

    logger.info('Output directory: {0}'.format(out_dir))

    try:
        temp_context = tempfile.TemporaryDirectory(dir=args.tmp) if args.tmp else tempfile.TemporaryDirectory()
    except Exception:
        logger.warning('Failed to create temporary extraction directory in specified location. Falling back to system default.')
        temp_context = tempfile.TemporaryDirectory()

    with temp_context as temp_dir:
        logger.debug('Using temporary extraction directory: {0}'.format(temp_dir))

        files = find_files(orig_dir, seen)
        if not files:
            logger.info('No archives found in: {0}'.format(orig_dir))
            return

        while files:
            logger.debug('Files queued for extraction: {0}'.format(files))
            extract(files, temp_dir)
            files = find_files(temp_dir, seen)
            if not files:
                logger.info('Finished processing directory: {0}'.format(orig_dir))

        os.makedirs(out_dir, exist_ok=True)
        logger.debug('Moving files from temporary directory: {0} to: {1}'.format(temp_dir, out_dir))

        for f in os.listdir(temp_dir):
            logger.debug('Moving file: {0} to: {1}'.format(f, out_dir))
            # files in temp_dir are extraction outputs; safe to delete after copy fallback
            safe_move(os.path.join(temp_dir, f), out_dir, remove_src=True)


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
    if not logger.handlers:
        logger.addHandler(handler)
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    main(args)
