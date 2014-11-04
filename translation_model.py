class TranslationModel(object):

	def __init__(self, path=None):
		self._tm = {}
		if path:
			self._read_file(path)

	def _read_file(self, path):
		f = open(path, 'r')
		for line in f:
			melody, harmony, prob = line.strip().split(" ||| ")
			self.add_to_model(melody, harmony, float(prob))

	def add_to_model(self, melody, harmony, prob):
		if melody not in self._tm:
			self._tm[melody] = {harmony : prob}
		else:
			self._tm[melody][harmony] = prob

	def get_probability(self, melody, harmony):
		if melody not in self._tm or harmony not in self._tm[melody]:
			raise Exception('No melody/harmony pair for {0}, {1}'.format(melody, harmony))
		else:
			return self._lm[melody][harmony]

	def get_harmonies(self, melody):
		if melody not in self._tm:
			return []
		else:
			return [(k,v) for k,v in self._tm[melody].iteritems()]



def main():
	tm = TranslationModel("data/bass_translation_model_major.txt")
	print tm.get_harmonies("C5")

		
if __name__ == "__main__":
    main()