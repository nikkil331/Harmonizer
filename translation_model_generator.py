from music21 import *
import multiprocessing
import optparse
import itertools
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
		self._training_paths = get_barbershop_data()
		self._tm_counts = None

	def _update_counts(self, melody, harmony):
		melody_phrase = []
		begin_offset = 0.0

		for melody_note in melody.flat.notesAndRests:
			melody_phrase.append(get_note_rep(melody_note))
			if len(melody_phrase) == 2:
				# get harmony phrase playing while melody phrase is sounding
				melody_tuple = tuple(melody_phrase)
				end_offset = begin_offset + get_phrase_length_from_rep(melody_tuple)
				harmony_tuple = get_phrase_rep(trim_stream(harmony.flat.notesAndRests, begin_offset, end_offset))
				
				# update counts for this pair of melody and harmony phrases
				if harmony_tuple not in self._tm_counts:
					self._tm_counts[harmony_tuple] = {}
				if melody_tuple not in self._tm_counts[harmony_tuple]:
					self._tm_counts[harmony_tuple][melody_tuple] = 0
				self._tm_counts[harmony_tuple][melody_tuple] += 1

				# update melody phrase sliding window
				melody_phrase = []
				begin_offset = end_offset

	def _create_tm_from_counts(self):
		tm = TranslationModel(harmony_part=self._harmony_part, melody_part=self._melody_part)
		for harmony_note in self._tm_counts:
			total_notes_harmonized = sum(self._tm_counts[harmony_note].values())
			harmony_counts = self._tm_counts[harmony_note].items()
			for (melody_note, count) in harmony_counts:
				prob = count / float(total_notes_harmonized)
				tm.add_to_model(melody_note,harmony_note,prob, tm._tm_phrases)
		return tm

	def generate_tm(self):
		self._tm_counts = {}
		num_songs = 0
		num_songs_without_part = 0
		for composition in training_songs:
			sys.stderr.write('.')
			try: 
				#keySig = composition.analyze('key')
				#if keySig.pitchAndMode[1] != self._mode:
				#	continue
				num_songs += 1
				#transpose(composition)
				melody = composition.parts[self._melody_part]
				harmony = composition.parts[self._harmony_part]
				self._update_counts(melody, harmony)


			except KeyError, e:
				num_songs_without_part += 1

		print "Number of songs: {0}".format(num_songs)
		print "Number of songs without {0} : {1}".format(self._harmony_part, num_songs_without_part)

		return self._create_tm_from_counts()

print "reading in..."
training_songs = [converter.parse(path) for path in get_barbershop_data()]
print "transposing..."
[transpose(s) for s in training_songs]

def main():
	parts = [0,1,2,3]
	map(generate_generator_helper, itertools.permutations(parts, 2))

def generate_generator_helper(t):
	generate_generator(*t)

def generate_generator(melody, harmony):
	print melody, harmony
	tm_generator = TranslationModelGenerator(melody_part=melody, harmony_part=harmony)
	tm = tm_generator.generate_tm()
	tm.write_to_file(tm._tm_phrases, 'data/barbershop/models/{0}_{1}_translation_model_major_rhythm_threshold.txt'.format(melody,harmony))	
if __name__ == "__main__":
    main()




