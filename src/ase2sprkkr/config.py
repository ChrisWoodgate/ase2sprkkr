""" This module contains configuration, that could be changed, preferrably
by .config/ase2sprkkr/__init__.py file"""

import os
import re
from .common.decorators import cache
from .common.grammar_types import CustomMixed, QString, Array, Bool, Keyword, Integer
from .common.container_definitions import SectionDefinition, ConfigurationRootDefinition
from .common.configuration_containers import RootConfigurationContainer
from .common.value_definitions import ValueDefinition as V
import warnings
import shutil
import platformdirs


class Section(SectionDefinition):
    info_in_data_description = True
    dir_common_attributes = False


def _get_suffix(*_):
    return os.environ.get('SPRKKR_EXECUTABLE_SUFFIX','')


def user_preferences_file():
    """ Return filename with user preferences """
    return os.path.join(platformdirs.user_config_dir('ase2sprkkr', 'ase2sprkkr'), '__init__.py')


def load_user_preferences():
    """ Load user defined preferences from
        ``$HOME/.config/ase2sprkkr/__init__.py``
    """
    file = user_preferences_file()

    try:
       if os.path.isfile(file):
           import types
           import importlib.machinery
           loader = importlib.machinery.SourceFileLoader('ase2sprkkr.personal', file)
           mod = types.ModuleType(loader.name)
           loader.exec_module(mod)
    except Exception as e:
        import warnings
        warnings.warn(f'Can not import {file} file with the user preferences: \n{e}')


@cache
def find_default_mpi_runner():
   for r in [ 'mpirun', 'mpirun.opmpirun', 'mpirun.mpich' ]:
       if shutil.which(r):
           return [ r ]
   return False


@cache
def get_default_mpi_runner():

   out = find_default_mpi_runner()
   if out:
       return out
   if config.mpi_warning():
       warnings.warn("No MPI runner found. Disabling MPI!!!")


def mpi_runner(mpi):
    """ Return a shell command to execute a mpi task.

    Parameters
    ----------
    mpi_runner: Union[bool,str,list,int]


      - If True is given, return the default mpi-runner
      - If False is given, no mpi-runner is returned.
      - If 'auto' is given, it is the same as True, however
           * no warning is given if no mpi is found
           * MPI is not used, if only one CPU is available
      - If a string is given, it is interpreted as a list of one item
      - If a list (of strings) is given, the user specified its own runner, use it as is
        as the parameters for subprocess.run.
      - If an integer is given, it is interpreted as the number of
        processes: the default mpi-runner is used, and the parameters
        to specify the number of processes.

    Return
    ------
    mpi_runner: list
      List of strings with the executable and its parameters, e.g.

      ::

          ['mpirun', '-np', '4']
    """
    if mpi is None:
       mpi=config.running.mpi()
    if mpi is False:
       return None
    if mpi is True:
       mpi=find_default_mpi_runner()
    if isinstance(mpi, list):
        return mpi
    if isinstance(mpi, str):
        if mpi == 'auto':
            if hasattr(os, 'sched_getaffinity') and len(os.sched_getaffinity(0))==1:
                return None
            return find_default_mpi_runner()
        return [ mpi ]
    if isinstance(mpi, int):
       return find_default_mpi_runner() + ['-np', str(mpi)]
    return mpi


class Configuration(RootConfigurationContainer):

    def set_permanent(self, name, value, doc=None, doc_regex=False):
        global user_preference_file
        self.set(name, value)

        file = user_preferences_file()
        if not os.path.isfile(file):
            raise ValueError("Please, generate the user prefernce file using 'ase2sprkkr config -d' first.")

        with open(file, 'r+') as f:
            content = f.read()
            pattern=f"(#?\\s*)*config.{name}\\s+="
            if value is None:
                line = ''
                cnt = 0
                last = ''
                if doc:
                    if not doc_regex:
                        pre = re.escape(doc)
                    else:
                        pre = doc
                    pre = f"(?:(?:^|\n)# {pre} *)?"
                else:
                    pre = ''
            else:
                line = f"config.{name} = {value.__repr__()}\n"
                cnt = 1
                pre = ''
                last= f"(?!(.*\n)*{pattern})"
            content, replaced = re.subn(f"{pre}(^|\n){pattern}[^\n]*(\n|$){last}", r'\1' + line, content, cnt)
            if replaced:
                f.seek(0)
                f.write(content)
            elif value is None:
                return
            else:
                i=len(content) - 1
                while i>=0:
                    if content[i] not in ('\r','\n', ' ', '\t'):
                        break
                    i-=1
                f.seek(i + 1)
                if i>0:
                    f.write("\n\n")
                if doc:
                    f.write(f"# {doc}\n")
                f.write(line)
            f.truncate()


class ConfigFileDefinition(ConfigurationRootDefinition):

    dir_common_attributes = False
    result_class = Configuration


""" The definition of ASE2SPRKKR configuration """
definition = ConfigFileDefinition('config', [

  Section('running', [
    V('empty_spheres', Keyword({
      True : 'Always do empty spheres finding.',
      False: 'Newer do empty spheres finding.',
      'auto': 'Do empty spheres finding for unconverged potential not containing any vaccuum atom.'
      }, transform=None), default_value='auto', info="Run empty spheres finding before calculation? Default value ``auto`` means only for SCF calculations not containing any vacuum atom."),
    V('print_output', Keyword({
      True: 'Print all output of SPRKKR executables to screen.',
      False: 'Do not print any output of SPRKKR executables.',
      'info': 'Print only brief information about iterations of SCF cycle.',
    }, transform=None), default_value='info', info="Print output of SPRKKR calculation. Default value ``info`` prints only short info each iteration."),
    V('mpi', CustomMixed(Bool, Array(QString.I), Integer.I), is_optional=True, default_value=None,
             info='Use mpi for calculation? List of strings means yes, use the given strings as mpi runner and its params (e.g. [ "mpirun", "-n", "4" ]). Default None means try to autodetect. Integer number means use the standard runner with a given number of processes.'),
    V('mpi_warning', True, info='Warn, if no MPI is found.')
  ], info='Default values for SPRKKR calculator parameters.'),

  Section('executables', [
    V('suffix', QString.I,
                default_value=_get_suffix,
                info="This suffix is appended (if not stated otherwise) to the SPRKKR "
                     "executable names."),
    V('dir', QString.I, is_optional=True, info='Directory, from which the executables will be runned. None mean use the default environment variable PATH mechanism')
  ], info="Configuration, that affects how the execubables are runned"),

  Section('nomad', [
    V('token', QString.I, info = "Token for NOMAD upload", is_optional=True)
  ])

])

config = definition.create_object()
