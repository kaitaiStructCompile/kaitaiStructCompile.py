import ast
import re
import typing
from pathlib import Path

from .utils import walkPathInMappingsTree

permissiveDecodingRx = re.compile("\\.decode\\((u?)([\"'])([\\w-]+)(\\2)\\)")


def permissiveDecoding(fileText: str, fileName: typing.Union[str, Path]) -> str:
	return permissiveDecodingRx.sub('.decode(\\1\\2\\3\\2, errors="ignore")', fileText)


class RewriteEnumIntoIntEnum(ast.NodeTransformer):
	__slots__ = ("registeredEnums", "registeredEnumVars", "rewriteFrom", "rewriteTo")

	def __init__(self):
		self.registeredEnums = {}
		self.registeredEnumVars = {}
		self.rewriteFrom = "Enum"
		self.rewriteTo = "IntEnum"
		self.currentPath = []

	def visit_ImportFrom(self, node):
		if node.module == "enum":
			for al in node.names:
				if al.name == self.rewriteFrom:
					al.name = self.rewriteTo
		return self.generic_visit(node)

	def registerEnum(self, enumNode):
		self.registerMember(self.registeredEnums, enumNode.name, enumNode)

	def registerEnumVariable(self, enumVarNodeName, payload):
		self.registerMember(self.registeredEnumVars, enumVarNodeName, payload)

	def registerMember(self, trie, memberName, payload):
		current = trie
		for c in self.currentPath:
			try:
				current = current[c]
			except KeyError:
				newSubItem = {}
				current[c] = newSubItem
				current = newSubItem

		current[memberName] = payload

	def getPathFromAttrNode(self, node):
		path = []
		current = node
		while isinstance(current, ast.Attribute):
			path.append(current.attr)
			current = current.value
		else:
			if isinstance(current, ast.Name):
				path.append(current.id)
			else:
				return None
		path.reverse()
		return tuple(path)

	def visit_Assign(self, node):
		if len(node.targets) == 1:
			t = node.targets[0]
			c = node.value
			if isinstance(c, ast.Call) and isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self" and isinstance(c.func, ast.Attribute) and isinstance(c.func.value, ast.Name) and c.func.value.id == "KaitaiStream" and c.func.attr == "resolve_enum":
				varName = t.attr
				if len(c.args) >= 2:
					a = c.args[0]
					if isinstance(a, ast.Attribute):
						p = self.getPathFromAttrNode(a)
						if p:
							self.registerEnumVariable(varName, p)
		return self.generic_visit(node)

	def lookupPathInEnums(self, path):
		return walkPathInMappingsTree(path, self.registeredEnums)

	def lookupPathInEnumVars(self, path):
		return walkPathInMappingsTree(path, self.registeredEnumVars)

	def visit_ClassDef(self, node):
		if len(node.bases) == 1 and node.bases[0].id == self.rewriteFrom:
			self.registerEnum(node)
			node.bases[0].id = self.rewriteTo

		self.currentPath.append(node.name)
		res = self.generic_visit(node)
		self.currentPath.pop()
		return res

	def visit_Attribute(self, node):
		path = self.getPathFromAttrNode(node)
		if path:
			if path[-1] == "value":
				path = path[:-1]  # we cut .value
				if path:
					if path[0] == "self":
						# possible use of a variable that a enum value
						path = path[1:]  # we cut self.
						path = tuple(self.currentPath) + path
						enumVar = self.lookupPathInEnumVars(path)
						if enumVar:
							return node.value
					else:
						# possible use of enum class
						path = path[:-1]  # we cut .value_name
						r = self.lookupPathInEnums(path)
						if r:
							return node.value
		return self.generic_visit(node)


def fixEnums(fileText: str, fileName: typing.Union[str, Path]) -> str:
	"""
	Replaces `Enum` with `IntEnum`, removes `.value` (result of `.to_i`, but broken for unrecognized enums, which are just ints) when it can derive the enum is used.

	ToDo: make it 2-pass"""

	iF = ast.parse(fileText, filename=fileName)
	resTree = RewriteEnumIntoIntEnum().visit(iF)
	ast.fix_missing_locations(resTree)
	return ast.unparse(resTree)


postprocessors = {
	"permissiveDecoding": permissiveDecoding,
	"fixEnums": fixEnums,
}

patch = None
try:
	import patch_ng as patch
except ImportError:
	try:
		import patch

		warnings.warn("patch_ng is not present, imported old broken and UNMAINTAINED `patch` by techtonik (the man is alive, but doesn't maintain)")
	except ImportError:
		pass

if patch:
	from io import BytesIO
	from pathlib import Path, PurePath

	def applyPatch(fileText: str, fileName: typing.Union[str, Path], patchFile: Path):
		with patchFile.open("rb") as psf:
			ps = patch.PatchSet(psf)
			ps.parse(psf)

		if len(ps.items) != 1:
			raise ValueError("Patch file contains more than 1 patch", patchFile, len(ps.items))

		p = ps.items[0]
		s = PurePath(p.source.decode("utf-8"))
		t = PurePath(p.target.decode("utf-8"))
		if s != t:
			raise ValueError("Patch file patches not the same file", patchFile)
		#t.name

		with BytesIO(fileText.encode("utf-8")) as sF:
			return b"".join(ps.patch_stream(sF, p.hunks)).decode("utf-8")

	def applyPatches(fileText: str, fileName: typing.Union[str, Path], *patchFiles: typing.Iterable[str]):
		for f in patchFiles:
			fileText = applyPatch(fileText, fileName, Path(f))
		return fileText

	postprocessors["applyPatches"] = applyPatches
