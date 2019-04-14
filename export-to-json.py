#!/usr/bin/env python3

import json
import csv
import hashlib
import getpass
import argparse
import sys
import os
import collections
import datetime

import requests
import progress.bar
import simplejson


def print_err( *args, **kwargs ):
    print( *args, file=sys.stderr, **kwargs )


def verify_response( r, data=None ):
    def pretty_json( ugly ):
        return json.dumps( ugly, indent=4, sort_keys=False )

    if not (200 <= r.status_code < 300):
        print_err( '$ ' + r.request.method + ' ' + r.request.url )
        if data is not None:
            print_err( '\n'.join( [f'> {line}' for line in pretty_json( data ).split( '\n' )] ) )
        try:
            js = r.json()
            if 'message' in js:
                print_err( str( r.status_code ) + ' ' + js['message'] )
            else:
                print_err( str( r.status_code ) + ':\n' + pretty_json( js ) )
        except simplejson.errors.JSONDecodeError:
            print_err( str( r.status_code ) + ':\n' + r.text )
        sys.exit( 1 )


def build_auth_header( token ):
    return {'Authorization': f'Bearer {token}'}


def date_to_string( date ):
    return date.strftime( '%Y-%m-%dT%H:%M:%S.%f' )[:23] + 'Z'


def login( url, email, username, password ):
    if password is None:
        password = getpass.getpass()
    data = {
        **({'email': email} if email is not None else {'username': username}),
        'password': hashlib.sha512( password.encode( 'utf-8' ) ).hexdigest()
    }

    print( 'Authenticating...' )
    try:
        r = requests.post( f'{url}/auth/login', json=data )
    except requests.exceptions.ConnectionError:
        print_err( 'Server is down.' )
        sys.exit( 1 )
    verify_response( r, data )
    access_token = r.json()['data']['access_token']
    refresh_token = r.json()['data']['refresh_token']
    user_id = r.json()['data']['id']

    return access_token, refresh_token, user_id


def logout( url, access_token, refresh_token ):
    print( 'Signing out...' )
    r = requests.delete( f'{url}/auth/revoke-access', headers=build_auth_header( access_token ) )
    verify_response( r )
    r = requests.delete( f'{url}/auth/revoke-refresh', headers=build_auth_header( refresh_token ) )
    verify_response( r )


def simple_changeset_to_list( data ):
    return [x['data'] for x in data['changeset']]


def fetch_users( url, token ):
    r = requests.get( f'{url}/user/', headers=build_auth_header( token ) )
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
