#!/usr/bin/env python3
"""Main entry point."""
import logging
import subprocess
import sys
from argparse import ArgumentParser
from pathlib import Path
import modules.webshare as ws

logging.basicConfig(format='%(asctime)s [%(levelname)-7s] %(name)s => %(message)s',
                    datefmt='%H:%M:%S')
LOGGER = logging.getLogger('WSOSAC')


def get_creds():
    """Read the file with credentials."""
    home_dir = Path.home()
    creds_file = str(home_dir) + '/.wscreds'

    try:
        with open(creds_file) as crfile:
            username, password = crfile.read().split()
    except OSError as error:
        LOGGER.fatal('Couldn\'t read credentials file: %s', error)
        sys.exit(1)

    return username, password


def main():
    """Start main."""

    parser = ArgumentParser('Wsosac - Webshare content search utility')
    parser.add_argument('run', help='Search term')
    parser.add_argument('-d', '--debug', help='Print debug messages', action='store_true')
    parser.add_argument('-l', '--limit', help='Limit the size of files (GB)', type=int)

    args = parser.parse_args()

    if args.debug:
        LOGGER.setLevel('DEBUG')
    else:
        LOGGER.setLevel('INFO')

    username, password = get_creds()

    ws_session = ws.Webshare()
    if ws_session.login(username=username, password=password):
        ret1, ret2 = ws_session.search_content(args.run, size_limit=args.limit, category='video')
        if ret1 and ret2:
            link = ws_session.get_file(ret1, ret2)

    subprocess.run(['mpv', '--fs', link], check=True)


if __name__ == '__main__':
    main()
