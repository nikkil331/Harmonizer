from music21 import *
import sys
import optparse
import copy
import math
from collections import namedtuple
from translation_model import TranslationModel
from language_model import LanguageModel
from music_utils import *
import progressbar

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
        new_context = list(curr_context + h_phrase)
        new_context_size = curr_context_size + len([h for h in h_phrase if h != "BAR" and h != "END"])
        while new_context_size > self._lm.ngram_size:
            popped = new_context.pop(0)
            if popped != "BAR" and popped != "END":
                new_context_size-=1
        return (tuple(new_context), new_context_size)

    def _update_hypothesis(self, curr_hyp, phrases, h_phrase):
        new_notes = curr_hyp.notes + h_phrase
        new_duration = curr_hyp.duration + get_phrase_length_from_rep(h_phrase)
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
                                        .get_harmonies(phrases[main_phrase_part]))
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

        phrases[part_idx] = get_phrase_rep(melody_phrase)
        for p_idx in range(len(self._parts)):
            if p_idx != part_idx:
                section = get_phrase_rep(trim_stream(self._parts[p_idx][1].semiFlat, duration, phrase_end))
                phrases[p_idx] = section
        return phrases

    def decode(self):
        bar = progressbar.ProgressBar(maxval=self._parts[0][1].duration.quarterLength, \
                                      widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
        beam = {0.0: [hypothesis((), 0.0, (), 0, 0.0, 0.0)]}
        new_beam = {}
        continue_growing_hyps = True
        longest_duration = 0.0
        while continue_growing_hyps:
            continue_growing_hyps = False
            for hyp_dur in beam:
                if hyp_dur >= self._parts[0][1].duration.quarterLength:
                    new_beam[hyp_dur] = beam[hyp_dur]
                else:
                    if hyp_dur > longest_duration:
                        longest_duration = hyp_dur
                        bar.update(longest_duration)
                    continue_growing_hyps = True
                    for (part_idx, p) in enumerate(self._parts):
                        # {part_idx: phrase}
                        melody_phrases = self.get_melody_phrases_after_duration(hyp_dur, part_idx)
                        for hyp in beam[hyp_dur]:
                            new_hyps = self._grow_hyps_in_beam(melody_phrases, part_idx, hyp)
                            for new_hyp in new_hyps:
                                if new_hyp.duration not in new_beam:
                                    new_beam[new_hyp.duration] = []
                                new_beam[new_hyp.duration].append(new_hyp)
            if continue_growing_hyps:
                all_new_hyps = [i for j in new_beam.values() for i in j]
                all_new_hyps = sorted(all_new_hyps, key = lambda hyp: get_score(hyp), reverse=True)[:100]
                beam = {}
                for hyp in all_new_hyps:
                    if hyp.duration not in beam:
                        beam[hyp.duration] = []
                    beam[hyp.duration].append(hyp)
                new_beam = {}

        for hyp in beam:
            new_hyps = self._grow_hyps_in_beam({i:("END",) for i in range(len(self._parts))}, 0, hyp)
            for new_hyp in new_hyps:
                if new_hyp.duration not in new_beam:
                    new_beam[new_hyp.duration] = []
                new_beam[new_hyp.duration].append(new_hyp)
        
        all_hyps = [i for j in new_beam.values() for i in j]
        all_hyps = sorted(all_hyps, key = lambda hyp: get_score(hyp), reverse=True)[:100]
        winner = [n for n in all_hyps[0].notes if n != "BAR" and n != "END"]

        # translate note sequence into music21 stream
        measure_stream = self._parts[0][1].getElementsByClass('Measure')
        winner_stream = make_stream_from_strings(winner)

        bar.finish()
        return put_notes_in_measures(measure_stream, winner_stream)


