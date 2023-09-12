"""Review Board API errors.

This builds upon the :py:mod:`djblets.webapi.errors` module, which contains
API errors provided by Djblets.
"""

from djblets.webapi.errors import WebAPIError


#: An error indicating a diff revision was missing in the request.
UNSPECIFIED_DIFF_REVISION = WebAPIError(
    code=200,
    msg='Diff revision not specified.',
    error_type='diff-revision-missing',
    http_status=400)  # 400 Bad Request


#: An error indicating a provided diff revision was invalid.
INVALID_DIFF_REVISION = WebAPIError(
    code=201,
    msg='Invalid diff revision.',
    error_type='diff-revision-invalid',
    http_status=404)  # 404 Not Found


#: An error indicating a provided action was invalid.
#:
#: This is not used by Review Board and is considered deprecated.
#:
#: Deprecated:
#:     6.0
INVALID_ACTION = WebAPIError(
    code=202,
    msg='Invalid action specified.',
    error_type='action-invalid',
    http_status=400)  # 400 Bad Request


#: An error indicating a commit ID could not be found in the repository.
INVALID_CHANGE_NUMBER = WebAPIError(
    code=203,
    msg='The commit ID specified could not be found.',
    error_type='repository-commit-id-invalid',
    http_status=404)  # 404 Not Found


#: An error indicating a commit ID is in use by another review request.
#:
#: For historical reasons, this is only used when creating review requests
#: or drafts, and applies to ``commit_id`` or ``changenum`` values.
#:
#: See :py:data:`COMMIT_ID_ALREADY_EXISTS`.
CHANGE_NUMBER_IN_USE = WebAPIError(
    code=204,
    msg='The commit ID specified has already been used.',
    error_type='review-request-commit-id-conflict',
    http_status=409)  # 409 Conflict


#: An error indicating a repository could not be found at a path.
MISSING_REPOSITORY = WebAPIError(
    code=205,
    msg='There was no repository found at the specified path.',
    error_type='repository-missing',
    http_status=400)  # 400 Bad Request


#: An error indicating a provided repository path/ID is invalid.
INVALID_REPOSITORY = WebAPIError(
    code=206,
    msg=(
        'The repository path specified is not in the list of known '
        'repositories.'
    ),
    error_type='repository-invalid',
    http_status=400)  # 400 Bad Request


#: An error indicating a file could not be found in a repository.
REPO_FILE_NOT_FOUND = WebAPIError(
    code=207,
    msg='The file was not found in the repository.',
    error_type='repository-file-not-found',
    http_status=400)  # 400 Bad Request


#: An error indicating a provided user does not exist.
#:
#: This is used when adding users to repositories, groups, or review requests
#: as reviewers.
INVALID_USER = WebAPIError(
    code=208,
    msg='User does not exist.',
    error_type='user-invalid',
    http_status=400)  # 400 Bad Request


#: An error indicating a repository request is not supported.
#:
#: This is used when a repository does not support fetching additional
#: information, such as repository metadata, commits, or branches.
REPO_NOT_IMPLEMENTED = WebAPIError(
    code=209,
    msg='The specified repository is not able to perform this action.',
    error_type='repository-request-not-supported',
    http_status=501)  # 501 Not Implemented


#: An error indicating failure fetching information from a repository.
#:
#: This is used when there's a communication error fetching state or
#: performing actions on a repository.
REPO_INFO_ERROR = WebAPIError(
    code=210,
    msg=(
        'There was an error communicating with this repository.'
    ),
    error_type='repository-communication-error',
    http_status=500)  # 500 Internal Server Error


#: An error indicating a publish failed due to a lack of changes.
NOTHING_TO_PUBLISH = WebAPIError(
    code=211,
    msg='You attempted to publish a review request without any modifications.',
    error_type='review-request-not-modified',
    http_status=400)  # 400 Bad Request


#: An error indicating a commit ID represents an empty changeset.
EMPTY_CHANGESET = WebAPIError(
    code=212,
    msg='The commit ID specified represents an empty changeset.',
    error_type='repository-commit-id-changeset-empty',
    http_status=400)  # 400 Bad Request


#: An error indicating a problem storing server-side configuration state.
#:
#: This is used when failing to store settings, certificate approvals,
#: credentials, or other data on a Review Board server.
SERVER_CONFIG_ERROR = WebAPIError(
    code=213,
    msg='There was an error storing configuration on the server.',
    error_type='server-config-error',
    http_status=500)  # 500 Internal Server Error


#: An error indicating a stored SSH host key does not match the server.
BAD_HOST_KEY = WebAPIError(
    code=214,
    msg='The SSH key on the host does not match the stored key.',
    error_type='ssh-host-key-mismatch',
    http_status=403)  # 403 Forbidden


#: An error indicating a SSH host key from a server is not verified.
UNVERIFIED_HOST_KEY = WebAPIError(
    code=215,
    msg='The SSH key on the host is unverified.',
    error_type='ssh-host-key-not-verified',
    http_status=403)  # 403 Forbidden


#: An error indicating a SSL certificate from a server is not verified.
UNVERIFIED_HOST_CERT = WebAPIError(
    code=216,
    msg='The HTTPS certificate on the host is unverified.',
    error_type='ssl-certificate-not-verified',
    http_status=403)  # 403 Forbidden


