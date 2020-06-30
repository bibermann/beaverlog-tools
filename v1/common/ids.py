import uuid

import requests
from hashids import Hashids

from common.auth import build_auth_header
from common.utils import verify_response

EMPTY_ID = '0'

OBFUSCATED_UUID_MIN_LENGTH = 20
OBFUSCATED_UUID_ALPHABET = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
OBFUSCATED_UUID_ALPHABET_REGEX = rf'[{OBFUSCATED_UUID_ALPHABET}]{{{OBFUSCATED_UUID_MIN_LENGTH},}}'

uuid_hashids = Hashids( salt='beaverlog', min_length=OBFUSCATED_UUID_MIN_LENGTH,
                        alphabet=OBFUSCATED_UUID_ALPHABET )


def _parse_uuid_hashids_value( value: str ) -> uuid.UUID:
    if value == '0':
        return uuid.UUID( int=0 )
    decoded: str = uuid_hashids.decode_hex( value )
    if decoded == '':
        raise ValueError( f'Could not decode "{value}"' )
    return uuid.UUID( int=int( decoded, 16 ) )


def _format_uuid_hashids_value( value: uuid.UUID ) -> str:
    if value.int == 0:
        return '0'
    encoded: str = uuid_hashids.encode_hex( value.hex.lstrip( '0' ) )
    if len( encoded ) < OBFUSCATED_UUID_MIN_LENGTH:
        raise ValueError( f'Could not encode "{value}"' )
    return encoded


def next_id( id_ ):
    id_uuid = _parse_uuid_hashids_value( id_ )
    return _format_uuid_hashids_value( uuid.UUID( int=id_uuid.int + 1 ) )


def get_id_data( url, access_token ):
    print( 'Fetching ID data...' )
    r = requests.post( f'{url}/id/', headers=build_auth_header( access_token ) )
    verify_response( r )
    payload = r.json()
    return payload['id_offset'], payload['id_token']
