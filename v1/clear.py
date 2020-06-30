#!/usr/bin/env python3

import argparse
import sys

from v1.common.auth import login
from v1.common.auth import logout
from v1.common.clear import clear_data
from v1.common.parser import add_default_arguments
from v1.common.parser import verify_default_arguments


def main():
    parser = argparse.ArgumentParser( description='(Re)import time data.' )
    add_default_arguments( parser, with_y=True )

    args = parser.parse_args()
    verify_default_arguments( args )

    access_token, refresh_token, _ = login( args.api, args.e, args.u, args.p )
    try:
        clear_data( args.api, access_token, args.y )
    finally:
        logout( args.api, access_token, refresh_token )

    print( 'Clear successful.' )


if __name__ == "__main__":
    try:
        sys.exit( main() )
    except KeyboardInterrupt:
        sys.exit( 1 )
