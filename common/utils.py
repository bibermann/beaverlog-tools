import json
import sys
import datetime

import simplejson


def print_err( *args, **kwargs ):
    print( *args, file=sys.stderr, **kwargs )


def pretty_json( ugly ):
    return json.dumps( ugly, indent=4, sort_keys=False )


def date_to_string( date ):
    return date.strftime( '%Y-%m-%dT%H:%M:%S.%f' )[:23] + 'Z'


def string_to_date( string ):
    return datetime.datetime.strptime( string, "%Y-%m-%dT%H:%M:%S.%fZ" )


def verify_response( r, data=None ):
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


def simple_changeset_to_list( data ):
    return [x['data'] for x in data['changeset']]
