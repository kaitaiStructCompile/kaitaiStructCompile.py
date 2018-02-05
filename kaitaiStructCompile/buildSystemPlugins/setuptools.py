import json
import os
import warnings
from copy import deepcopy
from distutils.cmd import Command
from importlib import import_module
from pathlib import Path

import setuptools

from .common import _schemaToUserOptions, compoundJsonTypesNames, doTranspilationWithCfg, getFromDicHierarchyByPath, getOurPyprojectTomlSectionFromAFile, prepareCfg, schema, setToDicHierarchyByPath, walkSchemaUserOptions
from .utils import inspectStackForUnexposedVariables

helperInitialized = False


def kaitaiTranspilationNeeded(cmd) -> bool:
	#print("kaitaiTranspilationNeeded", getattr(cmd.distribution, "kaitai", None))
	return bool(getattr(cmd.distribution, "kaitai", None))


def initializeHelper():
	global helperInitialized

	try:
		from setuptools.command.build import build
	except ImportError:
		from distutils.command.build import build

	build.sub_commands.insert(0, ("kaitai_transpile", kaitaiTranspilationNeeded))

	# print("Injected kaitai_transpile into build.sub_commands!")
	helperInitialized = True


def ensureHelperInitialized():
	if not helperInitialized:
		initializeHelper()


def kaitaiHelperSetupPy(dist, keyword, cfg: dict):
	kaitaiCfgInDist = getattr(dist, "kaitai", None)
	if kaitaiCfgInDist is None:
		dist.kaitai = kaitaiCfgInDist = cfg
	else:
		kaitaiCfgInDist.update(cfg)

	ensureHelperInitialized()


class kaitai_transpile(Command):
	description = "Compiles Kaitai Struct specs into code. Not necessarily python one."

	user_options = _schemaToUserOptions(schema)

	def initialize_options(self):
		cfg = deepcopy(getattr(self.distribution, "kaitai", {}))

		def initProp(k, el, prefix):
			path = prefix + (k,)
			propName = "_".join(path)
			v = getFromDicHierarchyByPath(cfg, path)
			if v is None:
				v = el["default"]
			#print("initialize_options", propName, v, el)
			setattr(self, propName, v)

		walkSchemaUserOptions(schema, initProp)
		prepareCfg(cfg)
		self.distribution.kaitai = cfg

	def finalize_options(self):
		cfg = deepcopy(getattr(self.distribution, "kaitai", {}))

		def setOptBack(k, el, prefix):
			path = prefix + (k,)
			propName = "_".join(path)

			rT = el.get("type", None)
			if rT:
				v = getattr(self, propName)
				#print("setOptBack", propName, getFromDicHierarchyByPath(cfg, path), v, el)
				if isinstance(rT, str) and rT in compoundJsonTypesNames and isinstance(el, str):
					v = json.loads(v)
				setToDicHierarchyByPath(cfg, path, v)

		walkSchemaUserOptions(schema, setOptBack)

		prepareCfg(cfg)
		self.distribution.kaitai = cfg

	def run(self):
		return doTranspilationWithCfg(getattr(self.distribution, "kaitai", None))


def getPyprojectTomlPath(dist):
	inis, tomls = dist._get_project_config_files(None)
	if tomls:
		return tomls[0]


setuptoolsDir = Path(setuptools.__file__).absolute().resolve().parent


def getDistributionObject() -> bool:  # DO NOT DELETE!!!!
	"""Returns the distribution object. While it is currently provided out of the box, this code may be useful in future, if anything breaks again"""

	cwd = Path(".").absolute().resolve()

	def getSetuptoolsDistObjectFromStack(i, f, funcFile):
		if f.function == "finalize_options":
			if setuptoolsDir / "dist.py" == funcFile:
				dist = f.frame.f_locals["self"]
				return dist

	return inspectStackForUnexposedVariables(getSetuptoolsDistObjectFromStack, None)


def isBuildingAWheel() -> bool:
	cwd = Path(".").absolute().resolve()

	def isSetuptoolsBuildWheelOnStack(i, f, funcFile):
		if funcFile:
			if funcFile.is_relative_to(cwd):
				return None  # It is likely `setup.py` or a custom build backend or its plugin

			if not funcFile.is_relative_to(setuptoolsDir):
				return False

		# print(f.function)
		if f.function == "build_wheel":
			if setuptoolsDir / "build_meta.py" == funcFile:
				return True

	return inspectStackForUnexposedVariables(isSetuptoolsBuildWheelOnStack, False)


def kaitaiHelperPyProjectToml(dist: setuptools.dist.Distribution, pyProjectTomlSection: dict = None, entryPoint: str = None, src_root: Path = None) -> None:
	if entryPoint is None:
		#warnings.warn("You version of setuptools is missing facilities for requesting additional data by plugins, (https://github.com/pypa/setuptools/pull/2034), working around ...")
		entryPointName = "tool.kaitai"
	else:
		entryPointName = entryPoint.name

	tomlFile = None

	bw = isBuildingAWheel()
	if not bw:
		return

	if src_root is None:
		src_root = dist.src_root
		if src_root is None:
			src_root = Path(".")  # PEP 617 backends set cwd to the package root

	src_root = src_root.absolute().resolve()

	if pyProjectTomlSection is None:
		tomlFile = getPyprojectTomlPath(dist)
		if tomlFile is not None:
			if tomlFile.is_file():
				pyProjectTomlSection = getOurPyprojectTomlSectionFromAFile(tomlFile)
		else:
			return  # bullshit called by virtualenv

	if pyProjectTomlSection is not None:
		if "prefixPath" not in pyProjectTomlSection:
			pyProjectTomlSection["prefixPath"] = src_root

		dist.kaitai = pyProjectTomlSection
		kaitaiHelperSetupPy(dist, "kaitai", dist.kaitai)
