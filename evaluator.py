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
			keySig = s.analyze('key')
			if keySig.pitchAndMode[1] != 'major':
				continue
			try:
				harmony = s.parts[lm.part].flat.notesAndRests
				hyp = lm_hypothesis(["S"], ("S"), 0.0)
				for note in harmony:
					note_rep = get_note_rep(note)
					hyp = update_lm_hypothesis(lm, hyp, note_rep)
				results.append(float(hyp.lm_logprob)/len(harmony))
			except KeyError, e:
				songsSkipped += 1
		#print "Songs skipped: {0}".format(songsSkipped)
		return sum(results)/len(results)

	def evaluate_translation_model(self, tm):
		results = []
		songsSkipped = 0
		for s in self.testSongs:
			keySig = s.analyze('key')
			if keySig.pitchAndMode[1] != 'major':
				continue
			try:
				hyp = 0.0
				melody = s.parts[tm.melody_part]
				harmony = s.parts[tm.harmony_part]
				for h in harmony.flat.notesAndRests:
					h_note = get_note_rep(h)
					m_notes =  [get_note_rep(m) for m in melody.allPlayingWhileSounding(h).flat.notesAndRests]
					for m_note in m_notes:
						hyp = update_tm_hypothesis(tm, hyp, m_note, h_note)
				results.append(float(hyp)/len(harmony.flat.notesAndRests))

				'''
				for m in melody.flat.notesAndRests:
					m_note = get_note_rep(m)
					h_notes = [get_note_rep(h) for h in get_harmony_notes(m, harmony)]
					for h_note in h_notes:
						hyp = update_tm_hypothesis(tm, hyp, m_note, h_note)
				results.append(float(hyp)/len(harmony.flat.notesAndRests))
				'''

			except KeyError, e:
				songsSkipped += 1

		#print "Songs skipped: {0}".format(songsSkipped)
		return sum(results)/len(results)

def main():
	e = Evaluator()
	lm_major = LanguageModel(path='data/Soprano_language_model_major.txt', part="Soprano")
	lm_both = LanguageModel(path='data/Soprano_language_model_both.txt', part="Soprano")

	tm_major = TranslationModel(path="data/Soprano_Alto_translation_model_major.txt", harmony_part="Alto", melody_part="Soprano")
	tm_both = TranslationModel(path="data/Soprano_Alto_translation_model_both.txt", harmony_part="Alto", melody_part="Soprano")
	tm_adjusted = TranslationModel(path="data/Soprano_Alto_translation_model_major_adjusted.txt", harmony_part="Alto", melody_part="Soprano")

	print "Language major: " + str(e.evaluate_language_model(lm_major))
	print "Language both: " + str(e.evaluate_language_model(lm_both))

	print "Translation major: " + str(e.evaluate_translation_model(tm_major))
	print "Translation both: " + str(e.evaluate_translation_model(tm_both))
	print "Translation adjusted: " + str(e.evaluate_translation_model(tm_adjusted))

if __name__ == "__main__":
    main()