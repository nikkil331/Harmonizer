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
		melody_phrase_raw = stream.Stream()
		for melody_note in melody.flat.notesAndRests:

			melody_phrase_raw.append(melody_note)
			if len(melody_phrase_raw) == 2:
				melody_phrase = []
				melody_duration = 0
				for melody_note in melody_phrase_raw:
					length = melody_note.duration.quarterLength
					melody_duration += length
					if not melody_note.isNote:
						melody_phrase.append('R:' + str(length))
					else:
						melody_phrase.append(melody_note.nameWithOctave + ":" + str(length))

				melody_phrase_tuple = tuple(melody_phrase)

				harmony_phrase_raw = [h for note in\
					melody_phrase_raw for h in harmony.flat.notesAndRests\
					.allPlayingWhileSounding(note) ]

				harmony_phrase = []
				for (i, harmony_note) in enumerate(harmony_phrase_raw):
					length = 0
					if i == 0:
						# harmony_note.offset is negative (if it stats before the melody phrase)
						# or zero. Adding harmony_note.offset chops of the note length that starts
						# before the pphrase
						length = harmony_note.duration.quarterLength + harmony_note.offset
					elif i == len(harmony_phrase_raw) - 1:
						harmony_duration = sum([float(s.split(":")[1]) for s in harmony_phrase])
						if harmony_duration + harmony_note.duration.quarterLength > melody_duration:
							length = melody_duration - harmony_duration
						else:
							length = harmony_note.duration.quarterLength
					else:
						if harmony_note.offset < 0:
							harmony_phrase.pop()
						length = harmony_note.duration.quarterLength

					if length == 0:
						continue

					if not harmony_note.isNote:
						harmony_phrase.append('R:' + str(length))
					else:
						harmony_phrase.append(harmony_note.nameWithOctave + ":" + str(length))

				harmony_phrase_tuple = tuple(harmony_phrase)

				if harmony_phrase_tuple not in self._tm_counts:
					d = {}
					self._tm_counts[harmony_phrase_tuple] = d

				if melody_phrase_tuple not in self._tm_counts[harmony_phrase_tuple]:
					self._tm_counts[harmony_phrase_tuple][melody_phrase_tuple] = 1
				else:
					self._tm_counts[harmony_phrase_tuple][melody_phrase_tuple] += 1

				melody_phrase_raw = stream.Stream()

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

			except KeyError, e:
				num_songs_without_part += 1

		print "Number of songs: {0}".format(num_songs)
		print "Number of songs without {0} : {1}".format(self._harmony_part, num_songs_without_part)

		return self._create_tm_from_counts()




def main():
	parts = ["Soprano", "Alto", "Tenor", "Bass"]
	for p1 in parts:
		for p2 in parts:
			if p1 != p2:
				print p1, p2
				tm_generator = TranslationModelGenerator(melody_part=p1, harmony_part=p2)
				tm = tm_generator.generate_tm()
				tm.write_to_file('data/{0}_{1}_translation_model_major_rhythm.txt'.format(p1,p2))


if __name__ == "__main__":
    main()




