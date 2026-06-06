import json
from pathlib import Path
import subprocess

def setup_powershell_autocomplete():
    """Automatically adds argcomplete to the user's PowerShell profile."""
    
    # The exact command you want to inject
    auto_cmd = "register-python-argcomplete --shell powershell libman | Out-String | Invoke-Expression"
    
    try:
        # Determine whether to use 'pwsh' (PowerShell Core 7+) or 'powershell' (Windows PowerShell 5.1)
        # Use pwsh if available, fallback to powershell
        shell_exe = "powershell"
        try:
            if subprocess.run(["pwsh", "-Version"], capture_output=True).returncode == 0:
                shell_exe = "pwsh"
        except FileNotFoundError:
            pass

        # Ask PowerShell for the path to the current user's profile
        result = subprocess.run(
            [shell_exe, "-NoProfile", "-Command", "Write-Output $PROFILE"],
            capture_output=True, text=True, check=True
        )
        
        profile_path = Path(result.stdout.strip())
        
        # Ensure the directory and file exist
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        if not profile_path.exists():
            profile_path.touch()
            
        # Read profile to check if it's already installed
        content = profile_path.read_text(encoding="utf-8")
        
        if auto_cmd in content:
            print("✓ Autocomplete is already configured in your PowerShell profile.")
            return

        # Append to the profile
        with profile_path.open("a", encoding="utf-8") as f:
            f.write("\n# libman autocomplete\n")
            f.write(f"{auto_cmd}\n")
            
        print(f"Added autocomplete to PowerShell profile: {profile_path}")
        print("! Please restart PowerShell or run '. $PROFILE' to apply changes.")

    except Exception as e:
        print(f"Failed to setup autocomplete automatically: {e}")
        print(f"Please manually add this line to your PowerShell profile:\n{auto_cmd}")


def package_name_completer(prefix, repo_path):
    """Complete Unity package names from existing packages"""
    try:
        repo_path = None

        if not repo_path or not Path(repo_path).exists():
            return []

        config_path = Path(repo_path) / ".libmanrc"
        
        unity_dir_name = "Unity"  # Default

        if config_path.exists():
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
                # Check potential config keys
                if "unity_root" in data:
                    unity_dir_name = data["unity_root"]
                elif "unity_folder" in data:
                    unity_dir_name = data["unity_folder"]
            except Exception:
                pass

        packages_dir = Path(repo_path) / unity_dir_name

        if packages_dir.exists():
            return [p.name for p in packages_dir.iterdir()
                    if p.is_dir() and p.name.startswith(prefix)]
    except Exception:
        pass

    return []