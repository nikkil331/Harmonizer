from music_utils import *

class LanguageModel(object):

	def __init__(self, part, path=None):
		self._lm = {}
		self.part = part
		if path:
			self._read_file(path)

	def _read_file(self, path):
		f = open(path, 'r')
		self.set_ngram_size(int(f.readline()))
		for line in f:
			context_string, note, prob = line.strip().split(" ||| ")
			context = tuple(context_string.split())
			self.add_to_model(context, note, float(prob))

	def set_ngram_size(self, ngram_size):
		self.ngram_size = ngram_size

	def add_to_model(self, context, note, prob):
		if context not in self._lm:
			self._lm[context] = {note : prob}
		else:
			self._lm[context][note] = prob

	def get_probability(self, context, phrase):
		total_prob = 0
		context_tuple = tuple([s.split(":")[0] for s in get_phrase_rep(context)])
		for note in phrase:
			note_rep = get_note_rep(note).split(":")[0]
			if note_rep == "BAR":
				context_tuple += ("BAR",)
			else:
				if context_tuple not in self._lm:
					total_prob += math.log(1e-10)
				elif note_rep not in self._lm[context_tuple]:
					total_prob += math.log(self._lm[context_tuple]["<UNK>"])
				else:
					total_prob += math.log(self._lm[context_tuple][note_rep])
				context_tuple = list(context_tuple)
				if context_tuple.pop(0) == "BAR":
					context_tuple.pop(0)
				context_tuple.append(note_rep)
				context_tuple = tuple(context_tuple)
		return total_prob


	def get_contexts(self):
		return self._lm.keys()

	def get_notes_for_context(self, context):
		if context not in self._lm:
			return []
		return self._lm[context].items()

	def write_to_file(self, path):
		f = open(path, 'w')
		f.write(str(self.ngram_size) + '\n')
		for context in self._lm:
			for note in self._lm[context]:
				context_str = ' '.join(context)
				output_line = ''.join([str(context_str), ' ||| ', str(note), ' ||| ', \
					str(self.get_probability(context, note)), '\n'])
				f.write(output_line)

def main():
	lm = LanguageModel("Bass", path="data/bass_language_model_major.txt")
	print lm.get_notes_for_context(('G3', 'C4', 'R'))

if __name__ == "__main__":
    main()