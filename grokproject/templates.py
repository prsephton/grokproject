from __future__ import print_function
import sys
import os
from six.moves.urllib.parse import urljoin           # @UnresolvedImport
from six.moves.urllib.error import HTTPError         # @UnresolvedImport
from six.moves.urllib.request import urlopen         # @UnresolvedImport
import xml.sax.saxutils
from paste.script import templates                   # @UnresolvedImport
from paste.script.templates import NoDefault         # @UnresolvedImport
from grokproject.utils import run_buildout
from grokproject.utils import ask_var
from grokproject.utils import get_boolean_value_for_option
from grokproject.utils import get_ssha_encoded_string
from grokproject.utils import create_buildout_default_file
from grokproject.utils import exist_buildout_default_file

#  Retrieve the currently checked out git source from the git configuration
# and figure out from that from whence we can download our versions.cfg
# base = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
# base = open(os.path.join(base, '.git', 'config')).read()
# base = base[base.find('url = ')+6:base.find('.git')]
# base = base.replace('github.com', 'raw.githubusercontent.com')

base = 'https://raw.githubusercontent.com/prsephton/grokproject'
GROK_RELEASE_URL = base + '/master/versions/'

class GrokProject(templates.Template):
    _template_dir = 'template'
    summary = "A grok project"
    required_templates = []

    vars = [
        ask_var(
            'user', 'Name of an initial administrator user',
            default=NoDefault),
        ask_var(
            'passwd', 'Password for the initial administrator user',
            default=NoDefault, should_echo=False),
        ask_var(
            'newest', 'Check for newer versions of packages',
            default='false', should_ask=False,
            getter=get_boolean_value_for_option),
        ask_var(
            'run_buildout', (
            "After creating the project area, run the buildout. "
            "Defaults to true"),
            default=True, should_ask=False,
            getter=get_boolean_value_for_option),
        ask_var(
            'use_distribute',
            "Use Distribute instead of setuptools for this project.",
            default=False, should_ask=False,
            getter=get_boolean_value_for_option),
        ask_var(
            'eggs_dir',
            'Location where zc.buildout will look for and place packages',
            default='', should_ask=False),
        ]

    def check_vars(self, vars, cmd):
        if vars['package'] in ('grok', 'zope'):
            print("Error: The chosen project name results in an invalid " \
                              "package name: %s." % vars['package'])
            print("Please choose a different project name.")
            sys.exit(1)

        explicit_eggs_dir = vars.get('eggs_dir')

        skipped_vars = {}
        for var in list(self.vars):
            if not var.should_ask:
                skipped_vars[var.name] = var.getter(vars, var)
                self.vars.remove(var)

        vars = super(GrokProject, self).check_vars(vars, cmd)
        for name in skipped_vars:
            vars[name] = skipped_vars[name]

        vars['passwd'] = get_ssha_encoded_string(vars['passwd'])
        for var_name in ['user', 'passwd']:
            # Escape values that go in site.zcml.
            if isinstance(vars[var_name], str):
                vars[var_name] = xml.sax.saxutils.quoteattr(vars[var_name])
            else:
                vars[var_name] = xml.sax.saxutils.quoteattr(vars[var_name].decode())
        vars['app_class_name'] = vars['project'].capitalize()
        vars['project_lowercase'] = vars['project'].lower()

        # Handling the version.cfg file.
        version_url = vars.get('version_url')
        find_links_url = ''
        if version_url is None:
            print("Determining current grok version...")
            # If no version URL was specified, we look up the current
            # version first and construct a URL.
            current_info_url = urljoin(GROK_RELEASE_URL, 'current')
            version = self.download(current_info_url).strip().replace(
                    'grok-', '').replace('.cfg', '')
            version_url = GROK_RELEASE_URL + version + '/versions.cfg'
            find_links_url = GROK_RELEASE_URL + version + '/eggs'

        vars['find_links_url'] = find_links_url
        vars['version_info_url'] = version_url

        buildout_default = exist_buildout_default_file()
        if explicit_eggs_dir:
            # Put explicit_eggs_dir in the vars; used by the post command.
            vars['explicit_eggs_dir'] = explicit_eggs_dir
            vars['eggs_dir'] = (
                '# Warning: when you share this buildout.cfg with friends\n'
                '# please remove the eggs-directory line as it is hardcoded.\n'
                'eggs-directory = %s') % explicit_eggs_dir
        elif buildout_default:
            vars['eggs-dir'] = ''
        else:
            create_buildout_default_file()

        vars['package_directory'] = os.path.abspath(os.path.join(
                os.getcwd(), vars['project']))

        include_site_packages = vars.get('include_site_packages')
        if include_site_packages is None:
            vars['include_site_packages'] = 'false'

        return vars

    def download(self, url):
        """Downloads a file and returns the contents.

        If an error occurs, we abort, giving some information about
        the reason.
        """
        contents = None
        try:
            contents = urlopen(url).read()
        except HTTPError:
            # Some 404 or similar happened...
            print("Error: cannot download required %s" % url)
            print("Maybe you specified a non-existing version?")
            sys.exit(1)
        except IOError as e:
            # Some serious problem: no connect to server...
            print("Error: cannot download required %s" % url)
            print("Server may be down.  Please try again later.")
            sys.exit(1)
        print(f"{url} = [{contents.decode('ISO-8859-1')}]")
        return contents.decode("ISO-8859-1")

    def post(self, command, output_dir, vars):
        if not vars['run_buildout']:
            return
        original_dir = os.getcwd()
        os.chdir(vars['project'])
        run_buildout(command.verbose, vars['use_distribute'])
        os.chdir(original_dir)
