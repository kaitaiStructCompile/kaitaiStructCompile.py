__all__ = ("compile", "ChosenBackend")
import typing
from pathlib import Path

from .backendSelector import ChosenBackend
from .ICompiler import ICompiler, ICompileResult, PostprocessResult


def compile(ksyFiles: typing.Union[Path, str, typing.Iterable[Path]], outputDir: Path = None, progressCallback=None, dirs=None, additionalFlags: typing.Tuple[str] = (), namespaces=None, backend: typing.Optional[typing.Type[ICompiler]] = None, **kwargs) -> typing.Dict[str, ICompileResult]:
	if isinstance(ksyFiles, str):
		ksyFiles = Path(ksyFiles)
	if isinstance(ksyFiles, Path):
		ksyFiles = [ksyFiles]

	if namespaces is None:
		namespaces = {"python": "."}

	if backend is None:
		backend = ChosenBackend

	compiler = backend(progressCallback=progressCallback, dirs=dirs, additionalFlags=(), namespaces=namespaces)

	if outputDir is None:
		needInMemory = True

	return compiler.compile(ksyFiles, outputDir, additionalFlags=additionalFlags, needInMemory=False, **kwargs)
