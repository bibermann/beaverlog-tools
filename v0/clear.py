#!/usr/bin/env python3

import argparse
import sys

import requests

from common.auth import build_auth_header
from common.auth import login
from common.auth import logout
from common.utils import verify_response
from v0.detail.parser import add_default_arguments
from v0.detail.parser import verify_default_arguments


def clear_data( url, token, skip_warning ):
    if not skip_warning:
        print( f'WARNING: This will permanently delete all your data' )
        print( f'         on {url}' )
        input( 'Press Enter to continue' )
    print( 'Removing data...' )
    r = requests.delete( f'{url}/batch/all-private', headers=build_auth_header( token ) )
    verify_response( r )


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
