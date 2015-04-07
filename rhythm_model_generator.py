import optparse
import os
import re
import sys
import itertools

from music21 import *

from rhythm_model import RhythmModel
from music_utils import *


class RhythmModelGenerator(object):
    def __init__(self, ngram_size=4, window_size=4, mode='major', part=1, training_composers=['bach', 'handel']):
        self._ngram_size = ngram_size
        self._window_size = window_size
        self._mode = 'major' if mode == 'major' else 'minor'
        self._part = part
        # for composer in training_composers:
        #	self._training_paths += corpus.getComposer(composer)
        self._training_paths = [p for p in get_barbershop_data() if "classic_tags" in p]
        self._lm_counts = None

    def _update_count(self, sliding_window, note_rep):
        if sliding_window not in self._lm_counts:
            self._lm_counts[sliding_window] = {note_rep: 1}
        else:
            if note_rep not in self._lm_counts[sliding_window]:
                self._lm_counts[sliding_window][note_rep] = 1
            else:
                self._lm_counts[sliding_window][note_rep] += 1

    # doesn't actually skip for now
    def _skip_and_update(self, ngram, note_rep, limits):
        note_ngram = [note.Note(n) for n in ngram if n != "BAR" and n != "END" and n != "R"]
        if note_ngram and min(note_ngram) > limits[0] and max(note_ngram) < limits[1]:
            self._update_count(ngram, note_rep)

    def _update_counts(self, harmony, limits):
        sliding_window = []
        sliding_window_size = 0
        for measure in harmony[1:]:
            sliding_window.append("BAR")
            while sliding_window_size > self._window_size:
                if sliding_window.pop(0) != "BAR":
                    sliding_window_size -= 1
            for note in measure.notesAndRests:
                    note_rep = get_rhythm_rep(note)
                self._skip_and_update(tuple(sliding_window), note_rep, limits)
                if not (sliding_window[-1] is 'R' and note_rep is 'R'):
                    sliding_window.append(note_rep)
                    sliding_window_size += 1
                while sliding_window_size > self._window_size:
                    if sliding_window.pop(0) != "BAR":
                        sliding_window_size -= 1

        self._skip_and_update(tuple(sliding_window), 'END', limits)


    def _create_lm_from_counts(self, smoothing):
        lm = LanguageModel(part=self._part)
        lm.set_ngram_size(self._ngram_size)
        for context in self._lm_counts:
            total_notes_after_context = sum(self._lm_counts[context].values())
            if len(self._lm_counts[context].keys()) > 2:
                context_counts = self._lm_counts[context].items()
                for (note, count) in context_counts:
                    # approximately 4 octaves in our vocabulary (48 notes)
                    prob = (count + smoothing) / float(total_notes_after_context + (48 * smoothing))
                    lm.add_to_model(context, note, prob)
                lm.add_to_model(context, "<UNK>", (smoothing / float(total_notes_after_context + (48 * smoothing))))
        return lm


    def generate_lm(self, smoothing=1e-5):
        self._lm_counts = {}
        num_songs = 0
        num_songs_without_part = 0

        for path in self._training_paths:
            sys.stderr.write('.')
            composition = converter.parse(path)
            limits = (get_min_pitch(composition, int(self._part)), get_max_pitch(composition, int(self._part)))
            try:
                harmony = composition.parts[int(self._part)]
                keySig = composition.analyze('key')
                num_songs += 1
                transpose(composition)
                self._update_counts(harmony, limits)

            except KeyError, e:
                num_songs_without_part += 1

        print "Number of songs: {0}".format(num_songs)
        print "Number of songs without {0} : {1}".format(self._part, num_songs_without_part)
        return self._create_lm_from_counts(smoothing)


    '''
    Returns language model dictionary
    '''

    def get_lm(self):
        if not self._lm:
            self.generate_lm()
        return self._lm()

    def write_lm(self):
        f = open(self._output_file, 'w')
        for context in self._lm:
            for note in self._lm[context]:
                output_line = ''.join(
                    [' '.join(context), ' ||| ', str(note), ' ||| ', str(self._lm[context][note]), '\n'])
                f.write(output_line)


