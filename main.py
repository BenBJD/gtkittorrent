import sys
import os

# Ensure project directory is in sys.path regardless of execution cwd
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from app import GTKittorrentApp

def main():
    app = GTKittorrentApp()
    return app.run(sys.argv)

if __name__ == "__main__":
    main()
