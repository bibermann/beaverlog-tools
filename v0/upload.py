#!/usr/bin/env python3

import argparse
import json
import sys

import progress.bar
import requests

from common.auth import build_auth_header
from common.auth import login
from common.auth import logout
from common.utils import pretty_json
from common.utils import print_err
from common.utils import verify_response
from v0.detail.parser import add_default_arguments
from v0.detail.parser import verify_default_arguments


def simple_changeset_to_list( data ):
    return [x['data'] for x in data['changeset']]


def clear_data( url, token, skip_warning ):
    if not skip_warning:
        print( f'WARNING: This will permanently delete all your data' )
        print( f'         on {url}' )
        input( 'Press Enter to continue' )
    print( 'Removing data...' )
    r = requests.delete( f'{url}/batch/all-private', headers=build_auth_header( token ) )
    verify_response( r )


def load_data( filename ):
    with open( filename ) as jsonfile:
        return json.load( jsonfile )


def import_subject( url, token, subject, new_id_map ):
    data = {
        'name': subject['name'],
        'organization_id': 0,
        'is_project': subject['is_project'],
        'parent_ids': [new_id_map[parent_id] for parent_id in subject['parent_ids']],
    }
    r = requests.post( f'{url}/subject/', json=data, headers=build_auth_header( token ) )
    verify_response( r, data )
    changes = simple_changeset_to_list( r.json() )
    assert len( changes ) == 1
    return changes[0]['id']


def check_subject_id_exists_on_server( url, token, subject_id ):
    r = requests.get( f'{url}/subject/{subject_id}', headers=build_auth_header( token ) )
    if not (200 <= r.status_code < 300):
        return False
    return True


def verify_subject_ids_exist_on_server( url, token, subjects ):
    missing_subjects = []
    for subject in subjects:
        if not check_subject_id_exists_on_server( url, token, subject['id'] ):
            missing_subjects.append( subject )
    if len( missing_subjects ) > 0:
        missing_subject_ids_text = ', '.join( [str( subject['id'] ) for subject in missing_subjects] )
        missing_subject_ids_arg_text = '--parent-id-map=\'{"' + '": null, "'.join(
            [str( subject['id'] ) for subject in missing_subjects] ) + '": null}\''
        print_err( f'FATAL: The following organization subjects are missing on the server:' )
        print_err( f'{pretty_json( missing_subjects )}' )
        print_err( f'ATTENTION: Please provide a mapping for the following ids: {missing_subject_ids_text}' )
        print_err( f'NOTE: You can skip these parents with: {missing_subject_ids_arg_text}' )
        sys.exit( 1 )


def import_subjects( url, token, subjects, subject_name_whitelist, subject_name_blacklist ):
    private_subjects = [subject for subject in subjects if subject['organization_id'] == 0]
    organization_subjects_map = {subject['id']: subject for subject in subjects if subject['organization_id'] != 0}
    used_organization_subject_ids = set()
    for subject in private_subjects:
        for parent_id in subject['parent_ids']:
            if parent_id in organization_subjects_map:
                used_organization_subject_ids.add( parent_id )
    used_organization_subjects = [organization_subjects_map[subject_id] for subject_id in used_organization_subject_ids]
    verify_subject_ids_exist_on_server( url, token, used_organization_subjects )
    organization_subject_ids = set( [item['id'] for item in used_organization_subjects] )
    new_id_map = {item['id']: item['id'] for item in used_organization_subjects}
    processed_ids = set()
    pending = {item['id']: item
               for item
               in private_subjects
               if (
                       (not subject_name_whitelist or item['name'] in subject_name_whitelist) and
                       (not item['name'] in subject_name_blacklist)
               )
               }
    bar = progress.bar.Bar( f'Uploading...', max=len( private_subjects ) )
    while len( pending ) > 0:
        delete = []
        for key, subject in pending.items():
            private_parent_ids = list(
                filter( lambda id_: id_ not in organization_subject_ids, subject['parent_ids'] ) )
            if len( private_parent_ids ) == 0 or all( parent_id in processed_ids for parent_id in private_parent_ids ):
                processed_ids.add( subject['id'] )
                new_id_map[subject['id']] = import_subject( url, token, subject, new_id_map )
                bar.next()
                delete.append( key )
        for key in delete:
            del pending[key]
        if len( delete ) == 0:
            print_err( f'\nFATAL: The following subjects have dangling parents:\n{pretty_json( pending )}' )
            sys.exit( 1 )
    bar.finish()
    return new_id_map


