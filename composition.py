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
	# TODO: fix add more tm args
	def create_part(self, name, lm_file, tm_phrase_files, tm_note_files):
		if len(self._parts) == 0:
			return
		lm = LanguageModel(path=lm_file, part=name)
		tms = []
		for (i, (f1, f2)) in enumerate(zip(tm_phrase_files, tm_note_files)):
			tms.append(TranslationModel(phrase_path=f1, note_path=f2, harmony_part=name, melody_part=self._parts[i][0]))
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
	c.create_part('Bass', \
				  'data/bass_language_model_major.txt', \
				  ['data/Soprano_Bass_translation_model_major_rhythm.txt'], \
				  ['data/Soprano_Bass_translation_model_major.txt'])
	#c.create_part('Alto', 'data/alto_language_model_major.txt', ['data/Soprano_Alto_translation_model_major_rhythm.txt',\
	#														    'data/Bass_Alto_translation_model_major_rhythm.txt'])
	#c.create_part('Tenor', 'data/Tenor_language_model_major.txt', ['data/Soprano_Tenor_translation_model_major_rhythm.txt',\
	#															 'data/Bass_Tenor_translation_model_major_rhythm.txt',\
	#															 'data/Alto_Tenor_translation_model_major_rhythm.txt'])
	c.play()

if __name__ == "__main__":
    main()

