from music21 import converter,instrument
import os
import argparse

argparser = argparse.ArgumentParser()
argparser.add_argument("input", help="directory with midi files whose instruments need to be fixed")
args = argparser.parse_args()

directory = args.input

for f in os.listdir(directory):
	s = converter.parse(directory + "/" + f)
	for el in s.recurse():
	    if 'Instrument' in el.classes:
	        el.activeSite.replace(el, instrument.Piano())

	s.write('midi', directory + "/" + f)