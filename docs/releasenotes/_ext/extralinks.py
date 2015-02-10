"""
Sphinx plugins for special links in the Release Notes.
"""
from docutils import nodes, utils


def setup(app):
    app.add_config_value('bugtracker_url', '', True)
    app.add_role('bug', bug_role)
    app.add_role('cve', cve_role)


def bug_role(role, rawtext, text, linenum, inliner, options={}, content=[]):
    try:
        bugnum = int(text)
        if bugnum <= 0:
            raise ValueError
    except ValueError:
        msg = inliner.reporter.error(
            'Bug number must be a number greater than or equal to 1; '
            '"%s" is invalid.' % text,
            line=linenum)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]

    bugtracker_url = inliner.document.settings.env.config.bugtracker_url

    if not bugtracker_url or '%s' not in bugtracker_url:
        msg = inliner.reporter.error('bugtracker_url must be configured.',
                                     line=linenum)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]

    ref = bugtracker_url % bugnum
    node = nodes.reference(rawtext, 'Bug #' + utils.unescape(text),
                           refuri=ref, **options)

    return [node], []


def cve_role(role, rawtext, text, linenum, inliner, options={}, content=[]):
    ref = 'http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-%s' % text
    node = nodes.reference(rawtext, 'CVE-' + utils.unescape(text),
                           refuri=ref, **options)

    return [node], []
