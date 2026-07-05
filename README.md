# LibMan

**LibMan** is a command-line package manager for monorepos, currently focused on managing **Unity UPM packages**. It automates common package maintenance tasks, keeps repositories organized, and integrates with Git for automatic commits.

The tool is designed for developers maintaining a library repository containing multiple Unity packages.

---

## Features

- 📦 Create new Unity packages
- ➕ Add runtime and editor files to existing packages
- ➖ Remove files from packages
- 🗑 Delete packages
- 📂 Browse package directory structure
- 📋 List all packages in a repository
- 🚀 Launch the configured Unity project
- 🔍 Remember ("focus") a repository to avoid repeatedly typing its path
- 🔄 Automatic Git commits for mutating operations
- 🧪 Dry-run mode to preview changes
- ⚡ PowerShell tab completion with `argcomplete`

---

## Requirements

LibMan currently **only supports Windows PowerShell**.

The tool relies on PowerShell-specific features for:

- Tab completion (`argcomplete`)
- The `visit` command (`cd` into the target directory)
- Automatic initialization performed by `libman init`

Other shells (Command Prompt, Git Bash, WSL, Bash, Zsh, etc.) are **not currently supported**.

---

# Installation

Clone the repository:

```bash
git clone https://github.com/<your-username>/libman.git
cd libman
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Configure your PowerShell profile

LibMan requires a small amount of PowerShell code to enable directory navigation and command completion.

A template is provided in:

```
PROFILE_CODE.txt
```

Copy the contents of this file into your PowerShell profile (`$PROFILE`).

If your profile doesn't exist yet, create it:

```powershell
New-Item -ItemType File -Force -Path $PROFILE
```

To open your profile in Notepad:

```powershell
notepad $PROFILE
```

Paste the contents of `PROFILE_CODE.txt`, save the file, then restart PowerShell.

### Initialize a repository

Once your PowerShell profile has been configured, initialize your repository:

```bash
libman init
```

This creates the `.libmanrc` configuration file used by LibMan.

---

# Repository Focus

LibMan remembers which repository you're currently working with.

Set the active repository:

```bash
libman focus /path/to/my/repository
```

Later you can simply use:

```bash
libman unity list
```

instead of

```bash
libman --repo /path/to/my/repository unity list
```

You can also temporarily override the focused repository using:

```bash
libman --repo /path/to/other/repository unity list
```

---

# Unity Package Commands

## Create a package

```bash
libman unity create MyPackage \
    --runtime Assets/Scripts/MyRuntime.cs \
    --editor Assets/Editor/MyEditor.cs
```

---

## List packages

```bash
libman unity list
```

---

## Visit a package

```bash
libman unity visit MyPackage
```

Copy the package path instead:

```bash
libman unity visit MyPackage --copy
```

---

## Display package structure

Show folders:

```bash
libman unity dir MyPackage
```

Include files:

```bash
libman unity dir MyPackage --files
```

---

## Add files

```bash
libman unity add-files MyPackage \
    --runtime Assets/Scripts/NewFeature.cs \
    --editor Assets/Editor/NewFeatureEditor.cs
```

---

## Remove files

Paths are relative to the package's `Runtime` or `Editor` directories.

```bash
libman unity remove-files MyPackage \
    --runtime NewFeature.cs \
    --editor NewFeatureEditor.cs
```

---

## Delete a package

```bash
libman unity delete MyPackage
```

---

## Launch Unity

Starts the Unity executable configured in `.libmanrc`.

```bash
libman unity start
```

---

# Repository Commands

Visit the currently focused repository:

```bash
libman visit
```

Copy the repository path:

```bash
libman visit --copy
```

---

# Global Options

## Dry Run

Preview all operations without modifying anything.

```bash
libman --dry-run unity create TestPackage
```

---

## Disable Automatic Git Commits

All mutating commands automatically create Git commits by default.

To disable this behavior:

```bash
libman --no-git unity add-files MyPackage --runtime Extra.cs
```

---

# Git Integration

The following commands automatically create descriptive commits:

- Package creation
- Package deletion
- Adding files
- Removing files

Example commit messages:

```
feat(unity): add MyPackage package
feat(unity/MyPackage): add files
chore(unity): remove MyPackage package
chore(unity/MyPackage): remove files
```

---

# Shell Autocomplete

LibMan supports command completion using **argcomplete**.

Autocomplete is available for:

- Package names
- Existing package files
- File paths
- Commands and options

PowerShell autocomplete is configured automatically during `libman init`.

---

# Example Workflow

```bash
# Select a repository
libman focus ~/Projects/MyLibrary

# Initialize it
libman init

# Create a package
libman unity create Networking \
    --runtime Assets/Scripts/Networking.cs

# Inspect it
libman unity dir Networking --files

# Add another runtime file
libman unity add-files Networking \
    --runtime Assets/Scripts/Connection.cs

# List all packages
libman unity list
```

---

# Philosophy

LibMan is designed around a few principles:

- Keep Unity package maintenance simple.
- Automate repetitive repository tasks.
- Encourage clean Git history.
- Make working across multiple library repositories effortless.
- Provide a fast command-line workflow with autocomplete and sensible defaults.

---

## License

MIT License
