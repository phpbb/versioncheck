#!/usr/bin/env python3
"""Validate phpbb/versions.json and the phpbb/*.txt version check files."""

import json
import re
import sys
from pathlib import Path

PHPBB_DIR = Path(__file__).resolve().parents[2] / 'phpbb'

VERSION_RE = re.compile(r'^\d+\.\d+\.\d+(-(a|b|rc|pl)\d+)?$', re.IGNORECASE)
BRANCH_RE = re.compile(r'^\d+\.\d+$')
URL_RE = re.compile(r'^https?://\S+$')

REQUIRED_KEYS = {'current', 'announcement', 'eol', 'security'}
OPTIONAL_KEYS = {'critical'}

errors = []


def error(file, message):
    errors.append(f'{file}: {message}')


def is_version_or_false(value):
    return value is False or (isinstance(value, str) and VERSION_RE.match(value))


def validate_versions_json(path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as e:
        error(path.name, f'invalid JSON: {e}')
        return

    if not isinstance(data, dict) or not data:
        error(path.name, 'top level must be a non-empty object')
        return

    for channel, branches in data.items():
        if not isinstance(branches, dict) or not branches:
            error(path.name, f'"{channel}" must be a non-empty object')
            continue

        for branch, info in branches.items():
            where = f'{channel}.{branch}'
            if not BRANCH_RE.match(branch):
                error(path.name, f'{where}: invalid branch name')
            if not isinstance(info, dict):
                error(path.name, f'{where}: must be an object')
                continue

            missing = REQUIRED_KEYS - info.keys()
            unknown = info.keys() - REQUIRED_KEYS - OPTIONAL_KEYS
            if missing:
                error(path.name, f'{where}: missing keys {sorted(missing)}')
            if unknown:
                error(path.name, f'{where}: unknown keys {sorted(unknown)}')

            current = info.get('current')
            if 'current' in info:
                if not isinstance(current, str) or not VERSION_RE.match(current):
                    error(path.name, f'{where}.current: invalid version {current!r}')
                elif not current.startswith(branch + '.'):
                    error(path.name, f'{where}.current: {current} does not belong to branch {branch}')

            announcement = info.get('announcement')
            if 'announcement' in info and not (isinstance(announcement, str) and URL_RE.match(announcement)):
                error(path.name, f'{where}.announcement: invalid URL {announcement!r}')

            eol = info.get('eol')
            if 'eol' in info and eol is not None and not isinstance(eol, str):
                error(path.name, f'{where}.eol: must be null or a string')

            for key in ('security', 'urgent'):
                if key in info and not is_version_or_false(info[key]):
                    error(path.name, f'{where}.{key}: must be false or a version, got {info[key]!r}')


def read_lines(path):
    try:
        content = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as e:
        error(path.name, f'unreadable: {e}')
        return None
    if '\r' in content:
        error(path.name, 'contains CR characters (use LF line endings)')
    return content.rstrip('\n').split('\n')


def validate_20x_txt(path):
    """Three lines with the major, minor and revision numbers of the 2.0.x release."""
    lines = read_lines(path)
    if lines is None:
        return
    if len(lines) != 3:
        error(path.name, f'expected 3 lines, got {len(lines)}')
    for i, line in enumerate(lines, 1):
        if not line.isdigit():
            error(path.name, f'line {i}: expected a number, got {line!r}')


def validate_pairs_txt(path):
    """Alternating version / announcement URL lines."""
    lines = read_lines(path)
    if lines is None:
        return
    if not lines or len(lines) % 2:
        error(path.name, f'expected version/URL line pairs, got {len(lines)} lines')
    for i, line in enumerate(lines, 1):
        if i % 2:
            if not VERSION_RE.match(line):
                error(path.name, f'line {i}: invalid version {line!r}')
        elif not URL_RE.match(line):
            error(path.name, f'line {i}: invalid URL {line!r}')


def main():
    validate_versions_json(PHPBB_DIR / 'versions.json')

    txt_files = sorted(PHPBB_DIR.glob('*.txt'))
    for path in txt_files:
        if path.name == '20x.txt':
            validate_20x_txt(path)
        else:
            validate_pairs_txt(path)

    if errors:
        for message in errors:
            print(f'::error::{message}')
        return 1

    print(f'versions.json and {len(txt_files)} txt file(s) are valid')
    return 0


if __name__ == '__main__':
    sys.exit(main())
