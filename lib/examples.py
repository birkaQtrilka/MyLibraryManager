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

{YELLOW}Global options
-------------------------------------{RESET}

{CYAN}Preview changes without modifying the repository{RESET}
  libman --dry-run unity create TestPackage

{CYAN}Skip the automatic git commit{RESET}
  libman --no-git unity add-files MyPackage --runtime Extra.cs
"""