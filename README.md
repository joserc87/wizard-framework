
# wizard-framework

A set of scripts to help the developer of wizard configurations.

Contains a daemon written in python that keeps your file system and the
document wizard server in sync. It is just a dirty tool that makes the
development and testing of wizards a bit easier.

# Why?

The development cicle of a wizard configuration involves:

1. Write a wizard configuration
2. Go to the document wizard portal
3. Upload the new wizard configuration
4. Close the wizard and go to the wizard page
5. Create a new document and test it
6. Edit the wizard configuration XML and fix the errors
7. GOTO step 2

After many iterations, doing this get's tiring. This script tries to remove the
need of doing steps 2, 3 and 4 so you can focus on writing and testing.

# What does it do?

- Connects to the Document Wizard server and downloads all the wizard
  configurations and event templates. This is done only one time, when the
  script starts.
- Watches the 'wizards' directory for changes in those wizard configuration
  files. When a file is changed, the daemon uploads the file to the server.

**WARNING:** Keep in mind that, when the wizard configuration or the event
template files are uploaded to the server, any previous content will be
overwritten and can't be recovered.

# Install

Download the project

Install pip requirements. (use of virtualenv is recommended)

```
$ pip install -r ./requirements.txt
``

Change the URL of the server in the scripts

# Use

Run the daemon

```
$ python wizard-daemon.py
```

Login with your active directory credentials. A `wizard/` directory will be
created and populated with all the wizard configurations. Change the
configurations. When you press save, the configurations will be automatically
uploaded.


