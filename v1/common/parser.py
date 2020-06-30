#!/usr/bin/env python3

import sys

from all.common.utils import print_err


def add_default_arguments( parser, with_y=False ):
    parser.add_argument( '--api', metavar='URL', type=str, help='default: %(default)s',
                         default='https://beaverlog.cc/api/v1' )
    parser.add_argument( '-e', metavar='EMAIL', type=str, help='email or username must be given' )
    parser.add_argument( '-u', metavar='USERNAME', type=str, help='email or username must be given' )
    parser.add_argument( '-p', metavar='PASSWORD', type=str, help='if not given you get prompted' )
    if with_y:
        parser.add_argument( '-y', action='store_true', help='skip warning notice' )


def verify_default_arguments( args ):
    if args.e is None and args.u is None:
        print_err( 'You must give -e or -u.' )
        sys.exit( 1 )

    if args.e is not None and args.u is not None:
        print_err( '-e and -u are mutually exclusive.' )
        sys.exit( 1 )
