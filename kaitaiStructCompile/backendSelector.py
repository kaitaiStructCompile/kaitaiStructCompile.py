import typing
import warnings
from collections import OrderedDict
from itertools import chain
from pathlib import Path

from . import ICompiler as ICompilerModule
from . import defaults, utils
from .KaitaiCompilerException import KaitaiCompilerException

try:
	from lazy_object_proxy import Proxy as LOProxy
except ImportError:
	LOProxy = None

defaultPriority = 0

ENTRY_POINT_KEY = "kaitai_struct_compile"


try:
	from importlib.metadata import EntryPoint, entry_points

	def _discoverEntryPoints(key: str) -> OrderedDict:
		try:
			return entry_points()[key]
		except KeyError:
			return {}

except ImportError:
	from pkg_resources import EntryPoint, iter_entry_points

	def _discoverEntryPoints(key: str) -> OrderedDict:
		return iter_entry_points(group=key)


class BackendDescriptor:
	__slots__ = ("entryPoint", "name", "prio", "issues")

	def __init__(self, entryPoint: EntryPoint, name: str, prio: int = defaultPriority, issues: set = None) -> None:
		self.entryPoint = entryPoint
		self.name = name
		self.prio = prio
		if issues:
			issues = set(issues)
		self.issues = issues

	@property
	def broken(self) -> bool:
		return self.prio < 0

	def __repr__(self):
		return self.__class__.__name__ + "(" + repr(self.entryPoint) + ")"

	def __call__(self) -> ICompilerModule.ICompiler:
		"""Initializes a backend"""
		init = self.entryPoint.load()
		return init(ICompilerModule, KaitaiCompilerException, utils, defaults)


def recognizeBackends(b: EntryPoint) -> BackendDescriptor:
	if hasattr(b.__class__, "__slots__") and "metadata" in b.__class__.__slots__:
		metadata = b.metadata
	else:
		backendName = b.name
		encoded = backendName.split("@", 1)
		backendName = encoded[0]
		if len(encoded) > 1:
			try:
				metadata = utils.json.loads(encoded[1])
			except BaseException:
				warnings.warn("Entry point " + repr(b) + " is invalid. The value after @ must be must be a valid JSON!.")
				return BackendDescriptor(b, backendName, prio=-1)  # broken, so not using
		else:
			metadata = None

	if metadata is not None:
		if isinstance(metadata, int):
			return BackendDescriptor(b, backendName, prio=metadata)  # it is priority
		elif isinstance(metadata, dict):
			return BackendDescriptor(b, backendName, **metadata)
		else:
			warnings.warn("Entry point " + repr(b) + " is invalid. The value after @ must be must be either a dict, or a number!.")
			return BackendDescriptor(b, backendName, prio=-1)  # broken, so not using
	else:
		return BackendDescriptor(b, backendName)


def discoverOurEntryPoints():
	return _discoverEntryPoints(ENTRY_POINT_KEY)


def entryPointsIntoBackends(pts: typing.Iterable[EntryPoint]):
	backendsList = sorted(filter(lambda b: not b.broken, map(recognizeBackends, pts)), key=lambda b: b.prio, reverse=True)
	return OrderedDict(((b.name, b) for b in backendsList))


def discoverBackends() -> OrderedDict:
	return entryPointsIntoBackends(discoverOurEntryPoints())


if LOProxy:
	discoveredBackends = LOProxy(discoverBackends)
else:
	discoveredBackends = discoverBackends()
	print(discoveredBackends)


def iterateSuitableBackends(tolerableIssues=None, backendsPresent: typing.Mapping[str, BackendDescriptor] = None, forcedBackend=None, debugPrint: bool = False) -> typing.Iterator[BackendDescriptor]:
	"""Iterates suitable backends. Suitability is determined by the arguments."""

	if backendsPresent is None:
		backendsPresent = discoveredBackends
	if tolerableIssues is None:
		tolerableIssues = utils.getTolerableIssuesFromEnv()

	if debugPrint:
		print("Tolerable issues:", sorted(tolerableIssues))

	if forcedBackend is None:
		forcedBackend = utils.getForcedBackendFromEnv()

	if forcedBackend:
		backendsPresent = {forcedBackend: backendsPresent[forcedBackend]}

	for b in backendsPresent.values():
		if debugPrint:
			print("Considering backend", b)
		if b.issues:
			disqualified = b.issues - tolerableIssues
			if disqualified:
				if debugPrint:
					print("Backend", b, "disqualified because of ", disqualified)
				continue

		yield b


def selectAndInitializeBackend(tolerableIssues=None, backendsPresent: typing.Mapping[str, BackendDescriptor] = None, forcedBackend=None, debugPrint: bool = False) -> typing.Optional[ICompilerModule.ICompiler]:
	"""Selects and initializes the first suitable backend from the all available."""

	for b in iterateSuitableBackends(tolerableIssues=tolerableIssues, backendsPresent=backendsPresent, forcedBackend=forcedBackend, debugPrint=debugPrint):
		try:
			return b()
		except Exception as ex:
			warnings.warn(repr(ex) + " when loading backend " + b.entryPoint.name)
			pass

if LOProxy:
	ChosenBackend = LOProxy(selectAndInitializeBackend)
else:
	ChosenBackend = selectAndInitializeBackend()
