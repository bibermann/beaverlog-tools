#!/usr/bin/env python3

import argparse
import sys

import requests

from common.auth import build_auth_header
from v0.common.auth import login
from v0.common.auth import logout
from common.utils import simple_changeset_to_list
from common.utils import verify_response
from v0.common.parser import add_default_arguments
from v0.common.parser import verify_default_arguments


def fetch_profile( url, token, user_id ):
    r = requests.get( f'{url}/user/{user_id}', headers=build_auth_header( token ) )
    verify_response( r )
    return simple_changeset_to_list( r.json() )[0]


def fetch_subject( url, token, subject_id ):
    r = requests.get( f'{url}/subject/{subject_id}', headers=build_auth_header( token ) )
    verify_response( r )
    return simple_changeset_to_list( r.json() )[0]


def update_subject( url, token, subject_id, data ):
    r = requests.put( f'{url}/subject/{subject_id}', json=data, headers=build_auth_header( token ) )
    verify_response( r )


def choose_subject():
    while True:
        id_string = input( "Choose subject ID to edit: " )
        try:
            id_ = int( id_string )
        except ValueError:
            continue
        return id_


def choose_project( archived_projects_map ):
    while True:
        id_string = input( "Choose project to de-archive: " )
        try:
            id_ = int( id_string )
        except ValueError:
            continue
        if id_ is None or id_ not in archived_projects_map.keys():
            continue
        return id_


def main():
    parser = argparse.ArgumentParser( description='Export TimeTracker data.' )
    add_default_arguments( parser, with_y=True )

    args = parser.parse_args()
    verify_default_arguments( args )

    access_token, refresh_token, user_id = login( args.api, args.e, args.u, args.p )
    try:
        subject_id = choose_subject()
        subject = fetch_subject( args.api, access_token, subject_id )
        print( f"Selected subject: {subject['name']}" )

        profile = fetch_profile( args.api, access_token, user_id )
        links_map = {id_: link for id_, link in map( lambda link: (link['id'], link), profile['gitlab_links'] )}

        archived_projects = list( filter( lambda project: project['is_archived'] == True, subject['gitlab_projects'] ) )
        archived_projects_map = {id_: project for id_, project in
                                 map( lambda project: (project['id'], project), archived_projects )}
        ids = sorted( archived_projects_map.keys() )
        print()
        if len( ids ) == 0:
            print( 'The subject does not have any archived projects.' )
            exit( 0 )
        print( 'Archived projects:' )
        for id_ in ids:
            print(
                f"{id_}: {links_map[archived_projects_map[id_]['link_id']]['name']} (GitLab-FID: {archived_projects_map[id_]['project_fid']})" )
        print()
        id_ = choose_project( archived_projects_map )

        archived_projects_map[id_]['is_archived'] = False
        new_projects = list( filter( lambda project: project['is_archived'] == False, subject['gitlab_projects'] ) )
        new_projects.append( archived_projects_map[id_] )
        update_subject( args.api, access_token, subject_id, {'gitlab_projects': new_projects} )
    finally:
        logout( args.api, access_token, refresh_token )

    print( 'De-archiving successful.' )


if __name__ == "__main__":
    try:
        sys.exit( main() )
    except KeyboardInterrupt:
        sys.exit( 1 )
