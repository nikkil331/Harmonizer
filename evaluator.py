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
				hyp = 0.0
				melody = s.parts[tm.melody_part]
				harmony = s.parts[tm.harmony_part]
				for m in melody.flat.notesAndRests:
					m_note = get_note_rep(m)
					h_notes = [get_note_rep(h) for h in get_harmony_notes(m, harmony)]
					for h_note in h_notes:
						hyp = update_tm_hypothesis(tm, hyp, m_note, h_note)
				results.append(float(hyp))

			except KeyError, e:
				songsSkipped += 1

		#print "Songs skipped: {0}".format(songsSkipped)
		return sum(results)

def main():
	e = Evaluator()
	lm_major = LanguageModel(path="data/bass_language_model_major.txt", part="Bass")
	lm_both = LanguageModel(path="data/bass_language_model_both.txt", part="Bass")

	tm_major = TranslationModel(path="data/Soprano_Bass_translation_model_major.txt", harmony_part="Bass", melody_part="Soprano")
	tm_both = TranslationModel(path="data/Soprano_Bass_translation_model_both.txt", harmony_part="Bass", melody_part="Soprano")
	tm_adjusted = TranslationModel(path="data/Soprano_Bass_translation_model_major_adjusted.txt", harmony_part="Bass", melody_part="Soprano")
	print "LM major: " + str(e.evaluate_language_model(lm_major))
	print "LM both: " + str(e.evaluate_language_model(lm_both))
	print "TM major: " + str(e.evaluate_translation_model(tm_major))
	print "TM both: " + str(e.evaluate_translation_model(tm_both))
	print "TM adjusted: " + str(e.evaluate_translation_model(tm_adjusted))

if __name__ == "__main__":
    main()