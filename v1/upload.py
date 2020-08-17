#!/usr/bin/env python3

import argparse
import copy
import json
import sys

import progress.bar
import requests
import typing

from shared.common.auth import build_auth_header
from shared.common.utils import pretty_json
from shared.common.utils import print_err
from shared.common.utils import simple_changeset_to_list
from shared.common.utils import verify_response
from v1.common.auth import login
from v1.common.auth import logout
from v1.common.clear import clear_data
from v1.common.data import load_data
from v1.common.ids import EMPTY_ID
from v1.common.parser import add_default_arguments
from v1.common.parser import verify_default_arguments
from v1.common.remote import IdManager
from v1.common.remote import RemoteData


def import_subject( remote_data: RemoteData, subject ):
    data = {
        'id_token': remote_data.id_manager.id_token,
        **subject,
    }
    data.pop( 'created_on', None )
    data.pop( 'activity_start', None )
    data.pop( 'activity_end', None )
    data.pop( 'activity_count', None )
    data.pop( 'milliseconds', None )
    data.pop( 'ancestor_ids', None )
    r = requests.post( f'{remote_data.url}/subject/', json=data, headers=build_auth_header( remote_data.access_token ) )
    verify_response( r, data )
    changes = simple_changeset_to_list( r.json() )
    assert len( changes ) == 1


def check_subject_id_exists_on_server( remote_data: RemoteData, subject_id ):
    r = requests.get( f'{remote_data.url}/subject/{subject_id}', headers=build_auth_header( remote_data.access_token ) )
    if not (200 <= r.status_code < 300):
        return False
    return True


def subject_id_to_detailled_json( sid, subjects_map ):
    s = subjects_map.get( sid, None )
    if s is None:
        return {sid: 'user-provided'}
    return {sid: s}


def subject_id_to_name( sid, subjects_map, organizations_map ):
    s = subjects_map.get( sid, None )
    if s is None:
        return f"{sid} (user-provided)"
    o = organizations_map[s['organization_id']]
    return f"{sid} ({o['name']} :: {s['name']})"


def verify_subject_ids_exist_on_server( remote_data: RemoteData, subject_ids: typing.Set[str], subjects, organizations ):
    organizations_map = {o['id']: o for o in organizations}
    subjects_map = {s['id']: s for s in subjects}
    missing_sids = []
    for sid in subject_ids:
        if not check_subject_id_exists_on_server( remote_data, sid ):
            missing_sids.append( sid )
    if len( missing_sids ) > 0:
        missing_subject_ids_text = '- ' + '\n- '.join(
            [subject_id_to_name( sid, subjects_map, organizations_map ) for sid in missing_sids] )
        missing_subject_ids_arg_text = '--parent-id-map=\'{"' + '": null, "'.join(
            missing_sids ) + '": null}\''
        print_err( f'FATAL: The following organization subjects are missing on the server:' )
        print_err(
            f'{pretty_json( list( map( lambda sid: subject_id_to_detailled_json( sid, subjects_map ), missing_sids ) ) )}' )
        print_err( f'ATTENTION: Please provide a mapping for the following ids:\n{missing_subject_ids_text}' )
        print_err( f'NOTE: You can skip these parents with: {missing_subject_ids_arg_text}' )
        sys.exit( 1 )


