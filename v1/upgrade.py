#!/usr/bin/env python3

import argparse
import sys

from v1.common.data import load_data
from v1.common.data import save_data


def main():
    parser = argparse.ArgumentParser( description='Upgrade a Beaverlog data file.' )
    parser.add_argument( '-y', action='store_true', help='skip warning notice' )
    parser.add_argument( 'input', metavar='INPUT', type=str, help='source json file' )
    parser.add_argument( 'output', metavar='OUTPUT', type=str, help='target json file' )

    args = parser.parse_args()

    data = load_data( args.input, True )
    save_data( data, args.output, args.y )

    print( 'Conversion successful.' )


if __name__ == "__main__":
    try:
        sys.exit( main() )
    except KeyboardInterrupt:
        sys.exit( 1 )
