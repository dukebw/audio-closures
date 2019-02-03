# Copyright 2019 Brendan Duke.
#
# This file is part of Audio Closures.
#
# Audio Closures is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# Audio Closures is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# Audio Closures. If not, see <http://www.gnu.org/licenses/>.

import json
import os

import click
import requests
from requests.auth import HTTPBasicAuth


def _to_seconds(seg):
    seg = seg.split(':')
    return 60*int(seg[0]) + int(seg[1])


@click.command()
@click.option('--youtube-id', type=str, default=None)
def segment_audio(youtube_id):
    if not os.path.exists(f'./data/{youtube_id}.mp4'):
        out_fname = f'./data/{youtube_id}.mp4'
        os.system(f'youtube-dl --format mp4 -o {out_fname} {youtube_id}')
        assert os.path.exists(out_fname)

    with open(f'./config/{youtube_id}.json', 'r') as fhan:
        segs = json.load(fhan)

    for seg in segs:
        start = _to_seconds(seg[0])
        end = _to_seconds(seg[1])
        back_id = f'{youtube_id}_{start:08d}_{end:08d}'
        back_fname = f'./data/{back_id}.mp4'
        if not os.path.exists(back_fname):
            os.system(f'ffmpeg -ss {start} -to {end} -i '
                      f'./data/{youtube_id}.mp4 -codec copy {back_fname}')

        os.system(f'ffmpeg -i {back_fname} -vn ./data/{back_id}_audio.mp4')

        requests.get(f'http://localhost:9090/requests/status.xml?command=in_play&input={back_fname}',
                     auth=HTTPBasicAuth('', 'a'))

        cloze_count = 0
        while True:
            if click.confirm('Finish segment?'):
                break

            seg_len = end - start
            cloze_start = click.prompt('Enter cloze start', type=float)
            assert 0 <= cloze_start <= seg_len

            cloze_end = click.prompt('Enter cloze end', type=float)
            assert 0 <= cloze_end <= seg_len

            vid_cloze_path = f'./data/{back_id}_cloze{cloze_count}.mp4'
            os.system(f'ffmpeg -i {back_fname} -af "volume=enable=\'between(t,{cloze_start},{cloze_end})\':volume=0" {vid_cloze_path}')

            requests.get(f'http://localhost:9090/requests/status.xml?command=in_play&input={vid_cloze_path}',
                         auth=HTTPBasicAuth('', 'a'))

            if click.confirm('Keep cloze?'):
                cloze_count += 1
                audio_cloze_path = f'{os.path.splitext(vid_cloze_path)[0]}_audio.mp4'
                os.system(f'ffmpeg -i {vid_cloze_path} -vn {audio_cloze_path}')

            os.remove(vid_cloze_path)


if __name__ == '__main__':
    segment_audio()  # pylint:disable=no-value-for-parameter
