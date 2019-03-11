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

import base64
from glob import glob
import os

import click
import requests


def _anki_post(action, params=None):
    post_json = {
        'action': action,
        'version': 6,
    }
    if params is not None:
        post_json['params'] = params

    resp = requests.post('http://localhost:8765', json=post_json)
    assert resp.status_code == 200

    resp = resp.json()
    assert resp['error'] is None, resp['error']

    return resp


@click.command()
@click.option('--youtube-id', type=str, default=None)
@click.option('--func', type=click.Choice(['create', 'reset', 'sync']))
def add_audio_card(youtube_id, func):
    resp = _anki_post('version')
    print(f'API version: {resp["result"]}')

    if func == 'sync':
        resp = _anki_post('sync')
        return

    resp = _anki_post('deckNames')
    assert 'audio_closures' in resp['result']

    if func == 'create':
        unique_audio_paths = glob(f'./data/{youtube_id}_*_audio.mp4')
        unique_audio_paths = [p for p in unique_audio_paths if 'cloze' not in p]
        assert len(unique_audio_paths) >= 1

        for uniq_aud_path in unique_audio_paths:
            fname_start_end = os.path.basename(uniq_aud_path)
            fname_start_end = os.path.splitext(fname_start_end)[0]
            fname_start_end = fname_start_end.replace('_audio', '')

            front_paths = glob(f'./data/{fname_start_end}_cloze*.mp4')
            if len(front_paths) < 1:
                print('No front paths!')
                continue
            back_card = f'./data/{fname_start_end}_audio.mp4'
            assert os.path.exists(back_card)

            media_existed = False
            for path in front_paths + [back_card]:
                fname = os.path.basename(path)
                resp = _anki_post('retrieveMediaFile', {'filename': fname})
                if resp['result']:
                    media_existed = True
                    continue

                with open(f'{path}', 'rb') as fhan:
                    raw = fhan.read()
                audio_base64 = base64.b64encode(raw).decode('utf-8')
                _anki_post('storeMediaFile',
                           {'filename': fname, 'data': audio_base64})

            if media_existed:
                click.confirm('Media existed. Skip and continue adding?',
                              abort=True)
                continue

            for front_path in front_paths:
                front = os.path.basename(front_path)
                front = os.path.splitext(front)[0]
                params = {
                    'note': {
                        'deckName': 'audio_closures',
                        'modelName': '基本',
                        'fields': {
                            'Front': f'[sound:{front}.mp4]',
                            'Back': f'[sound:{os.path.basename(back_card)}]'
                        },
                        'options': {'allowDuplicate': False},
                        'tags': [],
                    }
                }
                _anki_post('addNote', params)

        return

    if func == 'reset':
        click.confirm('Really reset?', abort=True)

        _anki_post('deleteDecks',
                   {'decks': ['audio_closures'], 'cardsToo': True})
        _anki_post('createDeck', {'deck': 'audio_closures'})

        return


if __name__ == '__main__':
    add_audio_card()  # pylint:disable=no-value-for-parameter
