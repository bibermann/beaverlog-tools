import requests

from shared.common.auth import request_kwargs
from shared.common.utils import verify_response
from v1.common.remote import RemoteData


def clear_data( remote_data: RemoteData, skip_warning ):
    if not skip_warning:
        print( f'WARNING: This will permanently delete all your data' )
        print( f'         on {remote_data.url}' )
        input( 'Press Enter to continue' )
    print( 'Removing data...' )
    r = requests.delete( f'{remote_data.url}/batch/all-private', **request_kwargs( remote_data.access_token ) )
    verify_response( r )
