import subprocess
import codecs
import os
import sys
from base64 import urlsafe_b64encode

from paste.script.templates import var  # @UnresolvedImport

try:
    from hashlib import sha1
except ImportError:
    from sha import sha as sha1

HOME = os.path.expanduser('~')


class ask_var(var):

    def __init__(self, name, description,
                 default='', should_echo=True, should_ask=True,
                 getter=None):
        super(ask_var, self).__init__(
            name, description, default=default,
            should_echo=should_echo)
        self.should_ask = should_ask
        self.getter = getter
        if self.getter is None:
            self.getter = lambda _x, _y: self.default

def create_buildout_default_file():
    default_dir = os.path.join(HOME, '.buildout')
    if not os.path.isdir(default_dir):
        os.mkdir(default_dir)
    eggs_dir = os.path.join(default_dir, 'eggs')
    if not os.path.isdir(eggs_dir):
        os.mkdir(eggs_dir)
    if sys.platform == 'win32':
        # Fix for paths with spaces on Windows.
        # See https://bugs.launchpad.net/grok/+bug/315223
        # See https://bugs.launchpad.net/grok/+bug/524000
        eggs_dir = eggs_dir.replace('\\', '\\'*2)
    default_cfg = os.path.join(HOME, '.buildout', 'default.cfg')
    if not os.path.isfile(default_cfg):
        config_file = open(default_cfg, 'w')
        contents = """[buildout]
eggs-directory = %s
""" % (eggs_dir)
        config_file.write(contents)
        config_file.close()

def get_ssha_encoded_string(password):
    """Encode the given `string` using "Secure" SHA.

    Taken from zope.password.password, however grokproject itself
    cannot depend on that package.
    """
    encoder = codecs.getencoder('utf-8')
    _hash = sha1(encoder(password)[0])
    salt = os.urandom(4)
    _hash.update(salt)
    return b'{SSHA}' + urlsafe_b64encode(_hash.digest() + salt)

def get_boolean_value_for_option(tvars, option):
    value = tvars.get(option.name)
    if value is not None:
        if isinstance(option.default, bool):
            want_boolean = True
        else:
            want_boolean = False
        value = value.lower()
        if value in ('1', 'true', 'yes'):
            if want_boolean:
                value = True
            else:
                value = 'true'
        elif value in ('0', 'false', 'no'):
            if want_boolean:
                value = False
            else:
                value = 'false'
        else:
            print("")
            print("Error: %s should be true or false." % option.name)
            sys.exit(1)
    else:
        value = option.default
    return value

def exist_buildout_default_file():
    default_cfg = os.path.join(HOME, '.buildout', 'default.cfg')
    return os.path.isfile(default_cfg)

def run_buildout(verbose=False, use_distribute=False):
    # Run the project's bootstrap.
    cmd = sys.executable + ' ' + os.path.join(os.getcwd(), 'bootstrap.py')
    if use_distribute:
        cmd += ' --distribute'
    print('Running %s...' % cmd)
    subprocess.call(cmd, shell=True)
    # Then, run the project's buildout.
    cmd = os.path.join(os.getcwd(), 'bin', 'buildout')
    if verbose:
        cmd += ' -v'
    print('Running %s...' % cmd)
    subprocess.call(cmd, shell=True)
