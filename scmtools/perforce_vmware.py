import re

from reviewboard.scmtools.perforce import PerforceTool

class VMwarePerforceTool(PerforceTool):
    """Specialization of PerforceTool which knows about VMware's change format.

       This is not terribly useful outside of VMware, except perhaps as an
       example of how to deal with a relatively common perforce customization.
       """

    @staticmethod
    def parse_change_desc(changedesc, changenum):
        changeset = ChangeSet()
        changeset.changenum = changenum

        changedesc_keys = {
            'QA Notes': "",
            'Testing Done': "",
            'Documentation Notes': "",
            'Bug Number': "",
            'Reviewed by': "",
            'Approved by': "",
            'Breaks vmcore compatibility': "",
            'Breaks vmkernel compatibility': "",
            'Breaks vmkdrivers compatibility': "",
            'Mailto': "",
        }

        process_summary = False
        process_description = False
        process_files = False

        cur_key = None

        for line in changedesc.split("\n"):
            if line == "Description:":
                process_summary = True
                continue
            elif line == "Files:":
                process_files = True
                cur_key = None
                continue
            elif line.strip() == "":
                if process_summary:
                    process_summary = False
                    process_description = True
                    continue

                line = ""
            elif line.startswith("\t") or line.startswith("    "):
                line = line.lstrip()

                if process_files:
                    changeset.files.append(line)
                    continue
                elif line.find(':') != -1:
                    key, value = line.split(':', 2)

                    if changedesc_keys.has_key(key):
                        process_description = False
                        cur_key = key

                        changedesc_keys[key] = value.lstrip() + "\n"
                        continue

            line += "\n"

            if process_summary:
                changeset.summary += line
            elif process_description:
                changeset.description += line
            elif cur_key != None:
                changedesc_keys[cur_key] += line

        changeset.summary = changeset.summary.strip()
        changeset.description = changeset.description.strip()
        changeset.testing_done = changedesc_keys['Testing Done'].strip()
        changeset.bugs_closed = re.split(r"[, ]+",
                                         changedesc_keys['Bug Number'].strip())

        # This is gross.
        if len(changeset.files) > 0:
            parts = changeset.files[0].split('/')

            if parts[2] == "depot":
                changeset.branch = parts[4]

        return changeset
