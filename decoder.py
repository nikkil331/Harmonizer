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

hypothesis = namedtuple("hypothesis", "notes, duration, context, context_size, tm_logprob, lm_logprob")

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

    def _update_hypothesis(self, curr_hyp, (part, m_phrase), h_phrase):
        bar_offset = None
        duration_so_far = 0.0
        for m_note in m_phrase:
            if m_note == "BAR":
                bar_offset = duration_so_far
            else:
                duration_so_far+=int(m_note.split(":")[1])

        new_notes = curr_hyp.notes[:]
        new_size = curr_hyp.context_size
        new_context = list(curr_hyp.context)
        new_lm_logprob = curr_hyp.lm_logprob
        duration_so_far = 0.0
        for h_note in h_phrase:
            h_note_pitch, h_note_duration = h_note.split(":")
            h_note_duration = int(h_note_duration)
            not_consecutive_rests = not (h_note_pitch == "R" and new_context[-1] == "R")
            duration_so_far+= h_note_duration
            if bar_offset:
                if duration_so_far == bar_offset:
                    new_notes.append(h_note)
                    if not_consecutive_rests:
                        new_context.append(h_note_pitch)
                        new_size += 1 
                    new_notes.append("BAR")
                    new_context.append("BAR")
                elif duration_so_far > bar_offset:
                    #new_notes has all timing info
                    after_bar_duration = (duration_so_far - bar_offset)
                    before_bar_duration = h_note_duration - after_bar_duration
                    new_notes.append(":".join([h_note_pitch, str(before_bar_duration)]))
                    new_notes.append("BAR")
                    new_notes.append(":".join([h_note_pitch, str(after_bar_duration)]))
                    #new_context only has pitch info
                    if not_consecutive_rests:
                        new_context.append(h_note_pitch)
                        new_size += 1 
                    new_context.append("BAR")
                    new_context.append(h_note_pitch)
                elif not_consecutive_rests:
                    new_context.append(h_note_pitch)  
                    new_size += 1 

            new_lm_logprob+=get_lm_score(self._lm, tuple(new_context), h_note_pitch)
            while new_size > self._lm.ngram_size:
                if new_context.pop(0) != "BAR":
                    new_size-=1

        # update tm logprob scores
        new_tm_logprob = curr_hyp.tm_logprob
        new_tm_logprob += get_tm_score(self._tms[part], tuple(m_phrase), tuple(h_phrase))
        for part_idx in range(len(self._parts)):
            if part_idx != part:
                # get the melody phrases playing during this time
                new_tm_logprob += get_tm_score(self._tms[part_idx], tuple(m_phrase), tuple(h_phrase))
        return hypothesis(new_notes, new_duration, new_context, new_size, new_tm_logprob, new_lm_logprob)

    def _grow_hyps_in_beam(self, melody_phrases, hyp):
        new_beam = []
        phrases_without_bar = {part_idx:n for (part_idx, phrase) in melody_phrases.iteritems()\
                               for n in phrase if n != "BAR"}
        for part_idx in range(len(self._parts)):
            possible_harmony_phrases = set(self._tms[part_idx].get_harmonies(phrases_without_bar[part_idx]))
            if len(possible_harmony_phrases) == 0:
                possible_harmony_phrases = set([('R', 'R')])
            for h in possible_harmony_phrases:
                new_hyp = self._update_hypothesis(hyp, (part_idx, melody_phrases[part_idx]), h)
                new_beam.append(new_hyp)
        return new_beam

    def get_section_sounding_during_phrase(phrase, part_idx):
        section = stream.Stream()
        ordered_set = OrderedSet([m for el in phrase if type(el) != stream.Measure for \
                                  m in self._parts[part_idx].semiFlat.allPlayingWhileSounding(el)])
        
        for el in ordered_set:
            section.append(el)
        if type(section[0]) == stream.Measure:
            section = section[1:]
        phrase_duration = sum([el.quarterLength for el in phrase where type(el) != stream.Measure])
        section_duration = sum([el.quarterLength for el in section where type(el) != stream.Measure])
        # trim first note with negative offset
        section[0].quarterLength = section[0].quarterLength + section[0].offset
        # trim last note with difference
        section[-1].quarterLength = section[-1].quarterLength - (section_duration - phrase_duration)
        return section


    def get_melody_phrases_after_duration(duration, part_idx):
        melody_phrases = {}
        semi_flat_part = self._parts[part_idx][1].semiFlat

        first_note = semi_flat_part.notesAndRests.getElementAtOrBefore(duration)
        melody_phrase = semi_flat_part.getElementsByOffset(duration, \
                                                           offsetEnd=first_note.quarterLength, \
                                                           mustBeginInSpan=False)
        if type(melody_phrase[0]) == stream.Measure:
            melody_phrase = melody_phrase[1:]
        to_subtract = duration - melody_phrase[0].offset()
        melody_phrase[0].quarterLength = melody_phrase.quarterLength - to_subtract
        melody_phrase[0].offset = melody_phrase.offset + to_subtract
        melody_phrases[part_idx] = melody_phrase
        for p_idx in range(len(self._parts)):
            if p_idx != part_idx:
                section = get_section_sounding_during_phrase(melody_phrase, \
                                                             part_idx)
                melody_phrases[p_idx] = section
        return melody_phrases

    def decode(self):
        beam = [hypothesis([], 0.0, (), 0, 0.0, 0.0)]
        new_beam = []
        continue_growing_hyps = True
        while continue_growing_hyps:
            continue_growing_hyps = False
            for hyp in beam:
                if hyp.duration >= self._parts[0][1].duration:
                    new_beam.append(hyp)
                else:
                    continue_growing_hyps = True
                    for (part_idx, p) in enumerate(self._parts):
                        # {part_idx: phrase}
                        melody_phrases = get_melody_phrases_after_duration(hyp.duration, part_idx)
                        # grow_hypes_in_beam() not implemented correctly yet
                        new_beam.extend(self._grow_hyps_in_beam(melody_phrases, hyp))
                        sys.stderr.write(".")
            if continue_growing_hyps:
                beam = sorted(new_beam, key = lambda hyp: get_score(hyp.tm_logprob, hyp.lm_logprob), reverse= True)
                new_beam = []
        # TODO: not sure how to apply stream model for "END"????
        # ^ final bar line object
        for hyp in beam:
            new_beam.extend(self._grow_hyps_in_beam({i:"END" for i in range(len(self._parts))}, hyp))
       
        beam = sorted(new_beam, key = lambda hyp: get_score(hyp.tm_logprob, hyp.lm_logprob), reverse=True)[:1000]
        winner = [n for n in beam[0].notes if n != "BAR" and n != "END"]

        # translate note sequence into music21 stream
        return make_stream_from_note_list(winner)




