#!/usr/bin/python
import time
from wizard import Broker, FileSystem
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class MyHandler(FileSystemEventHandler):
  """
  Watches for changes in the filesystem
  When a wizard configuration or an event template has been changed, it uploads
  it to the server
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
      print msg

  # File System events

  def on_modified(self, event):
    if event.is_directory:
      self.log('something happened in directory {0} '.format(event.src_path))
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
            self.log('Unrecognized file {0} with extension {1}'.format(filename, extension))
          return True
        else:
          self.log('File {0} has multiple dots?'.format(parts[-1]))
      else:
        self.log('Directory not deep enough or unexpected directory name {0}'.format(parts))
    except ValueError:
      self.log('value error')
      return
    self.log('Not doing anything for {0}'.format(path))

  def update_wizard_configuration(self, wizardID, path):
    wizard = broker.get_wizard(wizardID)
    # Check that wizard still exists
    if wizard is not None:
      wizard.set_configuration(self.filesystem.read(path))
      print "Uploading configuration xml for wizard {0}".format(wizard.name)
    else:
      print 'The wizard with ID {0} does not exist anymore!'.format(wizardID)

  def update_event_template(self, wizardID, path):
    wizard = broker.get_wizard(wizardID)
    # Check that wizard still exists
    if wizard is not None:
      wizard.set_event_template(self.filesystem.read(path))
      print "Uploading event template xml for wizard {0}".format(wizard.name)
    else:
      print 'The wizard with ID {0} does not exist anymore!'.format(wizardID)

def login(broker):
  import getpass
  # Login
  authenticated = ''
  while authenticated != 'OK':
    user = raw_input('User: ')
    pwd = getpass.getpass('Password: ')
    print('Authenticating...')
    authenticated = broker.login(user, pwd)
    print(authenticated)

if __name__ == "__main__":
  broker = Broker('http://WIN-DEVSRVR2012/')
  fs = FileSystem()

  # Login
  login(broker)

  # One time synchronization between the filesystem and the server
  print 'SYNCHRONIZING...'
  fs.update_wizard_folders(broker.get_wizards())
  print 'DONE'

  # Start the daemon
  event_handler = MyHandler(broker, fs, debug=False)

  observer = Observer()
  observer.schedule(event_handler, path='.', recursive=True)
  observer.start()

  print 'READY'
  print 'WATCHING FS'

  try:
    while True:
      time.sleep(1)
  except KeyboardInterrupt:
    observer.stop()
  observer.join()
