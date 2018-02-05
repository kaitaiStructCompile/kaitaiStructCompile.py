import jsonschema

from . import isPath, schema

types = {"function": callable, "path": isPath}
ValidatorT = jsonschema.validators._LATEST_VERSION
ourTypeChecker = ValidatorT.TYPE_CHECKER.redefine_many(types)
ValidatorT = jsonschema.validators.extend(ValidatorT, type_checker=ourTypeChecker)
validator = ValidatorT(schema)
flagsValidator = ValidatorT(schema["definitions"]["compilerFlags"])
