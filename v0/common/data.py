import json


def load_data( filename ):
    with open( filename ) as jsonfile:
        return json.load( jsonfile )