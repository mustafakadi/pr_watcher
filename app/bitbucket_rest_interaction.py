import requests
import enum
from app.repo_info import RepoInfo

""" Request header related private constants """
_HEADER_AUTH = "Authorization"
_HEADER_BEARER = "Bearer"
_CONTENT_TYPE = "Content-Type"
_APP_JSON = "application/json"

""" Request url related private constants """
_HTTPS = "https://"
_GIT_REST_API = "/git/rest/api/"
_GIT_REST_BUILD_STATUS = "/git/rest/build-status/"
_PROJECTS = "/projects/"
_REPOS = "/repos/"
_PULL_REQUESTS = "/pull-requests/"
_COMMITS_STATS = "/commits/stats/"
_ACTIVITIES = "/activities"
_MERGE = "/merge"
_QUERY_SIGN = "?"
_START_QUERY = "start="

""" Response JSON related private constants """
_SIZE = "size"
_IS_LAST_PAGE = "isLastPage"
_NEXT_PAGE_START = "nextPageStart"
_STATE = "state"
_CONFLICTED = "conflicted"
_CAN_MERGE = "canMerge"
_FROM_REF = "fromRef"
_LATEST_COMMIT = "latestCommit"
_SUCCESSFUL = "successful"
_IN_PROGRESS = "inProgress"
_FAILED = "failed"

""" Private constants for functionality """
_MERGED_STR = "MERGED"

""" dockstring """
class PrStatus(enum.Enum):
    FAILED = 1
    IN_PROGRESS = 2
    SUCCESS = 3
    NO_STATUS = 4


def get_pr_rest_url(pr_id):
    repo_info = RepoInfo.get_instance()
    return _HTTPS + repo_info.server_address + _GIT_REST_API + repo_info.api_version + _PROJECTS + \
        repo_info.project_name + _REPOS + repo_info.repo_name + _PULL_REQUESTS + pr_id


def get_pr_status_rest_url(commit_sha):
    repo_info = RepoInfo.get_instance()
    return _HTTPS + repo_info.server_address + _GIT_REST_BUILD_STATUS + repo_info.api_version + _COMMITS_STATS + \
        commit_sha


def get_request_headers():
    repo_info = RepoInfo.get_instance()
    return {_CONTENT_TYPE: _APP_JSON, _HEADER_AUTH: _HEADER_BEARER + " " + str(repo_info.access_token)}


def get_activities(pr_id):
    if not pr_id:
        return 0

    if not RepoInfo.are_all_fields_set():
        return 0

    pr_rest_target_url = get_pr_rest_url(pr_id)
    activities_url = pr_rest_target_url + _ACTIVITIES
    headers = get_request_headers()

    try:
        rsp = requests.get(activities_url, headers=headers)
        rsp.raise_for_status()
    except requests.exceptions.RequestException:
        return 0
    rsp_json = rsp.json()

    try:
        activity_cnt = rsp_json[_SIZE]
        is_last_page = rsp_json[_IS_LAST_PAGE]
    except ValueError:
        return 0

    while not is_last_page:
        try:
            next_start = rsp_json[_NEXT_PAGE_START]
            next_url = activities_url + _QUERY_SIGN + _START_QUERY + str(next_start)
            rsp = requests.get(next_url, headers=headers)
            rsp.raise_for_status()
            rsp_json = rsp.json()
            activity_cnt += rsp_json[_SIZE]
            is_last_page = rsp_json[_IS_LAST_PAGE]
        except ValueError:
            return 0
        except requests.exceptions.RequestException:
            return 0

    print("Activity Cnt: " + str(activity_cnt))
    return activity_cnt


