#!/usr/bin/env python3

import argparse
import copy
import json
import sys

import progress.bar
import requests

from all.common.auth import build_auth_header
from all.common.utils import pretty_json
from all.common.utils import print_err
from all.common.utils import simple_changeset_to_list
from all.common.utils import verify_response
from v1.common.auth import login
from v1.common.auth import logout
from v1.common.clear import clear_data
from v1.common.data import load_data
from v1.common.ids import EMPTY_ID
from v1.common.ids import get_id_data
from v1.common.parser import add_default_arguments
from v1.common.parser import verify_default_arguments


def import_subject( url, token, subject, new_id_map ):
    data = {
        **subject,
        'parent_ids': [new_id_map[parent_id] for parent_id in subject['parent_ids']],
    }
    data.pop( 'id', None )
    data.pop( 'created_on', None )
    data.pop( 'activity_start', None )
    data.pop( 'activity_end', None )
    data.pop( 'activity_count', None )
    data.pop( 'milliseconds', None )
    data.pop( 'ancestor_ids', None )
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
    private_subjects = [subject for subject in subjects if subject['organization_id'] == EMPTY_ID]
    organization_subjects_map = {subject['id']: subject for subject in subjects if
                                 subject['organization_id'] != EMPTY_ID}
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
        **location,
    }
    data.pop( 'id', None )
    data.pop( 'created_on', None )
    data.pop( 'activity_start', None )
    data.pop( 'activity_end', None )
    data.pop( 'activity_count', None )
    data.pop( 'milliseconds', None )
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


def import_tracker_link( url, token, tracker_link ):
    data = {
        **tracker_link,
    }
    data.pop( 'id', None )
    data.pop( 'created_on', None )
    r = requests.post( f'{url}/tracker-link/', json=data, headers=build_auth_header( token ) )
    verify_response( r, data )
    changes = simple_changeset_to_list( r.json() )
    assert len( changes ) == 1
    return changes[0]['id']


def import_tracker_links( url, token, tracker_links ):
    new_id_map = {}
    bar = progress.bar.Bar( f'Uploading...', max=len( tracker_links ) )
    for tracker_link in tracker_links:
        new_id_map[tracker_link['id']] = import_tracker_link( url, token, tracker_link )
        bar.next()
    bar.finish()
    return new_id_map


def import_tracker_project( url, token, tracker_project, new_tracker_link_id_map, new_subject_id_map ):
    data = {
        **tracker_project,
        'link_id': new_tracker_link_id_map[tracker_project['link_id']],
        'subject_id':
            new_subject_id_map[tracker_project['subject_id']]
            if 'subject_id' in tracker_project and tracker_project['subject_id'] != EMPTY_ID else EMPTY_ID,
    }
    data.pop( 'id', None )
    data.pop( 'created_on', None )
    r = requests.post( f'{url}/tracker-project/', json=data, headers=build_auth_header( token ) )
    verify_response( r, data )
    changes = simple_changeset_to_list( r.json() )
    assert len( changes ) == 1
    return changes[0]['id']


def import_tracker_projects( url, token, tracker_projects, new_tracker_link_id_map, new_subject_id_map ):
    new_id_map = {}
    bar = progress.bar.Bar( f'Uploading...', max=len( tracker_projects ) )
    for tracker_project in tracker_projects:
        new_id_map[tracker_project['id']] = import_tracker_project( url, token, tracker_project,
                                                                    new_tracker_link_id_map, new_subject_id_map )
        bar.next()
    bar.finish()
    return new_id_map


def import_tracker_issue( url, token, tracker_issue, new_tracker_project_id_map ):
    data = {
        **tracker_issue,
        'project_id': new_tracker_project_id_map[tracker_issue['project_id']],
    }
    data.pop( 'id', None )
    data.pop( 'created_on', None )
    r = requests.post( f'{url}/tracker-issue/', json=data, headers=build_auth_header( token ) )
    verify_response( r, data )
    changes = simple_changeset_to_list( r.json() )
    assert len( changes ) == 1
    return changes[0]['id']


def import_tracker_issues( url, token, tracker_issues, new_tracker_project_id_map ):
    new_id_map = {}
    bar = progress.bar.Bar( f'Uploading...', max=len( tracker_issues ) )
    for tracker_issue in tracker_issues:
        new_id_map[tracker_issue['id']] = import_tracker_issue( url, token, tracker_issue, new_tracker_project_id_map )
        bar.next()
    bar.finish()
    return new_id_map


def import_activity( url, token, activity, new_subject_id_map, new_location_id_map, new_tracker_issue_id_map ):
    data = {
        **activity,
        'subject_ids': list( map( lambda sid: new_subject_id_map[sid], activity['subject_ids'] ) ),
        'location_id': new_location_id_map[activity['location_id']],
        'issue_id':
            new_tracker_issue_id_map[activity['issue_id']]
            if 'issue_id' in activity and activity['issue_id'] != EMPTY_ID else EMPTY_ID,
    }
    data.pop( 'id', None )
    data.pop( 'created_on', None )
    r = requests.post( f'{url}/activity/', json=data, headers=build_auth_header( token ) )
    verify_response( r, data )


def import_activities( url, token, activities, new_subject_id_map, new_location_id_map, new_tracker_issue_id_map ):
    bar = progress.bar.Bar( f'Uploading...', max=len( activities ) )
    for activity in activities:
        import_activity( url, token, activity, new_subject_id_map, new_location_id_map, new_tracker_issue_id_map )
        bar.next()
    bar.finish()


def import_json( url, token, data, subject_name_whitelist, subject_name_blacklist ):
    print( 'Importing subject data...' )
    new_subject_id_map = import_subjects( url, token, data['subjects'], subject_name_whitelist, subject_name_blacklist )

    print( 'Importing location data...' )
    new_location_id_map = import_locations( url, token, data['locations'] )

    print( 'Importing tracker link data...' )
    new_tracker_link_id_map = import_tracker_links( url, token, data['tracker_links'] )

    print( 'Importing tracker project data...' )
    new_tracker_project_id_map = import_tracker_projects( url, token, data['tracker_projects'],
                                                          new_tracker_link_id_map, new_subject_id_map )

    print( 'Importing tracker issue data...' )
    new_tracker_issue_id_map = import_tracker_issues( url, token, data['tracker_issues'], new_tracker_project_id_map )

    print( 'Importing activity data...' )
    activities = copy.deepcopy( data['activities'] )
    for activity in activities:
        activity['subject_ids'] = list( filter( lambda sid: sid in new_subject_id_map, activity['subject_ids'] ) )
        if any( sid for sid in activity['subject_ids'] if
                not 'kind' in new_subject_id_map[sid] or new_subject_id_map[sid]['kind'] != 'label' ):
            activity['subject_ids'] = []
    import_activities( url, token,
                       [activity for activity in data['activities'] if len( activity['subject_ids'] ) > 0],
                       new_subject_id_map, new_location_id_map, new_tracker_issue_id_map )


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
        id_offset, id_token = get_id_data( args.api, access_token )
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
