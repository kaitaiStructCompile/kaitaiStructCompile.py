import typing
from pathlib import Path
from traceback import FrameSummary, StackSummary, TracebackException
from warnings import warn as _warn
from warnings import warn_explicit as _warn_explicit

try:
	from traceback import _some_str
except ImportError:
	from traceback import _safe_string

	def _some_str(value):
		return _safe_string(value, "unprintable")


class KaitaiCompilerException(Exception):
	__slots__ = ()


class KaitaiCompilerWarning(UserWarning):
	__slots__ = ()


class KaitaiStyleGuideViolationWarning(KaitaiCompilerWarning):
	__slots__ = ()


def warn(message: str):
	return _warn(message, KaitaiCompilerWarning, stacklevel=2)


def warnInKSY(mainFile: Path, srcFile: str, message: str, *, line: typing.Optional[int] = None, column: typing.Optional[int] = None, path: typing.Optional[typing.Iterable] = None):
	if "/ksy_style_guide.html" in message:
		wclass = KaitaiStyleGuideViolationWarning
	else:
		wclass = KaitaiCompilerWarning

	mainFile, srcFile, path = _preprocessIssue(mainFile, srcFile, path)

	if line is None:
		if path:
			from .utils import yamlNodeToLineAndColumn

			line, column, unneededEndColumn, unneededEndLine = yamlNodeToLineAndColumn(srcFile, path)

	return _warn_explicit(message, wclass, str(srcFile), line)


class KaitaiCompilerTracebackException(TracebackException):
	def __init__(self, exc):
		exc_type = type(exc)
		self.stack = self.toStackSummary()
		self.exc_type = self.__class__
		self._str = _some_str(exc)
		#cause = exc.getCause()
		#if cause:
		#	self.__cause__ = self.__class__(cause)
		#else:
		#	self.__cause__ = None
		self.__cause__ = None
		self.__context__ = None
		self.exc_traceback = True

	@classmethod
	def fromException(cls, exc, *args, **kwargs):
		return cls(exc, *args, **kwargs)


class ICompileIssue(KaitaiCompilerException):
	__slots__ = ("msg", "srcFile")

	def __init__(self, srcFile: Path, msg: str):
		self.srcFile = srcFile
		self.msg = msg

	def stacktrace(self):
		return "".join(l for l in KaitaiCompilerTracebackException(self).format())

	def toStackSummary(self):
		res = []
		for el in stack_trace:
			fn = self.srcFile
			if fn:
				fn = str(fn)
			else:
				fn = None
			res.append(FrameSummary(fn, self.line, ".".join(self.path), lookup_line=False, locals=None, line=None))
		res = StackSummary.from_list(res)
		return res


class YamlSyntaxError(ICompileIssue):
	__slots__ = ("line", "column")

	def __init__(self, srcFile: Path, msg: str, line: int, column: int):
		super().__init__(srcFile, msg)
		self.line = line
		self.column = column

	@property
	def path(self):
		return ()


class SemanticError(ICompileIssue):
	__slots__ = ("path", "_line", "_column")

	def __init__(self, srcFile: Path, msg: str, path: tuple, line: typing.Optional[int] = None, column: typing.Optional[int] = None):
		super().__init__(srcFile, msg)
		self._line = line
		self._column = column
		self.path = path

	def _ensureRowColPopulated(self):
		if not self._line or not self._column:
			from .utils import yamlNodeToLineAndColumn

			self._line, self._column, unneededEndColumn, unneededEndLine = yamlNodeToLineAndColumn(self.srcFile, self.path)

	@property
	def line(self):
		self._ensureRowColPopulated()
		return self._line

	@property
	def column(self):
		self._ensureRowColPopulated()
		return self._column


def _tryMakeInt(s: str):
	try:
		return int(s)
	except ValueError:
		return s


def _preprocessPath(path: typing.Iterable[str]) -> typing.Iterable[typing.Union[str, int]]:
	return tuple(_tryMakeInt(el) for el in path)


def _preprocessIssue(mainFile: Path, srcFile: str, path: typing.Optional[typing.Iterable[str]]):
	if srcFile == "(main)":
		srcFile = mainFile

	srcFile = Path(srcFile)

	if path:
		path = _preprocessPath(path)

	return mainFile, srcFile, path


def issueFactory(mainFile: Path, srcFile: str, msg: str, *, line: typing.Optional[int] = None, column: typing.Optional[int] = None, path: typing.Optional[typing.Iterable[str]] = None) -> ICompileIssue:
	"""`srcFile` is a `str` because the API sends strs and they are sometimes not valid paths"""

	mainFile, srcFile, path = _preprocessIssue(mainFile, srcFile, path)

	if path:
		return SemanticError(srcFile, msg, path, line, column)

	return YamlSyntaxError(srcFile, msg, line, column)
