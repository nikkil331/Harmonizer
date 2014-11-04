from music21 import *
import optparse
import re
import sys


class LanguageModelGenerator(object):

	def __init__(self, ngram_size=5, mode='major', part=1, \
				 output_file='data/language_model.txt', training_composers=['bach', 'handel']):
		self._ngram_size = ngram_size
		self._mode = 'major' if mode == 'major' else 'minor'
		self._part = part
		self._output_file = output_file
		self._training_paths = []
		#for composer in training_composers:
		#	self._training_paths += corpus.getComposer(composer)
		self._training_paths = corpus.getBachChorales()
		self._lm = None

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

	def _update_counts(self, harmony):
		sliding_window = ('S',)
		for note in harmony.flat.notesAndRests:
			if not note.isNote:
				note_rep = 'R'
			else:
				note_rep = note.nameWithOctave
			if sliding_window not in self._lm:
				self._lm[sliding_window] = {note_rep: 1}
			else:
				if note_rep not in self._lm[sliding_window]:
					self._lm[sliding_window][note_rep] = 1
				else:
					self._lm[sliding_window][note_rep] += 1
			list_window = list(sliding_window)
			if not (list_window[-1] is 'R' and note_rep is 'R'):
				list_window.append(note_rep)
			if len(list_window) > self._ngram_size:
				list_window.pop(0)
			sliding_window = tuple(list_window)

	def _update_probs_from_counts(self, smoothing):
		for context in self._lm:
			total_notes_after_context = len(self._lm[context])
			context_counts = self._lm[context].items()[:]
			for (note, count) in context_counts:
				#approximately 4 octaves in our vocabulary (48 notes)
				prob = (count + smoothing) / float(total_notes_after_context + (48*smoothing))
				self._lm[context][note] = prob
			self._lm[context]["<UNK>"] = smoothing / float(total_notes_after_context + (48*smoothing))


	def generate_lm(self, smoothing=1e-5):
		self._lm = {}
		num_songs = 0
		num_songs_without_part = 0
		for path in self._training_paths:
			sys.stderr.write('.')
			composition = corpus.parse(path)
			try:
				harmony = composition.parts[self._part]
				keySig = composition.analyze('key')
				if keySig.pitchAndMode[1] == self._mode:
					num_songs += 1
					self.transpose(composition)
					self._update_counts(harmony)
			except Exception, e:
				num_songs_without_part += 1
		self._update_probs_from_counts(smoothing)

		print "Number of songs: {0}".format(num_songs)
		print "Number of songs without {0} : {1}".format(self._part, num_songs_without_part)

	'''
	Returns language model dictionary
	'''
	def get_lm(self):
		if not self._lm:
			self.generate_lm()
		return self._lm()

	def write_lm(self):
		f = open(self._output_file, 'w')
		for context in self._lm:
			for note in self._lm[context]:
				output_line = ''.join([' '.join(context), ' ||| ', str(note), ' ||| ', str(self._lm[context][note]), '\n'])
				f.write(output_line)

def main():
	lm_generator = LanguageModelGenerator(part='Bass', output_file='data/bass_language_model_major.txt', ngram_size=5)
	lm_generator.generate_lm()
	lm_generator.write_lm()

if __name__ == "__main__":
    main()



