from music21 import *
import decoder
from translation_model import TranslationModel
from language_model import LanguageModel
from collections import namedtuple

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
			print f
			tms.append(TranslationModel(path=f, harmony_part=name, melody_part=self._parts[i][0]))
		d = decoder.Decoder(self._parts, lm, tms)
		new_part = d.decode()
		self._parts.append((name, new_part))


	def play(self):
		score = stream.Score([part[1] for part in self._parts])
		score.show()

def main():
	test_song = corpus.parse('bach/bwv390')
	c = Composition()
	c.add_part('Soprano', test_song.parts['Soprano'])
	c.create_part('Bass', 'data/bass_language_model_major.txt', ['data/bass_translation_model_major.txt'])
	c.create_part('Alto', 'data/alto_language_model_major.txt', ['data/soprano_alto_translation_model_major.txt',\
																 'data/bass_alto_translation_model_major.txt'])
	c.play()

if __name__ == "__main__":
    main()

