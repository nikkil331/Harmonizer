import argparse
import os

from music21 import converter, analysis
from tqdm import tqdm
import itertools as it

from compose.translation_model import TranslationModel
import utils.music_utils as mutil


class TranslationModelGenerator(object):
  def __init__(self, training_dir, melody_part, harmony_part, phrase_based=True):
    if type(melody_part) == str and melody_part.isdigit():
      melody_part = int(melody_part)
    if type(harmony_part) == str and harmony_part.isdigit():
      melody_part = int(harmony_part)
    self._melody_part = melody_part
    self._harmony_part = harmony_part
    self._phrase_based_mode = phrase_based
    self._tm_counts = None

    self._training_paths = [os.path.join(training_dir, p) for p in os.listdir(training_dir)]

  def _update_counts(self, melody, harmony, limits):
    melody_phrase = []
    begin_offset = 0.0
    flat_harmony = harmony.flat.notesAndRests.stream()

    for melody_note in melody.flat.notesAndRests:
      if melody_note.isNote and (melody_note < limits[self._melody_part][0] or
                                     melody_note > limits[self._melody_part][1]):
        continue
      if self._phrase_based_mode:
        melody_phrase.append(mutil.get_note_rep(melody_note))
        if len(melody_phrase) == 2:
          # get harmony phrase playing while melody phrase is sounding
          melody_tuple = tuple(melody_phrase)
          end_offset = begin_offset + mutil.get_phrase_length_from_rep(melody_tuple)
          harmony_tuple = mutil.get_phrase_rep(mutil.trim_stream(flat_harmony, begin_offset, end_offset))

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
        m_rep = mutil.get_pitch_rep(melody_note)
        harmony_notes = [(mutil.get_pitch_rep(n), n) for n in
                         flat_harmony.allPlayingWhileSounding(melody_note)]
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
    num_transpose_fails = 0
    num_songs_without_harmony_part = 0
    num_songs_without_melody_part = 0
    num_songs_without_either_part = 0
    for path in tqdm(self._training_paths):
      composition = converter.parse(path)
      part_names = [p.partName for p in composition.parts]
      missing_parts = 0
      if self._melody_part not in part_names:
        missing_parts += 1
      if self._harmony_part not in part_names:
        num_songs_without_harmony_part += 1
        missing_parts += 1

      if missing_parts == 2:
        num_songs_without_either_part += 1

      if missing_parts == 0:

        limits = {self._melody_part:
                    (mutil.get_min_pitch(composition, self._melody_part),
                     mutil.get_max_pitch(composition, self._melody_part)),
                  self._harmony_part:
                    (mutil.get_min_pitch(composition, self._harmony_part),
                     mutil.get_max_pitch(composition, self._harmony_part))}
        try:
          mutil.transpose(composition, "C")
          melody = composition.parts[self._melody_part]
          harmony = composition.parts[self._harmony_part]
          self._update_counts(melody, harmony, limits)
        except analysis.discrete.DiscreteAnalysisException:
          num_transpose_fails += 1


    print("Number of songs without {0} : {1}".format(self._harmony_part, num_songs_without_harmony_part))
    print("Number of songs without {0} : {1}".format(self._melody_part, num_songs_without_melody_part))
    print("Number of songs without either part: {0}".format(num_songs_without_either_part))
    print("Number of transpose failures: {0}".format(num_transpose_fails))

    return self._create_tm_from_counts()


def generate_generator(args):
  phrase_mode = not args.note_only
  for melody, harmony in it.combinations(args.part_name, 2):
    print("Creating translation model for {0} -> {1}".format(melody, harmony))
    tm_generator = TranslationModelGenerator(args.training_dir,
                                             melody_part=melody,
                                             harmony_part=harmony,
                                             phrase_based=phrase_mode)
    tm = tm_generator.generate_tm()
    suffix = "_rhythm" if phrase_mode else ""
    tm.write_to_file(tm._tm_phrases,
                     '{0}/{1}_{2}_translation_model{3}.txt'.format(
                       args.output_dir, melody, harmony, suffix), phrase=phrase_mode)


def main():
  argparser = argparse.ArgumentParser()
  argparser.add_argument("--part_name", required=True, help="Name of the harmony part", action="append")
  argparser.add_argument("--training_dir", required=True, help="Path to directory of songs to train on")
  argparser.add_argument("--output_dir", required=True, help="Directory in which to write the model")
  argparser.add_argument("--note_only", action='store_true', help="Don't create the phrase translation model")
  args = argparser.parse_args()

  generate_generator(args)


if __name__ == "__main__":
  main()
