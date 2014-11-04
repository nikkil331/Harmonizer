class LanguageModel(object):

	def __init__(self, path=None):
		self._lm = {}
		if path:
			self._read_file(path)

	def _read_file(self, path):
		f = open(path, 'r')
		for line in f:
			context_string, note, prob = line.strip().split(" ||| ")
			context = tuple(context_string.split())
			self.add_to_model(context, note, float(prob))

	def add_to_model(self, context, note, prob):
		if context not in self._lm:
			self._lm[context] = {note : prob}
		else:
			self._lm[context][note] = prob

	def get_probability(self, context, note):
		if context not in self._lm:
			return 1e-5
		elif note not in self._lm[context]:
			return self._lm[context]["<UNK>"]
		else:
			return self._lm[context][note]

	def get_contexts(self):
		return self._lm.keys()

	def get_notes_for_context(self, context):
		return self._lm[context].items()

def main():
	lm = LanguageModel("data/bass_language_model_major.txt")
	print lm.get_notes_for_context(('G3', 'C4', 'R', 'C3', 'D3'))

if __name__ == "__main__":
    main()