import getpass
import hashlib
import sys

import requests

from shared.common.auth import explain_first_request_exception
from shared.common.auth import request_kwargs
from shared.common.utils import verify_response


def login( url, email, username, password ):
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
    payload = r.json()['data']
    return payload['access_token'], payload['refresh_token'], payload['id']


def logout( url, access_token, refresh_token ):
    print( 'Signing out...' )
    r = requests.delete( f'{url}/auth/revoke-access', **request_kwargs( access_token ) )
    verify_response( r )
    r = requests.delete( f'{url}/auth/revoke-refresh', **request_kwargs( refresh_token ) )
    verify_response( r )
