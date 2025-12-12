# tExtractor
Extract torrents upon completion.

The script will recursively scan the `<download_location>/<torrent_name>` folder for compressed archives and extract them to `<download_location>/<torrent_name>/__extracted` (it will also scan the `__extracted` directory for any additional compressed archives and extract them into the same directory).

## Help

The extract.py script has 6 parameters:

Positional parameters:
- Position 1: torrent hash/id
- Position 2: the torrent name
- Position 3: the download location

Optional parameters:
- -t DIR / --tmp DIR: Specify a custom temporary directory to perform extraction into. NOTE: DIR must exist.
- -d / --direct: Extract directly to the `__extracted` directory (skips temp directory and intermediate file moving)
- -v / --verbose: debug output


## Usage
While this setup works with most torrent clients, I'll demonstrate the setup with qBittorrent:

- First navigate to Tools -> Options -> Downloads
- Then enable "Run external program on torrent completion"
- Enter the command: `/path/to/extract.py "%I" "%N" "%D"`
- Apply and restart qBittorrent for settings to take effect

The parameters `%I` (hash), `%N` (name), and `%D` (save path) will be automatically substituted by qBittorrent.

## Extras
In the folder `extras` within this repository you'll find `sonarr_cleanup` and `radarr_cleanup`. 

To use these scripts setup Sonarr/Radarr via Settings->Connect->Add Connection:
```
Name: Cleanup after processing
On Grab: No
On Download: Yes
On Upgrade: Yes
On Rename: No
Filter Movie Tags: N/A
Path: /path/to/script/location
```
This will check and delete the `__extracted` folder if Sonarr/Radarr grabbed the media item from there.
