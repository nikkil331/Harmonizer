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
    new_notes = curr_hyp.notes[:]
    new_notes.append(h_note)

    # update context sliding window
    new_context = list(curr_hyp.context)
    if m_note != "R" or new_context[-1] != "R":
        new_context.append(h_note)
    #get last n
    new_size = curr_hyp.context_size

    if h_note != "BAR":
        new_size += 1

    while new_size > lm.ngram_size:
        if new_context.pop(0) != "BAR":
            new_size -= 1

    if len([n for n in new_context if n != "BAR"]) != new_size:
        print "HERE"
    # update logprob scores
    new_tm_logprob = curr_hyp.tm_logprob + get_tm_score(m_note, h_note)
    if h_note != "BAR":
        new_lm_logprob = curr_hyp.lm_logprob + get_lm_score(tuple(curr_hyp.context), h_note)
    else:
        new_lm_logprob = curr_hyp.lm_logprob
    return hypothesis(new_notes, new_context, new_size, new_tm_logprob, new_lm_logprob)

def get_note_rep(note):
    if note.isNote:
        return note.nameWithOctave
    else:
        return "R"

def grow_hyps_in_beam(note, beam, tm):
    new_beam = []
    for hyp in beam:
        for (h, _) in tm.get_harmonies(note):
            new_hyp = update_hypothesis(hyp, note, h)
            new_beam.append(new_hyp)
    return new_beam

optparser = optparse.OptionParser()
optparser.add_option("--song", dest="song", default="bach/bwv390", help="Song to decode")
optparser.add_option("--tm", dest="tm", default="data/translation_model_major.txt", help="File containing translation model")
optparser.add_option("--lm", dest="lm", default="data/language_model_major.txt", help="File containing language model")
(opts, _) = optparser.parse_args()

lm = LanguageModel(path=opts.lm, part="Bass")
tm = TranslationModel(path=opts.tm, harmony_part="Bass", melody_part="Soprano")
song = corpus.parse(opts.song)

hypothesis = namedtuple("hypothesis", "notes, context, context_size, tm_logprob, lm_logprob")
beam = [hypothesis([], (), 0, 0.0, 0.0)]
melody = song.parts[0]

for measure in melody[1:]:
    beam = grow_hyps_in_beam("BAR", beam, tm)
    beam = sorted(beam, key = lambda hyp: get_score(hyp.tm_logprob, hyp.lm_logprob), reverse=True)[:500]
    for (i, m) in enumerate(measure.notesAndRests):
        print beam[0].lm_logprob
        m_rep = get_note_rep(m)
        beam = grow_hyps_in_beam(m_rep, beam, tm)
        beam = sorted(beam, key = lambda hyp: get_score(hyp.tm_logprob, hyp.lm_logprob), reverse=True)[:500]
        sys.stderr.write(".")

beam = grow_hyps_in_beam("END", beam, tm)
beam = sorted(beam, key = lambda hyp: get_score(hyp.tm_logprob, hyp.lm_logprob), reverse=True)[:500]

winner = [n for n in beam[0].notes if n != "BAR" and n != "END"]
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







