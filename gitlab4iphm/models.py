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
        self.issues = {}
        self.load_issues(milestone)

    def load_issues(self, milestone):
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
                    iid = issue[u'iid']
                    self.issues[iid] = {u'title': issue[u'title'], u'components': components}
                    self.load_notes(iid)

    def load_notes(self, iid):
        """
        Load all notes == comments for the issue, search for release notes comment
        """
        url = "{}/projects/{}/issues/{}/notes".format(conf.gitlab_base_url, conf.gitlab_project_id, iid)
        notes = perform_request(url, "get", headers=self.headers)
        for note in notes:
            if u'body' in note:
                body = note[u'body']
                if body.startswith(conf.gitlab_explicit_no_notes_header):
                    self.issues[iid][u'NoNotes'] = None
                    print(u"    Release Notes: Explicitly Empty")
                    break
                elif body.startswith(conf.gitlab_internal_notes_header):
                    self.issues[iid][u'InternalNotes'] = body.replace(conf.gitlab_internal_notes_header, "").strip()
                    print(u"    Release Notes: Internal")
                    print(u"----\n{}\n----".format(self.issues[iid][u'InternalNotes']))
                    break
                elif body.startswith(conf.gitlab_notes_header):
                    self.issues[iid][u'Notes'] = body.replace(conf.gitlab_notes_header, "").strip()
                    print(u"    Release Notes: Public")
                    print(u"----\n{}\n----".format(self.issues[iid][u'Notes']))
                    break
        else:
            print(u"    ERROR: Release Notes: NONE")

    def save(self):
        """
        Save the external and internal release notes to file(s)
        """
        pass
