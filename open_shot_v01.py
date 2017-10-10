import logging
import ftrack_api
import os


SDE_FILE_FORMAT = r'Z:\projects\{0}\episodes\{1}\shots\{2}{3}_{4}_{5}'

class OpenShot(object):
    ''' Opens the file location of the selected shot on the Media (Z:) drive. '''

    label = 'Open Shot Directory'
    identifier = 'open.shot'
    description = 'Opens the shot directory.'

    def __init__(self, session):
        '''Initialize action.'''
        super(OpenShot, self).__init__()
        self.session = session
        self.entity_type = ''

        ''' Set up logging '''
        self.logger = logging.getLogger('ACTION: ' + __name__ + '.' + self.__class__.__name__)

    def register(self):
        '''Register action.'''
        self.session.event_hub.subscribe(
                'topic=ftrack.action.discover and source.user.username={0}'.format(
                self.session.api_user), self.discover
                )

        self.session.event_hub.subscribe(
                'topic=ftrack.action.launch and data.actionIdentifier={0} and source.user.username={1}'.format(
                self.identifier, self.session.api_user), self.launch
                )

    def discover(self, event):
        '''Return action config if triggered on a single task.'''
        data = event['data']

        # If selection contains more than one item return early since
        # this action can only handle a single version.
        selection = data.get('selection', [])
        self.logger.info('Got selection: {0}'.format(selection))

        if len(selection) != 1:
            return

        # If selection is not a Shot or Task, return early.
        self.entity_type = self.get_type(selection[0]['entityId'])

        if self.entity_type != 'Shot' and self.entity_type != 'Task':
            return

        return {
            'items': [{
                'label': self.label,
                'description': self.description,
                'actionIdentifier': self.identifier
            }]
        }

    def launch(self, event):
        '''Callback method for custom action.'''
        selection = event['data'].get('selection', [])

        # Get the shot hierarchy.
        shot = self.session.get(self.entity_type, selection[0]['entityId'])
        hierarchy = self.get_shot_hierarchy(shot)

        # If the hierarchy contains the base task, replace it with the project name.
        # If not, append it.
        project_name = self.session.get('Project', shot['project_id'])['name']
        if len(hierarchy) > 4:
            hierarchy[4] = project_name
        else:
            hierarchy.append(project_name)

        path = self.assemble_path(hierarchy)

        os.startfile(path)

        return {
            'success': True,
            'message': 'Opening directory: {0}'.format(path)
        }

    def get_type(self, task_id):
        ''' Returns the entity type. '''
        context = self.session.get('TypedContext', task_id)
        return type(context).__name__

    def get_shot_hierarchy(self, shot):
        ''' Creates a list containing the selected shot's project, act, episode, and shot data.'''
        links = shot['link']
        tree = []
        for link in links:
            tree.append(link['name'])
        return tree

    def assemble_path(self, hierarchy):
        ''' Returns a path based on current SDE file conventions. '''
        project = hierarchy[0]
        episode = hierarchy[1]
        act = hierarchy[2]
        shot = hierarchy[3]
        project_short = hierarchy[4]

        return SDE_FILE_FORMAT.format(project, episode, project_short, episode, act, shot)

def register(session, **kw):
    '''Register plugin.'''

    # Validate that session is an instance of ftrack_api.Session. If not,
    # assume that register is being called from an incompatible API
    # and return without doing anything.
    if not isinstance(session, ftrack_api.Session):
        # Exit to avoid registering this plugin again.
        return

    action = OpenShot(session)
    action.register()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    session = ftrack_api.Session()
    register(session)

    # Wait for events.
    session.event_hub.wait()
    