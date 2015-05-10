import multiprocessing
import argparse
import itertools
import re
import sys

from music21 import *

from translation_model import TranslationModel
from music_utils import *


class TranslationModelGenerator(object):
    def __init__(self, training_paths, melody_part=0, harmony_part=1, phrase_based=True):
        if type(melody_part) == str and melody_part.isdigit():
            melody_part = int(melody_part)
        if type(harmony_part) == str and harmony_part.isdigit():
            melody_part = int(harmony_part)
        self._melody_part = melody_part
        self._harmony_part = harmony_part
        self._phrase_based_mode = phrase_based
        self._tm_counts = None

        f = open(training_paths, "r")
        self._training_paths = [p.strip() for p in f]

    def _update_counts(self, melody, harmony, limits):
        melody_phrase = []
        begin_offset = 0.0

        for melody_note in melody.flat.notesAndRests:
            if melody_note.isNote and (melody_note.pitch < limits[self._melody_part][0] or
                                               melody_note.pitch > limits[self._melody_part][1]):
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
                    if h_note.isNote and (h_note.pitch < limits[self._harmony_part][0] or
                                                  h_note.pitch > limits[self._harmony_part][1]):
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
        num_songs_without_harmony_part = 0
        num_songs_without_melody_part = 0
        num_songs_without_either_part = 0
        for path in self._training_paths:
            composition = converter.parse(path)
            missing_parts = 0
            
            try:
                melody = composition.parts[self._melody_part]
            except:
                num_songs_without_melody_part += 1
                missing_parts += 1
            try:
                harmony = composition.parts[self._harmony_part]
            except:
                num_songs_without_harmony_part += 1
                missing_parts += 1

            if missing_parts == 2:
                num_songs_without_either_part += 1

            if missing_parts > 0:
                continue

            limits = {self._melody_part:
                      (get_min_pitch(composition, self._melody_part),
                       get_max_pitch(composition, self._melody_part)),
                      self._harmony_part:
                      (get_min_pitch(composition, self._harmony_part),
                       get_max_pitch(composition, self._harmony_part))}
            sys.stderr.write('.')
            num_songs += 1
            transpose(composition, "C")
            self._update_counts(melody, harmony, limits)

        print "Number of songs: {0}".format(num_songs)
        print "Number of songs without {0} : {1}".format(self._harmony_part, num_songs_without_harmony_part)
        print "Number of songs without {0} : {1}".format(self._melody_part, num_songs_without_melody_part)
        print "Number of songs without either part: {0}".format(num_songs_without_either_part)

        return self._create_tm_from_counts()


def generate_generator(args):
    phrase_mode = not args.note_only
    tm_generator = TranslationModelGenerator(args.training_paths,
                                            melody_part=args.melody, 
                                            harmony_part=args.harmony, 
                                            phrase_based=phrase_mode)
    tm = tm_generator.generate_tm()
    suffix = "rhythm_" if phrase_mode else ""
    tm.write_to_file(tm._tm_phrases,
                     '{0}/{1}_{2}_translation_model_{3}.txt'.format(
                         args.output_dir, args.melody, args.harmony, suffix), phrase=phrase_mode)

def main():
    argparser = argparse.ArgumentParser()
    requiredNamed = argparser.add_argument_group('required named arguments')
    requiredNamed.add_argument("--melody", dest="melody",
                                help="Name of the melody part")
    requiredNamed.add_argument("--harmony", dest="harmony",
                                help="Name of the harmony part")
    requiredNamed.add_argument("--training_paths", dest="training_paths",
                                help="Path to file containing list of songs to train on")
    requiredNamed.add_argument("--output_dir", dest="output_dir",
                                help="Directory in which to write the model")
    argparser.add_argument("--note_only", action='store_true',
                                help="Don't create the phrase translation model")
    args = argparser.parse_args()

    generate_generator(args)

if __name__ == "__main__":
    main()




