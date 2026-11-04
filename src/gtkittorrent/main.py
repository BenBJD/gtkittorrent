import sys
from gtkittorrent.app import GTKittorrentApp

def main():
    app = GTKittorrentApp()
    return app.run(sys.argv)

if __name__ == "__main__":
    main()
