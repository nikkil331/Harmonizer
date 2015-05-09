import os
import optparse
from collections import namedtuple
import sys

from music21 import *

from language_model import LanguageModel
from translation_model import TranslationModel
from music_utils import *

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
        print "# parallel fifths per measure: {0}".format(float(len(p_fifths)) / num_measures)
        print "# improper dissonant intervals per measure: {0}".format(
            float(len(improper_dissonant_intervals)) / num_measures)
        print "# improper resolutions per measure: {0}".format(float(len(improper_resolutions)) / num_measures)

class PereplexityEvaluator(object):
    def __init__(self, testSongs):
        self.testSongs = testSongs
        # transpose all songs
        sys.stderr.write('Transposing...')
        for s in self.testSongs:
            sys.stderr.write('.')
            transpose(s, "C")
        sys.stderr.write('\n')

    def evaluate_language_model(self, lm):
        results = []
        songsSkipped = 0
        for s in self.testSongs:
            try:
                harmony = s.parts[lm.part].flat.notesAndRests
                hyp = lm_hypothesis(["S"], ("S"), 0.0)
                for note in harmony:
                    note_rep = get_note_rep(note)
                    hyp = update_lm_hypothesis(lm, hyp, note_rep)
                results.append(-float(hyp.lm_logprob))
            except KeyError, e:
                songsSkipped += 1
        return sum(results)

    def evaluate_translation_model(self, tm):
        results = []
        songsSkipped = 0
        for s in self.testSongs:
            try:
                phrase_hyp = 0.0
                note_hyp = 0.0
                melody = s.parts[tm.melody_part]
                harmony = s.parts[tm.harmony_part]
                m_notes = get_phrase_rep(melody.flat.notesAndRests)
                h_notes = get_phrase_rep(harmony.flat.notesAndRests)
                cur_melody_phrase = []
                for (i, m_note) in enumerate(m_notes):
                    if i >= 1 and i < len(m_notes) - 1:
                        harmony_phrase = notes_playing_while_sounding(h_notes, m_notes, i - 1, i + 1)
                        result = tm.get_probability(m_notes[i - 1:i + 1], harmony_phrase)
                        phrase_hyp += -float(result[0])
                        note_hyp += -float(result[1])
                results.append((phrase_hyp, note_hyp))

            except KeyError, e:
                songsSkipped += 1

        return (sum(map(lambda x: x[0], results)), sum(map(lambda x: x[1], results)))

    def evaluate_combined(self, tm, lm, phrase_weight, note_weight, lm_weight):
        phrase_score, notes_score = self.evaluate_translation_model(tm)
        lm_score = self.evaluate_language_model(lm)
        total_score = (phrase_weight*phrase_score) + (note_weight*notes_score) + (lm_weight*lm_score)
        normalized_score = total_score/sum([len(s.parts[0].getElementsByClass("Measure")) for s in self.testSongs])
        return normalized_score


def get_bach_test_songs():
    test_songs = []
    for s in corpus.getBachChorales()[:50]:
        comp = corpus.parse(s)
        keySig = comp.analyze('key')
        if keySig.pitchAndMode[1] == 'major':
            test_songs.append(comp)
    return test_songs


def get_random_test_songs():
    test_songs = []
    for f in os.listdir("anti_examples"):
        song_path = os.path.join("anti_examples", f)
        if os.path.isfile(song_path):
            comp = converter.parse(song_path)
            test_songs.append(comp)
    return test_songs


def getPerplexityScores(directory, lm_suffix, note_suffix, phrase_suffix, weights):
    test_songs = get_bach_test_songs()
    e = PereplexityEvaluator(test_songs)
    existing_parts = ["Soprano", "Alto", "Tenor", "Bass"]
    generated_parts = ["Alto", "Tenor", "Bass"]
    scores = {}
    for p1 in existing_parts:
        for p2 in generated_parts:
            if p1 == p2:
                continue
            lm_major = LanguageModel(path="{0}/{1}_{2}".format(directory, p2, lm_suffix), part=p2)
            tm_major = TranslationModel(phrase_path="{0}/{1}_{2}_{3}".format(directory, p1, p2, 
                                                                             phrase_suffix),
                                        note_path="{0}/{1}_{2}_{3}".format(
                                            directory, p1, p2, note_suffix),
                                        harmony_part=p2, melody_part=p1)
            score = e.evaluate_combined(tm_major, lm_major, weights[0], weights[1], weights[2])
            scores[(p1, p2)] = score
    return scores

def getTheoryScores():
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

def main():
    optparser = optparse.OptionParser()
    optparser.add_option("--mode", dest="mode", default="perplexity", 
                    help="Which evaluation type to run: perplexity or theoretical. Default is perplexity")
    optparser.add_option("--directory", dest="dir", default=".",
                    help="Directory where models live. Default is the current directory.")
    optparser.add_option("--tm_note_suffix", dest="tm_note_suffix", default="translation_model_major.txt",
                     help="Filename suffix for note translation models")
    optparser.add_option("--tm_phrase_suffix", dest="tm_phrase_suffix", default="translation_model_major_rhythm.txt",
                     help="Filename suffix for phrase translation models")
    optparser.add_option("--lm_suffix", dest="lm_suffix", default="language_model_major.txt",
                     help="Filename suffix for language models")
    optparser.add_option("--lm_weight",
                    dest="lm_weight",
                    default="1", 
                    help="Weight for language model. Default is 1")
    optparser.add_option("--tm_note_weight", 
                    dest="tm_note_weight", 
                    default="1", 
                    help="Weight for note translation model model. Default is 1")
    optparser.add_option("--tm_phrase_weight", 
                    dest="tm_phrase_weight", 
                    default="1", 
                    help="Weight for phrase translation model model. Default is 1")
    (opts, _) = optparser.parse_args()

    if opts.mode != "perplexity":
        scores = getTheoryScores()
    else:
        scores = getPerplexityScores(opts.dir, 
                                    opts.lm_suffix, opts.tm_note_suffix, opts.tm_phrase_suffix,
                                    (float(opts.tm_phrase_weight), 
                                     float(opts.tm_note_weight),
                                     float(opts.lm_weight)))
        for (k, v) in scores.items():
            print "%s : %f" % (k, v)


if __name__ == "__main__":
    main()