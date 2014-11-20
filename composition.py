from music21 import *
import decoder
from translation_model import TranslationModel
from language_model import LanguageModel
from collections import namedtuple
from itertools import *

class Composition(object):

	def __init__(self):
		self._parts = []

	def add_part(self, name, stream):
		self._parts.append((name, stream))

	'''
	Should only be called if there exist >= 1 part 
	in the composition already
	'''
	def create_part(self, name, lm_file, tm_files):
		if len(self._parts) == 0:
			return
		lm = LanguageModel(path=lm_file, part=name)
		tms = []
		for (i, f) in enumerate(tm_files):
			tms.append(TranslationModel(path=f, harmony_part=name, melody_part=self._parts[i][0]))
		d = decoder.Decoder(self._parts, lm, tms)
		new_part, score = d.decode()
		self._parts.append((name, new_part))
		return score


	def play(self):
		score = stream.Score([part[1] for part in self._parts])
		score.show()

def main():

	test_song = corpus.parse('bach/bwv390')
	parts = ["Alto", "Bass", "Tenor"]

	c = Composition()
	c.add_part("Soprano", test_song.parts["Soprano"])
	c.create_part("Bass", 'data/Bass_language_model_major.txt', ["data/Soprano_Bass_translation_model_major.txt"])
	c.create_part("Alto", 'data/Alto_language_model_major.txt', ["data/Soprano_Alto_translation_model_major.txt",\
														 	    "data/Bass_Alto_translation_model_major.txt"])
	c.create_part("Tenor", 'data/Tenor_language_model_major.txt', ["data/Soprano_Tenor_translation_model_major.txt",\
														    	  "data/Bass_Tenor_translation_model_major.txt",\
														   		  "data/Alto_Tenor_translation_model_major.txt"])	
	c.play()

'''
	for part_ordering in permutations(parts):
		c = Composition()
		c.add_part("Soprano", test_song.parts["Soprano"])
		score = 0
		parts_in_composition = ["Soprano"]
		for p in part_ordering:
			translation_models = ['data/{0}_{1}_translation_model_major.txt'.format(m, p) for m in parts_in_composition]
			score += c.create_part(p, 'data/{0}_language_model_major.txt'.format(p), translation_models)
			parts_in_composition.append(p)
		print score
		c.play()	'''	

if __name__ == "__main__":
    main()

