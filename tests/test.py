#!/usr/bin/env python3
import sys
import unittest
from collections import OrderedDict
from pathlib import Path


testsDir = Path(__file__).parent.absolute()
parentDir = testsDir.parent.absolute()

inputDir = testsDir / "ksys"


class Test(unittest.TestCase):
	def testCompile(self):
		from kaitaiStructCompile import ChosenBackend, compile
		print("ChosenBackend", ChosenBackend)
		res = compile(inputDir / "a.ksy")
		self.assertEqual(len(res), 2)

	def testKaitai_keyword(self):
		from kaitaiStructCompile.setuptools import kaitaiHelper
		outDir = testsDir / "output"
		ofn = "a.py"
		ofp = outDir / ofn
		testCfg = {
			"kaitai": {
				"formats": {
					ofn: {"path": "a.ksy"},
					# "postprocess":["permissiveDecoding"], #fucking jsonschema is broken
					# "flags": ["--ksc-json-output"] #fucking jsonschema is broken
				},
				"formatsRepo": {"localPath": testsDir / "formats", "update": False},
				"outputDir": outDir,
				"inputDir": inputDir,
				"search": True,
				"flags": {"readStoresPos": True, "opaqueTypes": True, "verbose": []},
			}
		}
		kaitaiHelper(None, None, testCfg["kaitai"])
		self.assertTrue(ofp.exists())

	def testImport(self):
		import kaitaiStructCompile.importer

		kaitaiStructCompile.importer._importer.searchDirs.append(inputDir)
		kaitaiStructCompile.importer._importer.flags["readStoresPos"] = True
		from kaitaiStructCompile.importer import a, b

		testData = "qwertyuiop"
		testDataBin = bytearray(testData, encoding="utf-8") + b"\0"
		r = a.A.from_bytes(testDataBin)
		self.assertIsInstance(r.test, a.b.B)
		self.assertEqual(r._debug["test"]["start"], 0)
		self.assertEqual(r._debug["test"]["end"], len(testDataBin))

		r2 = r.test
		self.assertEqual(testData, r2.test)
		self.assertEqual(r.test._debug["test"]["start"], 0)
		self.assertEqual(r.test._debug["test"]["end"], len(testDataBin))


if __name__ == "__main__":
	unittest.main()
