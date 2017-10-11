#!/usr/bin/python
import time
import os
from wizard import Broker, FileSystem
from endpoints import endpoints
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Python 2 and 3 compatibility
try:
    input = raw_input
except NameError:
    pass


class bcolors:
    # Colors from http://stackoverflow.com/questions/287871/print-in-terminal-with-colors-using-python
    HEADER = '\033[35m'
    OKBLUE = '\033[34m'
    OKGREEN = '\033[32m'
    WARNING = '\033[33m'
    FAIL = '\033[31m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def log(msg):
    print(bcolors.OKGREEN + msg + bcolors.ENDC)


def info(msg):
    print(bcolors.OKBLUE + msg + bcolors.ENDC)


def warn(msg):
    print(bcolors.WARNING + msg + bcolors.ENDC)


def err(msg):
    print(bcolors.FAIL + msg + bcolors.ENDC)


class MyHandler(FileSystemEventHandler):
    """
    Watches for changes in the filesystem
    When a wizard configuration or an event template has been changed, it
    uploads it to the server
    """

    def __init__(self, broker, filesystem, debug=False):
        """
        Constructor
        Args:
            broker (Broker): object to communicate with the server
            filesystem (FileSystem): helper object to access the filesystem
        """
        self.debug = debug
        self.broker = broker
        self.filesystem = filesystem

    def log(self, msg):
        if self.debug:
            print(bcolors.OKGREEN + msg + bcolors.ENDC)

    # File System events

    def on_modified(self, event):
        if event.is_directory:
            self.log('something happened in directory {0} '
                     .format(event.src_path))
        else:
            self.process_file(event.src_path)

    def on_created(self, event):
        if event.is_directory:
            self.log('new directory {0} '.format(event.src_path))
        else:
            self.process_file(event.src_path)

    def process_file(self, path):
        parts = path.split('/')
        try:
            # parts = wizards/{id}/file.xml
            if len(parts) >= 3 and parts[-3] == 'wizards':
                wizardFolder = parts[-2].split(' - ', 1)
                wizardID = int(wizardFolder[0])
                fileparts = parts[-1].split('.')
                # Get name and extension (file = name.ext)
                if len(fileparts) == 2:
                    filename = fileparts[0]
                    extension = fileparts[1]
                    if filename == 'WizardConfiguration' and extension == 'xml':
                        # Send
                        self.update_wizard_configuration(wizardID, path)
                    elif filename == 'EventTemplate' and extension == 'xml':
                        self.update_event_template(wizardID, path)
                    else:
                        self.log('Unrecognized file {0} with extension {1}'
                                 .format(filename, extension))
                    return True
                else:
                    self.log('File {0} has multiple dots?'.format(parts[-1]))
            else:
                self.log('Directory not deep enough or unexpected directory name {0}'
                         .format(parts))
        except ValueError:
            self.log('value error')
            return
        self.log('Not doing anything for {0}'.format(path))

    def update_wizard_configuration(self, wizardID, path):
        wizard = broker.get_wizard(wizardID)
        # Check that wizard still exists
        if wizard is not None:
            data = self.filesystem.read(path)
            errors = wizard.validate_configuration(data)
            if len(errors) == 0:
                info("Uploading configuration xml for wizard {0}"
                     .format(wizard.name))
                wizard.set_configuration(data)
            else:
                warn("Validation failed in configuration of wizard {0}:\n  - {1}"
                     .format(wizard.name, '\n  - '.join(errors)))
        else:
            err('The wizard with ID {0} does not exist anymore!'
                .format(wizardID))

    def update_event_template(self, wizardID, path):
        wizard = broker.get_wizard(wizardID)
        # Check that wizard still exists
        if wizard is not None:
            wizard.set_event_template(self.filesystem.read(path))
            info("Uploading event template xml for wizard {0}"
                 .format(wizard.name))
        else:
            err('The wizard with ID {0} does not exist anymore!'
                .format(wizardID))


def login(broker):
    import getpass
    # Login
    authenticated = ''
    while authenticated != 'OK':
        user = input('User: ')
        pwd = getpass.getpass('Password: ')
        log('Authenticating...')
        authenticated = broker.login(user, pwd)
        if authenticated == 'OK':
            log(authenticated)
        else:
            err(authenticated)


if __name__ == "__main__":
    # Select the endpoint to connect to
    endpoint = ''
    while endpoint not in endpoints.keys():
        endpoint = input('endpoint [{}]: '
                         .format('/'.join(endpoints.keys()))).lower()

    url, base = endpoints[endpoint]['url'], endpoints[endpoint]['base']

    # Custom endpoint: fill in by the user
    if endpoint == 'other':
        while url is None:
            url = input('server url (e.g. http://myserver.com/): ')
        base = input("base api [default 'api/']: ") or base

    # Add last slash
    url = (url + '/') if url[-1] != '/' else url

    broker = Broker(url, base)
    root = './data/' + endpoint + '/'
    # Crete the directory if it does not exist
    if not os.path.exists(root):
        os.makedirs(root)

    fs = FileSystem(root + 'wizards/')

    # Login
    login(broker)

    # One time synchronization between the filesystem and the server
    log('SYNCHRONIZING...')
    fs.update_wizard_folders(broker.get_wizards())
    log('DONE')

    # Start the daemon
    event_handler = MyHandler(broker, fs, debug=False)

    observer = Observer()
    observer.schedule(event_handler, path=root, recursive=True)
    observer.start()

    log('READY')
    log('WATCHING FS')

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
