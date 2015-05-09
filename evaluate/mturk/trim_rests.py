import os
import sys
from music21 import *

input_directory = sys.argv[1]
output_directory = sys.argv[2]

for f in os.listdir(input_directory):
    path = input_directory + "/" + f
    print path
    s = converter.parse(path)
    melody = s.parts[0].flat.notesAndRests
    n = melody[0]
    while n.isRest:
        print "popping"
        melody.pop(0)
        n = melody[0]

    n = melody[-1]
    while n.isRest:
        print "popping"
        melody.pop(-1)
        n = melody[-1]

    melody.insert(0, s.parts[0].getKeySignatures()[0])
    xf = open(output_directory + "/" + f, 'w')
    xf.write(musicxml.m21ToString.fromMusic21Object(melody))
    xf.close()
