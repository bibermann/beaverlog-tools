import getpass
import hashlib
import sys

import requests

from common.auth import build_auth_header
from common.utils import print_err
from common.utils import verify_response


def login( url, email, username, password ):
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
    return payload['access_token'], payload['refresh_token'], payload['id']


def logout( url, access_token, refresh_token ):
    print( 'Signing out...' )
    r = requests.delete( f'{url}/auth/revoke-access', headers=build_auth_header( access_token ) )
    verify_response( r )
    r = requests.delete( f'{url}/auth/revoke-refresh', headers=build_auth_header( refresh_token ) )
    verify_response( r )
