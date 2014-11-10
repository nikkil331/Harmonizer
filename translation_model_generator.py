from music21 import *
import optparse
import re
import sys
from translation_model import TranslationModel
from music_utils import *

class TranslationModelGenerator(object):

	def __init__(self, mode='major', melody_part=0, harmony_part=1, training_composers=['bach', 'handel']):
		self._mode = 'major' if mode == 'major' else 'minor'
		self._melody_part = melody_part
		self._harmony_part = harmony_part
		self._training_paths = []
		#for composer in training_composers:
		#	self._training_paths += corpus.getComposer(composer)
		self._training_paths = corpus.getBachChorales()[50:]
		self._tm_counts = None

	def _update_counts(self, melody, harmony):
		for harmony_note in harmony.flat.notesAndRests:
			if not harmony_note.isNote:
				harmony_rep = 'R'
			else:
				harmony_rep = harmony_note.nameWithOctave
			# test this make sure it works
			harmony_offset = harmony_note.offset
			melody_notes = melody.getElementsByOffset(harmony_offset, offsetEnd=harmony_offset + harmony_note.duration.quarterLength, 
												     mustFinishInSpan=False, mustBeginInSpan=False)
			if harmony_rep not in self._tm_counts:
				d = {}
				self._tm_counts[harmony_rep] = d
			else:
				d = self._tm_counts[harmony_rep]

			for melody_note in melody_notes.flat.notesAndRests:
				if not melody_note.isNote:
					melody_rep = 'R'
				else:
					melody_rep = melody_note.nameWithOctave
				if melody_rep not in d:
					d[melody_rep] = 1
				else:
					d[melody_rep] += 1

	def _create_tm_from_counts(self):
		tm = TranslationModel(harmony_part=self._harmony_part, melody_part=self._melody_part)
		for harmony_note in self._tm_counts:
			total_notes_harmonized = sum(self._tm_counts[harmony_note].values())
			harmony_counts = self._tm_counts[harmony_note].items()
			for (melody_note, count) in harmony_counts:
				prob = count / float(total_notes_harmonized)
				tm.add_to_model(melody_note,harmony_note,prob)
		return tm

	def generate_tm(self):
		self._tm_counts = {}
		num_songs = 0
		num_songs_without_part = 0
		for path in self._training_paths:
			sys.stderr.write('.')
			composition = corpus.parse(path)
			try: 
				keySig = composition.analyze('key')
				if keySig.pitchAndMode[1] != self._mode:
					continue
				num_songs += 1
				transpose(composition)
				melody = composition.parts[self._melody_part]
				harmony = composition.parts[self._harmony_part]
				self._update_counts(melody, harmony)
			except Exception, e:
				num_songs_without_part += 1

		print "Number of songs: {0}".format(num_songs)
		print "Number of songs without {0} : {1}".format(self._harmony_part, num_songs_without_part)

		return self._create_tm_from_counts()




def main():
	tm_generator = TranslationModelGenerator(melody_part="Bass", harmony_part="Alto")
	tm = tm_generator.generate_tm()
	tm.write_to_file('data/bass_alto_translation_model_major.txt')

if __name__ == "__main__":
    main()




