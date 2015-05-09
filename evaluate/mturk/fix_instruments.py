from music21 import converter,instrument
import os

directory = "/Users/nicolelimtiaco/Documents/Penn/fa14/cis400/evaluation/mturk/clips/uamp/harmonized_chunks"

for f in os.listdir(directory):
	s = converter.parse(directory + "/" + f)
	for el in s.recurse():
	    if 'Instrument' in el.classes:
	        el.activeSite.replace(el, instrument.Piano())

	s.write('midi', directory + "/" + f)