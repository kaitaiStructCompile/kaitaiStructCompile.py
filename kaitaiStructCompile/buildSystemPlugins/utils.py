import typing
from pathlib import Path

thisPackageDir = Path(__file__).parent.parent


def skipCurrentPackageFromStackFrameAndProvideAbsolutePaths(stack):
	for f in stack:
		if f.filename and f.filename[0] == "<":
			funcFile = None
		else:
			funcFile = Path(f.filename).absolute().resolve()

			if funcFile.is_relative_to(thisPackageDir):
				continue

		yield f, funcFile


def inspectStackForUnexposedVariables(lam: typing.Callable[[int, "inspect.FrameInfo", Path], typing.Any], defaultValue: typing.Any) -> typing.Any:
	"""Goes back by stack and fetches the needed unexposed variables from needed modules"""
	import inspect

	s = inspect.stack()
	s = s[1:]

	setuptoolsFrameFound = None
	for i, (f, funcFile) in enumerate(skipCurrentPackageFromStackFrameAndProvideAbsolutePaths(s)):
		res = lam(i, f, funcFile)
		if res is not None:
			return res

	return defaultValue