def is_pr_merged(pr_id):
    if not pr_id:
        return 0

    if not RepoInfo.are_all_fields_set():
        return 0

    pr_rest_target_url = get_pr_rest_url(pr_id)
    headers = get_request_headers()

    try:
        rsp = requests.get(pr_rest_target_url, headers=headers)
        rsp.raise_for_status()
    except requests.exceptions.RequestException:
        return False
    rsp_json = rsp.json()

    try:
        state = rsp_json[_STATE]
    except ValueError:
        return False

    print("is_pr_merged: " + str(state))

    return state == _MERGED_STR


def is_pr_conflicted(pr_id):
    if not pr_id:
        return 0

    if not RepoInfo.are_all_fields_set():
        return 0

    pr_rest_target_url = get_pr_rest_url(pr_id)
    merge_url = pr_rest_target_url + _MERGE
    headers = get_request_headers()

    if is_pr_merged(pr_id):
        return False

    try:
        rsp = requests.get(merge_url, headers=headers)
        rsp.raise_for_status()
    except requests.exceptions.RequestException:
        return False
    rsp_json = rsp.json()

    try:
        conflicted = rsp_json[_CONFLICTED]
    except ValueError:
        return False

    print("is_pr_conflicted: " + str(conflicted))

    return conflicted


def is_ready_to_merge(pr_id):
    if not pr_id:
        return 0

    if not RepoInfo.are_all_fields_set():
        return 0

    pr_rest_target_url = get_pr_rest_url(pr_id)
    merge_url = pr_rest_target_url + _MERGE
    headers = get_request_headers()

    if is_pr_merged(pr_id):
        return False

    try:
        rsp = requests.get(merge_url, headers=headers)
        rsp.raise_for_status()
    except requests.exceptions.RequestException:
        return False
    rsp_json = rsp.json()

    try:
        can_merge = rsp_json[_CAN_MERGE]
    except ValueError:
        return False

    print("is_ready_to_merge: " + str(can_merge))

    return can_merge


def get_status(pr_id):
    if not pr_id:
        return 0

    if not RepoInfo.are_all_fields_set():
        return 0

    pr_rest_target_url = get_pr_rest_url(pr_id)
    headers = get_request_headers()

    try:
        rsp = requests.get(pr_rest_target_url, headers=headers)
        rsp.raise_for_status()
    except requests.exceptions.RequestException:
        return PrStatus.NO_STATUS
    rsp_json = rsp.json()

    print("[get_status][" + pr_rest_target_url + "] " + str(rsp_json))

    try:
        commit_sha = rsp_json[_FROM_REF][_LATEST_COMMIT]
    except ValueError:
        return PrStatus.NO_STATUS

    target_status_url = get_pr_status_rest_url(commit_sha)

    try:
        rsp = requests.get(target_status_url, headers=headers)
        rsp.raise_for_status()
    except requests.exceptions.RequestException:
        return PrStatus.NO_STATUS
    rsp_json = rsp.json()

    print("[get_status][" + target_status_url + "] " + str(rsp_json))

    try:
        successful = rsp_json[_SUCCESSFUL]
        in_progress = rsp_json[_IN_PROGRESS]
        failed = rsp_json[_FAILED]
    except ValueError:
        return PrStatus.NO_STATUS

    print("[get_status] SUCCESSFUL: " + str(successful) + ", IN_PROGRESS: " + str(in_progress) + ", FAILED: " + str(
        failed))

    if failed > 0:
        return PrStatus.FAILED
    elif in_progress > 0:
        return PrStatus.IN_PROGRESS
    elif successful > 0:
        return PrStatus.SUCCESS
    else:
        return PrStatus.NO_STATUS


def does_pr_exist(pr_id):
    if not pr_id:
        return 0

    if not RepoInfo.are_all_fields_set():
        return 0

    pr_rest_target_url = get_pr_rest_url(pr_id)
    headers = get_request_headers()

    try:
        rsp = requests.get(pr_rest_target_url, headers=headers)
        rsp.raise_for_status()
    except requests.exceptions.HTTPError:
        return False
    except requests.exceptions.RequestException:
        return False

    return True
