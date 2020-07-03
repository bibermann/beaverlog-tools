import typing
import uuid
from dataclasses import dataclass

from v1.common.ids import _format_uuid_hashids_value
from v1.common.ids import get_id_data
from v1.common.ids import next_id


class IdManager:
    def __init__( self, url, access_token ):
        id_offset, self.id_token = get_id_data( url, access_token )
        self.prev_id = _format_uuid_hashids_value( uuid.UUID( id_offset ) )
        self.entity_id_map = {}

    def mapped_id( self, entity: str, eid: str, assert_included: bool = False ) -> str:
        if not entity in self.entity_id_map:
            assert (not assert_included)
            self.entity_id_map[entity] = {}
        id_map = self.entity_id_map[entity]
        if not eid in id_map:
            assert (not assert_included)
            id_map[eid] = self.prev_id = next_id( self.prev_id )
        return id_map[eid]

    def has_id( self, entity: str, eid: str ) -> bool:
        if not entity in self.entity_id_map:
            return False
        id_map = self.entity_id_map[entity]
        return eid in id_map

    def map_id( self, entity: str, eid: str, new_id: str ) -> None:
        if not entity in self.entity_id_map:
            self.entity_id_map[entity] = {}
        id_map = self.entity_id_map[entity]
        assert not eid in id_map
        id_map[eid] = new_id


@dataclass
class RemoteData:
    url: str
    access_token: str
    refresh_token: str
    user_id: str
    id_manager: typing.Optional[IdManager]
