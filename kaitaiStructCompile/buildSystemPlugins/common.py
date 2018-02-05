import os
import typing
import warnings
from copy import deepcopy
from importlib import import_module
from pathlib import Path

from ..backendSelector import selectAndInitializeBackend
from ..colors import styles
from ..ICompiler import InFileCompileResult, InMemoryCompileResult, PostprocessResult
from ..postprocessors import postprocessors
from ..schemas import schema
from ..utils import getTolerableIssuesFromEnv

try:
	from ..schemas.validators import validator
except ImportError as ex:
	validator = None
	warnings.warn("Cannot import kaitaiStructCompile.schemas: " + str(ex) + " . Skipping JSONSchema validation...")


def empty(o, k):
	return k not in o or not o[k]


def prepareFdir(repoURI, refspec, fdir):
	if empty(fdir, "update"):
		fdir["update"] = schema["definitions"]["formatsRepoRefspec"]["properties"]["update"]["default"]

	if empty(fdir, "git"):
		if not repoURI:
			repoURI = schema["definitions"]["formatsRepoRefspec"]["properties"]["git"]["default"]

		fdir["git"] = repoURI

	if empty(fdir, "refspec"):
		if not refspec:
			refspec = schema["definitions"]["formatsRepoRefspec"]["properties"]["refspec"]["default"]

		fdir["refspec"] = refspec

	if empty(fdir, "localPath"):
		if fdir["update"]:
			localDirName = os.path.basename(fdir["git"])
			a = os.path.splitext(localDirName)
			if len(a) > 1 and a[-1] == ".git":
				localDirName = a[0]

			fdir["localPath"] = Path(".") / localDirName
		else:
			fdir["localPath"] = None


def prepareCompilerFlags(flags):
	if empty(flags, "additionalFlags"):
		flags["additionalFlags"] = schema["definitions"]["additionalFlags"]["default"]
		if empty(flags, "namespaces"):
			flags["namespaces"] = schema["definitions"]["namespacesSpec"]["default"]


def preparePathInCfg(cfg, schema, propName: str, prefixPath: Path) -> Path:
	res = cfg.get(propName, schema["definitions"][propName]["default"])

	if res is not None:
		if not isinstance(res, Path):
			if prefixPath is not None:
				res = prefixPath / res

	cfg[propName] = res
	return res


def prepareCfg(cfg):
	if empty(cfg, "postprocessors"):
		cfg["postprocessors"] = type(postprocessors)(postprocessors)

	if empty(cfg, "tolerableIssues"):
		cfg["tolerableIssues"] = schema["properties"]["tolerableIssues"]["default"]

	if empty(cfg, "forceBackend"):
		cfg["forceBackend"] = schema["properties"]["forceBackend"]["default"]

	if empty(cfg, "kaitaiStructRoot"):
		cfg["kaitaiStructRoot"] = schema["properties"]["kaitaiStructRoot"]["default"]

	if "search" not in cfg:
		cfg["search"] = schema["definitions"]["search"]["default"]

	if empty(cfg, "flags"):
		cfg["flags"] = {}

	prefixPath = preparePathInCfg(cfg, schema, "prefixPath", Path("."))
	defaultOutputDir = preparePathInCfg(cfg, schema, "outputDir", prefixPath)

	defaultLocalPath = preparePathInCfg(cfg, schema, "localPath", prefixPath)
	defaultInputDir = preparePathInCfg(cfg, schema, "inputDir", defaultLocalPath)

	prepareCompilerFlags(cfg["flags"])

	if validator is not None:
		validator.check_schema(cfg)
		validator.validate(cfg)

	repos = cfg["repos"]

	for repoURI, repoCfg in repos.items():
		for refspec, repoRefspecCfg in repoCfg.items():
			prepareFdir(repoURI, refspec, repoRefspecCfg)

			if "search" not in repoRefspecCfg:
				repoRefspecCfg["search"] = cfg["search"]

			if "postprocessors" not in repoRefspecCfg:
				repoRefspecCfg["postprocessors"] = cfg["postprocessors"]

			localPath = preparePathInCfg(repoRefspecCfg, schema, "localPath", prefixPath)
			if not localPath:
				localPath = repoRefspecCfg["localPath"] = defaultLocalPath

			if not isinstance(localPath, Path):
				raise ValueError("localPath must be set. At least either in the config root, or in per-refspec-config. The easiest way to resolve this issue is to set it into `kaitai_struct_formats` in the root. I refuse to set it for you, you must determine yourself where it is appropriate to keep it for your project.")

			preparePathInCfg(repoRefspecCfg, schema, "inputDir", localPath)  # side effect, sets into repoRefspecCfg
			if not repoRefspecCfg["inputDir"]:
				if defaultInputDir is None:
					repoRefspecCfg["inputDir"] = localPath
				else:
					repoRefspecCfg["inputDir"] = defaultInputDir

			preparePathInCfg(repoRefspecCfg, schema, "outputDir", prefixPath)  # side effect, sets into repoRefspecCfg
			if not repoRefspecCfg["outputDir"]:
				if defaultOutputDir is None:
					repoRefspecCfg["outputDir"] = repoRefspecCfg["inputDir"]
				else:
					repoRefspecCfg["outputDir"] = defaultOutputDir

	#prepareFormats(cfg)

	if validator is not None:
		validator.check_schema(cfg)
		validator.validate(cfg)


