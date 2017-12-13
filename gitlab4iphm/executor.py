from .config import get_config
from .models import MilestoneNotes
from .utils import perform_request


class Executor(object):
    def __init__(self, config_path):
        self.conf = get_config(config_path)

    def prepare_release_notes(self, milestone):
        '''
        Prepare release notes for a particular GitLab milestone.
        '''
        milestone_notes = MilestoneNotes(self.conf, milestone)
        milestone_notes.save()
