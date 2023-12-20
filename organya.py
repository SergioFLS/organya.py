# organya.py: hand-translated port of https://github.com/alula/organya-js
# This port is available under two licenses. You may choose either one of them:
# Option 1: MIT No Attribution
# 
# Copyright (c) 2023 SergioFLS
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# 
# Option 2: BSD 3-Clause License
# 
# Copyright (c) 2023 SergioFLS
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# 
# The original organya.js is available under the BSD 3-Clause License:
# 
# Copyright (c) 2021, Alula, Rxo Inverse, Studio Pixel
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# 
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# 
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import pyaudio
import time
import struct
import math

drums = []
wave_table = b''
freq_table = [261, 278, 294, 311, 329, 349, 371, 391, 414, 440, 466, 494]
pan_table = [0, 43, 86, 129, 172, 215, 256, 297, 340, 383, 426, 469, 512]
adv_table = [1, 1, 2, 2, 4, 8, 16, 32]
oct_table = [32, 64, 64, 128, 128, 128, 128, 128]

def sign_byte(h: int):
    return (h&0xff) if not (h & 128) else (h&0xff)-256

class Song:
    def __init__(self, data: bytearray | bytes):
        p = 0

        # Org-
        org1 = data[p:p+4]
        p += 4
        if not org1 == b'Org-':
            raise Exception('Invalid magic')
        
        orgVersion = data[p:p+2]
        p += 2
        if orgVersion != b'02':
            raise Exception('Invalid version')
        
        self.wait = struct.unpack('<H', data[p:p+2])[0]
        p += 2
        self.meas = list(struct.unpack('<BB', data[p:p+2]))
        p += 2
        self.start = struct.unpack('<I', data[p:p+4])[0]
        p += 4
        self.end = struct.unpack('<I', data[p:p+4])[0]
        p += 4

        self.instruments = []

        for i in range(16):
            freq = struct.unpack('<H', data[p:p+2])[0]
            p += 2
            wave, pipi = struct.unpack('<BB', data[p:p+2])
            p += 2
            notes = struct.unpack('<H', data[p:p+2])[0]
            p += 2

            self.instruments.append({'freq': freq, 'wave': wave, 'pipi': pipi, 'notes': notes})
        
        self.tracks = []

        for i in range(16):
            track = []
            #track['length'] = self.instruments[i]['notes']

            for j in range(self.instruments[i]['notes']):
                track.append({'pos': 0, 'key': 0, 'len': 0, 'vol': 0, 'pan': 0})
            
            for j in range(self.instruments[i]['notes']):
                track[j]['pos'] = struct.unpack('<i', data[p:p+4])[0]
                p += 4
            
            for j in range(self.instruments[i]['notes']):
                track[j]['key'] = struct.unpack('<B', data[p:p+1])[0]
                p += 1
            
            for j in range(self.instruments[i]['notes']):
                track[j]['len'] = struct.unpack('<B', data[p:p+1])[0]
                p += 1
            
            for j in range(self.instruments[i]['notes']):
                track[j]['vol'] = struct.unpack('<B', data[p:p+1])[0]
                p += 1
            
            for j in range(self.instruments[i]['notes']):
                track[j]['pan'] = struct.unpack('<B', data[p:p+1])[0]
                p += 1
            
            self.tracks.append(track)

