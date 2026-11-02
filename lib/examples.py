GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RESET = "\033[0m"

EXAMPLES = f"""\




{GREEN}Common workflows
==================================={RESET}

{CYAN}Select a library to work with{RESET}
  libman focus /path/to/repo
  libman visit
  libman visit --copy

{CYAN}Initialize a repository{RESET}
  libman init

{CYAN}Commit pending changes{RESET}
  libman commit

{CYAN}Work on another repository without changing focus{RESET}
  libman --repo /path/to/other/repo unity list

{YELLOW}Unity packages
-------------------------------------{RESET}

{CYAN}Create a package{RESET}
  libman unity create MyPackage \
      --runtime Assets/Scripts/MyRuntime.cs \
      --editor Assets/Editor/MyEditor.cs

{CYAN}List packages{RESET}
  libman unity list

{CYAN}Visit a package{RESET}
  libman unity visit MyPackage

{CYAN}Display the package structure{RESET}
  libman unity dir MyPackage
  libman unity dir MyPackage --files

{CYAN}Add files{RESET}
  libman unity add-files MyPackage \
      --runtime Assets/Scripts/NewFeature.cs \
      --editor Assets/Editor/NewFeatureEditor.cs

{CYAN}Remove files{RESET}
  libman unity remove-files MyPackage \
      --runtime NewFeature.cs \
      --editor NewFeatureEditor.cs

{CYAN}Delete a package{RESET}
  libman unity delete MyPackage

{CYAN}Copying files to your current directory{RESET}

libman unity pull Utils                       # whole package → ./Utils/
libman unity pull Utils Runtime               # a directory → ./Runtime/
libman unity pull Utils Runtime --flat        # directory contents → ./
libman unity pull Utils Pool.cs Editor/PoolEditor.cs   # bare name is searched recursively
libman unity pull Utils Pool.cs --force --dry-run

{CYAN}Searching through the library{RESET}

libman unity find pool                        # ranked list
libman unity find obj pool -p Utils           # multi-token, one package
libman unity find poolmgr --pull              # pick results by number to copy to cwd

{YELLOW}Global options
-------------------------------------{RESET}

{CYAN}Preview changes without modifying the repository{RESET}
  libman --dry-run unity create TestPackage

{CYAN}Skip the automatic git commit{RESET}
  libman --no-git unity add-files MyPackage --runtime Extra.cs
"""