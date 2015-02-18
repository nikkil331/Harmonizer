import optparse
from language_model import LanguageModel
from translation_model import TranslationModel
from music21 import *
from collections import namedtuple
from music_utils import *
import sys

optparser = optparse.OptionParser()
optparser.add_option("--tm", dest="tm_path", default="data/translation_model_major.txt", help="File containing translation model")
optparser.add_option("--lm", dest="lm_path", default="data/language_model_major.txt", help="File containing language model")
optparser.add_option("--output", dest="output_file", default="evaluation_scores.txt", help="Destination of results")
(opts, _) = optparser.parse_args()

class Evaluator(object):

	def __init__(self):
		sys.stderr.write('Parsing...')
		self.testSongs = []
		for s in corpus.getBachChorales()[:50]:
			sys.stderr.write('.')
			self.testSongs.append(corpus.parse(s))
		sys.stderr.write('\n')

		#transpose all songs
		sys.stderr.write('Transposing...')
		for s in self.testSongs:
			sys.stderr.write('.')
			transpose(s)
		sys.stderr.write('\n')

	def evaluate_language_model(self, lm):
		results = []
		songsSkipped = 0
		for s in self.testSongs:

			try:
				keySig = s.analyze('key')
				if keySig.pitchAndMode[1] != 'major':
					continue
				harmony = s.parts[lm.part].flat.notesAndRests
				hyp = lm_hypothesis(["S"], ("S"), 0.0)
				for note in harmony:
					note_rep = get_note_rep(note)
					hyp = update_lm_hypothesis(lm, hyp, note_rep)
				results.append(-float(hyp.lm_logprob))
			except KeyError, e:
				songsSkipped += 1
		#print "Songs skipped: {0}".format(songsSkipped)
		return sum(results)

	def evaluate_translation_model(self, tm):
		results = []
		songsSkipped = 0
		for s in self.testSongs:
			try:
				keySig = s.analyze('key')
				if keySig.pitchAndMode[1] != 'major':
					continue
				phrase_hyp = 0.0
				note_hyp = 0.0
				melody = s.parts[tm.melody_part]
				harmony = s.parts[tm.harmony_part]
				m_notes = get_phrase_rep(melody.flat.notesAndRests)
				h_notes = get_phrase_rep(harmony.flat.notesAndRests)
				cur_melody_phrase = []
				for (i, m_note) in enumerate(m_notes):
					if i >= 1 and i < len(m_notes) - 1:
						harmony_phrase = notes_playing_while_sounding(h_notes, m_notes, i-1, i+1)
						result = tm.get_probability(m_notes[i-1:i+1], harmony_phrase)
						phrase_hyp += -float(result[0])
						note_hyp += -float(result[1])
				results.append((phrase_hyp, note_hyp))

			except KeyError, e:
				songsSkipped += 1

		#print "Songs skipped: {0}".format(songsSkipped)
		return (sum(map(lambda x: x[0], results)), sum(map(lambda x: x[1], results)))

	def evaluate_combined(self, tm, lm, phrase_weight, note_weight, lm_weight):
		phrase_score, notes_score = self.evaluate_translation_model(tm)
		lm_score = self.evaluate_language_model(lm)
		return phrase_weight*phrase_score + note_weight*notes_score + lm_weight*lm_score

def main():
	existing_parts = ["Soprano", "Alto", "Tenor", "Bass"]
	generated_parts = ["Alto", "Tenor", "Bass"]
	for p1 in existing_parts:
		for p2 in generated_parts:
			if p1 == p2:
				continue
			print p1, p2
			e = Evaluator()
			lm_major = LanguageModel(path="data/{0}_language_model_major.txt".format(p2), part=p2)
			tm_major = TranslationModel(phrase_path="data/{0}_{1}_translation_model_major_rhythm.txt".format(p1, p2), 
										note_path="data/{0}_{1}_translation_model_major.txt".format(p1, p2),
										harmony_part=p2, melody_part=p1)

			#print "TM major: ", str(e.evaluate_translation_model(tm_major))
			print "unweighted with phrases: ", str(e.evaluate_combined(tm_major, lm_major, 0.5726547297805934, 0.061101102321016725, 0.0020716756164958113))
if __name__ == "__main__":
    main()