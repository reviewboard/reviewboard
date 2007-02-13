import re

from reviewboard.scmtools.perforce import PerforceTool

class VMwarePerforceTool(PerforceTool):
    """Specialization of PerforceTool which knows about VMware's change format.

       This is not terribly useful outside of VMware, except perhaps as an
       example of how to deal with a relatively common perforce customization.
       """

    @staticmethod
    def parse_change_desc(changedesc, changenum):
        changeset = PerforceTool.parse_change_desc(changedesc, changenum)

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
        for line, i in zip(lines, range(len(lines))):
            for section in sections:
                if line.startswith(section):
                    locations[i] = section
        section_indices = sorted(locations.keys())

        # The interesting part of the description field contains everything up
        # to the first marked section.
        changeset.description = '\n'.join(lines[:section_indices[0]])

        # Now pull out each individual section.  This gives us a dictionary
        # mapping section name to a string.
        sections = {}
        for start, end in map(None, section_indices, section_indices[1:]):
            name = locations[start]
            sections[name] = ' '.join(lines[start:end])[len(name):].strip()

        changeset.testing_done = sections['Testing Done:']
        changeset.bugs_closed = re.split(r"[, ]+", sections['Bug Number:'])
        # FIXME: branch?

        return changeset
