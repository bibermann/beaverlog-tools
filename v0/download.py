#!/usr/bin/env python3

import json
import argparse
import sys
import os
import collections
import datetime

import requests
import progress.bar

from common.utils import verify_response
from common.utils import print_err
from common.utils import date_to_string
from common.auth import login
from common.auth import logout
from common.auth import build_auth_header


def simple_changeset_to_list( data ):
    return [x['data'] for x in data['changeset']]


def fetch_users( url, token ):
    r = requests.get( f'{url}/user/all', headers=build_auth_header( token ) )
    verify_response( r )
    return simple_changeset_to_list( r.json() )


def fetch_organizations( url, token ):
    r = requests.get( f'{url}/organization/', headers=build_auth_header( token ) )
    verify_response( r )
    return simple_changeset_to_list( r.json() )


def fetch_subjects( url, token ):
    r = requests.get( f'{url}/subject/', headers=build_auth_header( token ) )
    verify_response( r )
    return simple_changeset_to_list( r.json() )


def fetch_locations( url, token ):
    r = requests.get( f'{url}/location/', headers=build_auth_header( token ) )
    verify_response( r )
    return simple_changeset_to_list( r.json() )


def fetch_activities( url, token ):
    r = requests.get( f'{url}/activity/', headers=build_auth_header( token ) )
    verify_response( r )
    return simple_changeset_to_list( r.json() )


def fetch_data( url, token ):
    bar = progress.bar.Bar( f'Downloading...', max=5 )
    users = fetch_users( url, token )
    bar.next()
    organizations = fetch_organizations( url, token )
    bar.next()
    subjects = fetch_subjects( url, token )
    bar.next()
    locations = fetch_locations( url, token )
    bar.next()
    activities = fetch_activities( url, token )
    bar.next()
    bar.finish()
    return collections.OrderedDict( [
        ('users', users),
        ('organizations', organizations),
        ('subjects', subjects),
        ('locations', locations),
        ('activities', activities),
    ] )


def export_data( url, token, filename, skip_warning, user_id ):
    data = collections.OrderedDict( [
        ('exported_on', date_to_string( datetime.datetime.utcnow() )),
        ('user_id', user_id),
        ('data', fetch_data( url, token ))
    ] )

    if os.path.exists( filename ) and not skip_warning:
        print( f'WARNING: {filename} already exists' )
        print( f'         and will get overridden' )
        input( 'Press Enter to continue' )
    json.dump( data, open( filename, 'w' ), indent=4, sort_keys=False )


def main():
    parser = argparse.ArgumentParser( description='Export TimeTracker data.' )
    parser.add_argument( '--api', metavar='URL', type=str, help='default: %(default)s',
                         default='https://time.nevees.org/api' )
    parser.add_argument( '-e', metavar='EMAIL', type=str, help='email or username must be given' )
    parser.add_argument( '-u', metavar='USERNAME', type=str, help='email or username must be given' )
    parser.add_argument( '-p', metavar='PASSWORD', type=str, help='if not given you get prompted' )
    parser.add_argument( '-y', action='store_true', help='skip warning notice' )
    parser.add_argument( 'output', metavar='OUTPUT', type=str, help='target json file' )
    args = parser.parse_args()

    if args.e is None and args.u is None:
        print_err( 'You must give -e or -u.' )
        sys.exit( 1 )

    if args.e is not None and args.u is not None:
        print_err( '-e and -u are mutually exclusive.' )
        sys.exit( 1 )

    access_token, refresh_token, user_id = login( args.api, args.e, args.u, args.p )
    try:
        export_data( args.api, access_token, args.output, args.y, user_id )
    finally:
        logout( args.api, access_token, refresh_token )

    print( 'Export successful.' )


if __name__ == "__main__":
    try:
        sys.exit( main() )
    except KeyboardInterrupt:
        sys.exit( 1 )