def scanForKsys(repoRefspecCfg) -> None:
	if repoRefspecCfg["search"]:
		for file in repoRefspecCfg["inputDir"].glob("**/*.ksy"):
			repoRefspecCfg["formats"][repoRefspecCfg["outputDir"] / file.parent.relative_to(repoRefspecCfg["inputDir"]) / (file.stem + ".py")] = {"path": file}


def prepareFormats(repoRefspecCfg) -> None:
	scanForKsys(repoRefspecCfg)

	formats = repoRefspecCfg["formats"]
	iD = repoRefspecCfg["inputDir"]
	oD = repoRefspecCfg["outputDir"]
	newFormats = type(formats)(formats)

	for target, descriptor in formats.items():
		if not isinstance(target, Path):
			del newFormats[target]
			newFormats[oD / target] = descriptor
	formats = newFormats

	for target, descriptor in formats.items():
		if not isinstance(descriptor["path"], Path):
			fp = iD / descriptor["path"]
			if not fp.is_file() and isinstance(descriptor["path"], str) and not descriptor["path"].endswith(".ksy"):
				fpFixed = iD / (descriptor["path"] + ".ksy")
				if fpFixed.is_file():
					fp = fpFixed

			formats[target]["path"] = fp

	repoRefspecCfg["formats"] = formats


def getFromDicHierarchyByPath(dic, path: typing.Iterable[str], default=None):
	cur = dic

	for comp in path:
		cur = cur.get(comp, None)
		if cur is None:
			return default

	return cur


def setToDicHierarchyByPath(dic, path: typing.Iterable[str], v: typing.Any):
	cur = dic

	try:
		for comp in path[:-1]:
			cur1 = cur.get(comp, None)
			if cur1 is None:
				cur1 = cur[comp] = {}
			cur = cur1

		cur[path[-1]] = v
	except BaseException:
		#print("setToDicHierarchyByPath error:", path, v)
		raise


def decodeRef(refAddr: str):
	if refAddr[0:2] != "#/":
		raise ValueError
	return refAddr[2:].split("/")


def getSchemaItemByRef(refStr: str):
	path = decodeRef(refStr)
	return getFromDicHierarchyByPath(schema, path)


def walkSchemaUserOptions(schema, callback, prefix: tuple = ()):
	if not schema:
		return

	for k, v in schema.get("properties", {}).items():
		ref = v.get("$ref", None)
		if ref:
			item = getSchemaItemByRef(ref)
			walkSchemaUserOptions(item, callback, prefix + (k,))
		else:
			rT = v.get("type", None)
			if rT:
				if rT == "object":
					walkSchemaUserOptions(v, callback, prefix + (k,))
				else:
					callback(k, v, prefix)


def _schemaToUserOptions(schema):
	res = []

	def appendOpt(k, v, prefix):
		res.append((
			"-".join(prefix + (k,)),
			None,
			v.get("description", None)
		))

	walkSchemaUserOptions(schema, appendOpt)

	return res


compoundJsonTypesNames = {"array", "object"}


