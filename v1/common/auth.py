import getpass
import hashlib
import sys

import requests

from shared.common.auth import explain_first_request_exception
from shared.common.auth import request_kwargs
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
        r = requests.post( f'{url}/auth/login', json=data, **request_kwargs() )
    except Exception as e:
        explain_first_request_exception(e)
        sys.exit( 1 )
    verify_response( r, data )
    payload = r.json()
    return RemoteData( url, payload['access_token'], payload['refresh_token'], payload['id'], None )


def logout( remote_data: RemoteData ):
    print( 'Signing out...' )
    r = requests.delete( f'{remote_data.url}/auth/revoke-access',
                         **request_kwargs( remote_data.access_token ) )
    verify_response( r )
    r = requests.delete( f'{remote_data.url}/auth/revoke-refresh',
                         **request_kwargs( remote_data.refresh_token ) )
    verify_response( r )
