import os
import re
import argparse
from music21 import *

argparser = argparse.ArgumentParser()
argparser.add_argument("input", help="directory with xml files to be converted")
argparser.add_argument("output", help="directory to write midi files to")
args = argparser.parse_args()

input_directory = args.input
output_directory = args.output

for fname in os.listdir(input_directory):
	file_path = input_directory + "/" + fname
	_, extension = os.path.splitext(file_path)
	if extension == ".xml":
		midi_path = output_directory + "/" + fname[:-4] + ".mid" 
		print file_path
		c = converter.parse(file_path)
		mf = midi.translate.streamToMidiFile(c)
		mf.open(midi_path, 'wb')
		mf.write()
		mf.close()