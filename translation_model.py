class TranslationModel(object):

	def __init__(self, harmony_part, melody_part, path=None):
		self._tm = {}
		self.harmony_part = harmony_part
		self.melody_part = melody_part
		if path:
			self._read_file(path)

	def _read_file(self, path):
		f = open(path, 'r')
		for line in f:
			melody_string, harmony_string, prob = line.strip().split(" ||| ")
			melody_phrase = tuple(melody_string.split())
			harmony_phrase = tuple(harmony_string.split())
			self.add_to_model(melody_phrase, harmony_phrase, float(prob))

	def add_to_model(self, melody, harmony, prob):
		if melody not in self._tm:
			self._tm[melody] = {harmony : prob}
		else:
			self._tm[melody][harmony] = prob

	def get_probability(self, melody, harmony):
		if melody not in self._tm:
		 	if harmony is not melody:
				return 1e-10
			else:
				return 1.0
		elif harmony not in self._tm[melody]:
			return 1e-10
		else:
			return self._tm[melody][harmony]

	def get_harmonies(self, melody):
		if melody not in self._tm:
			return [(melody, 1.0)]
		else:
			return [(k,v) for k,v in self._tm[melody].iteritems()]

	def write_to_file(self,path):
		f = open(path, 'w')
		for melody_phrase in self._tm:
			for harmony_phrase in self._tm[melody_phrase]:
				melody_string = ' '.join(melody_phrase)
				harmony_string = ' '.join(harmony_phrase)
				output_line = ''.join([str(melody_string), ' ||| ', str(harmony_string), ' ||| ', \
					str(self.get_probability(melody_phrase, harmony_phrase)), '\n'])
				f.write(output_line)


def main():
	tm = TranslationModel("Bass", "Soprano", path="data/bass_translation_model_major.txt")
	print tm.get_harmonies("C5")

		
if __name__ == "__main__":
    main()