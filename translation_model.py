from music_utils import *

class TranslationModel(object):

	def __init__(self, harmony_part, melody_part, phrase_path=None, note_path=None):
		self._tm_phrases = {}
		self._tm_notes = {}
		self.harmony_part = harmony_part
		self.melody_part = melody_part
		if phrase_path:
			self._read_file(phrase_path, phrases=True)
		if note_path:
			self._read_file(note_path, phrases=False)

	def _read_file(self, path, phrases):
		f = open(path, 'r')
		for line in f:
			melody_string, harmony_string, prob = line.strip().split(" ||| ")
			if phrases:
				melody_phrase = tuple(melody_string.split())
				harmony_phrase = tuple(harmony_string.split())
				self.add_to_model(melody_phrase, harmony_phrase, float(prob), self._tm_phrases)
			else:
				self.add_to_model(melody_string, harmony_string, float(prob), self._tm_notes)

	def add_to_model(self, melody, harmony, prob, model):
		if melody not in model:
			model[melody] = {harmony : prob}
		else:
			model[melody][harmony] = prob

	def get_probability_phrase(self, melody, harmony):
		if not self._tm_phrases:
			return self.get_probability_notes(melody, harmony)

		m_phrase_rep = get_phrase_rep(melody)
		h_phrase_rep = get_phrase_rep(harmony)
		if m_phrase_rep not in self._tm_phrases:
		 	if harmony is not melody:
				return self.get_probability_notes(melody, harmony)
			else:
				return 1.0
		elif h_phrase_rep not in self._tm_phrases[melody]:
			return self.get_probability_notes(melody, harmony)
		else:
			return self._tm_phrases[m_phrase_rep][h_phrase_rep]

	def get_probability_notes(self, melody, harmony):
		if not self._tm_notes:
			return -1
		total_prob = 1
		for m_note in melody:
			m_rep = get_note_rep(m_note)
			h_notes = harmony.allPlayingWhileSounding(m_note)
			for h_note in h_notes:
				h_note = get_note_rep(h_note)
				if m_rep not in self._tm_notes:
					if h_rep is not m_rep:
						total_prob *= 1e-10
					else:
						total_prob *= 1.0
				elif h_rep not in self._tm_notes[m_rep]:
					total_prob *= 1e-10
				else:
					total_prob *= self._tm_notes[m_rep][h_rep]

		return total_prob


	def get_harmonies(self, melody):
		if melody not in self._tm_phrases:
			return [(melody, 1.0)]
		else:
			return [(k,v) for k,v in self._tm_phrases[melody].iteritems()]

	def write_to_file(self,path):
		f = open(path, 'w')
		for melody_phrase in self._tm_phrases:
			for harmony_phrase in self._tm_phrases[melody_phrase]:
				melody_string = ' '.join(melody_phrase)
				harmony_string = ' '.join(harmony_phrase)
				output_line = ''.join([str(melody_string), ' ||| ', str(harmony_string), ' ||| ', \
					str(self.get_probability(melody_phrase, harmony_phrase)), '\n'])
				f.write(output_line)


def main():
	tm = TranslationModel("Bass", "Soprano", note_path="data/bass_translation_model_major.txt")
	print tm.get_harmonies("C5")

		
if __name__ == "__main__":
    main()