import getpass
import hashlib
import sys

import requests

from shared.common.auth import build_auth_header
from shared.common.utils import print_err
from shared.common.utils import verify_response
from v1.common.remote import RemoteData


def login( url, email, username, password ) -> RemoteData:
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
    payload = r.json()
    return RemoteData( url, payload['access_token'], payload['refresh_token'], payload['id'], None )


def logout( remote_data: RemoteData ):
    print( 'Signing out...' )
    r = requests.delete( f'{remote_data.url}/auth/revoke-access',
                         headers=build_auth_header( remote_data.access_token ) )
    verify_response( r )
    r = requests.delete( f'{remote_data.url}/auth/revoke-refresh',
                         headers=build_auth_header( remote_data.refresh_token ) )
    verify_response( r )
