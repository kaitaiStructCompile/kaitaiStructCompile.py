from pathlib import Path

from ..utils import json

thisDir = Path(__file__).parent
schemasDir = thisDir / "schemas"
with (schemasDir / "config.schema.json").open("rt", encoding="utf-8") as f:
	schema = json.load(f)


def isPath(val):
	if isinstance(val, Path):
		return True
	elif isinstance(val, str):
		try:
			Path(val)
		except BaseException:
			return False
	return False
