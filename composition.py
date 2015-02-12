from music21 import *
import decoder
import multiprocessing
from translation_model import TranslationModel
from language_model import LanguageModel
from collections import namedtuple


class Composition(object):

	def __init__(self):
		self._parts = []

	def add_part(self, name, stream):
		self._parts.append((name, stream))


	def play(self):
		score = stream.Score([part[1] for part in self._parts])
		score.show()


	'''
	Should only be called if there exist >= 1 part 
	in the composition already
	'''
	def create_part(self, name, lm_file, tm_phrase_files, tm_note_files):
		lm = LanguageModel(path=lm_file, part=name)
		tms = []
		for (i, (f1, f2)) in enumerate(zip(tm_phrase_files, tm_note_files)):
			tms.append(TranslationModel(phrase_path=f1, note_path=f2, harmony_part=name, melody_part=self._parts[i][0]))
		d = decoder.Decoder(self._parts, lm, tms)
		hyp = d.decode(1)[0]
		new_part = d.hyp_to_stream(hyp)
		return (name, new_part, decoder.get_score(hyp))

	def best_new_part(self, parts):
		second_parts = map(lambda x: self.create_part(x, 'data/{0}_language_model_major.txt'.format(x),
											['data/{0}_{1}_translation_model_major_rhythm.txt'.format(y[0],x) for y in self._parts],
											['data/{0}_{1}_translation_model_major.txt'.format(y[0],x) for y in self._parts]), 
										parts)
		winner = max(second_parts, key=lambda x: x[2])
		self._parts.append((winner[0],winner[1]))
		return winner[0]


def main():
	test_song = corpus.parse('bach/bwv390')
	parts = ['Alto', 'Tenor', 'Bass']
	c = Composition()
	c.add_part('Soprano', test_song.parts['Soprano'])
	while parts:
		parts.remove(c.best_new_part(parts))
	c.play()

if __name__ == "__main__":
    main()

