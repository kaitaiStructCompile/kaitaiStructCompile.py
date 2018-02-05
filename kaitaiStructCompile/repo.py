import re
from pathlib import Path

import git

from .colors import styles

headBranchExtractionRegExp = re.compile("^\\s*HEAD\\s+branch:\\s+(.+)\\s*$", re.M)


def getRemoteDefaultBranch(remote):
	# get_remote_ref_states
	return headBranchExtractionRegExp.search(remote.repo.git.remote("show", remote.name)).group(1)


def upgradeLibrary(localPath: Path, gitUri: str, refspec: str = None, progressCallback=None, prefixPath: Path = None):
	"""Upgrades a library of Kaitai Struct formats"""
	if progressCallback is None:

		def progressCallback(x):
			return None

	localPath = Path(localPath).absolute()
	r = None
	actName = ""
	if not (localPath.exists() and localPath.is_dir()):
		localPath.mkdir()
		#assert (localPath.exists() and localPath.is_dir())

	if not (localPath / ".git").exists():
		actName = "Clon"
		r = git.Repo.init(str(localPath))  # git.Repo.clone disallows to specify a dir, so we workaround with init + pull
		# assert ( (localPath/".git").exists() )
	else:
		actName = "Pull"
		r = git.Repo(str(localPath))

	#progress=print
	# A function (callable) that is called with the progress information.
	# Signature: ``progress(op_code, cur_count, max_count=None, message='')``.
	#origin = r.create_remote('origin', repo.remotes.origin.url)
	try:
		r.remotes["origin"].set_url(gitUri)
		remote = r.remotes["origin"]
	except BaseException:
		remote = r.create_remote("origin", gitUri)

	gargs = [r.remotes["origin"].name]
	if not refspec:
		refspec = getRemoteDefaultBranch(remote)

	gargs.append(refspec)
	r.git.checkout(refspec, B=True)

	#def progressHandler(op_code, cur_count, max_count=None, message=''):
	#	print(op_code, cur_count, max_count, message)
	#	progressCallback(message)

	gkwargs = {
		"depth": 1,
		"force": True,
		"update-shallow": True,
		#"verify-signatures":True,
		#"progress":progressHandler,
		"verbose": True,
	}

	def pathToPrettyString(p: Path) -> str:
		return str(p.relative_to(prefixPath) if prefixPath else p)

	progressCallback(styles["operationName"](actName + "ing") + " " + styles["info"](gitUri) + " to " + styles["info"](pathToPrettyString(localPath)) + " ...")
	r.remotes["origin"].fetch(*gargs[1:], **gkwargs)
	r.head.reset(r.remotes["origin"].name + "/" + refspec, index=True, working_tree=True)

	progressCallback("\b" + styles["operationName"](actName + "ed"))
