from music21 import *
import sys
import optparse
import copy
import math
from collections import namedtuple
from translation_model import TranslationModel
from language_model import LanguageModel
from music_utils import *

hypothesis = namedtuple("hypothesis", "notes, context, context_size, tm_logprob, lm_logprob")

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

    def _update_hypothesis(self, curr_hyp, m_phrases, h_phrase):
        bar_indices = []
        for (i, m_note) in enumerate(m_phrases[self._parts[0][0]]):
            if m_note == "BAR":
                bar_indices.append(i)

        new_notes = curr_hyp.notes[:]
        new_size = curr_hyp.context_size
        new_context = list(curr_hyp.context)
        new_lm_logprob = curr_hyp.lm_logprob
        curr_index = 0
        for h_note in h_phrase:
            if curr_index in bar_indices:
                new_notes.append("BAR")
                new_context.append("BAR")
                curr_index+=1
            if not (h_note == "R" and new_context[-1] == "R"):
                new_context.append(h_note)  
                new_size += 1 
            new_notes.append(h_note)
            new_lm_logprob+=get_lm_score(self._lm, tuple(new_context), h_note)
            while new_size > self._lm.ngram_size:
                if new_context.pop(0) != "BAR":
                    new_size-=1
            curr_index+=1

        # update tm logprob scores
        new_tm_logprob = curr_hyp.tm_logprob
        for (i, (part, m_phrase)) in enumerate(m_phrases.items()):
            new_tm_logprob += get_tm_score(self._tms[i], tuple(m_phrase), tuple(h_phrase))
        return hypothesis(new_notes, new_context, new_size, new_tm_logprob, new_lm_logprob)

    def _grow_hyps_in_beam(self, melody_phrases, beam):
        new_beam = []
        phrases_without_bar = {}
        for p in self._parts:
            phrases_without_bar[p[0]] = tuple([n for n in melody_phrases[p[0]] if n != "BAR"])
        for hyp in beam:
            possible_harmony_phrase = set([phrase_rep for (phrase_rep, _) in self._tms[0].get_harmonies(phrases_without_bar[self._parts[0][0]])])
            for (i, phrase) in enumerate(self._parts[1:]):
                next_set = set([note_rep for (note_rep, _) in self._tms[i + 1].get_harmonies(phrases_without_bar[self._parts[i + 1][0]])])
                possible_harmony_phrase = possible_harmony_phrase.intersection(next_set)
            if len(possible_harmony_phrase) == 0:
                possible_harmony_phrase = set([('R', 'R')])
            for h in possible_harmony_phrase:
                new_hyp = self._update_hypothesis(hyp, melody_phrases, h)
                new_beam.append(new_hyp)
        return new_beam

    def decode(self):
        beam = [hypothesis([], (), 0, 0.0, 0.0)]
        melody_phrases = {}
        num_notes = 0
        # get note sequence for part

        for (measure_idx, measure) in enumerate(self._parts[0][1][1:]):
            for p in self._parts:
                if p[0] in melody_phrases:
                    melody_phrases[p[0]].append("BAR")
                else:
                    melody_phrases[p[0]] = ["BAR"]

            for note_idx in xrange(len(measure.notesAndRests)):
                for p in self._parts:
                    if p[0] in melody_phrases:
                        raw_note = p[1][measure_idx + 1].notesAndRests[note_idx]
                        melody_phrases[p[0]].append(get_note_rep(raw_note))
                    else:
                        raw_note = p[1][measure_idx + 1].notesAndRests[note_idx]
                        melody_phrases[p[0]] = [get_note_rep(raw_note)]
                num_notes += 1
                if num_notes == 2:
                    beam = self._grow_hyps_in_beam(melody_phrases, beam)
                    beam = sorted(beam, key = lambda hyp: get_score(hyp.tm_logprob, hyp.lm_logprob), reverse=True)[:1000]
                    num_notes = 0
                    melody_phrases = {}
                    sys.stderr.write(".")


        beam = self._grow_hyps_in_beam({p[0]:("END",) for p in self._parts}, beam)
        beam = sorted(beam, key = lambda hyp: get_score(hyp.tm_logprob, hyp.lm_logprob), reverse=True)[:1000]
        winner = [n for n in beam[0].notes if n != "BAR" and n != "END"]

        # translate note sequence into music21 stream
        harmony = stream.Stream()
        for n_rep in winner:
            pitch, duration = n_rep.split(":")
            if pitch == "R":
                n = note.Rest(quarterLength=float(duration))
            else:
                n = note.Note(pitch, quarterLength=float(duration))
            harmony.append(n)

        return harmony




