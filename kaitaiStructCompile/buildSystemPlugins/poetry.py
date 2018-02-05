import poetry
from cleo.commands.command import Command
from cleo.events.console_command_event import ConsoleCommandEvent
from cleo.events.console_events import COMMAND
from cleo.events.event_dispatcher import EventDispatcher
from cleo.io.io import IO
from poetry.console.application import Application
from poetry.console.commands.build import BuildCommand
from poetry.console.commands.env_command import EnvCommand
from poetry.core.utils.helpers import module_name
from poetry.plugins.application_plugin import ApplicationPlugin
from poetry.plugins.plugin import Plugin
from poetry.poetry import Poetry

from .common import Path, doTranspilationAssummingPyprojectTomlIsInCWD, doTranspilationWithCfgPopulatePathWithCWD, getFromDicHierarchyByPath
from .utils import inspectStackForUnexposedVariables


class KaitaiPoetryCommand(Command):

	name = "kaitai transpile"
	description = "Transpiles Kaitai Struct code present within the package."

	def handle(self) -> int:
		doTranspilationAssummingPyprojectTomlIsInCWD()


class KaitaiPoetryApplicationPlugin(ApplicationPlugin):
	@property
	def commands(self):
		return (KaitaiPoetryCommand,)


poetryDir = Path(poetry.poetry.__file__).absolute().resolve().parent
poetryConsoleDir = Path(poetry.console.__file__).absolute().resolve().parent


def getApplicationObject() -> bool:
	def getApplicationObjectFromStackFrame(i: int, frame: "inspect.FrameInfo", funcFile: Path):
		if funcFile:
			if not funcFile.is_relative_to(poetryDir):
				return False

		# print(frame.function)
		if frame.function == "configure_env":
			if poetryConsoleDir / "application.py" == funcFile:
				cmd = frame.frame.f_locals["self"]
				return cmd

	return inspectStackForUnexposedVariables(getApplicationObjectFromStackFrame, False)


#from icecream import ic

class KaitaiPoetryPlugin(Plugin):
	alreadyInvoked = False

	def activate(self, poetry: Poetry, io: IO) -> None:
		if self.__class__.alreadyInvoked:
			from warnings import warn
			warn("Repeated activation of " + repr(self.__class__) + " `poetry` plugin. Ignored as a workaround to what seems to be a bug in `poetry`. If you need to invoke it again, reset `alreadyInvoked`")
			return

		self.__class__.alreadyInvoked = True
		app = getApplicationObject()
		#ic(self, app._commands, app._get_command_name, app._running_command, app._single_command)
		if isinstance(app._running_command, BuildCommand):
			pyProjectToml = poetry.pyproject.data
			#ic(poetry.package.__class__, poetry.package.build_config, poetry.package.build_script, poetry.package.build_should_generate_setup, poetry.package.files)
			# poetry.package.add_dependency, poetry.package.add_dependency_group
			# poetry.locker
			# lock, lock_data locked_repository, set_lock_data

			pyProjectTomlSection = getFromDicHierarchyByPath(pyProjectToml, ("tool", "kaitai"), None)
			if pyProjectTomlSection:
				doTranspilationWithCfgPopulatePathWithCWD(pyProjectTomlSection.unwrap())
