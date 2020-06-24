# tExtractor
Extract torrents upon completion.

The script will recursively scan the `<download_location>/<torrent_name>` folder for compressed archives and extract them to `<download_location>/<torrent_name>/__extracted` (it will also scan the `__extracted` directory for any additional compressed archives and extract them into the same directory).

## Help

The extract.py script has 5 parameters:

Positional parameters:
- Postion 1: torrent hash/id - currently not used
- Postion 2: the torrent name
- Postion 3: the download location

Optional parameters:
- -t DIR / --tmp DIR: Specify a custom temporary directory to perform extraction into. NOTE: DIR must exist.
- -v / --verbose: debug output


## Usage
While this setup works with most torrent clients, I'll demonstrate the setup with Deluge:

- Fist make sure you have the `Execute` plugin installed
- Then add a new event on `Torrent Completed` and then enter the location of extract.py in the command box
- Restart Deluge for settings to take effect

The execute plugin will run any script with the paramters `<script> torrent_id torrent_name download_location`, but you don't need to enter the paramters here

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
Path: /path/to/script/location`
```
This will check and delete the `__extracted` folder if Sonarr/Radarr grabbed the media item from there.
