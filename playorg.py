#!/usr/bin/env python3
# playorg.py: example CLI application for using organya.py
# PyAudio is used for feeding wave data to your speakers.
# for more library info, see https://people.csail.mit.edu/hubert/pyaudio/
import organya
import pyaudio
import struct
import sys

# 12 = C-1
KEYS_LUT = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']
def org_update(self):
    for i in range(8):
        s = self.state[i]
        k = s['key']
        if k != 255:
            print(f'{KEYS_LUT[k%12]}{k//12}', end=' ')
        else:
            print('   ', end=' ')
    
    print('\r', end='')

if __name__ == '__main__':
    if len(sys.argv) <= 1:
        print('usage: playorg FILE')
        exit(1)
    
    org = None
    with open(sys.argv[1], 'rb') as org_read:
        org = organya.Organya(org_read.read())
    
    with open('wavetable.bin', 'rb') as wt_read:
        org.load_wavetable(wt_read.read())
    
    org.set_sample_rate(11025) # 11KHz due to renderer being slow
    org.samples_this_tick = 0
    
    org.on_update = org_update
    def pa_callback(in_data, frame_count, time_info, status):
        left_ch = [0.0]*frame_count
        right_ch = left_ch
    
        left_ch, right_ch = org.synth(left_ch, right_ch)
    
        data = bytearray()
    
        for i in range(len(left_ch)):
            for l in struct.pack('<f', left_ch[i]):
                data.append(l)
            for r in struct.pack('<f', right_ch[i]):
                data.append(r)
        
        return (bytes(data), pyaudio.paContinue)
    
    pa = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paFloat32,
                        channels=2,
                        rate=org.sample_rate,
                        output=True,
                        stream_callback=pa_callback)
    
    input() # do nothing until input is passed
    
    stream.close()
    pa.terminate()
