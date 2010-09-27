"""
Sphinx plugin to add a ``http`` role.
"""
from docutils import nodes


DEFAULT_HTTP_STATUS_CODES_URL = \
    'http://en.wikipedia.org/wiki/List_of_HTTP_status_codes#%s'

HTTP_STATUS_CODES = {
    100: 'Continue',
    101: 'Switching Protocols',
    102: 'Processing',
    200: 'OK',
    201: 'Created',
    202: 'Accepted',
    203: 'Non-Authoritative Information',
    204: 'No Content',
    205: 'Reset Content',
    206: 'Partial Content',
    207: 'Multi-Status',
    300: 'Multiple Choices',
    301: 'Moved Permanently',
    302: 'Found',
    303: 'See Other',
    304: 'Not Modified',
    305: 'Use Proxy',
    306: 'Switch Proxy',
    307: 'Temporary Redirect',
    400: 'Bad Request',
    401: 'Unauthorized',
    402: 'Payment Required',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    406: 'Not Acceptable',
    407: 'Proxy Authentication Required',
    408: 'Request Timeout',
    409: 'Conflict',
    410: 'Gone',
    411: 'Length Required',
    412: 'Precondition Failed',
    413: 'Request Entity Too Large',
    414: 'Request-URI Too Long',
    415: 'Unsupported Media Type',
    416: 'Requested Range Not Satisfiable',
    417: 'Expectation Failed',
    418: 'I\m a teapot',
    422: 'Unprocessable Entity',
    423: 'Locked',
    424: 'Failed Dependency',
    425: 'Unordered Collection',
    426: 'Upgrade Required',
    449: 'Retry With',
    450: 'Blocked by Windows Parental Controls',
    500: 'Internal Server Error',
    501: 'Not Implemented',
    502: 'Bad Gateway',
    503: 'Service Unavailable',
    504: 'Gateway Timeout',
    505: 'HTTP Version Not Supported',
    506: 'Variant Also Negotiates',
    507: 'Insufficient Storage',
    509: 'Bandwidth Limit Exceeded',
    510: 'Not Extended',
}


def setup(app):
    app.add_config_value('http_status_codes_url',
                         DEFAULT_HTTP_STATUS_CODES_URL, True)
    app.add_role('http', http_role)


def http_role(role, rawtext, text, linenum, inliner, options={}, content=[]):
    try:
        status_code = int(text)

        if status_code not in HTTP_STATUS_CODES:
            raise ValueError
    except ValueError:
        msg = inliner.reporter.error(
            'HTTP status code must be a valid HTTP status; '
            '"%s" is invalid.' % text,
            line=linenum)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]

    http_status_codes_url = \
        inliner.document.settings.env.config.http_status_codes_url

    if not http_status_codes_url or '%s' not in http_status_codes_url:
        msg = inliner.reporter.error('http_status_codes_url must be '
                                     'configured.',
                                     line=linenum)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]

    ref = http_status_codes_url % status_code
    status_code_text = 'HTTP %s %s' % (status_code,
                                       HTTP_STATUS_CODES[status_code])
    node = nodes.reference(rawtext, status_code_text, refuri=ref, **options)

    return [node], []
