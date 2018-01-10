from __future__ import unicode_literals

from djblets.webapi.errors import WebAPIError


#
# Standard error messages
#
UNSPECIFIED_DIFF_REVISION = WebAPIError(
    200,
    'Diff revision not specified.',
    http_status=400)  # 400 Bad Request

INVALID_DIFF_REVISION = WebAPIError(
    201,
    'Invalid diff revision.',
    http_status=404)  # 404 Not Found

INVALID_ACTION = WebAPIError(
    202,
    'Invalid action specified.',
    http_status=400)  # 400 Bad Request

INVALID_CHANGE_NUMBER = WebAPIError(
    203,
    'The commit ID specified could not be found.',
    http_status=404)  # 404 Not Found

CHANGE_NUMBER_IN_USE = WebAPIError(
    204,
    'The commit ID specified has already been used.',
    http_status=409)  # 409 Conflict

MISSING_REPOSITORY = WebAPIError(
    205,
    'There was no repository found at the specified path.',
    http_status=400)  # 400 Bad Request

INVALID_REPOSITORY = WebAPIError(
    206,
    'The repository path specified is not in the list of known repositories.',
    http_status=400)  # 400 Bad Request

REPO_FILE_NOT_FOUND = WebAPIError(
    207,
    'The file was not found in the repository.',
    http_status=400)  # 400 Bad Request

INVALID_USER = WebAPIError(
    208,
    'User does not exist.',
    http_status=400)  # 400 Bad Request

REPO_NOT_IMPLEMENTED = WebAPIError(
    209,
    'The specified repository is not able to perform this action.',
    http_status=501)  # 501 Not Implemented

REPO_INFO_ERROR = WebAPIError(
    210,
    'There was an error fetching extended information for this repository.',
    http_status=500)  # 500 Internal Server Error

NOTHING_TO_PUBLISH = WebAPIError(
    211,
    'You attempted to publish a review request without any modifications.',
    http_status=400)  # 400 Bad Request

EMPTY_CHANGESET = WebAPIError(
    212,
    'The commit ID specified represents an empty changeset.',
    http_status=400)  # 400 Bad Request

SERVER_CONFIG_ERROR = WebAPIError(
    213,
    'There was an error storing configuration on the server.',
    http_status=500)  # 500 Internal Server Error

BAD_HOST_KEY = WebAPIError(
    214,
    'The SSH key on the host does ot match the stored key.',
    http_status=403)  # 403 Forbidden

UNVERIFIED_HOST_KEY = WebAPIError(
    215,
    'The SSH key on the host is unverified.',
    http_status=403)  # 403 Forbidden

UNVERIFIED_HOST_CERT = WebAPIError(
    216,
    'The HTTPS certificate on the host is unverified.',
    http_status=403)  # 403 Forbidden

MISSING_USER_KEY = WebAPIError(
    217,
    'A public SSH key was requested, but no SSH key was available to send.',
    http_status=403)  # 403 Forbidden

REPO_AUTHENTICATION_ERROR = WebAPIError(
    218,
    'Unable to authenticate with the repository using the provided '
    'credentials.',
    http_status=403)  # 403 Forbidden

DIFF_EMPTY = WebAPIError(
    219,
    'The specified diff file is empty.',
    http_status=400)  # 400 Bad Request

DIFF_TOO_BIG = WebAPIError(
    220,
    'The specified diff file is too large.',
    http_status=400)  # 400 Bad Request

FILE_RETRIEVAL_ERROR = WebAPIError(
    221,
    'There was an error fetching a source file.',
    http_status=500)  # 500 Internal Server Error

HOSTINGSVC_AUTH_ERROR = WebAPIError(
    222,
    'There was an error authorizing with a service.',
    http_status=403)  # 403 Forbidden

GROUP_ALREADY_EXISTS = WebAPIError(
    223,
    'A group with this name already exists.',
    http_status=409)  # 409 Conflict

DIFF_PARSE_ERROR = WebAPIError(
    224,
    'The specified diff file could not be parsed.',
    http_status=400)  # 400 Bad Request

PUBLISH_ERROR = WebAPIError(
    225,
    'An error occurred during publishing.',
    http_status=500)  # 500 Internal Server Error

USER_QUERY_ERROR = WebAPIError(
    226,
    'An error occurred querying the user list.',
    http_status=500)  # 500 Internal Server Error

COMMIT_ID_ALREADY_EXISTS = WebAPIError(
    227,
    'Review request with this commit ID already exists in the repository.',
    http_status=409)  # 409 Conflict

TOKEN_GENERATION_FAILED = WebAPIError(
    228,
    'There was an error generating the API token. Please try again.',
    http_status=500)  # 500 Internal Server Error.

REPOSITORY_ALREADY_EXISTS = WebAPIError(
    229,
    'A repository with this name already exists.',
    http_status=409)  # 409 Conflict

CLOSE_ERROR = WebAPIError(
    230,
    'An error occurred while closing the review request.',
    http_status=500)  # 500 Internal Server Error

REOPEN_ERROR = WebAPIError(
    231,
    'An error occurred while reopening the review request.',
    http_status=500)  # 500 Internal Server Error

REVOKE_SHIP_IT_ERROR = WebAPIError(
    232,
    'An error occurred while revoking the Ship It for a review.',
    http_status=500)  # 500 Internal Server Error

READ_ONLY_ERROR = WebAPIError(
    233,
    'The site is currently in read-only mode.',
    http_status=503)  # 503 Service Unavailable Error
