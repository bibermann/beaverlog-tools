import copy
import typing

import simplejson as json

from v1.common.ids import EMPTY_ID

next_issue_id = 1
projects = {}


def _add_issue( project_id, issue, data ):
    global next_issue_id
    global projects

    issue_fid = issue['issue_fid']
    is_archived = issue['is_archived']

    if not project_id in projects:
        projects[project_id] = {}
    projects[project_id][issue_fid] = next_issue_id

    if not 'tracker_issues' in data:
        data['tracker_issues'] = []
    data['tracker_issues'].append( {
        'id': str( next_issue_id ),
        'project_id': project_id,
        'key': str( issue_fid ),
        'title': str( issue_fid ),
        'is_hidden': is_archived,
        'was_used': True,
    } )
    next_issue_id += 1


def _get_issue_id( project_id, issue_fid ):
    return projects[project_id][issue_fid]


def _convert_link( item ):
    item['id'] = str( item['id'] )
    item['service'] = 'gitlab'
    del item['is_archived']
    return item


def _convert_project( item, subject_id, data ):
    item['id'] = str( item['id'] )
    item['link_id'] = str( item['link_id'] )
    item['subject_id'] = subject_id
    item['name'] = str( item['project_fid'] )
    item['key'] = str( item['project_fid'] )
    if 'is_archived' in item:
        item['is_hidden'] = item['is_archived']
        del item['is_archived']
    if not 'tracker_issues' in data:
        data['tracker_issues'] = []
    for issue in item['issues']:
        _add_issue( item['id'], issue, data )
    del item['issues']
    del item['project_fid']
    return item


def _transform_users( data ):
    for item in data['users']:
        item['id'] = str( item['id'] )
        if 'gitlab_links' in item:
            data['tracker_links'] = list( map( _convert_link, item['gitlab_links'] ) )
            del item['gitlab_links']


def _transform_organizations( data ):
    for item in data['organizations']:
        item['id'] = str( item['id'] )
        if 'members' in item:
            for member in item['members']:
                member['user_id'] = str( member['user_id'] )


def _transform_subjects( data ):
    for item in data['subjects']:
        item['id'] = str( item['id'] )
        item['organization_id'] = str( item['organization_id'] )
        item['parent_ids'] = list( map( str, item['parent_ids'] ) )
        item['ancestor_ids'] = list( map( str, item['ancestor_ids'] ) )
        if 'is_project' in item:
            if item['is_project']:
                item['kind'] = 'project'
            del item['is_project']
        if 'gitlab_projects' in item:
            if not 'tracker_projects' in data:
                data['tracker_projects'] = []
            data['tracker_projects'].extend(
                map( lambda p: _convert_project( p, item['id'], data ), item['gitlab_projects'] ) )
            del item['gitlab_projects']


def _transform_locations( data ):
    for item in data['locations']:
        item['id'] = str( item['id'] )


def _get_activity_subject_id( sid, data,
                              subject_map: typing.Dict[str, typing.Dict[str, any]],
                              subject_replacement_map: typing.Dict[str, str] ):
    sid = str( sid )
    s = subject_map[sid]
    is_organization_subject = s['organization_id'] != EMPTY_ID
    if not is_organization_subject:
        return sid
    if sid in subject_replacement_map:
        return subject_replacement_map[sid]

    old_name = s['name']
    organization_name = next(o['name'] for o in data['organizations'] if o['id'] == s['organization_id'])

    # create child subject
    s = copy.deepcopy( s )
    s['organization_id'] = EMPTY_ID
    s['parent_ids'] = [sid]
    s['name'] += ' [private]'
    s['id'] += '_child'
    s.pop( 'ancestor_ids', None )
    s.pop( 'activity_count', None )
    s.pop( 'activity_start', None )
    s.pop( 'activity_end', None )
    s.pop( 'created_on', None )
    s.pop( 'gitlab_projects', None )
    s.pop( 'is_project', None )
    data['subjects'].append( s )

    new_id = s['id']
    new_name = s['name']
    subject_replacement_map[sid] = new_id
    print( f'Note: Added subject "{new_name}" ({new_id}) as child of organization subject '
           f'"{organization_name} :: {old_name}" ({sid}) to hold your activity/activities.' )
    return s['id']


def _transform_activities( data ):
    subject_map = {s['id']: s for s in data['subjects']}
    subject_replacement_map = {}
    for item in data['activities']:
        item['id'] = str( item['id'] )
        item['location_id'] = str( item['location_id'] )
        item['subject_ids'] = [
            _get_activity_subject_id( item['subject_id'], data, subject_map, subject_replacement_map )]
        del item['subject_id']
        if 'data' in item:
            if isinstance( item['data'], dict ):
                if 'issue' in item['data']:
                    item['issue_id'] = str( _get_issue_id( str( item['data']['issue']['project_id'] ),
                                                           item['data']['issue']['issue_fid'] ) )
                    del item['data']['issue']
            elif isinstance( item['data'], str ):
                try:
                    string_as_json = json.loads( item['data'] )
                    if isinstance( string_as_json, dict ) and 'comment' in string_as_json:
                        item['data'] = {'comment': string_as_json['comment']}
                    else:
                        item['data'] = {'original_data': string_as_json}
                except:
                    if item['data'][:12] == '{"comment":"' and item['data'][-2:] == '"}':
                        item['data'] = {'comment': item['data'][12:-2]}
                    else:
                        item['data'] = {'original_data': item['data']}
            else:
                item['data'] = {'original_data': item['data']}


def upgrade_from_v0( data ):
    new_data = copy.deepcopy( data )
    _transform_users( new_data['data'] )
    _transform_organizations( new_data['data'] )
    _transform_subjects( new_data['data'] )
    _transform_locations( new_data['data'] )
    _transform_activities( new_data['data'] )
    return {
        'exported_on': new_data['exported_on'],
        'api_version': 1,
        'user_id': new_data['user_id'],
        'data': new_data['data'],
    }
