import sys
import os

# Ensure src directory is in sys.path when running from git checkout
repo_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(repo_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from gtkittorrent.main import main

if __name__ == "__main__":
    main()