#: An error indicating a public SSH key is not available for the server.
MISSING_USER_KEY = WebAPIError(
    code=217,
    msg=(
        'A public SSH key was requested, but no SSH key was available to send.'
    ),
    error_type='ssh-public-key-missing',
    http_status=403)  # 403 Forbidden


#: An error indicating an authentication error with a repository.
REPO_AUTHENTICATION_ERROR = WebAPIError(
    code=218,
    msg=(
        'Unable to authenticate with the repository using the provided '
        'credentials.'
    ),
    error_type='repository-auth-error',
    http_status=403)  # 403 Forbidden


#: An error indicating a provided diff is empty.
DIFF_EMPTY = WebAPIError(
    code=219,
    msg='The specified diff file is empty.',
    error_type='diff-empty',
    http_status=400)  # 400 Bad Request


#: An error indicating a provided diff exceeds configured size limits.
DIFF_TOO_BIG = WebAPIError(
    code=220,
    msg='The specified diff file is too large.',
    error_type='diff-too-large',
    http_status=400)  # 400 Bad Request


#: An error indicating a failure retrieving a file from a repository
#:
#: This is used when a file should be present but unexpectedly could not be
#: retrieved.
FILE_RETRIEVAL_ERROR = WebAPIError(
    code=221,
    msg='There was an error fetching a source file.',
    error_type='repository-file-error',
    http_status=500)  # 500 Internal Server Error


#: An error indicating an authenticatiion error with a hosting service.
HOSTINGSVC_AUTH_ERROR = WebAPIError(
    code=222,
    msg='There was an error authorizing with a service.',
    error_type='hosting-service-auth-error',
    http_status=403)  # 403 Forbidden


#: An error indicating a review group already exists.
GROUP_ALREADY_EXISTS = WebAPIError(
    code=223,
    msg='A group with this name already exists.',
    error_type='review-group-conflict',
    http_status=409)  # 409 Conflict


#: An error indicating a provided diff could not be parsed.
DIFF_PARSE_ERROR = WebAPIError(
    code=224,
    msg='The specified diff file could not be parsed.',
    error_type='diff-parse-error',
    http_status=400)  # 400 Bad Request


#: An error indicating a review request could not be published.
#:
#: This is used if there's an error publishing the review request due to
#: missing state, a validation error, or an extension-provided failure.
PUBLISH_ERROR = WebAPIError(
    code=225,
    msg='An error occurred during publishing.',
    error_type='review-request-publish-error',
    http_status=500)  # 500 Internal Server Error


#: An error indicating a user could not be queried from an auth backend.
USER_QUERY_ERROR = WebAPIError(
    code=226,
    msg='An error occurred querying the user list.',
    error_type='user-query-error',
    http_status=500)  # 500 Internal Server Error


#: An error indicating a commit ID is in use by another review request.
#:
#: For historical reasons, this is only used when updating review requests
#: or drafts.
#:
#: See :py:data:`CHANGE_NUMBER_IN_USE`.
COMMIT_ID_ALREADY_EXISTS = WebAPIError(
    code=227,
    msg=(
        'Review request with this commit ID already exists.',
    ),
    error_type='review-request-commit-id-conflict',
    http_status=409)  # 409 Conflict


#: An error indicating an API token could not be generated.
TOKEN_GENERATION_FAILED = WebAPIError(
    code=228,
    msg='There was an error generating the API token. Please try again.',
    error_type='api-token-generation-error',
    http_status=500)  # 500 Internal Server Error.


#: An error indicating a repository already exists.
#:
#: This is used when trying to create a repository that conflicts with
#: an existing repository.
REPOSITORY_ALREADY_EXISTS = WebAPIError(
    code=229,
    msg='A repository with this name already exists.',
    error_type='repository-conflict',
    http_status=409)  # 409 Conflict


#: An error indicating a failure closing a review request.
CLOSE_ERROR = WebAPIError(
    code=230,
    msg='An error occurred while closing the review request.',
    error_type='review-request-close-error',
    http_status=500)  # 500 Internal Server Error


#: An error indicating a failure reopening a review request.
REOPEN_ERROR = WebAPIError(
    code=231,
    msg='An error occurred while reopening the review request.',
    error_type='review-request-reopen-error',
    http_status=500)  # 500 Internal Server Error


#: An error indicating a failure revoking a Ship It!
REVOKE_SHIP_IT_ERROR = WebAPIError(
    code=232,
    msg='An error occurred while revoking the Ship It for a review.',
    error_type='review-request-revoke-ship-it-error',
    http_status=500)  # 500 Internal Server Error


#: An error indicating the site is in read-only mode.
#:
#: This is used when attempting to perform operations that may write to the
#: server without permission while in Read-Only Mode,
READ_ONLY_ERROR = WebAPIError(
    code=233,
    msg='The site is currently in read-only mode.',
    error_type='server-read-only',
    http_status=503)  # 503 Service Unavailable Error


#: An error indicating a review group does not exist.
INVALID_GROUP = WebAPIError(
    code=234,
    msg='Group does not exist.',
    error_type='review-group-invalid',
    http_status=400)  # 400 Bad Request
