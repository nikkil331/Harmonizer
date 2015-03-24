from music21 import *
import sys
import optparse
import copy
import math
from decimal import *
from collections import namedtuple
from translation_model import TranslationModel
from language_model import LanguageModel
from music_utils import *
import progressbar


hypothesis = namedtuple("hypothesis", "notes, duration, context, context_size, tm_phrase_logprob, tm_notes_logprob, lm_logprob")

def get_score(hyp, tm_phrase_weight=0.5726547297805934, tm_notes_weight=0.061101102321016725, lm_weight=0.0020716756164958113):
    return ((tm_phrase_weight*hyp.tm_phrase_logprob) + 
            (tm_notes_weight*hyp.tm_notes_logprob) +
            (lm_weight*hyp.lm_logprob))/float(hyp.duration)

def get_lm_score(lm, context, phrase):
    return lm.get_probability(tuple([s.encode('ascii') for s in context]), phrase)
    
def get_tm_score(tm, m_phrase, h_phrase):
    return tm.get_probability(m_phrase, h_phrase)

class Decoder(object):
    def __init__(self, parts, lm, tms, tm_phrase_weight=1, 
                 tm_notes_weight=1, lm_weight=1):
        #self._original_key = parts[0][1].analyze('key').pitchAndMode[0]
        self._parts = parts
        #for (name, stream) in self._parts:
        #    music_utils.transpose(stream, 'C')
        self._lm = lm
        self._tms = tms
        self._tm_phrase_weight = tm_phrase_weight
        self._tm_notes_weight = tm_notes_weight
        self._lm_weight = lm_weight

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
        new_tm_phrase_logprob = curr_hyp.tm_phrase_logprob
        new_tm_notes_logprob = curr_hyp.tm_notes_logprob
        for part_idx, phrase in phrases.items():
            if phrase:
                (phrase_prob, note_prob) = self._tms[part_idx].get_probability(phrase, h_phrase)
                new_tm_phrase_logprob += phrase_prob
                new_tm_notes_logprob += note_prob
        new_lm_logprob = curr_hyp.lm_logprob + self._lm.get_probability(curr_hyp.context, h_phrase)
        return hypothesis(new_notes, new_duration, new_context, new_context_size, new_tm_phrase_logprob, new_tm_notes_logprob, new_lm_logprob) 

    def _grow_hyps_in_beam(self, phrases, main_phrase_part, hyp):
        new_beam = []
        # get_harmonies always returns at least one harmony
        if phrases[0] == ("END",):
            possible_harmony_phrases = set([("END",)])
        else:
            possible_harmony_phrases = set(self._tms[main_phrase_part]\
                                            .get_harmonies(phrases[main_phrase_part]))
        for h in possible_harmony_phrases:
            new_hyp = self._update_hypothesis(hyp, phrases, h)
            new_beam.append(new_hyp)
        return new_beam

    def get_melody_phrases_after_duration(self, duration, measure_pairs, part_idx):
        phrases = {}
        semi_flat_part = measure_pairs[part_idx].semiFlat
        first_note = semi_flat_part.notesAndRests.getElementAtOrBefore(duration)
        if first_note == None:
            return None
        second_note = semi_flat_part.getElementAfterElement(first_note, [note.Note, note.Rest])
        if second_note:
            phrase_end = second_note.offset + second_note.quarterLength
        else:
            phrase_end = first_note.offset + first_note.quarterLength

        melody_phrase = trim_stream(semi_flat_part, duration, phrase_end)
        phrases[part_idx] = get_phrase_rep(melody_phrase)
        for p_idx in range(len(measure_pairs)):
            if p_idx != part_idx:
                section = get_phrase_rep(trim_stream(measure_pairs[p_idx].semiFlat, duration, phrase_end))
                if len(section) == 0:
                    section = None
                phrases[p_idx] = section
        return phrases


    def _decodeMeasurePair(self, measure_pairs, n_best_hyps):
        beam = {0.0: [hypothesis((), 0.0, (), 0, 0.0, 0.0, 0.0)]}
        new_beam = {}
        continue_growing_hyps = True
        full_duration = measure_pairs[0].duration.quarterLength - measure_pairs[0][0].offset
        while continue_growing_hyps:
            continue_growing_hyps = False
            for hyp_dur in beam:
                if abs(full_duration - hyp_dur) < 0.00000000001:
                    new_beam[hyp_dur] = beam[hyp_dur]
                else:
                    continue_growing_hyps = True
                    for (part_idx, p) in enumerate(measure_pairs):
                        # {part_idx: phrase}
                        melody_phrases = self.get_melody_phrases_after_duration(measure_pairs[0][0].offset + hyp_dur, measure_pairs, part_idx)
                        for hyp in beam[hyp_dur]:
                            new_hyps = self._grow_hyps_in_beam(melody_phrases, part_idx, hyp)
                            for new_hyp in new_hyps:
                                if new_hyp.duration not in new_beam:
                                    new_beam[new_hyp.duration] = []
                                new_beam[new_hyp.duration].append(new_hyp)
            if continue_growing_hyps:
                all_new_hyps = [i for j in new_beam.values() for i in j]
                consolidated_all_new_hyps = []
                notes_set = set()
                for h in all_new_hyps:
                    if tuple(h.notes) not in notes_set:
                        consolidated_all_new_hyps.append(h)
                        notes_set.add(tuple(h.notes))
                all_new_hyps = sorted(consolidated_all_new_hyps, 
                                      key = lambda hyp: get_score(hyp, self._tm_phrase_weight, 
                                                                  self._tm_notes_weight, 
                                                                  self._lm_weight), 
                                      reverse=True)[:10]
                beam = {}
                for hyp in all_new_hyps:
                    if hyp.duration not in beam:
                        beam[hyp.duration] = []
                    beam[hyp.duration].append(hyp)
                new_beam = {}

        final_hyps = [i for j in beam.values() for i in j]
                  
        consolidated_final_hyps = []
        notes_set = set()
        for h in final_hyps:
            if tuple(h.notes) not in notes_set:
                consolidated_final_hyps.append(h)
                notes_set.add(tuple(h.notes))

        final_hyps = sorted(consolidated_final_hyps, 
                          key = lambda hyp: get_score(hyp, self._tm_phrase_weight, 
                                                      self._tm_notes_weight, 
                                                      self._lm_weight), 
                          reverse=True)[:10]
        return final_hyps[:max(n_best_hyps, 10)]

    def _get_measure_pairs(self):
        measures = [part.measures(0, len(self._parts[0][1].getElementsByClass('Measure')), collect=())
                    for (name, part) in self._parts]
        for i in xrange(0, len(measures[0]), 4):
            end_idx = min(4, len(measures[0]) - i)
            yield [m[i:i+end_idx] for m in measures]

    def decode(self, n_best_hyps):
        bar = progressbar.ProgressBar(maxval=self._parts[0][1].duration.quarterLength, \
                                      widgets=[progressbar.Bar('=', '[', ']'), ' ', progressbar.Percentage()])
        bar.update(0)
        best_hyps_so_far = [hypothesis((), 0.0, (), 0, 0.0, 0.0, 0.0)]
        for (mid, measure_pairs) in enumerate(self._get_measure_pairs()):
            best_hyps_continuation = self._decodeMeasurePair(measure_pairs, n_best_hyps)
            new_best_hyps = []
            for prefix_hyp in best_hyps_so_far[:n_best_hyps]:
                for suffix_hyp in best_hyps_continuation:
                    new_notes = prefix_hyp.notes + suffix_hyp.notes
                    new_tm_phrase_logprob = prefix_hyp.tm_phrase_logprob + suffix_hyp.tm_phrase_logprob
                    new_tm_notes_logprob = prefix_hyp.tm_notes_logprob + suffix_hyp.tm_notes_logprob
                    new_lm_logprob = prefix_hyp.lm_logprob + suffix_hyp.lm_logprob
                    new_duration = prefix_hyp.duration + suffix_hyp.duration
                    new_best_hyps.append(hypothesis(new_notes, new_duration, suffix_hyp.context, suffix_hyp.context_size, new_tm_phrase_logprob, new_tm_notes_logprob, new_lm_logprob))
            best_hyps_so_far = sorted(new_best_hyps, 
                                      key = lambda hyp: get_score(hyp, self._tm_phrase_weight, 
                                                      self._tm_notes_weight, 
                                                      self._lm_weight), 
                                      reverse=True)
            bar.update(best_hyps_so_far[0].duration)

        final_hyps = []
        for hyp in best_hyps_so_far:
            new_beams = self._grow_hyps_in_beam({i:("END",) for i in range(len(self._parts))}, 0, hyp)
            final_hyps.extend(new_beams)

        consolidated_final_hyps = []
        notes_set = set()
        for h in final_hyps:
            if tuple(h.notes) not in notes_set:
                consolidated_final_hyps.append(h)
                notes_set.add(tuple(h.notes))

        final_hyps = sorted(consolidated_final_hyps, 
                          key = lambda hyp: get_score(hyp, self._tm_phrase_weight, 
                                                      self._tm_notes_weight, 
                                                      self._lm_weight), 
                          reverse=True)[:n_best_hyps]
        bar.finish()
        return best_hyps_so_far[:n_best_hyps]

    def hyp_to_stream(self, hyp):
        notes = [n for n in hyp.notes if n != "BAR" and n != "END"]
        # translate note sequence into music21 stream
        measure_stream = self._parts[0][1].getElementsByClass('Measure')
        notes_stream = make_stream_from_strings(notes)

        return put_notes_in_measures(measure_stream, notes_stream)


