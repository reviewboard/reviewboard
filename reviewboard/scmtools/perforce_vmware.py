import re

from reviewboard.scmtools.perforce import PerforceTool

class VMwarePerforceTool(PerforceTool):
    """Specialization of PerforceTool which knows about VMware's change format.

       This is not terribly useful outside of VMware, except perhaps as an
       example of how to deal with a relatively common perforce customization.
       """
    name = "Perforce (VMware)"

    @staticmethod
    def parse_change_desc(changedesc, changenum):
        changeset = PerforceTool.parse_change_desc(changedesc, changenum)

        if not changeset:
            return None

        # VMware's perforce changeset template is just the basic perforce one
        # with a bunch of extra fields at the end of the description.  We
        # leave the summary and file list as-is, and process the description
        # field to populate a couple more members of the ChangeSet object and
        # remove a lot of stuff that reviewers don't care about.
        sections = ['QA Notes:',
                    'Testing Done:',
                    'Documentation Notes:',
                    'Bug Number:',
                    'Reviewed by:',
                    'Approved by:',
                    'Breaks vmcore compatibility:',
                    'Breaks vmkernel compatibility:',
                    'Breaks vmkdrivers compatibility:',
                    'Mailto:',
                    'Merge to:']

        lines = changeset.description.split('\n')

        # First we go through and find the line numbers that start each section.
        # We then sort these line numbers so we can slice out each individual
        # section of text.
        locations = {}
        for i, line in enumerate(lines):
            for section in sections:
                if line.startswith(section):
                    locations[i] = section
        section_indices = sorted(locations.keys())

        # Pull the branch name out of the file list
        branches = []
        for file in changeset.files:
            try:
                branch = file.split('/')[4]
                if branch not in branches:
                    branches.append(branch)
            except IndexError:
                pass
        branch = ', '.join(branches)

        try:
            # The interesting part of the description field contains everything up
            # to the first marked section.
            changeset.description = '\n'.join(lines[:section_indices[0]])
        except IndexError:
            # If none of the sections exist, just return the changeset as-is
            return changeset

        # Now pull out each individual section.  This gives us a dictionary
        # mapping section name to a string.  We special-case "Merge to:" in
        # here, since it can appear multiple times.
        sections = {}
        branches = [branch]
        for start, end in map(None, section_indices, section_indices[1:]):
            name = locations[start]
            if name == 'Merge to:':
                # Include merge information in the branch field
                m = re.match('Merge to: (?P<branch>[\w\-]+): (?P<type>[A-Z]+)',
                             lines[start])
                if m:
                    if m.group('type') == 'YES':
                        branches.append(m.group('branch'))
                    elif m.group('type') == 'MANUAL':
                        branches.append(m.group('branch') + ' (manual)')

            else:
                sections[name] = '\n'.join(lines[start:end])[len(name):].strip()

        changeset.branch = ' &rarr; '.join(branches)

        changeset.testing_done = sections.get('Testing Done:')

        try:
            changeset.bugs_closed = re.split(r"[, ]+", sections['Bug Number:'])
        except KeyError:
            pass

        return changeset
