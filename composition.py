from music21 import *
import decoder
from translation_model import TranslationModel
from language_model import LanguageModel
from collections import namedtuple
import sys

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
		new_part = d.hyp_to_stream(d.decode(1)[0])
		self._parts.append((name, new_part))


	def play(self):
		score = stream.Score([part[1] for part in self._parts])
		score.show()

        def save(self, name):
                score = stream.Score([part[1] for part in self._parts])
                f = open(name, 'w')
                f.write(musicxml.m21ToString.fromMusic21Object(score))
                f.close()

def main():
        test_song = converter.parse('cis401/Harmonizer/ttls.xml')
	#test_song = corpus.parse('bach/bwv390')
	c = Composition()
	c.add_part('Soprano', test_song.parts['Piano'])
        sys.stderr.write("Creating bass\n")
        c.create_part('Bass', \
                      'cis401/Harmonizer/data/bass_language_model_major.txt', \
                      ['cis401/Harmonizer/data/Soprano_Bass_translation_model_major_rhythm.txt'], \
                      ['cis401/Harmonizer/data/Soprano_Bass_translation_model_major.txt'])
        sys.stderr.write("Creating alto\n")
        c.create_part('Alto', 'cis401/Harmonizer/data/alto_language_model_major.txt', \
                      ['cis401/Harmonizer/data/Soprano_Alto_translation_model_major_rhythm.txt', \
                       'cis401/Harmonizer/data/Bass_Alto_translation_model_major_rhythm.txt'], \
                      ['cis401/Harmonizer/data/Soprano_Alto_translation_model_major.txt',\
                       'cis401/Harmonizer/data/Bass_Alto_translation_model_major.txt'])
        sys.stderr.write("Creating tenor\n")
        c.create_part('Tenor', 'cis401/Harmonizer/data/Tenor_language_model_major.txt', \
                      ['cis401/Harmonizer/data/Soprano_Tenor_translation_model_major_rhythm.txt',\
                       'cis401/Harmonizer/data/Bass_Tenor_translation_model_major_rhythm.txt',\
                       'cis401/Harmonizer/data/Alto_Tenor_translation_model_major_rhythm.txt'], \
                      ['cis401/Harmonizer/data/Soprano_Tenor_translation_model_major.txt',\
                       'cis401/Harmonizer/data/Bass_Tenor_translation_model_major.txt',\
                       'cis401/Harmonizer/data/Alto_Tenor_translation_model_major.txt'])

        c.save('ttls_generated.xml')

if __name__ == "__main__":
    main()

