import sys
import os
from urllib.error import HTTPError
from urllib.request import urlopen
import xml.sax.saxutils
from paste.script import templates            # @UnresolvedImport
from paste.script.templates import NoDefault  # @UnresolvedImport
from grokproject.utils import run_buildout
from grokproject.utils import ask_var
from grokproject.utils import get_boolean_value_for_option
from grokproject.utils import get_ssha_encoded_string
from grokproject.utils import create_buildout_default_file
from grokproject.utils import exist_buildout_default_file

#  Retrieve the currently checked out git source from the git configuration
# and figure out from that from whence we can download our versions.cfg

GROK_RELEASE_URL = 'https://raw.githubusercontent.com/zopefoundation/groktoolkit/master/grok-versions.cfg'

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

    def check_vars(self, tvars, cmd):
        if tvars['package'] in ('grok', 'zope'):
            print("Error: The chosen project name results in an invalid " \
                              "package name: %s." % tvars['package'])
            print("Please choose a different project name.")
            sys.exit(1)

        explicit_eggs_dir = tvars.get('eggs_dir')

        skipped_vars = {}
        for var in list(self.vars):
            if not var.should_ask:
                skipped_vars[var.name] = var.getter(tvars, var)
                self.vars.remove(var)

        tvars = super(GrokProject, self).check_vars(tvars, cmd)
        for name in skipped_vars:
            tvars[name] = skipped_vars[name]

        tvars['passwd'] = get_ssha_encoded_string(tvars['passwd'])
        for var_name in ['user', 'passwd']:
            # Escape values that go in site.zcml.
            if isinstance(tvars[var_name], str):
                tvars[var_name] = xml.sax.saxutils.quoteattr(tvars[var_name])
            else:
                tvars[var_name] = xml.sax.saxutils.quoteattr(tvars[var_name].decode())
        tvars['app_class_name'] = tvars['project'].capitalize()
        tvars['project_lowercase'] = tvars['project'].lower()

        # Handling the version.cfg file.
        version_url = tvars.get('version_url')
        find_links_url = ''
        if version_url is None:
            version_url = GROK_RELEASE_URL

        tvars['find_links_url'] = find_links_url
        tvars['version_info_url'] = version_url

        buildout_default = exist_buildout_default_file()
        if explicit_eggs_dir:
            # Put explicit_eggs_dir in the vars; used by the post command.
            tvars['explicit_eggs_dir'] = explicit_eggs_dir
            tvars['eggs_dir'] = (
                '# Warning: when you share this buildout.cfg with friends\n'
                '# please remove the eggs-directory line as it is hardcoded.\n'
                'eggs-directory = %s') % explicit_eggs_dir
        elif buildout_default:
            tvars['eggs-dir'] = ''
        else:
            create_buildout_default_file()

        tvars['package_directory'] = os.path.abspath(os.path.join(
                os.getcwd(), tvars['project']))

        include_site_packages = tvars.get('include_site_packages')
        if include_site_packages is None:
            tvars['include_site_packages'] = 'false'

        return tvars

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
        except IOError as _e:
            # Some serious problem: no connect to server...
            print("Error: cannot download required %s" % url)
            print("Server may be down.  Please try again later.")
            sys.exit(1)
        print(f"{url} = [{contents.decode('ISO-8859-1')}]")
        return contents.decode("ISO-8859-1")

    def post(self, command, _output_dir, tvars):
        if not tvars['run_buildout']:
            return
        original_dir = os.getcwd()
        os.chdir(tvars['project'])
        run_buildout(command.verbose, tvars['use_distribute'])
        os.chdir(original_dir)
