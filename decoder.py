from music21 import *
import sys
import optparse
import copy
import math
from collections import namedtuple
from translation_model import TranslationModel
from language_model import LanguageModel


def get_score(tm_score, lm_score):
    return tm_score + lm_score

def get_lm_score(context, note):
    return math.log(lm.get_probability(context, note))
    
def get_tm_score(m_note, h_note):
    return math.log(tm.get_probability(m_note, h_note))

def update_hypothesis(curr_hyp, m_note, h_note):
    # update note list
    new_notes = curr_hyp.notes
    new_notes.append(h_note)

    # update context sliding window
    new_context = list(curr_hyp.context)
    if m_note != "R" or new_context[-1] != "R":
        new_context.append(h_note)
    #get last n
    new_context = tuple(new_context[-ngram_size:])

    # update logprob scores
    new_tm_logprob = curr_hyp.tm_logprob + get_tm_score(m_note, h_note)
    new_lm_logprob = curr_hyp.lm_logprob + get_lm_score(curr_hyp.context, h_note) 

    return hypothesis(new_notes, new_context, new_tm_logprob, new_lm_logprob)

def get_note_rep(note):
    if note.isNote:
        return note.nameWithOctave
    else:
        return "R"

optparser = optparse.OptionParser()
optparser.add_option("--song", dest="song", default="bach/bwv390", help="Song to decode")
optparser.add_option("--tm", dest="tm", default="data/translation_model_major.txt", help="File containing translation model")
optparser.add_option("--lm", dest="lm", default="data/language_model_major.txt", help="File containing language model")
optparser.add_option("--n", dest="n", default='5', help="N-gram size")
(opts, _) = optparser.parse_args()

ngram_size = int(opts.n)
lm = LanguageModel(opts.lm)
tm = TranslationModel(opts.tm)
song = corpus.parse(opts.song)

hypothesis = namedtuple("hypothesis", "notes, context, tm_logprob, lm_logprob")
beam = [hypothesis(["S"], ("S"), 0.0, 0.0)]
melody = song.parts[0]

for m in melody.flat.notesAndRests:
    m_rep = get_note_rep(m)
    new_beam = []
    for hyp in beam:
        for (h, _) in tm.get_harmonies(m_rep):
            new_hyp = update_hypothesis(hyp, m_rep, h)
            new_beam.append(new_hyp)
    beam = new_beam
    sys.stderr.write (".")
    beam = sorted(beam, key = lambda hyp: get_score(hyp.tm_logprob, hyp.lm_logprob), reverse=True)[:500]

winner = beam[0].notes[1:]
harmony = copy.deepcopy(melody)
for (i, h) in enumerate(harmony.flat.notesAndRests):
    if winner[i] == "R":
        length = h.quarterLength
        h = note.Rest()
        h.quarterLength = length
    else:
        h.pitch = pitch.Pitch(winner[i])

score = stream.Score([melody, harmony])
score.show()






