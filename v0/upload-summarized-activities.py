#!/usr/bin/env python3

import json
import argparse
import sys
import datetime
import enum

import requests
import progress.bar

from common.utils import verify_response
from common.utils import print_err
from common.utils import string_to_date
from common.utils import date_to_string
from common.auth import login
from common.auth import logout
from common.auth import build_auth_header


class Alignment( enum.Enum ):
    daily = 'daily'
    weekly = 'weekly'
    monthly = 'monthly'

    def __str__( self ):
        return self.value


def simple_changeset_to_list( data ):
    return [x['data'] for x in data['changeset']]


def fetch_activities( url, token ):
    r = requests.get( f'{url}/activity/', headers=build_auth_header( token ) )
    verify_response( r )
    return simple_changeset_to_list( r.json() )


def fetch_activity_data( url, token ):
    activities = fetch_activities( url, token )
    return activities


def filter_activity_data_by_subject( data, subject_id ):
    return list( filter( lambda activity: activity['subject_id'] == subject_id, data ) )


def delete_activity_data( url, token, activity_id ):
    r = requests.delete( f'{url}/activity/{activity_id}', headers=build_auth_header( token ) )
    verify_response( r )


def delete_subject_activities( url, token, target_subject, skip_warning ):
    print( 'Downloading complete activity data...' )
    activities = filter_activity_data_by_subject( fetch_activity_data( url, token ), target_subject )
    if len( activities ) > 0:
        if not skip_warning:
            print( f'WARNING: This will permanently delete all activity data' )
            print( f'         of subject {target_subject} on {url}' )
            input( 'Press Enter to continue' )
        bar = progress.bar.Bar( f'Removing activity data...', max=len( activities ) )
        for activity in activities:
            delete_activity_data( url, token, activity['id'] )
            bar.next()
        bar.finish()


def load_data( filename ):
    with open( filename ) as jsonfile:
        return json.load( jsonfile )


def get_subject_descendants( data, subject_id ):
    # NOTE: We could use `ancestor_ids` as follows, but to allow simpler data structures
    #       (i.e. when input was manually built instead of exported), we use a slightly more complex algorithm.
    # Code which uses `ancestor_ids`:
    #     return set( [subject['id'] for subject in data['subjects'] if subject_id in subject['ancestor_ids']] )

    descendants = set()
    for subject in data['subjects']:
        if subject_id in subject['parent_ids']:
            descendants.add( subject['id'] )
            descendants.update( get_subject_descendants( data, subject['id'] ) )
    return descendants


def align_date( date: datetime.datetime, alignment: Alignment ):
    def add_some_hours( date_: datetime.date ) -> datetime.datetime:
        return datetime.datetime.combine( date_, datetime.datetime.min.time() ) + datetime.timedelta( hours=6 )

    if alignment == Alignment.daily:
        return add_some_hours( date.date() )
    elif alignment == Alignment.weekly:
        return add_some_hours( date.date() + datetime.timedelta( days=-date.date().weekday() ) )
    elif alignment == Alignment.monthly:
        return add_some_hours( datetime.date( date.year, date.month, 1 ) )
    else:
        return date


def calc_daily_summarized_times( data, subject_ids, alignment: Alignment ):
    aligned_start_to_milliseconds = {}
    for activity in data['activities']:
        if activity['subject_id'] in subject_ids:
            if activity['end'] == '':
                activity_id = activity['id']
                print( f'WARNING: Skipping activity {activity_id} because it is still running' )
                continue
            start = string_to_date( activity['start'] )
            end = string_to_date( activity['end'] )
            milliseconds = (end - start).total_seconds() * 1000
            aligned_start = align_date( start, alignment )
            if not aligned_start in aligned_start_to_milliseconds:
                aligned_start_to_milliseconds[aligned_start] = milliseconds
            else:
                aligned_start_to_milliseconds[aligned_start] += milliseconds
    return [{
        'start': date_to_string( day ),
        'end': date_to_string( day + datetime.timedelta( milliseconds=milliseconds ) ),
    } for day, milliseconds in aligned_start_to_milliseconds.items()]


def import_activity( url, token, data ):
    r = requests.post( f'{url}/activity/', json=data, headers=build_auth_header( token ) )
    verify_response( r, data )


def import_activities( url, token, activities ):
    bar = progress.bar.Bar( f'Uploading activity data...', max=len( activities ) )
    for activity in activities:
        import_activity( url, token, activity )
        bar.next()
    bar.finish()


def main():
    parser = argparse.ArgumentParser( description='(Re)import summarized activities.' )
    parser.add_argument( '--api', metavar='URL', type=str, help='default: %(default)s',
                         default='https://time.nevees.org/api' )
    parser.add_argument( '-e', metavar='EMAIL', type=str, help='email or username must be given' )
    parser.add_argument( '-u', metavar='USERNAME', type=str, help='email or username must be given' )
    parser.add_argument( '-p', metavar='PASSWORD', type=str, help='if not given you get prompted' )
    parser.add_argument( '-s', type=Alignment, choices=list( Alignment ), help='How to summarize, default: %(default)s',
                         default=Alignment.daily )
    parser.add_argument( '-y', action='store_true', help='skip warning notice' )
    parser.add_argument( 'input', metavar='INPUT', type=str, help='source json file' )
    parser.add_argument( 'source_subject', metavar='SOURCE_SUBJECT', type=int, help='source subject id' )
    parser.add_argument( 'target_subject', metavar='TARGET_SUBJECT', type=int, help='target subject id' )
    parser.add_argument( 'target_location', metavar='TARGET_LOCATION', type=int, help='target location id' )
    args = parser.parse_args()

    if args.e is None and args.u is None:
        print_err( 'You must give -e or -u.' )
        sys.exit( 1 )

    if args.e is not None and args.u is not None:
        print_err( '-e and -u are mutually exclusive.' )
        sys.exit( 1 )

    access_token, refresh_token, user_id = login( args.api, args.e, args.u, args.p )
    try:
        delete_subject_activities( args.api, access_token, args.target_subject, args.y )
        data = load_data( args.input )
        subject_ids = get_subject_descendants( data['data'], args.source_subject )
        subject_ids.add( args.source_subject )
        times = calc_daily_summarized_times( data['data'], subject_ids, args.s )
        import_activities( args.api, access_token, [{
            **time,
            'subject_id': args.target_subject,
            'location_id': args.target_location
        } for time in times] )
    finally:
        logout( args.api, access_token, refresh_token )

    print( 'Import successful.' )


if __name__ == "__main__":
    try:
        sys.exit( main() )
    except KeyboardInterrupt:
        sys.exit( 1 )
