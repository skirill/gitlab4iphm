import io
from .utils import perform_request

conf = None


class MilestoneNotes(object):
    """
    Release notes for all issues in GitLab that pertain to a particular milestone.
    """
    def __init__(self, config, milestone):
        global conf
        conf = config
        self.headers = conf.default_headers
        self.milestone = milestone
        self.issues = []
        self.error_issues = 0
        self._load_issues(milestone)

    def _load_issues(self, milestone):
        """
        Load all issues for the milestone, check status, search for release notes comments
        """
        url = "{}/projects/{}/issues".format(conf.gitlab_base_url, conf.gitlab_project_id)
        params = {"milestone": milestone, "scope": "all"}
        issues = perform_request(url, "get", headers=self.headers, params=params)

        for state in [u'opened', u'closed']:
            issues_by_state = [i for i in issues if i[u'state'] == state]
            print(u"{} issues ({})".format(state, len(issues_by_state)))
            for issue in sorted(issues_by_state, key=lambda k: k[u'title']):
                print(u"  {}".format(issue[u'title']))
                components = [l for l in issue[u'labels'] if not (l.startswith("#") or l.startswith("_"))]
                print(u"    Components: {}".format(", ".join(components)))
                if state == u'closed':
                    rec = {u'iid': issue[u'iid'], u'title': issue[u'title'], u'components': components}
                    self._load_notes(rec)
                    self.issues.append(rec)

    def _load_notes(self, rec):
        """
        Load all notes == comments for the issue, search for release notes comment
        """
        url = "{}/projects/{}/issues/{}/notes".format(conf.gitlab_base_url, conf.gitlab_project_id, rec[u'iid'])
        notes = perform_request(url, "get", headers=self.headers)
        for note in notes:
            if u'body' in note:
                body = note[u'body']
                if body.startswith(conf.gitlab_explicit_no_notes_header):
                    self._set_notes(rec, u'Empty', None)
                    break
                elif body.startswith(conf.gitlab_internal_notes_header):
                    self._set_notes(rec, u'Internal', body)
                    break
                elif body.startswith(conf.gitlab_notes_header):
                    self._set_notes(rec, u'Public', body)
                    break
        else:
            print(u"    ERROR: Release Notes: NONE")
            self.error_issues += 1

    @staticmethod
    def _set_notes(rec, notes_type, notes):
        if notes:
            lines = notes.strip().split(u'\n')[1:]
            rec[notes_type] = u'\n'.join(lines)
            description = u" ({} line{})".format(len(lines), ending(lines))
        else:
            rec[notes_type] = None
            description = u""
        print(u"    Release Notes: {}{}".format(notes_type, description))

    def save(self):
        """
        Save the external and internal release notes to file(s)
        """
        print(u'\nCreating output files\n')
        for notes_type in [u'Public', u'Internal', u'Empty']:
            issues = [rec for rec in self.issues if notes_type in rec]
            if notes_type == u'Empty':
                if issues:
                    print(u"Skipped {} issue{} with explicit empty release notes".format(len(issues), ending(issues)))
            else:
                file_name = u'ReleaseNotes-{}-{}.txt'.format(self.milestone, notes_type)
                if issues:
                    with io.open(file_name, 'w', encoding='utf-8') as f:
                        for issue in issues:
                            f.write(u'{}\n{}\n{}\n----\n'.format(
                                issue[u'title'],
                                u", ".join(issue[u'components']),
                                issue[notes_type]
                            ))
                    print(u"Saved notes for {} {} issue{} to {}".format(
                        len(issues),
                        notes_type,
                        ending(issues),
                        file_name
                    ))
                else:
                    print(u"Skipped creating {}: there are no {} issues".format(file_name, notes_type))

        if self.error_issues:
            print(u"ERROR: {} closed issue{} left undocumented, see above".format(
                self.error_issues, ending(self.error_issues)
            ))


def ending(obj):
    count = len(obj) if type(obj) in [list, dict, tuple] else int(obj)
    return u'' if count == 1 else u's'
