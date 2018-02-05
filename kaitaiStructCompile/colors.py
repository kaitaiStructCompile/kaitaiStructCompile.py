__all__ = ("styles",)
try:
	from RichConsole import groups

	styles = {
		"ksyName": groups.Fore.lightgreenEx,
		"resultName": groups.Fore.lightredEx,
		"operationName": groups.Fore.yellow,
		"info": groups.Fore.lightblueEx,
	}
except BaseException:

	def dummy(arg):
		return arg

	styles = {
		"ksyName": dummy,
		"resultName": dummy,
		"operationName": dummy,
		"info": dummy
	}
