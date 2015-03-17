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

class ScoreEvaluator(object):
	def __init__(self, song):
		self.song = song

	def evaluate(self):
		num_measures = len(self.song.parts[0].getElementsByClass('Measure'))
		theoryAnalysis.theoryAnalyzer.identifyParallelFifths(self.song)
		p_fifths = self.song.analysisData['ResultDict']['parallelFifths']
		theoryAnalysis.theoryAnalyzer.identifyImproperDissonantIntervals(self.song)
		improper_dissonant_intervals = self.song.analysisData['ResultDict']['improperDissonantIntervals']
		theoryAnalysis.theoryAnalyzer.identifyImproperResolutions(self.song)
		improper_resolutions = self.song.analysisData['ResultDict']['improperResolution']
		#theoryAnalysis.theoryAnalyzer.identifyOpensIncorrectly(self.song)
		#theoryAnalysis.theoryAnalyzer.identifyClosesIncorrectly(self.song)
		print "# parallel fifths per measure: {0}".format(float(len(p_fifths))/num_measures)
		print "# improper dissonant intervals per measure: {0}".format(float(len(improper_dissonant_intervals))/num_measures)
		print "# improper resolutions per measure: {0}".format(float(len(improper_resolutions))/num_measures)
		# print "opens incorrectly: {0}".format(self.song.analysisData['ResultDict']['opensIncorrectly'])
		# print "closes incorrectly: {0}".format(self.song.analysisData['ResultDict']['closesIncorrectly'][0].text)
		# print "Parallel fifths:"
		# print '\n'.join(map(lambda x: x.text, p_fifths))
		# print "Improper dissonances:"
		# print '\n'.join(map(lambda x: x.text, improper_dissonant_intervals))


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
	'''e = Evaluator()

	tm_soprano_bass = TranslationModel(phrase_path="data/Soprano_Bass_translation_model_major_rhythm.txt", note_path="data/Soprano_Bass_translation_model_major.txt", harmony_part="Bass", melody_part="Soprano")
	tm_alto_bass = TranslationModel(phrase_path="data/Alto_Bass_translation_model_major_rhythm.txt", note_path="data/Alto_Bass_translation_model_major.txt", harmony_part="Bass", melody_part="Soprano")

	print "TM S B: " + str(e.evaluate_translation_model(tm_soprano_bass))
	print "TM A B: " + str(e.evaluate_translation_model(tm_alto_bass))'''
	print "+++ACTUAL_BACH+++"
	e = ScoreEvaluator(corpus.parse('bach/bwv390'))
	e.evaluate()
	print "+++BACH+++"
	e1 = ScoreEvaluator(converter.parse("bwv390_with_weights.xml"))
	e1.evaluate()
	print "+++BACH_SKIP_GRAM+++"
	e5 = ScoreEvaluator(converter.parse("bach_with_skips.xml"))
	e5.evaluate()
	print "+++BACH_NOTE_BASED+++"
	e4 = ScoreEvaluator(converter.parse("bach_note_based.xml"))
	e4.evaluate()
	print "+++OLD_BACH+++"
	e3 = ScoreEvaluator(converter.parse("bach_scaled.xml"))
	e3.evaluate()
	print "+++TTLS+++"
	e2 = ScoreEvaluator(converter.parse("ttls_with_weights.xml"))
	e2.evaluate()

if __name__ == "__main__":
    main()