import json
import re
from argparse import ArgumentParser
from logging import getLogger
import wave
from os import remove
from sys import stderr
from tempfile import mktemp
from time import sleep
from typing import Any

import proglog
from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.VideoClip import VideoClip
import requests
from mysutils.file import remove_files
from requests import Response
from urllib3.exceptions import MaxRetryError
from moviepy.editor import VideoFileClip
from mysutils.tmp import removable_tmp

log = getLogger(__name__)
MAX_ATTEMPTS = 10
WAIT = 10
DEF_QUALITY = 3200000

class ArgumentError(Exception):
    pass


class LinkedinArgParser(object):
    """ Class for parsing command line arguments. """
    @property
    def url(self) -> str:
        """
        :return: The Manifest URL with all the video fragments.
        """
        return self._args.url

    @property
    def file(self) -> str:
        """
        :return: The output file to store the video.
        """
        return self._args.file

    @property
    def max_attempts(self) -> int:
        """
        :return: The maximum number of attempts to download the video.
        """
        return self._args.max_attempts

    @property
    def wait(self) -> int:
        """
        :return: The number of seconds to wait between each attempt.
        """
        return self._args.wait

    @property
    def limit(self) -> float:
        """
        :return: The maximum video time to download.
        """
        return self._args.limit

    @property
    def quality(self) -> int:
        """
        :return: The quality of the video.
        """
        return self._args.quality

    def __init__(self) -> None:
        """ Parse the app arguments. """
        parser = ArgumentParser(description='Download videos from LinkedIn')
        parser.add_argument('url', metavar='URL', type=str, help='The URL to the video streaming')
        parser.add_argument('file', metavar='FILE', type=str, help='The file to save the video.')
        parser.add_argument('-m', '--max_attempts', metavar='NUMBER', type=int, default=MAX_ATTEMPTS,
                            help='The maximum number of attempts in case of connection error.')
        parser.add_argument('-w', '--wait', metavar='SECONDS', type=int, default=WAIT,
                            help='A delay time between several download intents.')
        parser.add_argument('-l', '--limit', metavar='SECONDS', type=float, default=0,
                            help='The maximum time to download. 0 for all the video. By default, 0.')
        parser.add_argument('-q', '--quality', metavar='QUALITY', type=int, default=DEF_QUALITY,
                            help=f'The maximum time to download. 0 for all the video. By default, {DEF_QUALITY}.')
        self._args = parser.parse_args()


def trying_get(url, max_attempts: int = MAX_ATTEMPTS, wait: int = WAIT, **kwargs) -> requests.Response:
    """ Makes a get request to an url trying several times if it fails.
    :param url: The URL to download.
    :param max_attempts: The maximum number of attempts to download the video.
    :param wait: The number of seconds to wait between each attempt.
    :return: A http response.
    """
    attempts = max_attempts
    while attempts:
        try:
            return requests.get(url, **kwargs)
        except (requests.exceptions.ConnectionError, MaxRetryError) as e:
            attempts -= 1
            log.warning(f'Connection error to "{url}" trying again '
                        f'{max_attempts - attempts} of {max_attempts} after {wait} seconds...')
            if not attempts:
                raise e
            sleep(wait)