def import_location( url, token, location ):
    data = {
        'name': location['name'],
        'coordinates': location['coordinates'],
    }
    r = requests.post( f'{url}/location/', json=data, headers=build_auth_header( token ) )
    verify_response( r, data )
    changes = simple_changeset_to_list( r.json() )
    assert len( changes ) == 1
    return changes[0]['id']


def import_locations( url, token, locations ):
    new_id_map = {}
    bar = progress.bar.Bar( f'Uploading...', max=len( locations ) )
    for location in locations:
        new_id_map[location['id']] = import_location( url, token, location )
        bar.next()
    bar.finish()
    return new_id_map


def import_activity( url, token, activity, new_subject_id_map, new_location_id_map ):
    data = {
        'subject_id': new_subject_id_map[activity['subject_id']],
        'location_id': new_location_id_map[activity['location_id']],
        'start': activity['start'],
        'end': activity['end'],
        'data': activity['data'],
    }
    r = requests.post( f'{url}/activity/', json=data, headers=build_auth_header( token ) )
    verify_response( r, data )


def import_activities( url, token, activities, new_subject_id_map, new_location_id_map ):
    bar = progress.bar.Bar( f'Uploading...', max=len( activities ) )
    for activity in activities:
        import_activity( url, token, activity, new_subject_id_map, new_location_id_map )
        bar.next()
    bar.finish()


def import_json( url, token, data, subject_name_whitelist, subject_name_blacklist ):
    print( 'Importing subject data...' )
    new_subject_id_map = import_subjects( url, token, data['subjects'], subject_name_whitelist, subject_name_blacklist )
    print( 'Importing location data...' )
    new_location_id_map = import_locations( url, token, data['locations'] )
    print( 'Importing activity data...' )
    import_activities( url, token,
                       [activity for activity in data['activities'] if activity['subject_id'] in new_subject_id_map],
                       new_subject_id_map, new_location_id_map )


def map_parent_ids( subjects, parent_id_map ):
    for subject in subjects:
        new_parent_ids = []
        for parent_id in subject['parent_ids']:
            mapped_id = parent_id_map.get( str( parent_id ), parent_id )
            if mapped_id is not None:
                new_parent_ids.append( mapped_id )
        subject['parent_ids'] = new_parent_ids


def main():
    parser = argparse.ArgumentParser( description='(Re)import time data.' )
    add_default_arguments( parser, with_y=True )
    parser.add_argument( '--parent-id-map', metavar='JSON', type=str, help='map for organization parent ids' )
    parser.add_argument( '--whitelist', metavar='JSON', type=str, help='array with subject names to allow' )
    parser.add_argument( '--blacklist', metavar='JSON', type=str, help='array with subject names to ignore' )
    parser.add_argument( 'input', metavar='INPUT', type=str, help='source json file' )

    args = parser.parse_args()
    verify_default_arguments( args )

    parent_id_map = {}
    if args.parent_id_map is not None:
        parent_id_map = json.loads( args.parent_id_map )

    subject_name_whitelist = set()
    if args.whitelist is not None:
        subject_name_whitelist = set( json.loads( args.whitelist ) )

    subject_name_blacklist = set()
    if args.blacklist is not None:
        subject_name_blacklist = set( json.loads( args.blacklist ) )

    if subject_name_whitelist & subject_name_blacklist:
        print_err( f'--whitelist and --blacklist must not have common items' )
        sys.exit( 1 )

    access_token, refresh_token, _ = login( args.api, args.e, args.u, args.p )
    try:
        clear_data( args.api, access_token, args.y )
        data = load_data( args.input )
        if len( parent_id_map ) > 0:
            map_parent_ids( data['data']['subjects'], parent_id_map )
        import_json( args.api, access_token, data['data'], subject_name_whitelist, subject_name_blacklist )
    finally:
        logout( args.api, access_token, refresh_token )

    print( 'Import successful.' )


if __name__ == "__main__":
    try:
        sys.exit( main() )
    except KeyboardInterrupt:
        sys.exit( 1 )
