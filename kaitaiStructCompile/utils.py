import os
import shutil
import typing
import warnings
from pathlib import Path

from .defaults import compilerName

try:
	import mujson as json
except ImportError:
	try:
		import ujson as json
	except BaseException:
		import json

KS_ENV_PREFIX = "KAITAI_STRUCT_"
ENV_PREFIX = KS_ENV_PREFIX + "COMPILE_"


def getKSCRoot() -> Path:
	varName = KS_ENV_PREFIX + "ROOT"
	p = os.getenv(varName, default=None)
	if not p:
		p = shutil.which(compilerName)
		if p:
			p = Path(p).resolve().absolute().parent.parent
	if not p:
		p = Path(".") / compilerName
		warnings.warn("`" + varName + "` env variable was neither set, nor the compiler available in PATH. Defaulting to '" + str(p) + "' ('" + str(p.absolute()) + "')")
		return p
	else:
		return Path(p)


def getTolerableIssuesFromEnv() -> typing.Set[str]:
	varName = ENV_PREFIX + "TOLERATE_ISSUES"
	issStr = os.getenv(varName, default="")
	return set(issStr.split(","))


def getForcedBackendFromEnv() -> str:
	varName = ENV_PREFIX + "FORCE_BACKEND"
	return os.getenv(varName, default="")


def getAdditionalBackendEntryPointSources() -> str:
	varName = ENV_PREFIX + "ADDITIONAL_BACKEND_ENTRY_POINTS"
	return os.getenv(varName, default="").splitlines()


class KSCDirs:
	def __init__(self, subDirsNames: typing.Dict[str, str], root=None) -> None:
		if root is None:
			root = getKSCRoot()
		self.root = Path(root)
		self.subDirsNames = subDirsNames

	def __getattr__(self, key: str) -> Path:
		return self.root / self.subDirsNames[key]

	def __hasattr__(self, key):
		return key in self.subDirsNames


def empty(o, k):
	return k not in o or not o[k]


def walkPathInMappingsTree(path: typing.Iterable[typing.Any], tree: typing.MutableMapping[typing.Any, typing.Any]) -> typing.Any:
	current = tree
	for c in path:
		try:
			current = current[c]
		except KeyError:
			return None

	return current


def yamlNodeToLineAndColumn(filePath: Path, path: typing.Tuple[typing.Union[int, str]]) -> (int, int, int, int):
	from ruamel.yaml import YAML

	y = YAML(typ="rt")
	with filePath.open("rt") as f:
		d = y.load(f)

	# Working around issue with nonexistent `\id` in instances https://github.com/kaitai-io/kaitai_struct/issues/920
	if len(path) >= 3:
		if path[-1] == "id" and path[-3] == "instances":
			path = path[:-1]

	return walkPathInMappingsTree(path[:-1], d).lc.data[path[-1]]


def transformName(name: str, isClass: bool = False):
	"""Transforms a name as KSC transforms it for python language"""
	if isClass:

		def capitalizeFirstLetter(word):
			return word[0].upper() + word[1:]

		return "".join((capitalizeFirstLetter(p) for p in name.split("_")))
	else:
		return name


def selectRights(st: os.stat_result, uid: int, gid: int) -> int:
	"""Computes rwx single triple effective rights based on files permissions, current user and its group"""
	rights = st.st_mode & 7  # nobody
	if gid == st.st_gid:
		rights |= (st.st_mode >> 3) & 7  # group
	if uid == st.st_uid:
		rights |= (st.st_mode >> 6) & 7  # owner
	return rights


assert selectRights(os.stat_result((0o421, 0, 0, 1, 101, 101, 0, 0, 0, 0)), 101, 101) == 7
assert selectRights(os.stat_result((0o400, 0, 0, 1, 101, 101, 0, 0, 0, 0)), 101, 101) == 4
assert selectRights(os.stat_result((0o020, 0, 0, 1, 101, 101, 0, 0, 0, 0)), 101, 101) == 2
assert selectRights(os.stat_result((0o001, 0, 0, 1, 101, 101, 0, 0, 0, 0)), 101, 101) == 1

assert selectRights(os.stat_result((0o421, 0, 0, 1, 1, 101, 0, 0, 0, 0)), 101, 101) == 3
assert selectRights(os.stat_result((0o400, 0, 0, 1, 1, 101, 0, 0, 0, 0)), 101, 101) == 0
assert selectRights(os.stat_result((0o020, 0, 0, 1, 1, 101, 0, 0, 0, 0)), 101, 101) == 2
assert selectRights(os.stat_result((0o001, 0, 0, 1, 1, 101, 0, 0, 0, 0)), 101, 101) == 1

assert selectRights(os.stat_result((0o421, 0, 0, 1, 101, 1, 0, 0, 0, 0)), 101, 101) == 5
assert selectRights(os.stat_result((0o400, 0, 0, 1, 101, 1, 0, 0, 0, 0)), 101, 101) == 4
assert selectRights(os.stat_result((0o020, 0, 0, 1, 101, 1, 0, 0, 0, 0)), 101, 101) == 0
assert selectRights(os.stat_result((0o001, 0, 0, 1, 101, 1, 0, 0, 0, 0)), 101, 101) == 1

assert selectRights(os.stat_result((0o421, 0, 0, 1, 1, 1, 0, 0, 0, 0)), 101, 101) == 1
assert selectRights(os.stat_result((0o400, 0, 0, 1, 1, 1, 0, 0, 0, 0)), 101, 101) == 0
assert selectRights(os.stat_result((0o020, 0, 0, 1, 1, 1, 0, 0, 0, 0)), 101, 101) == 0
assert selectRights(os.stat_result((0o001, 0, 0, 1, 1, 1, 0, 0, 0, 0)), 101, 101) == 1


def computePermissionsEffectiveForAFileForAUser(file: Path) -> int:
	"""Computes rights for a current user for a file. If a file is a link, a user needs rights to both link and file."""
	gid = os.getegid()
	uid = os.geteuid()

	linkRights = selectRights(file.lstat(), uid, gid)
	fileRights = selectRights(file.stat(), uid, gid)
	return linkRights & fileRights


def checkPermissions(file: Path, neededRights: int) -> bool:
	"""Returns True if `neededRights` match file mode based permissions for current file for current user"""
	return (neededRights & computePermissionsEffectiveForAFileForAUser(file)) == neededRights