class Organya:
    def __init__(self, data: bytearray | bytes):
        self.song = Song(data)
        self.node = None
        self.on_update = None
        self.t = 0
        self.play_pos = 0
        self.samples_per_tick = 0
        self.samples_this_tick = 0
        self.state = []
        for i in range(16):
            self.state.append({
                't': 0,
                'key': 0,
                'frequency': 0,
                'octave': 0,
                'pan': 0.0,
                'vol': 1.0,
                'length': 0,
                'num_loops': 0,
                'playing': False,
                'looping': False,
            })
    
    def synth(self, left_buffer: list[float], right_buffer: list[float]):
        """Generates audio data. Returns a tuple of arrays."""
        left_out = left_buffer
        right_out = right_buffer
        for sample in range(len(left_buffer)):
            if self.samples_this_tick == 0: self.update()
            left_out[sample] = 0
            right_out[sample] = 0

            for i in range(16):
                if self.state[i]['playing']:
                    samples = 256 if (i < 8) else drums[i - 8]['samples']

                    self.state[i]['t'] += (self.state[i]['frequency'] / self.sample_rate) * adv_table[self.state[i]['octave']]

                    if math.floor(self.state[i]['t']) >= samples:
                        if self.state[i]['looping'] and self.state[i]['num_loops'] != 1:
                            self.state[i]['t'] %= samples
                            if self.state[i]['num_loops'] != 1:
                                self.state[i]['num_loops'] -= 1
                        else:
                            self.state[i]['t'] = 0
                            self.state[i]['playing'] = False
                            continue
                    
                    t = math.floor(self.state[i]['t']) & ~(adv_table[self.state[i]['octave']] - 1)
                    pos = t % samples
                    pos2 = pos if (not self.state[i]['looping'] and t == samples) \
                        else (math.floor(self.state[i]['t'] + adv_table[self.state[i]['octave']]) & ~(adv_table[self.state[i]['octave']] - 1)) % samples
                    s1 = (sign_byte(wave_table[256 * self.song.instruments[i]['wave'] + pos]) / 256) if (i < 8) \
                        else (((sign_byte(wave_table[drums[i - 8]['file_pos'] + pos]) & 0xff) - 0x80) / 256)
                    s2 = (sign_byte(wave_table[256 * self.song.instruments[i]['wave'] + pos2]) / 256) if (i < 8) \
                        else (((sign_byte(wave_table[drums[i - 8]['file_pos'] + pos2]) & 0xff) - 0x80) / 256)
                    fract = (self.state[i]['t'] - pos) / adv_table[self.state[i]['octave']]

                    # Perform linear interpolation
                    s = s1 + (s2 - s1) * fract

                    s *= math.pow(10, ((self.state[i]['vol'] - 255) * 8) / 2000)

                    pan = (pan_table[self.state[i]['pan']] - 256) * 10
                    left = 1
                    right = 1

                    if pan < 0:
                        right = math.pow(10, pan / 2000)
                    elif pan > 0:
                        left = math.pow(10, -pan / 2000)
                    
                    left_out[sample] += s * left
                    right_out[sample] += s * right
                
            self.samples_this_tick += 1
            if self.samples_this_tick == self.samples_per_tick:
                self.play_pos += 1
                self.samples_this_tick = 0

                if self.play_pos == self.song.end:
                    self.play_pos = self.song.start

        return (left_out, right_out)
    
    def update(self):
        if self.on_update: self.on_update(self)

        for track in range(8):
            note = None
            for n in self.song.tracks[track]:
                if n['pos'] == self.play_pos:
                    note = n
                    break
            
            if note:
                if note['key'] != 255:
                    octave = note['key'] // 12
                    key = note['key'] % 12

                    if self.state[track]['key'] == 255:
                        self.state[track]['key'] = note['key']
                    
                        self.state[track]['frequency'] = freq_table[key] * oct_table[octave] + (self.song.instruments[track]['freq'] - 1000)
                        if self.song.instruments[track]['pipi'] != 0 and not self.state[track]['playing']:
                            self.state[track]['num_loops'] = ((octave + 1) * 4)
                    elif self.state[track]['key'] != note['key']:
                        self.state[track]['key'] = note['key']
                        self.state[track]['frequency'] = freq_table[key] * oct_table[octave] + (self.song.instruments[track]['freq'] - 1000)
                
                    if self.song.instruments[track]['pipi'] != 0 and not self.state[track]['playing']:
                        self.state[track]['num_loops'] = ((octave + 1) * 4)
                
                    self.state[track]['octave'] = octave
                    self.state[track]['playing'] = True
                    self.state[track]['looping'] = True
                    self.state[track]['length'] = note['len']
                
                if self.state[track]['key'] != 255:
                    if note['vol'] != 255: self.state[track]['vol'] = note['vol']
                    if note['pan'] != 255: self.state[track]['pan'] = note['pan']
            
            if self.state[track]['length'] == 0:
                if self.state[track]['key'] != 255:
                    if self.song.instruments[track]['pipi'] == 0:
                        self.state[track]['looping'] = False
                    
                    self.state[track]['playing'] = False
                    self.state[track]['key'] = 255
            else:
                self.state[track]['length'] -= 1
        
        for track in range(8, 15):
            note = None
            for n in self.song.tracks[track]:
                if n['pos'] == self.play_pos:
                    note = n
                    break
            
            if not note: continue

            if note['key'] != 255:
                self.state[track]['frequency'] = note['key'] * 800 + 100
                self.state[track]['t'] = 0
                self.state[track]['playing'] = True
            
            if note['vol'] != 255: self.state[track]['vol'] = note['vol']
            if note['pan'] != 255: self.state[track]['pan'] = note['pan']

    def load_wavetable(self, data: bytearray | bytes):
        global wave_table
        wave_table = data
        global drums

        i = 256 * 100
        while i < len(wave_table) - 4:
            if wave_table[i:i+4] == b'WAVE':
                i += 4
                riff_id = wave_table[i:i+4]
                i += 4
                riff_len = wave_table[i:i+4]
                i += 4
                if riff_id != b'fmt\x20':
                    continue

                start_pos = i
                a_format = struct.unpack('<H', wave_table[i:i+2])[0]
                i += 2

                if a_format != 1:
                    # Invalid audio format
                    i = start_pos + riff_len
                    continue

                channels = struct.unpack('<H', wave_table[i:i+2])[0]
                i += 2

                if channels != 1:
                    # Only 1 channel files are supported
                    i = start_pos + riff_len
                    continue

                samples = struct.unpack('<I', wave_table[i:i+4])[0]
                i += 10 # skip rate + padding
                bits = struct.unpack('<H', wave_table[i:i+2])[0]
                i += 2
                wav_data = wave_table[i:i+4]
                i += 4
                wav_len = struct.unpack('<I', wave_table[i:i+4])[0]
                i += 4

                if wav_data != b'data':
                    i = start_pos + riff_len
                    continue

                drums.append({'file_pos':i, 'bits': bits, 'channels': channels, 'samples': wav_len})
                i += wav_len
            i += 1
        pass

    def set_sample_rate(self, rate: int):
        """Helper function to set a specific sample rate for playback. Automatically sets samples_per_tick."""
        self.sample_rate = rate
        self.samples_per_tick = math.floor((self.sample_rate / 1000) * self.song.wait)