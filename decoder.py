from music21 import *
import sys
import optparse
import copy
import math
from collections import namedtuple
from translation_model import TranslationModel
from language_model import LanguageModel
import music_utils

hypothesis = namedtuple("hypothesis", "notes, context, context_size, tm_logprob, lm_logprob")

def get_note_rep(note):
    if note.isNote:
        return note.nameWithOctave
    else:
        return "R"

def get_score(tm_score, lm_score):
    return tm_score + lm_score

def get_lm_score(lm, context, note):
    return math.log(lm.get_probability(context, note))
    
def get_tm_score(tm, m_note, h_note):
    return math.log(tm.get_probability(m_note, h_note))

class Decoder(object):
    def __init__(self, parts, lm, tms):
        #self._original_key = parts[0][1].analyze('key').pitchAndMode[0]
        self._parts = parts
        #for (name, stream) in self._parts:
        #    music_utils.transpose(stream, 'C')
        self._lm = lm
        self._tms = tms

    def _update_hypothesis(self, curr_hyp, m_notes, h_note):
        # update note list
        new_notes = curr_hyp.notes[:]
        new_notes.append(h_note)
       
        # update context sliding window
        new_size = curr_hyp.context_size
        new_context = list(curr_hyp.context)
        if not (h_note == "R" and new_context[-1] == "R"):
            new_context.append(h_note)  
            if h_note != "BAR":
                new_size += 1     

        while new_size > self._lm.ngram_size:
            if new_context.pop(0) != "BAR":
                new_size -= 1
        # update logprob scores
        new_tm_logprob = curr_hyp.tm_logprob
        for (i, m_note) in enumerate(m_notes):
            new_tm_logprob += get_tm_score(self._tms[i], m_note, h_note)
        if h_note != "BAR":
            new_lm_logprob = curr_hyp.lm_logprob + get_lm_score(self._lm, tuple(curr_hyp.context), h_note)
        else:
            new_lm_logprob = curr_hyp.lm_logprob
        return hypothesis(new_notes, new_context, new_size, new_tm_logprob, new_lm_logprob)

    def _grow_hyps_in_beam(self, notes, beam):
        new_beam = []
        for hyp in beam:
            possible_harmonies = set([note_rep for (note_rep, _) in self._tms[0].get_harmonies(notes[0])])
            for (i, note) in enumerate(notes[1:]):
                next_set = set([note_rep for (note_rep, _) in self._tms[i + 1].get_harmonies(note)])
                possible_harmonies = possible_harmonies.intersection(next_set)
            for h in possible_harmonies:
                new_hyp = self._update_hypothesis(hyp, notes, h)
                new_beam.append(new_hyp)
        return new_beam

    def decode(self):
        beam = [hypothesis([], (), 0, 0.0, 0.0)]

        # get note sequence for part
        for (measure_idx, measure) in enumerate(self._parts[0][1][1:]):
            beam = self._grow_hyps_in_beam(["BAR" for _ in self._parts], beam)
            beam = sorted(beam, key = lambda hyp: get_score(hyp.tm_logprob, hyp.lm_logprob), reverse=True)[:1000]
            for (note_idx, _) in enumerate(measure.notesAndRests):
                m_reps = []
                for p in self._parts:
                    note = p[1][measure_idx + 1].notesAndRests[note_idx]
                    m_reps.append(get_note_rep(note))
                beam = self._grow_hyps_in_beam(m_reps, beam)
                beam = sorted(beam, key = lambda hyp: get_score(hyp.tm_logprob, hyp.lm_logprob), reverse=True)[:1000]
                sys.stderr.write(".")

        beam = self._grow_hyps_in_beam(["END" for _ in self._parts], beam)
        beam = sorted(beam, key = lambda hyp: get_score(hyp.tm_logprob, hyp.lm_logprob), reverse=True)[:1000]
        winner = [n for n in beam[0].notes if n != "BAR" and n != "END"]
        score = get_score(beam[0].tm_logprob, beam[0].lm_logprob)

        # translate note sequence into music21 stream
        harmony = copy.deepcopy(self._parts[0][1])
        for (i, h) in enumerate(harmony.flat.notesAndRests):
            if winner[i] == "R":
                length = h.quarterLength
                h = note.Rest()
                h.quarterLength = length
            else:
                h.pitch = pitch.Pitch(winner[i])

        return (harmony, score)




