import sys
import os
import argparse

from tqdm import tqdm

from compose.language_model import LanguageModel
from utils.music_utils import *


class LanguageModelGenerator(object):
  def __init__(self, part, ngram_size=3, window_size=3, training_dir=None):
    self._ngram_size = ngram_size
    self._window_size = window_size
    if type(part) == str and part.isdigit():
      part = int(part)
    self._part = part
    if not training_dir:
      self._training_paths = corpus.getBachChorales()[50:]
    else:
      self._training_paths = [os.path.join(training_dir, p) for p in os.listdir(training_dir)]
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
      if type(measure) == stream.Measure:
        sliding_window.append("BAR")
        while sliding_window_size > self._window_size:
          if sliding_window.pop(0) != "BAR":
            sliding_window_size -= 1
        for note in measure.notesAndRests:
          if not note.isNote:
            note_rep = 'R'
          else:
            note_rep = get_pitch_rep(note)
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
    num_songs_without_part = 0
    num_transpose_fails = 0

    for path in tqdm(self._training_paths):
      composition = converter.parse(path)
      part_names = [p.partName for p in composition.parts]

      if self._part in part_names:
        limits = (get_min_pitch(composition, self._part), get_max_pitch(composition, self._part))
        harmony = composition.parts[self._part]
        try:
          transpose(composition, "C")
          self._update_counts(harmony, limits)
        except analysis.discrete.DiscreteAnalysisException:
          num_transpose_fails += 1

      else:
        num_songs_without_part += 1

    print("Number of songs without {0}: {1}".format(self._part, num_songs_without_part))
    print("Number of transpose failures: {0}".format(num_transpose_fails))
    return self._create_lm_from_counts(smoothing)

  def get_lm(self):
    if not self._lm:
      self.generate_lm()
    return self._lm()

def main():
  argparser = argparse.ArgumentParser()
  argparser.add_argument("--part_name", required=True, type=str, help="Name of the part to model")
  argparser.add_argument("--training_dir", required=True, type=str,
                         help="Path to file containing list of songs to train on")
  argparser.add_argument("--output_dir", required=True, type=str, help="Directory in which to write the model")
  argparser.add_argument("--ngram_size", default=3, help="Size of ngrams in the model. Default is 3")
  args = argparser.parse_args()

  lm_generator = LanguageModelGenerator(part=args.part_name, ngram_size=args.ngram_size,
                                        window_size=args.ngram_size, training_dir=args.training_dir)
  lm = lm_generator.generate_lm()
  os.makedirs(args.output_dir, exist_ok=True)
  lm.write_to_file('{0}/{1}_language_model.txt'.format(args.output_dir, args.part_name))


if __name__ == "__main__":
  main()