def import_subjects( remote_data: RemoteData,
                     subjects, organizations, parent_id_map,
                     subject_name_whitelist, subject_name_blacklist ):
    organization_subject_ids = set( s['id'] for s in subjects if s['organization_id'] != EMPTY_ID )
    remote_organization_subject_ids = copy.copy( organization_subject_ids )

    new_subjects = []
    referenced_organization_subject_ids = set()
    for entity in subjects:
        if not (
                (not subject_name_whitelist or entity['name'] in subject_name_whitelist) and
                (not entity['name'] in subject_name_blacklist)
        ):
            continue
        if entity['id'] in parent_id_map:
            continue
        if entity['organization_id'] != EMPTY_ID:
            continue

        entity['id'] = remote_data.id_manager.mapped_id( 'subject', entity['id'] )

        new_parent_ids = []
        for parent_id in entity['parent_ids']:
            if parent_id in parent_id_map:
                mapped_id = parent_id_map[parent_id]
                if mapped_id is not None:
                    new_parent_ids.append( mapped_id )
                    if not remote_data.id_manager.has_id( 'subject', parent_id ):
                        remote_data.id_manager.map_id( 'subject', parent_id, mapped_id )
                    referenced_organization_subject_ids.add( mapped_id )
                    remote_organization_subject_ids.add( mapped_id )
            else:
                if parent_id not in organization_subject_ids:
                    new_parent_ids.append( remote_data.id_manager.mapped_id( 'subject', parent_id ) )
                else:
                    referenced_organization_subject_ids.add( parent_id )
        entity['parent_ids'] = new_parent_ids

        new_subjects.append( entity )

    verify_subject_ids_exist_on_server( remote_data, referenced_organization_subject_ids, subjects, organizations )
    processed_ids = set()
    pending = {item['id']: item for item in new_subjects}
    bar = progress.bar.Bar( f'Uploading...', max=len( new_subjects ) )
    while len( pending ) > 0:
        done = []
        for key, entity in pending.items():
            private_parent_ids = list(
                filter( lambda id_: id_ not in remote_organization_subject_ids, entity['parent_ids'] ) )
            if len( private_parent_ids ) == 0 or all( parent_id in processed_ids for parent_id in private_parent_ids ):
                processed_ids.add( entity['id'] )
                import_subject( remote_data, entity )
                bar.next()
                done.append( key )
        for key in done:
            del pending[key]
        if len( done ) == 0:
            print_err( f'\nFATAL: The following subjects have dangling parents:\n{pretty_json( pending )}' )
            sys.exit( 1 )
    bar.finish()


def import_location( remote_data: RemoteData, location ):
    data = {
        'id_token': remote_data.id_manager.id_token,
        **location,
        'id': remote_data.id_manager.mapped_id( 'location', location['id'] ),
    }
    data.pop( 'created_on', None )
    data.pop( 'activity_start', None )
    data.pop( 'activity_end', None )
    data.pop( 'activity_count', None )
    data.pop( 'milliseconds', None )
    r = requests.post( f'{remote_data.url}/location/', json=data,
                       headers=build_auth_header( remote_data.access_token ) )
    verify_response( r, data )
    changes = simple_changeset_to_list( r.json() )
    assert len( changes ) == 1


def import_locations( remote_data: RemoteData, locations ):
    bar = progress.bar.Bar( f'Uploading...', max=len( locations ) )
    for location in locations:
        import_location( remote_data, location )
        bar.next()
    bar.finish()


def import_tracker_link( remote_data: RemoteData, tracker_link ):
    data = {
        'id_token': remote_data.id_manager.id_token,
        **tracker_link,
        'id': remote_data.id_manager.mapped_id( 'tracker_link', tracker_link['id'] ),
    }
    data.pop( 'created_on', None )
    r = requests.post( f'{remote_data.url}/tracker-link/', json=data,
                       headers=build_auth_header( remote_data.access_token ) )
    verify_response( r, data )
    changes = simple_changeset_to_list( r.json() )
    assert len( changes ) == 1


def import_tracker_links( remote_data: RemoteData, tracker_links ):
    bar = progress.bar.Bar( f'Uploading...', max=len( tracker_links ) )
    for tracker_link in tracker_links:
        import_tracker_link( remote_data, tracker_link )
        bar.next()
    bar.finish()


def import_tracker_project( remote_data: RemoteData, tracker_project ):
    data = {
        'id_token': remote_data.id_manager.id_token,
        **tracker_project,
        'id': remote_data.id_manager.mapped_id( 'tracker_project', tracker_project['id'] ),
        'link_id': remote_data.id_manager.mapped_id( 'tracker_link', tracker_project['link_id'], True ),
        'subject_id':
            remote_data.id_manager.mapped_id( 'subject', tracker_project['subject_id'], True )
            if 'subject_id' in tracker_project and tracker_project['subject_id'] != EMPTY_ID else EMPTY_ID,
    }
    data.pop( 'created_on', None )
    r = requests.post( f'{remote_data.url}/tracker-project/', json=data,
                       headers=build_auth_header( remote_data.access_token ) )
    verify_response( r, data )
    changes = simple_changeset_to_list( r.json() )
    assert len( changes ) == 1


def import_tracker_projects( remote_data: RemoteData, tracker_projects ):
    bar = progress.bar.Bar( f'Uploading...', max=len( tracker_projects ) )
    for tracker_project in tracker_projects:
        import_tracker_project( remote_data, tracker_project )
        bar.next()
    bar.finish()


