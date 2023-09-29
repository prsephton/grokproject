from __future__ import print_function
import sys
import pkg_resources                    # @UnresolvedImport
from paste.script import command        # @UnresolvedImport
import optparse
import re
from grokproject import GrokProject

project_name_re=re.compile('[A-z_][A-z0-9_]*')

def main(vars=GrokProject.vars, template_name='grok'):
    usage = "usage: %prog [options] PROJECT"
    parser = optparse.OptionParser(usage=usage)
    # parser.add_option(
    #     '--svn-repository', dest="repos", default=None, help=(
    #     "Import project to given repository location (this "
    #     "will also create the standard trunk/ tags/ branches/ "
    #     "hierarchy)."))
    parser.add_option(
        '--version-url', dest="version_url", default=None, help=(
        "Specify the URL to a buildout file defining package versions. "
        "If not given, the latest version info found on the grok website is "
        "used."))
    parser.add_option(
        '-v', '--verbose', action="store_true", dest="verbose", default=False,
        help="Be verbose.")
    parser.add_option(
        '--version', action="store_true", dest="version", default=False,
        help="Show grokproject version.")

    # Options that override the interactive part of filling the templates.
    for var in vars:
        option_name = '--'+var.name.replace('_', '-')
        if not parser.has_option(option_name):
            parser.add_option(
                option_name, dest=var.name,
                help=var.description)

    options, args = parser.parse_args()

    if options.version:
        print(get_version())
        return 0

    if len(args) != 1:
        parser.print_usage()
        return 1

    # create sandbox using paste.script
    project = args[0]
    commands = command.get_commands()
    cmd = commands['create'].load()
    runner = cmd('create')

    option_args = []
    # if options.repos is not None:
    #     option_args.extend(['--svn-repository', options.repos])
    if not options.verbose:
        option_args.append('-q')

    # Process the options that override the interactive part of filling
    # the templates.
    extra_args = []
    for var in vars:
        supplied_value = getattr(options, var.name)
        if supplied_value is not None:
            extra_args.append('%s=%s' % (var.name, supplied_value))
    if options.version_url:
        extra_args.append('version_url=%s' % options.version_url)

    # Assert that the project name is a valid Python identifier.
    if not project_name_re.match(project):
        print
        print("Error: The chosen project name is not a valid " \
              "package name: %s." % project)
        print("Please choose a different project name.")
        sys.exit(1)

    existing = False
    try:
        __import__(project)
        existing = True
    except ImportError:
        pass
    if existing:
        print
        print("Error: The package '%s' is already on sys.path." % project)
        print("Please choose a different project name.")
        sys.exit(1)

    # Create the project.   
    exit_code = runner.run(option_args + ['-t', template_name, project] + extra_args)
    sys.exit(exit_code)

def get_version():
    info = pkg_resources.get_distribution('grokproject')
    if info.has_version and info.version:
        return info.version
    return 'Unknown'
