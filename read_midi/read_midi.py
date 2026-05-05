import mido
from mido import MidiFile

for msg in MidiFile('freude.mid').play():
    print(msg)
    print(msg.type)
    print(msg.note)