class Downloader(object):
    """ Class for downloading videos from LinkedIn. """
    def __init__(self, url: str, max_attempts: int = MAX_ATTEMPTS, wait: int = WAIT, limit: float = 0,
                 quality: int = DEF_QUALITY) -> None:
        """ Int the LinkedIn video downloader.

        :param url: The URL to the manifest file.
        :param max_attempts: The maximum number of attempts when the connection fails.
        :param wait: The time to wait between connection errors.
        :param limit: The time limit to download.
        """
        self._max_attempts = max_attempts
        self._wait = wait
        url = self.get_manifest(url, quality, max_attempts, wait)
        r = trying_get(url, max_attempts, wait)
        raw_text = r. text.replace('\r', '')
        lines = raw_text.split('\n')
        download_url = re.sub('Manifest.*', '', url)
        self.paths = [download_url + line for line in lines if line.startswith('Fragments')]
        self.times = [0.] + [float(line.split(':')[1].split(',')[0]) for line in lines if line.startswith('#EXTINF:')]
        self.duration = min(sum(self.times), limit) if limit else sum(self.times)
        self.pos = 0
        self.clip = 0
        self.audio_fps = None
        self.wav_file = mktemp(suffix='.wav')
        self.audio_file = wave.open(self.wav_file, 'wb')
        self.current_clip = self._get_next_clip(self.paths[self.clip])

    @property
    def fps(self) -> int:
        """
        :return: The video frames per second.
        """
        return self.current_clip.fps

    def _make_frame(self, t: float) -> Any:
        """ Get the next frame from the stream.

        :param t: The current time of the frame.
        :return: The video frame.
        """
        if self.current_clip.duration < t - self.pos:
            self.pos += self.current_clip.duration
            self.clip += 1
            self.current_clip.close()
            remove(self.current_clip.filename)
            self.current_clip = self._get_next_clip(self.paths[self.clip])

        return self.current_clip.get_frame(t - self.pos)

    def _get_next_clip(self, url: str) -> VideoFileClip:
        """ Get the next clip from the stream.

        :param url: The URL to the next video fragment.
        :return: The video clip.
        """
        video_tmp_file = mktemp('.mp4')
        r = trying_get(url, self._max_attempts, self._wait)
        with open(video_tmp_file, 'wb') as file:
            file.write(r.content)
        clip = VideoFileClip(video_tmp_file)
        with removable_tmp(suffix='.wav') as audio_tmp_file:
            clip.audio.write_audiofile(audio_tmp_file, logger=None)
            with wave.open(audio_tmp_file, "rb") as w:
                try:
                    self.audio_file.getparams()
                except wave.Error:
                    self.audio_file.setparams(w.getparams())
                self.audio_file.writeframes(w.readframes(w.getnframes()))
        return clip

    def download(self, file: str) -> None:
        """ Download the video and write it to the specified file.

        :param file: The name of the file to download the video.
        """
        tmp = mktemp('.mp4')
        clip = VideoClip(self._make_frame, False, self.duration)
        clip.write_videofile(tmp, fps=self.fps, logger=proglog.TqdmProgressBarLogger(print_messages=False))
        clip.close()
        self.audio_file.close()
        clip = VideoFileClip(tmp)
        audio = AudioFileClip(self.wav_file)
        clip.audio = audio
        clip.write_videofile(file, logger=proglog.TqdmProgressBarLogger(print_messages=False))
        audio.close()
        clip.close()
        remove_files(tmp, self.wav_file)

    def close(self) -> None:
        """ Close this object and clean all the temporary files. """
        self.current_clip.close()
        self.audio_file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_manifest(self, url: str, quality: int, max_attempts: int = MAX_ATTEMPTS, wait: int = WAIT) -> str:
        """ Get the real manifest url.

        :param url: The url of the page with the video.
        :param quality: The quality of the video.
        :param max_attempts: The maximum number of attempts when the connection fails.
        :param wait: The time to wait between connection errors.
        :return: A URL where is the manifest with all the links to the video fragments.
        """
        if '/Manifest' in url:
            return url
        if '/manifest' in url:
            return self.get_quality(url, quality)
        r = trying_get(url)
        cookie = [cookie for cookie in r.cookies if cookie.name == 'JSESSIONID'][0]
        id = self.get_video_id(r)
        headers={
            'Accept-Encoding': 'gzip, deflate, br',
            'csrf-token': f'{cookie.value}',
            'Cookie': f'{cookie.name}="{cookie.value}"'
        }
        r = trying_get(f'https://www.linkedin.com/voyager/api/video/liveUpdates/urn%3Ali%3AugcPost%3A{id}',
                       max_attempts, wait, headers=headers, cookies=r.cookies)
        result = json.loads(r.content)
        metadata = result['content']['com.linkedin.voyager.feed.render.LinkedInVideoComponent']['videoPlayMetadata']
        url = metadata['adaptiveStreams'][0]['masterPlaylists'][0]['url']
        return self.get_manifest(url, quality, max_attempts, wait)

    def get_quality(self, url: str, quality: int) -> str:
        """ The manifest URL with that quality.

        :param url: The URL with the manifest with the qualities.
        :param quality: The quality of the video.
        :return: The URL with the manifest of the video fragments with the given quality.
        """
        r = trying_get(url, self._max_attempts, self._wait)
        lines = r.content.decode('utf-8').replace('\r', '').split('\n')
        available_qualities = []
        for line in lines:
            if line.startswith('QualityLevels'):
                available_qualities.append(int(re.sub(r'QualityLevels\(|\).*$', '', line)))
                if line.startswith(f'QualityLevels({quality})/Manifest'):
                    return re.sub('/[^/]+$', f'/{line}', url)
        available_qualities.sort()
        available_qualities = "\n  ".join([str(q) for q in available_qualities])
        raise ArgumentError(f'Incorrect quality level. The available quality levels are:\n  {available_qualities}')

    def get_video_id(self, r: Response) -> str:
        """ Get the video id from the page response.

        :param r: The response from the page.
        :return: The video id.
        """
        if '/urn:li:ugcPost:' in r.url:
            return re.sub(r'^.*/urn:li:ugcPost:|/.*$', '', r.url)
        text_to_find = 'main-feed-activity-card-with-comments" data-activity-urn="urn:li:activity:'
        line = [line for line in r.text.split('\n') if text_to_find in line][0]
        return re.sub(r'.*urn:li:ugcPost:|".*', '', line)


def main() -> None:
    """ The main function.

    :param args: The arguments.
    """
    args = LinkedinArgParser()
    try:
        with Downloader(args.url, args.max_attempts, args.wait, args.limit, args.quality) as downloader:
            downloader.download(args.file)
    except ArgumentError as e:
        print('Argument -q QUALITY error: ' + str(e), file=stderr)


if __name__ == '__main__':
    main()
