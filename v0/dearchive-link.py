#!/usr/bin/env python3

import argparse
import sys

import requests

from shared.common.auth import request_kwargs
from v0.common.auth import login
from v0.common.auth import logout
from shared.common.utils import simple_changeset_to_list
from shared.common.utils import verify_response
from v0.common.parser import add_default_arguments
from v0.common.parser import verify_default_arguments


def fetch_profile( url, token, user_id ):
    r = requests.get( f'{url}/user/{user_id}', **request_kwargs( token ) )
    verify_response( r )
    return simple_changeset_to_list( r.json() )[0]


def update_profile( url, token, user_id, data ):
    r = requests.put( f'{url}/user/{user_id}', json=data, **request_kwargs( token ) )
    verify_response( r )


def choose_link( archived_links_map ):
    while True:
        id_string = input( "Choose link ID to de-archive: " )
        try:
            id_ = int( id_string )
        except ValueError:
            continue
        if id_ is None or id_ not in archived_links_map.keys():
            continue
        return id_


def main():
    parser = argparse.ArgumentParser( description='De-archive a GitLab link reference.' )
    add_default_arguments( parser, with_y=True )

    args = parser.parse_args()
    verify_default_arguments( args )

    access_token, refresh_token, user_id = login( args.api, args.e, args.u, args.p )
    try:
        profile = fetch_profile( args.api, access_token, user_id )
        archived_links = list( filter( lambda link: link['is_archived'] == True, profile['gitlab_links'] ) )
        archived_links_map = {id_: link for id_, link in map( lambda link: (link['id'], link), archived_links )}
        ids = sorted( archived_links_map.keys() )
        print()
        if len( ids ) == 0:
            print( 'You do not have any archived links.' )
            exit( 0 )
        print( 'Archived links:' )
        for id_ in ids:
            print( f"{id_}: {archived_links_map[id_]['name']}" )
        print()
        id_ = choose_link( archived_links_map )

        archived_links_map[id_]['is_archived'] = False
        new_links = list( filter( lambda link: link['is_archived'] == False, profile['gitlab_links'] ) )
        new_links.append( archived_links_map[id_] )
        update_profile( args.api, access_token, user_id, {'gitlab_links': new_links} )
    finally:
        logout( args.api, access_token, refresh_token )

    print( 'De-archiving successful.' )


if __name__ == "__main__":
    try:
        sys.exit( main() )
    except KeyboardInterrupt:
        sys.exit( 1 )
