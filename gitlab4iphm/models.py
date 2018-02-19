import io
from .config import get_config
from .utils import perform_request


class MilestoneNotes(object):
    """
    Release notes for all issues in GitLab that pertain to a particular milestone.
    """

    def __init__(self, config_path, milestone):
        self.conf = get_config(config_path)
        self.headers = self.conf.default_headers
        self.milestone = milestone
        self.issues = []
        self.error_issues = 0
        self._load_issues(milestone)

    def _load_issues(self, milestone):
        """
        Load all issues for the milestone, check status, search for release notes comments
        """
        url = "{}/projects/{}/issues".format(self.conf.gitlab_base_url, self.conf.gitlab_project_id)
        page = 1
        issues = []
        while True:
            params = {"milestone": milestone, "scope": "all", "page": page}
            resp_headers, page_issues = perform_request(url, "get", headers=self.headers, params=params)

            issues += page_issues

            if str(page) == resp_headers["X-Total-Pages"]:
                break
            page += 1

        for state in ["opened", "closed"]:
            issues_by_state = [i for i in issues if i["state"] == state]
            print("{} issues ({})".format(state, len(issues_by_state)))
            for issue in sorted(issues_by_state, key=lambda k: k["title"]):
                print(u"  {}".format(issue["title"]))
                components = [l for l in issue["labels"] if not (l.startswith("#") or l.startswith("_"))]
                print(u"    Components: {}".format(", ".join(components)))
                if state == "closed":
                    rec = {"iid": issue["iid"], "title": issue["title"], "components": components}
                    self._load_notes(rec)
                    self.issues.append(rec)

    def _load_notes(self, rec):
        """
        Load all notes == comments for the issue, search for release notes comment
        """
        url = "{}/projects/{}/issues/{}/notes".format(self.conf.gitlab_base_url, self.conf.gitlab_project_id,
                                                      rec["iid"])
        page = 1
        while True:
            resp_headers, notes = perform_request(url, "get", headers=self.headers, params={"page": page})
            for note in notes:
                if "body" in note and self._detect_and_set_notes(note["body"], rec):
                    break
            if "notes" in rec or str(page) == resp_headers["X-Total-Pages"]:
                break
            page += 1
        if "notes" not in rec:
            print(u"    ERROR: Release Notes: NONE")
            self.error_issues += 1

    def _detect_and_set_notes(self, body, rec):
        if body.startswith(self.conf.gitlab_explicit_no_notes_header):
            MilestoneNotes._set_notes(rec, "Empty", None)
        elif body.startswith(self.conf.gitlab_internal_notes_header):
            MilestoneNotes._set_notes(rec, "Internal", body)
        elif body.startswith(self.conf.gitlab_notes_header):
            MilestoneNotes._set_notes(rec, "Public", body)
        return "notes" in rec

    @staticmethod
    def _set_notes(rec, notes_type, notes):
        if notes:
            lines = notes.strip().split(u'\n')[1:]
            rec["notes"] = (notes_type, u'\n'.join(lines))
            description = u" ({} line{})".format(len(lines), ending(lines))
        else:
            rec["notes"] = (notes_type, None)
            description = u""
        print(u"    Release Notes: {}{}".format(notes_type, description))

    def save(self, destination):
        """
        Save the external and internal release notes to file(s)
        """
        print(u"\nCreating output files\n")
        total_issues = 0
        for notes_type in ["Public", "Internal", "Empty"]:
            issues = [rec for rec in self.issues if "notes" in rec and rec["notes"][0] == notes_type]
            if notes_type == "Empty":
                if issues:
                    print(u"Skipped {} issue{} with explicit empty release notes".format(len(issues), ending(issues)))
            else:
                self.save_issues(issues, notes_type, destination)
            total_issues += len(issues)
        print(u"TOTAL: {} issue{}".format(total_issues, ending(total_issues)))

        if self.error_issues:
            print(u"ERROR: {} closed issue{} left undocumented, see above".format(
                self.error_issues, ending(self.error_issues)
            ))

    def save_issues(self, issues, notes_type, destination):
        if destination == "file":
            self.save_issues_to_file(issues, notes_type)
        elif destination == "wiki":
            self.save_issues_to_wiki(issues, notes_type)
        else:
            print(u"Unknown destination: {}".format(destination))

    def save_issues_to_file(self, issues, notes_type):
        file_name = u'ReleaseNotes-{}-{}.txt'.format(self.milestone, notes_type)
        payload = MilestoneNotes._format(issues)
        if payload:
            with io.open(file_name, 'w', encoding='utf-8') as f:
                f.write(payload)
            print(u"Saved notes for {} {} issue{} to {}".format(len(issues), notes_type, ending(issues), file_name))
        else:
            print(u"Skipped creating {}: there are no {} issues".format(file_name, notes_type))

    def save_issues_to_wiki(self, issues, notes_type):
        payload = MilestoneNotes._format(issues)
        if payload:
            url = "{}/projects/{}/wikis".format(self.conf.gitlab_base_url, self.conf.gitlab_project_id)
            data = {"title": u"{}: {} release notes".format(self.milestone, notes_type), "content": payload}
            try:
                page_url = "{}/{}".format(url, data["title"].replace(u" ", u"-"))
                perform_request(page_url, "get", headers=self.headers)
                # Page found so update it
                verb, action = "put", u"Updated"
                url = page_url
            except Exception:
                # Page not found, so create it with "post", slug is an output parameter
                verb, action = "post", u"Created"
            _, resp = perform_request(url, verb, headers=self.headers, data=data)
            print(u"{} notes for {} {} issue{} in {}".format(
                action, len(issues), notes_type, ending(issues), resp["slug"]))
        else:
            print(u"Skipped saving notes for {} issues: there are none".format(notes_type))

    @staticmethod
    def _format(issues):
        return "\n".join(
                [
                    u'#### {}\n{}\n{}\n'.format(
                        issue["title"],
                        u" ".join([u'~"{}"'.format(x) for x in issue["components"]]),
                        issue["notes"][1]
                    )
                    for issue in issues
                ]
            )


def ending(obj):
    count = len(obj) if type(obj) in [list, dict, tuple] else int(obj)
    return u'' if count == 1 else u's'
