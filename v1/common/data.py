import json
import os
import sys

from shared.common.utils import print_err
from v1.detail.upgrade.v0 import upgrade_from_v0


def _upgrade_data( data, error_on_noop ):
    if not 'api_version' in data:
        print( 'Upgrading data from v0 to v1...' )
        return upgrade_from_v0( data )
    version = data['api_version']
    if version == 1:
        if error_on_noop:
            print_err( 'Only data exported by v0 can be converted to v1.' )
            sys.exit( 1 )
        # TODO: complete upload script
        print_err( 'Attention: v1 data cannot be processed yet, only downloaded.' )
        sys.exit( 1 )
        # return data
    else:
        print_err( f'Data version {version} not supported yet.' )
        sys.exit( 1 )



def load_data( filename, error_on_noop=False ):
    with open( filename ) as jsonfile:
        return _upgrade_data( json.load( jsonfile ), error_on_noop )


def save_data( data, filename, skip_warning ):
    if os.path.exists( filename ) and not skip_warning:
        print( f'WARNING: {filename} already exists' )
        print( f'         and will get overridden' )
        input( 'Press Enter to continue' )
    json.dump( data, open( filename, 'w' ), indent=4, sort_keys=False )
