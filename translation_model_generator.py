import multiprocessing
import optparse
import itertools
import re
import sys

from music21 import *

from translation_model import TranslationModel
from music_utils import *


class TranslationModelGenerator(object):
    def __init__(self, mode='major', melody_part=0, harmony_part=1, phrase_based=True):
        self._mode = 'major' if mode == 'major' else 'minor'
        self._melody_part = melody_part
        self._harmony_part = harmony_part
        self._training_paths = []
        self._phrase_based_mode = phrase_based
        self._training_paths = get_barbershop_data()
        self._tm_counts = None

    def _update_counts(self, melody, harmony, limits):
        melody_phrase = []
        begin_offset = 0.0

        for melody_note in melody.flat.notesAndRests:
            if melody_note.isNote and melody_note.pitch < limits[self._melody_part][0] or \
                            melody_note.pitch > limits[self._melody_part][1]:
                continue
            if self._phrase_based_mode:
                melody_phrase.append(get_note_rep(melody_note))
                if len(melody_phrase) == 2:
                    # get harmony phrase playing while melody phrase is sounding
                    melody_tuple = tuple(melody_phrase)
                    end_offset = begin_offset + get_phrase_length_from_rep(melody_tuple)
                    harmony_tuple = get_phrase_rep(trim_stream(harmony.flat.notesAndRests, begin_offset, end_offset))

                    # update counts for this pair of melody and harmony phrases
                    if harmony_tuple not in self._tm_counts:
                        self._tm_counts[harmony_tuple] = {}
                    if melody_tuple not in self._tm_counts[harmony_tuple]:
                        self._tm_counts[harmony_tuple][melody_tuple] = 0
                    self._tm_counts[harmony_tuple][melody_tuple] += 1

                    # update melody phrase sliding window
                    melody_phrase = []
                    begin_offset = end_offset
            else:
                m_rep = get_pitch_rep(melody_note)
                harmony_notes = [(get_pitch_rep(n), n) for n in
                                 harmony.flat.notesAndRests.allPlayingWhileSounding(melody_note)]
                for (h_rep, h_note) in harmony_notes:
                    if h_note.pitch < limits[self._harmony_part][0] or \
                                    h_note.pitch > limits[self._harmony_part][1]:
                        continue
                    if h_rep not in self._tm_counts:
                        self._tm_counts[h_rep] = {}
                    if m_rep not in self._tm_counts[h_rep]:
                        self._tm_counts[h_rep][m_rep] = 0
                    self._tm_counts[h_rep][m_rep] += 1


    def _create_tm_from_counts(self):
        tm = TranslationModel(harmony_part=self._harmony_part, melody_part=self._melody_part)
        for harmony_note in self._tm_counts:
            total_notes_harmonized = sum(self._tm_counts[harmony_note].values())
            if len(self._tm_counts[harmony_note].keys()) > 2:
                harmony_counts = self._tm_counts[harmony_note].items()
                for (melody_note, count) in harmony_counts:
                    prob = count / float(total_notes_harmonized)
                    tm.add_to_model(melody_note, harmony_note, prob, tm._tm_phrases)
        return tm

    def generate_tm(self):
        self._tm_counts = {}
        num_songs = 0
        num_songs_without_part = 0
        for path in self._training_paths:
            composition = converter.parse(path)
            limits = {self._melody_part: (get_min_pitch(composition, 0), get_max_pitch(composition, 0)),
                      self._harmony_part: (get_min_pitch(composition, 1), get_max_pitch(composition, 1))}
            sys.stderr.write('.')
            try:
                keySig = composition.analyze('key')
                if keySig.pitchAndMode[1] != self._mode:
                    sys.stderr.write(str(composition) + '\n')
                    continue
                num_songs += 1
                transpose(composition)
                melody = composition.parts[int(self._melody_part)]
                harmony = composition.parts[int(self._harmony_part)]
                self._update_counts(melody, harmony, limits)


            except KeyError, e:
                num_songs_without_part += 1
            except ValueError:
                sys.stderr.write(str(get_barbershop_data()[training_songs.index(composition)]) + "\n")

        print "Number of songs: {0}".format(num_songs)
        print "Number of songs without {0} : {1}".format(self._harmony_part, num_songs_without_part)

        return self._create_tm_from_counts()


print "reading in..."
training_songs = [converter.parse(path) for path in get_barbershop_data() if "classic_tags" in path]


def main():
    generate_generator(sys.argv[1], sys.argv[2], sys.argv[3])


def generate_generator_helper(t):
    generate_generator(*t)


def generate_generator(melody, harmony, mode):
    print melody, harmony
    print mode
    phrase_mode = False
    if mode == "phrase":
        phrase_mode = True
    tm_generator = TranslationModelGenerator(melody_part=melody, harmony_part=harmony, phrase_based=phrase_mode)
    tm = tm_generator.generate_tm()
    suffix = "rhythm_" if phrase_mode else ""
    tm.write_to_file(tm._tm_phrases,
                     'Harmonizer/data/barbershop/models/{0}_{1}_translation_model_major_{2}threshold_2_tag.txt'.format(
                         melody, harmony, suffix), phrase=phrase_mode)


if __name__ == "__main__":
    main()




