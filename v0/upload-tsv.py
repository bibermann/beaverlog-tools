#!/usr/bin/env python3

import argparse
import csv
import sys

import progress.bar
import requests

from all.common.auth import build_auth_header
from v0.common.auth import login
from v0.common.auth import logout
from all.common.utils import verify_response
from v0.common.clear import clear_data
from v0.common.parser import add_default_arguments
from v0.common.parser import verify_default_arguments


def import_csv( url, token, reader, on_row_complete, dry_run ):
    def normalized_date( csv_date ):
        date = csv_date.replace( ' ', 'T' )
        if len( date ) == 19:
            date += '.000Z'
        elif len( date ) == 23:
            date += 'Z'
        return date

    for row in reader:
        data = {
            'start': normalized_date( row[0] ),
            'end': normalized_date( row[1] ),
            'subject_parent_name': row[3],
            'subject_name': row[4],
            'location_name': row[2],
            **({'data': {"comment": row[5]}} if len( row ) > 5 and row[5] != '' else {})
        }
        if not dry_run:
            r = requests.post( f'{url}/activity/', json=data, headers=build_auth_header( token ) )
            verify_response( r, data )
        on_row_complete()


def import_files( url, token, filenames, dry_run ):
    for filename in filenames:
        with open( filename ) as csvfile:
            reader = csv.reader( csvfile, delimiter='\t', quotechar='"' )

            row_count = sum( 1 for _ in reader )
            csvfile.seek( 0 )

            bar = progress.bar.Bar( f'Uploading {filename}...', max=row_count )
            import_csv( url, token, reader, lambda: bar.next(), dry_run )
            bar.finish()


def main():
    parser = argparse.ArgumentParser( description='(Re)import time data.' )
    add_default_arguments( parser, with_y=True )
    parser.add_argument( '--append', action='store_true', help='do not clear data before importing' )
    parser.add_argument( '--dry-run', action='store_true', help='useful to check input files for errors' )
    parser.add_argument( 'input', metavar='INPUT', type=str, nargs='+', help='one or more tsv files' )

    args = parser.parse_args()
    verify_default_arguments( args )

    if not args.dry_run:
        access_token, refresh_token, _ = login( args.api, args.e, args.u, args.p )
    else:
        access_token = 'dummy'
        refresh_token = 'dummy'
    try:
        if not args.dry_run and not args.append:
            clear_data( args.api, access_token, args.y )
        import_files( args.api, access_token, args.input, args.dry_run )
    finally:
        if not args.dry_run:
            logout( args.api, access_token, refresh_token )

    print( 'Import successful.' )


if __name__ == "__main__":
    try:
        sys.exit( main() )
    except KeyboardInterrupt:
        sys.exit( 1 )
