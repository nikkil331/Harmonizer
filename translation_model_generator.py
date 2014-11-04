from music21 import *
import optparse
import re
import sys

class TranslationModelGenerator(object):

	def __init__(self, mode='major', melody_part=0, harmony_part=1, \
				 output_file='data/translation_model.txt', training_composers=['bach', 'handel']):
		self._mode = 'major' if mode == 'major' else 'minor'
		self._melody_part = melody_part
		self._harmony_part = harmony_part
		self._output_file = output_file
		self._training_paths = []
		for composer in training_composers:
			self._training_paths += corpus.getComposer(composer)
		self._tm = None

	def transpose(self, stream):
		curr_pitch = stream.analyze('key').pitchAndMode[0].name
		new_pitch = 'C' if self._mode == 'major' else 'A'
		# what is 5 and does this generalize to the bass part???
		sc = scale.ChromaticScale(curr_pitch + '5')
		sc_pitches = [str(p) for p in sc.pitches]
		num_halfsteps = 0
		pattern = re.compile(new_pitch + '\d')
		for pitch in sc_pitches:
			if pattern.match(pitch):
				break
			else:
				num_halfsteps = num_halfsteps + 1
		stream.flat.transpose(num_halfsteps, inPlace=True)

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
			if harmony_rep not in self._tm:
				d = {}
			else:
				d = self._tm[harmony_rep]

			for melody_note in melody_notes.flat.notesAndRests:
				if not melody_note.isNote:
					melody_rep = 'R'
				else:
					melody_rep = melody_note.nameWithOctave
				if melody_rep not in d:
					d[melody_rep] = 1
				else:
					d[melody_rep] += 1

	def _update_probs_from_counts(self):
		for harmony_note in self._tm:
			total_notes_harmonized = len(self._tm[harmony_note])
			for melody_note in self._tm[harmony_note]:
				prob = self._tm[harmony_note][melody_note] / float(total_notes_harmonized)

	def generate_tm(self):
		self._tm = {}
		num_songs = 0
		for path in self._training_paths:
			sys.stderr.write('.')
			composition = corpus.parse(path)
			if self._melody_part >= len(composition.parts):
				continue
			if self._harmony_part >= len(composition.parts):
				continue
			keySig = composition.analyze('key')
			if keySig.pitchAndMode[1] != self._mode:
				continue
			num_songs = num_songs + 1
			self.transpose(composition)
			melody = composition.parts[self._melody_part]
			harmony = composition.parts[self._harmony_part]
			self._update_counts(melody, harmony)
			self._update_probs_from_counts()
		print num_songs

	def write_tm(self):
		f = open(self._output_file, 'w')
		for harmony_note in self._tm:
			for melody_note in self._tm[harmony_note]:
				output_line = ''.join([str(melody_note), ' ||| ', str(harmony_note), ' ||| ', str(self._tm[harmony_note][melody_note]), '\n'])
				f.write(self._output_file)


def main():
	tm_generator = TranslationModelGenerator(melody_part=0, harmony_part=3, output_file='data/bass_translation_model_major.txt')
	tm_generator.generate_tm()
	tm_generator.write_tm()

if __name__ == "__main__":
    main()




