#!/usr/bin/env python3

import argparse
import collections
import datetime
import json
import os
import sys

import progress.bar
import requests

from common.auth import build_auth_header
from common.auth import login
from common.auth import logout
from common.utils import date_to_string
from common.utils import verify_response
from v0.detail.parser import add_default_arguments
from v0.detail.parser import verify_default_arguments


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
    add_default_arguments( parser, with_y=True )
    parser.add_argument( 'output', metavar='OUTPUT', type=str, help='target json file' )

    args = parser.parse_args()
    verify_default_arguments( args )

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
