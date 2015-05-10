import os
import re
from music21 import *

input_directory = "/Users/nicolelimtiaco/Documents/Penn/fa14/cis400/mturk_clips/bach/melody_line_chunks"
output_directory = "/Users/nicolelimtiaco/Documents/Penn/fa14/cis400/algorithmic-composition/midi"


for fname in os.listdir(input_directory):
	path = input_directory + "/" + fname
	midi_path = output_directory + "/" + fname[:-4] + ".mid" 
	print path
	c = converter.parse(path)
	mf = midi.translate.streamToMidiFile(c)
	mf.open(midi_path, 'wb')
	mf.write()
	mf.close()