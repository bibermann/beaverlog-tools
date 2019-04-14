import hashlib
import getpass
import sys

import requests

from .utils import print_err
from .utils import verify_response


def build_auth_header( token ):
    return {'Authorization': f'Bearer {token}'}


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
    access_token = r.json()['data']['access_token']
    refresh_token = r.json()['data']['refresh_token']
    user_id = r.json()['data']['id']

    return access_token, refresh_token, user_id


def logout( url, access_token, refresh_token ):
    print( 'Signing out...' )
    r = requests.delete( f'{url}/auth/revoke-access', headers=build_auth_header( access_token ) )
    verify_response( r )
    r = requests.delete( f'{url}/auth/revoke-refresh', headers=build_auth_header( refresh_token ) )
    verify_response( r )
