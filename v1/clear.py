#!/usr/bin/env python3

import argparse
import sys

from v1.common.auth import login
from v1.common.auth import logout
from v1.common.clear import clear_data
from v1.common.parser import add_default_arguments
from v1.common.parser import verify_default_arguments


def main():
    parser = argparse.ArgumentParser( description='Clear Beaverlog data.' )
    add_default_arguments( parser, with_y=True )

    args = parser.parse_args()
    verify_default_arguments( args )

    remote_data = login( args.api, args.e, args.u, args.p )
    try:
        clear_data( remote_data, args.y )
    finally:
        logout( remote_data )

    print( 'Clear successful.' )


if __name__ == "__main__":
    try:
        sys.exit( main() )
    except KeyboardInterrupt:
        sys.exit( 1 )
