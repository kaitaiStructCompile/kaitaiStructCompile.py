from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.plugin import hookimpl

from .common import doTranspilationAssummingPyprojectTomlIsInCWD


class KaitaiHatchlingPlugin(BuildHookInterface):
	PLUGIN_NAME = "kaitai_transpile"

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

	def initialize(self, version, build_data):
		if self.target_name != "wheel":
			return

		emittedFiles = doTranspilationAssummingPyprojectTomlIsInCWD()
		fi = build_data["force_include"]
		cwd = Path(".").absolute().resolve()
		for res, pth in emittedFiles:
			rp = pth.relative_to(cwd)
			fi[rp] = rp


@hookimpl
def hatch_register_build_hook():  # this must be exactly `hatch_register_build_hook`
	return KaitaiHatchlingPlugin
