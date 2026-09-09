import os
import sys
import subprocess
from pathlib import Path

# Redefine the default Kagglehub cache directory to drive D: to avoid disk space issues
cache_dir = Path(__file__).resolve().parent / ".cache"
os.environ["KAGGLEHUB_CACHE_DIR"] = str(cache_dir)

# Set custom temp directory on drive D: to prevent filling C: drive temp space
temp_dir = Path(__file__).resolve().parent / "temp"
temp_dir.mkdir(exist_ok=True)
os.environ["TEMP"] = str(temp_dir)
os.environ["TMP"] = str(temp_dir)

# Ensure kagglehub is installed
try:
    import kagglehub
except ImportError:
    print("Installing kagglehub package...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "kagglehub"])
    import kagglehub

def main():
    print("Downloading samithsachidanandan/human-face-emotions dataset...")
    # Download latest version
    path = kagglehub.dataset_download("samithsachidanandan/human-face-emotions")
    print("Path to dataset files in cache:", path)
    
    # Path to destination directory in local workspace
    dest = Path(__file__).resolve().parent / "human-face-emotions"
    
    if dest.exists() or dest.is_symlink():
        print(f"Destination {dest} already exists.")
    else:
        print(f"Creating directory link from {path} to {dest}...")
        try:
            if os.name == 'nt':
                # Creating Directory Junction on Windows (does not require administrator privileges)
                subprocess.run(f'mklink /J "{dest}" "{path}"', shell=True, check=True)
            else:
                os.symlink(path, dest, target_is_directory=True)
            print("Link created successfully.")
        except Exception as e:
            print(f"Failed to create link: {e}")
            print(f"Please manually reference the dataset at: {path}")

if __name__ == "__main__":
    main()
