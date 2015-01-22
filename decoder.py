from music21 import *
import sys
import optparse
import copy
import math
from collections import namedtuple
from ordered_set import OrderedSet
from translation_model import TranslationModel
from language_model import LanguageModel
from music_utils import *
import gc

hypothesis = namedtuple("hypothesis", "notes, duration, context, context_size, tm_logprob, lm_logprob")

def get_score(hyp):
    return (hyp.tm_logprob + hyp.lm_logprob)/float(hyp.duration)

def get_lm_score(lm, context, phrase):
    return lm.get_probability(context, phrase)
    
def get_tm_score(tm, m_phrase, h_phrase):
    return tm.get_probability(m_phrase, h_phrase)

class Decoder(object):
    def __init__(self, parts, lm, tms):
        #self._original_key = parts[0][1].analyze('key').pitchAndMode[0]
        self._parts = parts
        #for (name, stream) in self._parts:
        #    music_utils.transpose(stream, 'C')
        self._lm = lm
        self._tms = tms

    # returns (new_context, new_context_size) based on the old
    # context and size and the added phrase
    def update_context(self, curr_context, curr_context_size, h_phrase):
        new_context = curr_context + h_phrase
        new_context_size = curr_context_size + len(h_phrase)
        while new_context_size > self._lm.ngram_size:
            popped = new_context.pop(0)
            if type(popped) == note.Note or type(popped) == note.Rest:
                new_context_size-=1
        return (new_context, new_context_size)

    # TODO: use streams in language model
    def _update_hypothesis(self, curr_hyp, phrases, h_phrase):
        new_notes = curr_hyp.notes + (h_phrase,)
        new_duration = curr_hyp.duration + get_duration_of_stream(h_phrase)
        new_context, new_context_size = self.update_context(curr_hyp.context, curr_hyp.context_size, h_phrase)
        new_tm_logprob = curr_hyp.tm_logprob
        for part_idx, phrase in phrases.items():
            new_tm_logprob += self._tms[part_idx].get_probability(phrase, h_phrase)
        new_lm_logprob = curr_hyp.lm_logprob + self._lm.get_probability(new_context, h_phrase)
        return hypothesis(new_notes, new_duration, new_context, new_context_size, new_tm_logprob, new_lm_logprob) 

    def _grow_hyps_in_beam(self, phrases, main_phrase_part, hyp):
        new_beam = []
        # get_harmonies always returns at least one harmony
        possible_harmony_phrases = set(self._tms[main_phrase_part]\
                                        .get_harmonies(get_phrase_rep(phrases[main_phrase_part])))
        for h in possible_harmony_phrases:
            new_hyp = self._update_hypothesis(hyp, phrases, h)
            new_beam.append(new_hyp)
        return new_beam

    def get_melody_phrases_after_duration(self, duration, part_idx):
        phrases = {}
        semi_flat_part = self._parts[part_idx][1].semiFlat

        first_note = semi_flat_part.notesAndRests.getElementAtOrBefore(duration)
        second_note = semi_flat_part.getElementAfterElement(first_note, [note.Note, note.Rest])
        if second_note:
            phrase_end = second_note.offset + second_note.quarterLength
        else:
            phrase_end = first_note.offset + first_note.quarterLength
        melody_phrase = trim_stream(semi_flat_part, duration, phrase_end)
        
        phrases[part_idx] = melody_phrase
        for p_idx in range(len(self._parts)):
            if p_idx != part_idx:
                section = trim_stream(self._parts[p_idx], duration, phrase_end)
                phrases[p_idx] = section
        return phrases

    def decode(self):
        print "total duration:", self._parts[0][1].duration.quarterLength
        beam = [hypothesis((), 0.0, (), 0, 0.0, 0.0)]
        new_beam = []
        continue_growing_hyps = True
        longest_duration = 0.0
        while continue_growing_hyps:
            continue_growing_hyps = False
            for hyp in beam:
                if hyp.duration >= self._parts[0][1].duration.quarterLength:
                    new_beam.append(hyp)
                else:
                    if hyp.duration > longest_duration:
                        longest_duration = hyp.duration
                        print longest_duration
                    continue_growing_hyps = True
                    for (part_idx, p) in enumerate(self._parts):
                        # {part_idx: phrase}
                        melody_phrases = self.get_melody_phrases_after_duration(hyp.duration, part_idx)
                        # grow_hypes_in_beam() not implemented correctly yet
                        new_beam.extend(self._grow_hyps_in_beam(melody_phrases, part_idx, hyp)) # is part_idx right?
                        for part_idx in xrange(len(melody_phrases)):
                            del melody_phrases[part_idx]
                        del melody_phrases
                        gc.collect()
                        sys.stderr.write(".")
            if continue_growing_hyps:
                beam = sorted(new_beam, key = lambda hyp: get_score(hyp), reverse=True)[:50]
                new_beam = []

        for hyp in beam:
            final_stream = stream.Stream()
            final_stream.append(bar.Barline(style='final'))
            new_beam.extend(self._grow_hyps_in_beam({i:final_stream for i in range(len(self._parts))}, 0, hyp))
       
        beam = sorted(new_beam, key = lambda hyp: get_score(hyp), reverse=True)[:50]
        winner = [n for n in beam[0].notes if n != "BAR" and n != "END"]

        # translate note sequence into music21 stream
        return make_stream_from_notes(winner)




