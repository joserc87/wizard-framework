import os
import requests
from requests.auth import HTTPBasicAuth

class Wizard:

  def __init__(self, broker, id, name, description, is_active):
    self.broker = broker
    self.id = id
    self.name = name
    self.description = description
    self.is_active = is_active
    self.configuration = None
    self.event_template = None

  def __str__(self):
    return "Wizard[{0}]: '{1}' ({2})".format(self.id, self.name, 'active' if self.is_active else 'inactive')

  def get_configuration(self):
    if self.configuration is None:
      r = self.broker.get('/wizards/{0}/configuration'.format(self.id))
      self.configuration = r.content
    return self.configuration

  def set_configuration(self, content):
    if self.configuration != content:
      r = self.broker.put('/wizards/{0}/configuration'.format(self.id), content)
      self.configuration = content
      if r.status_code == 200:
        return True
      else:
        return False
    else:
      return True

  def validate_configuration(self, content):
      """
      Validates a wizard configuration and returns possible errors in a list of strings
      Returns an empty list if the validation passes
      """
      r = self.broker.post('/wizards/configuration/validation', content)
      if r.status_code == 200:
        return r.json()
      else:
        return ['validation returned code {0}'.format(r.status_code)]

  def get_event_template(self):
    if self.event_template is None:
      r = self.broker.get('/wizards/{0}/event'.format(self.id))
      self.event_template = r.content
    return self.event_template

  def set_event_template(self, content):
    if self.event_template != content:
      r = self.broker.put('/wizards/{0}/event'.format(self.id), content)
      self.event_template = content
      if r.status_code == 200:
        return True
      else:
        return False
    else:
      return True

class Broker:

  def __init__(self, host='http://localhost/', base='api/v2.0'):
    self.host = host
    self.base = base
    self.DEBUG = False

  def debug(self, msg):
    if (self.DEBUG):
      print(msg)

  # part should start with '/'
  def getURL(self, part):
    return self.host + self.base + part

  def get(self, part):
    url = self.getURL(part)
    self.debug(' -- GET :: {0}'.format(url))
    return requests.get(url, auth=self.auth)

  def post(self, part, content):
    url = self.getURL(part)
    self.debug(' -- POST :: {0}'.format(url))
    return requests.post(url, data=content, auth=self.auth)

  def put(self, part, content):
    url = self.getURL(part)
    self.debug(' -- PUT :: {0}'.format(url))
    return requests.put(url, data=content, auth=self.auth)

  # Web Service calls

  def login(self, user, password):
    self.auth = (user, password)
    # Dummy call to see if we are authenticated
    r = self.get('/users/current')
    if r.status_code == 200:
      return 'OK'
    elif r.status_code == 401:
      return 'Error 401: Unauthorized'
    else:
      return 'Error code: {0}'.format(r.status_code)
    return 'OK'

  def get_wizards(self):
    # Call the rest web service
    r = self.get('/wizards')

    # Check the output
    if r.status_code == 200:
      result = r.json()
      if result['Error'] is None:
        wizards = [ Wizard(
          self,
          int(w['ID']),
          w['Name'],
          w['Description'],
          bool(w['IsActive'])) for w in result['Wizards'] ]

        return wizards
      else: # Result contains an error
        print('There was an error in the call to /wizards:')
        print(result['Error'])
    else:
      print('Something went wrong' )
    return None

  def get_wizard(self, wizardID):
    # Call the rest web service
    r = self.get('/wizards/{0}'.format(wizardID))

    # Check the output
    if r.status_code == 200:
      result = r.json()
      if result['Error'] is None:
        w = result['Wizard']
        wizard = Wizard(
          self,
          int(w['ID']),
          w['Name'],
          w['Description'],
          bool(w['IsActive']))

        return wizard
      else: # Result contains an error
        print('There was an error in the call to /wizards/{id}:')
        print(result['Error'])
    else:
      print('Something went wrong')
    return None

class FileSystem:

  def __init__(self, path = './wizards/'):
    self.path = path

  def update_wizard_folders(self, wizards):
    for wizard in wizards:
      wizard_dir = '{0}{1} - {2}'.format(self.path,  wizard.id, wizard.name)
      # If the folder does not exist, create it
      if not os.path.isdir(wizard_dir):
        print("New wizard found: '{0}'".format(wizard.name))
        os.makedirs(wizard_dir)
      files = [
          (wizard_dir + '/WizardConfiguration.xml', wizard.get_configuration()),
          (wizard_dir + '/EventTemplate.xml', wizard.get_event_template())]
      for (filePath, content) in files:
        # If the files do not exist, create them
        if not os.path.exists(filePath):
          print("Downloading file '{0}' for wizard '{1}'".format(filePath, wizard.name))
          self.write(content, filePath)
        else:
          if not self.compare_file_with_data(filePath, content):
            # Ask the user if he wants to overwrite
            q = ''
            while q != 'y' and q != 'n':
              q = raw_input('The file {0} has been modified locally. Overrwite? (y/n)'.format(filePath)).lower()
              if q.lower() == 'y':
                self.write(content, filePath)
              elif q.lower() == 'n':
                print('Ignoring. File not in sync')
              else:
                print('Invalid option')

  def compare_file_with_data(self, path, content):
    # Return false when they are different
    if self.read(path) == content:
      return True
    return False

  def write(self, content, path):
    with open(path, 'wb') as f:
      f.write(content)

  def read(self, path):
    with open(path, 'rb') as f:
      return f.read()


# Main

if __name__ == "__main__":
  import getpass
  broker = Broker('http://WIN-DEVSRVR2012/')

  # Login
  authenticated = ''
  while authenticated != 'OK':
    user = raw_input('User:')
    pwd = getpass.getpass('Password:')
    print('Authenticating...')
    authenticated = broker.login(user, pwd)
    print(authenticated)

  # Get all the wizards
  wizards = broker.get_wizards()

  # Update the file system
  fs = FileSystem()
  fs.update_wizard_folders(wizards)
