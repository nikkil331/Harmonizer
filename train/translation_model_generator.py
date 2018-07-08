import argparse
import os

import music21 as m21
from tqdm import tqdm
import itertools as it

from compose.translation_model import TranslationModel
import utils.music_utils as mutil


def _is_outside_limits(note, limits):
  return note.pitch < limits[0].pitch or note.pitch > limits[1].pitch


class TranslationModelGenerator(object):
  def __init__(self, training_dir, melody_part, harmony_part):
    if type(melody_part) == str and melody_part.isdigit():
      melody_part = int(melody_part)
    if type(harmony_part) == str and harmony_part.isdigit():
      melody_part = int(harmony_part)
    self._melody_part = melody_part
    self._harmony_part = harmony_part
    self._tm_note_counts = {}
    self._tm_phrase_counts = {}

    self._training_paths = [os.path.join(training_dir, p) for p in os.listdir(training_dir)]

  def _update_note_counts(self, melody, harmony, limits):
    flat_harmony = harmony.flat.notesAndRests.stream()
    for melody_note in melody.flat.notesAndRests:
      if melody_note.isNote and _is_outside_limits(melody_note, limits[self._melody_part]):
        continue
      m_rep = mutil.get_pitch_rep(melody_note)
      harmony_notes = [(mutil.get_pitch_rep(n), n) for n in
                       flat_harmony.allPlayingWhileSounding(melody_note)]
      for (h_rep, h_note) in harmony_notes:
        if h_note.isNote and _is_outside_limits(h_note, limits[self._harmony_part]):
          continue
        if h_rep not in self._tm_phrase_counts:
          self._tm_phrase_counts[h_rep] = {}
        if m_rep not in self._tm_phrase_counts[h_rep]:
          self._tm_phrase_counts[h_rep][m_rep] = 0
        self._tm_phrase_counts[h_rep][m_rep] += 1

  def _update_phrase_counts(self, melody, harmony, limits):
    melody_phrase = []
    begin_offset = 0.0
    flat_harmony = harmony.flat.notesAndRests.stream()

    for melody_note in melody.flat.notesAndRests:
      if melody_note.isNote and _is_outside_limits(melody_note, limits[self._melody_part]):
        melody_phrase.append(mutil.get_note_rep(melody_note))
        if len(melody_phrase) == 2:
          # get harmony phrase playing while melody phrase is sounding
          melody_tuple = tuple(melody_phrase)
          end_offset = begin_offset + mutil.get_phrase_length_from_rep(melody_tuple)
          harmony_tuple = mutil.get_phrase_rep(mutil.trim_stream(flat_harmony, begin_offset, end_offset))

          # update counts for this pair of melody and harmony phrases
          if harmony_tuple not in self._tm_phrase_counts:
            self._tm_phrase_counts[harmony_tuple] = {}
          if melody_tuple not in self._tm_phrase_counts[harmony_tuple]:
            self._tm_phrase_counts[harmony_tuple][melody_tuple] = 0
          self._tm_phrase_counts[harmony_tuple][melody_tuple] += 1

          # update melody phrase sliding window
          melody_phrase = []
          begin_offset = end_offset

  def _normalized_counts(self, counts):
    for harmony in counts:
      total_notes_harmonized = sum(counts[harmony].values())
      if len(counts[harmony].keys()) > 2:
        harmony_counts = counts[harmony].items()
        for (melody, count) in harmony_counts:
          prob = count / float(total_notes_harmonized)
          yield melody, harmony, prob

  def _create_tm_from_counts(self):
    tm = TranslationModel(harmony_part=self._harmony_part, melody_part=self._melody_part)
    for melody, harmony, prob in self._normalized_counts(self._tm_phrase_counts):
      tm.add_phrase(melody, harmony, prob)
    for melody, harmony, prob in self._normalized_counts(self._tm_note_counts):
      tm.add_note(melody, harmony, prob)
    return tm

  def generate_tm(self):
    num_transpose_fails = 0
    num_songs_without_harmony_part = 0
    num_songs_without_melody_part = 0
    num_songs_without_either_part = 0
    for path in tqdm(self._training_paths):
      composition = m21.converter.parse(path)
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
          self._update_note_counts(melody, harmony, limits)
          self._update_phrase_counts(melody, harmony, limits)
        except m21.analysis.discrete.DiscreteAnalysisException:
          num_transpose_fails += 1

    print("Number of songs without {0} : {1}".format(self._harmony_part, num_songs_without_harmony_part))
    print("Number of songs without {0} : {1}".format(self._melody_part, num_songs_without_melody_part))
    print("Number of songs without either part: {0}".format(num_songs_without_either_part))
    print("Number of transpose failures: {0}".format(num_transpose_fails))

    return self._create_tm_from_counts()


def run_generator(args):
  for melody, harmony in it.permutations(args.part_name, 2):
    print("Creating translation model for {0} -> {1}".format(melody, harmony))
    tm_generator = TranslationModelGenerator(args.training_dir,
                                             melody_part=melody,
                                             harmony_part=harmony)
    tm = tm_generator.generate_tm()
    tm.save(phrase_path=os.path.join(args.output_dir,'{0}_{1}_translation_model_rhythm.txt'.format(melody, harmony)),
            note_path=os.path.join(args.output_dir, '{0}_{1}_translation_model.txt'.format(melody, harmony)))


def main():
  argparser = argparse.ArgumentParser()
  argparser.add_argument("--part_name", required=True, help="Name of the harmony part", action="append")
  argparser.add_argument("--training_dir", required=True, help="Path to directory of songs to train on")
  argparser.add_argument("--output_dir", required=True, help="Directory in which to write the model")
  args = argparser.parse_args()

  run_generator(args)


if __name__ == "__main__":
  main()