def import_tracker_issue( remote_data: RemoteData, tracker_issue ):
    data = {
        'id_token': remote_data.id_manager.id_token,
        **tracker_issue,
        'id': remote_data.id_manager.mapped_id( 'tracker_issue', tracker_issue['id'] ),
        'project_id': remote_data.id_manager.mapped_id( 'tracker_project', tracker_issue['project_id'], True ),
    }
    data.pop( 'created_on', None )
    r = requests.post( f'{remote_data.url}/tracker-issue/', json=data,
                       headers=build_auth_header( remote_data.access_token ) )
    verify_response( r, data )
    changes = simple_changeset_to_list( r.json() )
    assert len( changes ) == 1


def import_tracker_issues( remote_data: RemoteData, tracker_issues ):
    bar = progress.bar.Bar( f'Uploading...', max=len( tracker_issues ) )
    for tracker_issue in tracker_issues:
        import_tracker_issue( remote_data, tracker_issue )
        bar.next()
    bar.finish()


def import_activity( remote_data: RemoteData, activity ):
    data = {
        'id_token': remote_data.id_manager.id_token,
        **activity,
        'id': remote_data.id_manager.mapped_id( 'activity', activity['id'] ),
        'subject_ids': list(
            map( lambda sid: remote_data.id_manager.mapped_id( 'subject', sid, True ), activity['subject_ids'] ) ),
        'location_id': remote_data.id_manager.mapped_id( 'location', activity['location_id'], True ),
        'issue_id':
            remote_data.id_manager.mapped_id( 'tracker_issue', activity['issue_id'], True )
            if 'issue_id' in activity and activity['issue_id'] != EMPTY_ID else EMPTY_ID,
    }
    data.pop( 'created_on', None )
    r = requests.post( f'{remote_data.url}/activity/', json=data,
                       headers=build_auth_header( remote_data.access_token ) )
    verify_response( r, data )


def import_activities( remote_data: RemoteData, activities ):
    bar = progress.bar.Bar( f'Uploading...', max=len( activities ) )
    for activity in activities:
        import_activity( remote_data, activity )
        bar.next()
    bar.finish()


def import_json( remote_data: RemoteData, data, parent_id_map, subject_name_whitelist, subject_name_blacklist ):
    if 'subjects' in data:
        print( 'Importing subject data...' )
        import_subjects( remote_data,
                         data['subjects'],
                         data['organizations'] if 'organizations' in data else [],
                         parent_id_map,
                         subject_name_whitelist,
                         subject_name_blacklist )

    if 'locations' in data:
        print( 'Importing location data...' )
        import_locations( remote_data, data['locations'] )

    if 'tracker_links' in data:
        print( 'Importing tracker link data...' )
        import_tracker_links( remote_data, data['tracker_links'] )

    if 'tracker_projects' in data:
        print( 'Importing tracker project data...' )
        import_tracker_projects( remote_data, data['tracker_projects'] )

    if 'tracker_issues' in data:
        print( 'Importing tracker issue data...' )
        import_tracker_issues( remote_data, data['tracker_issues'] )

    if 'activities' in data:
        print( 'Importing activity data...' )
        for activity in data['activities']:
            for sid in activity['subject_ids']:
                if not remote_data.id_manager.has_id( 'subject', sid ):
                    print(f'sid missing: {sid}')
                    assert False
        import_activities( remote_data, data['activities'] )


def map_parent_ids( subjects, parent_id_map ):
    for subject in subjects:
        new_parent_ids = []
        for parent_id in subject['parent_ids']:
            mapped_id = parent_id_map.get( parent_id, parent_id )
            if mapped_id is not None:
                new_parent_ids.append( mapped_id )
        subject['parent_ids'] = new_parent_ids


def main():
    parser = argparse.ArgumentParser( description='(Re)import Beaverlog data.' )
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

    remote_data = login( args.api, args.e, args.u, args.p )
    try:
        remote_data.id_manager = IdManager( remote_data.url, remote_data.access_token )
        clear_data( remote_data, args.y )
        data = load_data( args.input )
        import_json( remote_data, data['data'], parent_id_map, subject_name_whitelist,
                     subject_name_blacklist )
    finally:
        logout( remote_data )

    print( 'Import successful.' )


if __name__ == "__main__":
    try:
        sys.exit( main() )
    except KeyboardInterrupt:
        sys.exit( 1 )
