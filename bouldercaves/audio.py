"""
Various audio output options. Here the specific audio library code is located.
Supported audio output libraries:
- miniaudio
- sounddevice (both thread+blocking stream, and nonblocking callback stream variants)

It can play multiple samples at the same time via real-time mixing, and you can
loop samples as well without noticable overhead (great for continous effects or music)
Wav (PCM) files and .ogg files can be loaded (requires oggdec from the
vorbis-tools package to decode those)

High level api functions:
  init_audio
  play_sample
  silence_audio
  shutdown_audio

Original version written by Irmen de Jong (irmen@razorvine.net)
Extended version by Michael Kamensky

License: GNU GPL 3.0, see LICENSE
"""

import pkgutil
import time
import tempfile
import os
import random
import subprocess
from typing import Union, Dict, Tuple
from synthplayer import streaming, params as synth_params
from synthplayer.sample import Sample
from synthplayer.playback import Output, best_api
from . import user_data_dir


__all__ = ["init_audio", "play_sample", "silence_audio", "shutdown_audio"]


def prepare_oggdec_exe():
    # on windows, make sure the embedded oggdec.exe is made available
    if os.name == "nt":
        filename = user_data_dir + "oggdec.exe"
        if not os.path.isfile(filename):
            oggdecexe = pkgutil.get_data(__name__, "sounds/oggdec.exe")
            with open(filename, "wb") as exefile:
                exefile.write(oggdecexe)
        streaming.AudiofileToWavStream.oggdec_executable = filename
        return True
    return False


# audio parameters
synth_params.norm_samplerate = 44100
try:
    if not prepare_oggdec_exe():
        subprocess.call("oggdec", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    streaming.AudiofileToWavStream.ffprobe_executable = ""  # force use of oggdec instead of ffmpeg
    streaming.AudiofileToWavStream.ffmpeg_executable = ""  # force use of oggdec instead of ffmpeg
except IOError:
    # no oggdec, stick with ffmpeg
    pass


samples = {}    # type: Dict[str, Union[str, Sample]]


class SoundEngine:
    def __init__(self, samples_to_load: Dict[str, Tuple[Union[str, Sample], int]]) -> None:
        global samples
        samples.clear()
        self.output = Output(mixing="mix")
        if any(isinstance(smp, str) for smp, _ in samples_to_load.values()):
            print("Loading sound files...")
        for name, (filename, max_simultaneously) in samples_to_load.items():
            if isinstance(filename, Sample):
                samples[name] = filename
            else:
                data = pkgutil.get_data(__name__, "sounds/" + filename)
                if data:
                    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ogg")
                    try:
                        tmp.write(data)
                        tmp.close()
                        samples[name] = Sample(streaming.AudiofileToWavStream(tmp.name), name).stereo()
                    finally:
                        os.remove(tmp.name)
                else:
                    raise SystemExit("corrupt package; sound data is missing")
            self.output.set_sample_play_limit(name, max_simultaneously)
        print("Sound API initialized:", self.output.audio_api)

    def play_sample(self, samplename, repeat=False, after=0.0):
        self.output.play_sample(samples[samplename], repeat, after)

    def silence(self, sid_or_name=None):
        if sid_or_name:
            self.output.stop_sample(sid_or_name)
        else:
            self.output.silence()

    def close(self):
        self.output.close()


sound_engine = None


def init_audio(samples_to_load) -> SoundEngine:
    global sound_engine
    sound_engine = SoundEngine(samples_to_load)
    return sound_engine


def play_sample(samplename, repeat=False, after=0.0):
    return sound_engine.play_sample(samplename, repeat, after)

# Krissz Engine specific boulder fall sound, a choice from one of two possibilities
def play_krissz_boulder_sample(repeat=False, after=0.0):
    return sound_engine.play_sample(random.choice(["boulder", "boulder2"]), repeat, after)

# Krissz Engine sometimes plays a single diamond fall sound, and sometimes two overlapping diamond fall sounds
def play_krissz_diamond_sample():
    diamond_sounds = [1, 2, 3, 4, 5, 6]
    first_sound = random.choice(diamond_sounds)
    sound_engine.play_sample("diamond" + str(first_sound))
    if random.randint(1, 2) == 2: # 50% chance. Consider revising?
        diamond_sounds.remove(first_sound)
        sound_engine.play_sample("diamond" + str(random.choice(diamond_sounds)), after=0.170)

def play_timeout_sample(id):
    for i in range(9):
        silence_audio("timeout" + str(i))
    sound_engine.play_sample("timeout" + str(id))


def silence_audio(sid_or_name=None):
    sound_engine.silence(sid_or_name)


def shutdown_audio():
    sound_engine.close()


def check_api():
    a = best_api()
    a.close()


if __name__ == "__main__":
    smp = Sample.from_raw_frames([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], 2, 44100, 1)
    chunks = smp.chunked_frame_data(chunksize=51, repeat=True)
    for _ in range(60):
        print(next(chunks).tobytes())
    if os.name == "nt":
        prepare_oggdec_exe()
    sound_engine = init_audio({
        "explosion": ("explosion.ogg", 99),
        "amoeba": ("amoeba.ogg", 99),
        "game_over": ("game_over.ogg", 99)
    })
    print("PLAY SAMPLED SOUNDS...")
    amoeba_sid = sound_engine.play_sample("amoeba", repeat=True)
    time.sleep(3)
    print("PLAY ANOTHER SOUND!")
    sid = sound_engine.play_sample("game_over", repeat=False)
    time.sleep(0.5)
    print("STOPPING AMOEBA!")
    sound_engine.silence("amoeba")
    time.sleep(0.5)
    print("PLAY ANOTHER SOUND!")
    sid = sound_engine.play_sample("explosion", repeat=True)
    time.sleep(4)
    print("STOP SOUND!")
    sound_engine.silence()
    time.sleep(2)
    print("SHUTDOWN!")
    sound_engine.close()
    time.sleep(0.5)
