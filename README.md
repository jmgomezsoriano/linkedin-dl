LinkedIn-Downloader
===================

A small tool to download videos from linkeding.

# Requirements

* Python 3.7 or higher.
* pip 22.1.x or higher

# Install

1. Install tool

   ```bash
   pip install linkedin-dl
   ```

# Usage

You can use this tool very easily, with the argument -h you can obtain information about its use:

```bash
linkedin-dl -h
usage: linkedin-dl [-h] [-m NUMBER] [-w NUMBER] [-l SECONDS] [-q QUALITY] URL FILE

Download videos from LinkedIn

positional arguments:
  URL                   The URL to the video streaming
  FILE                  The file to save the video.

optional arguments:
  -h, --help            show this help message and exit
  -m NUMBER, --max_attempts NUMBER
                        The maximum number of attempts in case of connection error.
  -w NUMBER, --wait SECONDS
                        A delay time between several download intents.
  -l SECONDS, --limit SECONDS
                        The maximum time to download. 0 for all the video. By default, 0.
  -q QUALITY, --quality QUALITY
                        The maximum time to download. 0 for all the video. By default, 3200000.
```

Where _URL_ is the URL with the LinkedIn page that contain the video and
_FILE_ is the path to the file to save the video locally.
The rest of the arguments are optionals:

* -m _NUMBER_ is the number of attempts to reconnect when the connection fails;
* -w _SECONDS_ is the time in seconds to wait between each attempt in case of connection fail;
* -l _SECONDS_ is the limit of time in seconds to download, by default, all the video is downloaded.
* -q _QUALITY_ is the video quality to download, by default, it is the maximum, the available values are:
  * 128000
  * 400000
  * 800000
  * 1600000
  * 3200000

# Download a video

```bash
linkedin-dl "URL" "FILE" -l SECONDS -q QUALITY
```

Some examples:

```bash
# Download all the video
linkedin-dl "https://www.linkedin.com/video/live/urn:li:ugcPost:6940332883056205824/" "Te mereces destacar.mp4"

# Download only the first 60 seconds
linkedin-dl "https://www.linkedin.com/video/live/urn:li:ugcPost:6940332883056205824/" "Te mereces destacar.mp4" -l 60
```
