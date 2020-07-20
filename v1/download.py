#!/usr/bin/env python3

import argparse
import datetime
import json
import os
import sys

import progress.bar
import requests

from shared.common.auth import build_auth_header
from shared.common.utils import date_to_string
from shared.common.utils import simple_changeset_to_list
from shared.common.utils import verify_response
from v1.common.auth import login
from v1.common.auth import logout
from v1.common.parser import add_default_arguments
from v1.common.parser import verify_default_arguments


def fetch_users( remote_data ):
    r = requests.get( f'{remote_data.url}/user/', headers=build_auth_header( remote_data.access_token ) )
    verify_response( r )
    return simple_changeset_to_list( r.json() )


def fetch_subjects( remote_data ):
    r = requests.get( f'{remote_data.url}/subject/', headers=build_auth_header( remote_data.access_token ) )
    verify_response( r )
    return simple_changeset_to_list( r.json() )


def fetch_locations( remote_data ):
    r = requests.get( f'{remote_data.url}/location/', headers=build_auth_header( remote_data.access_token ) )
    verify_response( r )
    return simple_changeset_to_list( r.json() )


def fetch_activities( remote_data ):
    r = requests.get( f'{remote_data.url}/activity/', headers=build_auth_header( remote_data.access_token ) )
    verify_response( r )
    return simple_changeset_to_list( r.json() )


def fetch_organizations( remote_data ):
    r = requests.get( f'{remote_data.url}/organization/', headers=build_auth_header( remote_data.access_token ) )
    verify_response( r )
    return simple_changeset_to_list( r.json() )


def fetch_tracker_links( remote_data ):
    r = requests.get( f'{remote_data.url}/tracker-link/', headers=build_auth_header( remote_data.access_token ) )
    verify_response( r )
    return simple_changeset_to_list( r.json() )


def fetch_tracker_projects( remote_data ):
    r = requests.get( f'{remote_data.url}/tracker-project/', headers=build_auth_header( remote_data.access_token ) )
    verify_response( r )
    return simple_changeset_to_list( r.json() )


def fetch_tracker_issues( remote_data ):
    r = requests.get( f'{remote_data.url}/tracker-issue/', headers=build_auth_header( remote_data.access_token ) )
    verify_response( r )
    return simple_changeset_to_list( r.json() )


def fetch_reports( remote_data ):
    r = requests.get( f'{remote_data.url}/report/', headers=build_auth_header( remote_data.access_token ) )
    verify_response( r )
    return simple_changeset_to_list( r.json() )


def fetch_data( remote_data ):
    bar = progress.bar.Bar( f'Downloading...', max=9 )
    users = fetch_users( remote_data )
    bar.next()
    subjects = fetch_subjects( remote_data )
    bar.next()
    locations = fetch_locations( remote_data )
    bar.next()
    activities = fetch_activities( remote_data )
    bar.next()
    organizations = fetch_organizations( remote_data )
    bar.next()
    tracker_links = fetch_tracker_links( remote_data )
    bar.next()
    tracker_projects = fetch_tracker_projects( remote_data )
    bar.next()
    tracker_issues = fetch_tracker_issues( remote_data )
    bar.next()
    reports = fetch_reports( remote_data )
    bar.next()
    bar.finish()
    return {
        'users': users,
        'subjects': subjects,
        'locations': locations,
        'activities': activities,
        'organizations': organizations,
        'tracker_links': tracker_links,
        'tracker_projects': tracker_projects,
        'tracker_issues': tracker_issues,
        'reports': reports,
    }


def export_data( remote_data, filename, skip_warning ):
    data = {
        'exported_on': date_to_string( datetime.datetime.utcnow() ),
        'api_version': 1,
        'user_id': remote_data.user_id,
        'data': fetch_data( remote_data ),
    }

    if os.path.exists( filename ) and not skip_warning:
        print( f'WARNING: {filename} already exists' )
        print( f'         and will get overridden' )
        input( 'Press Enter to continue' )
    json.dump( data, open( filename, 'w' ), indent=4, sort_keys=False )


def main():
    parser = argparse.ArgumentParser( description='Export Beaverlog data.' )
    add_default_arguments( parser, with_y=True )
    parser.add_argument( 'output', metavar='OUTPUT', type=str, help='target json file' )

    args = parser.parse_args()
    verify_default_arguments( args )

    remote_data = login( args.api, args.e, args.u, args.p )
    try:
        export_data( remote_data, args.output, args.y )
    finally:
        logout( remote_data )

    print( 'Export successful.' )


if __name__ == "__main__":
    try:
        sys.exit( main() )
    except KeyboardInterrupt:
        sys.exit( 1 )
