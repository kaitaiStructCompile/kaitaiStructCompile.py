import ast
import types
import typing
from enum import IntEnum
from pathlib import Path, PurePath

from .defaults import subDirsNames
from .KaitaiCompilerException import KaitaiCompilerException, issueFactory, warnInKSY
from .utils import KSCDirs


class ICompileResult:
	__slots__ = ("msg", "moduleName", "mainClassName", "sourcePath", "path")

	def __init__(self, moduleName: str, mainClassName: str, msg: str, sourcePath=None, path: typing.Optional[Path] = None) -> None:
		self.msg = msg
		self.moduleName = moduleName
		self.mainClassName = mainClassName
		self.sourcePath = sourcePath
		self.path = path

	def getText(self) -> str:
		raise NotImplementedError()

	@property
	def needsSave(self):
		raise NotImplementedError()

	def __repr__(self) -> str:
		return self.__class__.__name__ + "<" + ", ".join((self.moduleName, self.mainClassName)) + ">"


class IndexResultsBy(IntEnum):
	"""Used to specify the way in which results are returned."""

	unindexed = 0  # returns an Iterable
	ids = 1
	fileNamesStems = 2


class InMemoryCompileResult(ICompileResult):
	__slots__ = ("text",)

	def __init__(self, moduleName: str, mainClassName: str, msg: str, text: str) -> None:
		super().__init__(moduleName, mainClassName, msg)
		self.text = text

	def getText(self):
		return self.text

	@property
	def needsSave(self):
		return True


class InFileCompileResult(InMemoryCompileResult):
	__slots__ = ("_needsSave",)

	def __init__(self, moduleName: str, mainClassName: str, msg: str, path):
		self._needsSave = False
		super().__init__(moduleName, mainClassName, msg, None)
		self.path = path

	def getText(self):
		if self.text is None:
			with self.path.open("rt", encoding="utf-8") as f:
				self.text = f.read()
		return self.text

	@property
	def needsSave(self):
		return self._needsSave

	def __repr__(self) -> str:
		return self.__class__.__name__ + "<" + repr(self.path) + ">"


class WrappedResult(ICompileResult):
	__slots__ = ("wrapped",)

	def __init__(self, wrapped: ICompileResult) -> None:
		self.wrapped = wrapped

	def getText(self) -> str:
		return self.wrapped.getText()

	@property
	def msg(self):
		return self.wrapped.msg

	@property
	def moduleName(self):
		return self.wrapped.moduleName

	@property
	def mainClassName(self):
		return self.wrapped.mainClassName

	@property
	def sourcePath(self):
		return self.wrapped.sourcePath

	@property
	def path(self):
		return self.wrapped.path

	@property
	def needsSave(self):
		return self.wrapped.needsSave

	def __repr__(self) -> str:
		return self.__class__.__name__ + "(" + repr(self.wrapped) + ")"


class PostprocessResult(WrappedResult):
	__slots__ = ()

	def __init__(self, wrapped: ICompileResult, postprocessingTasks: typing.Mapping[str, typing.Iterable[typing.Any]]) -> None:
		super().__init__(wrapped)
		path = self.path if self.path else "<KS in-memory result>"
		ppi = tuple(postprocessingTasks.items())
		for i, (postprocessor, args) in enumerate(ppi):
			text = postprocessor(self.getText(), path, *args)
			self.wrapped = InMemoryCompileResult(moduleName=wrapped.moduleName, mainClassName=wrapped.mainClassName, msg=wrapped.msg, text=text)
			path = "<KS intermediate postprocessed result: " + repr(ppi[: i + 1]) + ">"


class IPrefsStorage:
	def __init__(self, namespaces=None, destDir: str = None, additionalFlags: typing.Iterable[str] = (), importPath=None, verbose: typing.Optional[typing.Iterable[str]] = None, opaqueTypes: typing.Optional[bool] = None, autoRead: typing.Optional[bool] = None, readStoresPos: typing.Optional[bool] = None, target: str = "python"):
		raise NotImplementedError()


class ICompiler:
	__slots__ = ("progressCallback", "dirs", "namespaces", "importPath")

	def __init__(self, progressCallback=None, dirs=None, namespaces=None, importPath: typing.Optional[Path] = None) -> None:
		if progressCallback is None:

			def progressCallback(x):
				return None
				#progressCallback = print

		self.progressCallback = progressCallback

		if dirs is None or isinstance(dirs, str):
			dirs = KSCDirs(subDirsNames, root=dirs)
		self.dirs = dirs

		self.namespaces = namespaces
		self.importPath = importPath

	def prepareSourceFilePath(self, sourceFilePath):
		sourceFilePath = Path(sourceFilePath).absolute()
		if not sourceFilePath.exists():
			raise KaitaiCompilerException("Source file " + str(sourceFilePath) + " doesn't exist")
		return sourceFilePath

	def compile(self, sourceFilesPaths: typing.Iterable[Path], destDir: Path, additionalFlags: typing.Iterable[str] = (), needInMemory: bool = False, target: str = "python", verbose: typing.Optional[typing.Iterable[str]] = None, opaqueTypes: typing.Optional[bool] = None, autoRead: typing.Optional[bool] = None, readStoresPos: typing.Optional[bool] = None) -> typing.Mapping[str, ICompileResult]:
		if destDir is not None:
			destDir = Path(destDir).absolute()
		else:
			# We don't emit a warning here because `needInMemory` is a hint that we prefer avoiding disk writes
			needInMemory = True

		sourceFilesPaths = [self.prepareSourceFilePath(p) for p in sourceFilesPaths]
		return self.compile_(sourceFilesAbsPaths=sourceFilesPaths, destDir=destDir, additionalFlags=additionalFlags, verbose=verbose, opaqueTypes=opaqueTypes, autoRead=autoRead, readStoresPos=readStoresPos, needInMemory=needInMemory, target=target)

	def compile_(self, sourceFilesAbsPaths: typing.Iterable[Path], destDir: Path, additionalFlags: typing.Iterable[str], needInMemory: bool, target: str, verbose, opaqueTypes, autoRead, readStoresPos) -> typing.Iterable[ICompileResult]:
		raise NotImplementedError()