def doTranspilationWithCfg(cfg):
	emittedFiles = []
	if not cfg:
		return

	prefixPath = cfg["prefixPath"]

	def pathToPrettyString(p: Path) -> str:
		return str(p.relative_to(prefixPath))

	# `repoUnneeded` is unneeded, we have migrated it into `git` property
	for repoUnneeded, repoCfg in cfg["repos"].items():
		# `refspecUnneeded` is unneeded, we have migrated it into `refspec` property
		for refspecUnneeded, repoRefSpecCfg in repoCfg.items():
			if repoRefSpecCfg["update"]:
				from .repo import upgradeLibrary

				upgradeLibrary(repoRefSpecCfg["localPath"], repoRefSpecCfg["git"], repoRefSpecCfg["refspec"], print, prefixPath=prefixPath)

			prepareFormats(repoRefSpecCfg)

			ChosenBackend = selectAndInitializeBackend(tolerableIssues=set(cfg["tolerableIssues"]) | getTolerableIssuesFromEnv(), forcedBackend=cfg["forceBackend"])
			print(styles["operationName"]("Using backend") + ":", styles["info"](str(ChosenBackend.__name__)))
			compiler = ChosenBackend(progressCallback=print, dirs=cfg["kaitaiStructRoot"], **cfg["flags"], importPath=repoRefSpecCfg["localPath"])

			os.makedirs(pathToPrettyString(repoRefSpecCfg["outputDir"]), exist_ok=True)
			for compilationResultFilePath, targetDescr in repoRefSpecCfg["formats"].items():
				if "flags" not in targetDescr:
					targetDescr["flags"] = {}

				print(styles["operationName"]("Compiling") + " " + styles["ksyName"](pathToPrettyString(targetDescr["path"])) + " into " + styles["resultName"](pathToPrettyString(compilationResultFilePath)) + " ...")

				compileResults = compiler.compile([targetDescr["path"]], repoRefSpecCfg["outputDir"], additionalFlags=targetDescr["flags"])
				# print(compileResults)

				print(styles["operationName"]("Postprocessing") + " " + styles["resultName"](pathToPrettyString(compilationResultFilePath)) + " ...")

				for moduleName, res in compileResults.items():
					print("targetDescr", targetDescr)
					if "postprocess" in targetDescr:
						pp = targetDescr["postprocess"]
						if not hasattr(pp, "items"):
							pp = {el: () for el in pp}

						res = PostprocessResult(res, {repoRefSpecCfg["postprocessors"][funcName]: args for funcName, args in pp.items()})

					if isinstance(res, InFileCompileResult):
						savePath = res.path
					else:
						savePath = (compilationResultFilePath.parent / (moduleName + ".py")).absolute()

					print("res.needsSave", res.needsSave, savePath)
					if res.needsSave:
						with savePath.open("wt", encoding="utf-8") as f:
							f.write(res.getText())
					else:
						pass  # TODO: find out if we need to move files
					emittedFiles.append((res, savePath))

	return emittedFiles


def doTranspilationWithCfgPopulatePathWithCWD(cfg):
	if cfg.get("prefixPath", None) is None:
		cfg["prefixPath"] = Path(".").absolute().resolve()

	prepareCfg(cfg)
	return doTranspilationWithCfg(cfg)


def loadPyprojectTomlFile(tomlFile: Path) -> typing.MutableMapping:
	try:
		import tomllib
	except ImportError:
		import tomli as tomllib

	with tomlFile.open("rb") as f:
		return tomllib.load(f)


def loadOurPyprojectTomlSection(pyProjectToml: typing.Mapping) -> typing.Optional[typing.Mapping]:
	return getFromDicHierarchyByPath(pyProjectToml, ("tool", "kaitai"), None)


def getOurPyprojectTomlSectionFromAFile(tomlFile: Path):
	return loadOurPyprojectTomlSection(loadPyprojectTomlFile(tomlFile))


def doTranspilationWithCfgPopulatePathWithCWDWithPyprojectTomlFile(tomlFile: Path):
	return doTranspilationWithCfgPopulatePathWithCWD(getOurPyprojectTomlSectionFromAFile(tomlFile))


def doTranspilationAssummingPyprojectTomlIsInCWD():
	return doTranspilationWithCfgPopulatePathWithCWDWithPyprojectTomlFile(Path(".") / "pyproject.toml")
