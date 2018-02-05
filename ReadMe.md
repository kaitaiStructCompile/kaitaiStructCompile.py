kaitaiStructCompile.py [![Unlicensed work](https://raw.githubusercontent.com/unlicense/unlicense.org/master/static/favicon.png)](https://unlicense.org/)
======================
[wheel](https://gitlab.com/kaitaiStructCompile.py/kaitaiStructCompile.py/-/jobs/artifacts/master/raw/wheels/kaitaiStructCompile-0.CI-py3-none-any.whl?job=build)
[![PyPi Status](https://img.shields.io/pypi/v/kaitaiStructCompile.py.svg)](https://pypi.python.org/pypi/kaitaiStructCompile.py)
[![GitLab build status](https://gitlab.com/kaitaiStructCompile.py/kaitaiStructCompile.py/badges/master/pipeline.svg)](https://gitlab.com/kaitaiStructCompile.py/kaitaiStructCompile.py/commits/master)
[![Coveralls Coverage](https://img.shields.io/coveralls/KOLANICH/kaitaiStructCompile.py.svg)](https://coveralls.io/r/KOLANICH/kaitaiStructCompile.py)
[![GitLab coverage](https://gitlab.com/kaitaiStructCompile.py/kaitaiStructCompile.py/badges/master/coverage.svg)](https://gitlab.com/kaitaiStructCompile.py/kaitaiStructCompile.py/commits/master)
[![Libraries.io Status](https://img.shields.io/librariesio/github/KOLANICH/kaitaiStructCompile.py.svg)](https://libraries.io/github/KOLANICH/kaitaiStructCompile.py)
[![Code style: antiflash](https://img.shields.io/badge/code%20style-antiflash-FFF.svg)](https://github.com/KOLANICH-tools/antiflash.py)

This is a tool automating compilation [Kaitai Struct](https://github.com/kaitai-io/kaitai_struct) ```*.ksy``` files into python ones.


Features
--------

* python bindings to compile KS `.ksy` specs into python source code.
* importer allowing to import `ksy`s. Seamlessly compiles `ksy`s into python sources. Useful for playing in IPython shell.
* `setuptools` plugin to automate compiling `ksy`s into `py` in process of building of your package.

Prerequisites
-------------
* [Kaitai Struct compiler](https://github.com/kaitai-io/kaitai_struct_compiler) must be unpacked somewhere and all its prerequisites like `JRE` or `OpenJDK ` must be installed.
* Path to Kaitai Struct compiler root dir (the one containing `lib`, `bin` and `formats`) must be exposed as `KAITAI_STRUCT_ROOT` environment variable.
* A backend must be installed. [CLI backend](https://github.com/kaitaiStructCompile/kaitaiStructCompileBackendCLI) is currently the only one publicly available.

Usage
-----

### Importing a ksy

```python
import kaitaiStructCompile.importer
kaitaiStructCompile.importer._importer.searchDirs.append(Path("./dirWithKSYFiles")) # you can add a dir to search for KSY files.
kaitaiStructCompile.importer._importer.flags["readStoresPos"]=True # you can set compiler flags, for more details see the JSON schema
from kaitaiStructCompile.importer.test import Test
Test # kaitaiStructCompile.importer.test.Test
```

### Manual compilation

```python
from kaitaiStructCompile import compile
compile("./ksyFilePath.ksy", "./outputDir", additionalFlags=[
	#you can expose additional params here
])
```

### Backends

#### CLI
See https://github.com/kaitaiStructCompile/kaitaiStructCompileBackendCLI for more info.

#### Other backends
More backends may be available in future. Even by third parties. Even for alternative Kaitai Struct compiler implementations.


#### JVM backend
I have created a JVM backend. It is **not distributed** and **YOU CANNOT OBTAIN IT** until [the issue with GPL license virality](https://github.com/kaitai-io/kaitai_struct/issues/466) is resolved.

Cons:
* GPL virality
* breaks sometimes


Pros:
* better security
* works much faster


### `importer`
This is an importer allowing to import `ksy`s. Seamlessly compiles `ksy`s into python sources. Useful for playing in IPython shell.


#### Usage

```python
import kaitaiStructCompile.importer
kaitaiStructCompile.importer._importer.searchDirs.append(Path("./dirWithKSYFiles"))  # you can add a dir to search for KSY files.
kaitaiStructCompile.importer._importer.flags["readStoresPos"] = True  # you can set compiler flags, for more details see the JSON schema
from kaitaiStructCompile.importer.test import Test
Test # kaitaiStructCompile.importer.test.Test
```


### Build systems extensions
This is a set of build system plugins allowing you to just specify `ksy` files you need to compile into python sources in process of building your package in a declarative way.

Supported build systems:
* `setuptools`
* `hatchling`
	* to enable also add an empty `[tool.hatch.build.hooks.kaitai_transpile]` section into your `pyproject.toml`.
* `poetry`
	* works only with `poetry`, not `poetry-core` (because `poetry-core` has no support of plugins at all).
	* adds `kaitai transpile` command.


#### Usage
Just an add a property `tool.kaitai` into the `pyproject.toml`. This dict specified and documented with [the JSON Schema](./kaitaiStructCompile/schemas/config.schema.json), so read it carefully.


Here a piece from one project with comments follows:
```toml
[build-system]
requires = ["setuptools>=44", "wheel", "setuptools_scm[toml]>=3.4.3", "kaitaiStructCompile[toml]"]  # we need this tool !
...

# `tool.kaitai.repos` must contain 2-level nested dicts. The first component is usually repo URI, the second one is the refspec. But one can put there irrelevant things, if one needs for example compile multiple stuff from the same repo and refspec
[tool.kaitai.repos."https://github.com/KOLANICH/kaitai_struct_formats.git"."mdt"]
# one can put something irrelevant into the components of the section header, then he has to set `git` and `refspec`
#git = "https://github.com/KOLANICH/kaitai_struct_formats.git"
#refspec = "mdt" 
update = true # automatically download the freshest version of the repo each time the project is built
search = true # glob all the spec from `inputDir`
localPath = "kaitai_struct_formats" #  Where (rel to `setup.py` dir) the repo of formats will be downloaded and from which location the compiler will use it.
inputDir = "scientific/nt_mdt" # the directory we take KSYs from rel to `localPath`
outputDir = "NTMDTRead/kaitai" # the directory we will put the generated file rel to setup.py dir

[tool.kaitai.repos."https://github.com/KOLANICH/kaitai_struct_formats.git"."mdt".formats]
# here we declare our targets. MUST BE SET, even if empty!!!
```

Or one can pass the dict of the similar structure to `setuptools.setup` directly using `kaitai` param (in this case you set all the paths yourself!!!), but it is disrecommended. Use the declarative config everywhere it is possible.

#### Real Examples

[1](https://github.com/KOLANICH-physics/NTMDTRead/blob/master/pyproject.toml)
[2](https://github.com/KOLANICH-physics/SpecprParser.py/blob/master/pyproject.toml)
[3](https://github.com/KOLANICH-tools/FrozenTable.py/blob/master/pyproject.toml)
[4](https://github.com/KOLANICH-libs/lime.py/blob/master/pyproject.toml)
[5](https://github.com/KOLANICH-libs/sunxi_fex.py/blob/master/pyproject.toml)
[6](https://github.com/KOLANICH-tools/WindowsTelemetryViewer.py/blob/master/pyproject.toml)
[7](https://github.com/KOLANICH-libs/MFCTool.py/blob/master/pyproject.toml)
[8](https://github.com/KOLANICH-ML/RDataParser.py/blob/master/pyproject.toml)
[9](https://github.com/KOLANICH-tools/inkwave.py/blob/master/pyproject.toml)

