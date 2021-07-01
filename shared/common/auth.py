import os

import requests
import urllib3

from shared.common.utils import print_err


def check_ssl_no_verify():
    value = os.environ.get( 'SSL_NO_VERIFY' )
    no_verify = value is not None and str(value) != '0' and str(value).lower() != 'false'

    if no_verify:
        urllib3.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'
        urllib3.disable_warnings( urllib3.exceptions.InsecureRequestWarning )

    return no_verify


ssl_no_verify = check_ssl_no_verify()


def request_kwargs( token=None ):
    return {
        **({'headers': {'Authorization': f'Bearer {token}'}} if token is not None else {}),
        **({'verify': False} if ssl_no_verify else {}),
    }


def explain_first_request_exception( e ):
    if e.__class__ == requests.exceptions.SSLError:
        print_err( 'SSL error. If you trust the server and accept your vulnerability to man-in-the-middle (MitM) attacks, you may try:\n'
                   'SSL_NO_VERIFY=1 poetry run <COMMAND>' )
    elif e.__class__ == requests.exceptions.ConnectionError:
        print_err( 'Server is down.' )
