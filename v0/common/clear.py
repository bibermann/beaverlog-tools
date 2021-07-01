import requests

from shared.common.auth import request_kwargs
from shared.common.utils import verify_response


def clear_data( url, token, skip_warning ):
    if not skip_warning:
        print( f'WARNING: This will permanently delete all your data' )
        print( f'         on {url}' )
        input( 'Press Enter to continue' )
    print( 'Removing data...' )
    r = requests.delete( f'{url}/batch/all-private', **request_kwargs( token ) )
    verify_response( r )