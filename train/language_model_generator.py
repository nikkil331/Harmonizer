import os
import argparse

import music21 as m21
from tqdm import tqdm

from compose.language_model import LanguageModel
import utils.music_utils as mutil


class LanguageModelGenerator(object):
  def __init__(self, part, window_size=3, training_dir=None):
    self._window_size = window_size
    if type(part) == str and part.isdigit():
      part = int(part)
    self._part = part
    if not training_dir:
      self._training_paths = m21.corpus.getComposer('bach', 'xml')[50:]
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
    note_ngram = [m21.note.Note(n) for n in ngram if n != "BAR" and n != "END" and n != "R"]
    if note_ngram and min(note_ngram, key=lambda x: x.pitch).pitch > limits[0] and max(note_ngram, key=lambda x: x.pitch).pitch < limits[1]:
      self._update_count(ngram, note_rep)

  def _update_counts(self, harmony, limits):
    sliding_window = []
    sliding_window_size = 0
    for measure in harmony[1:]:
      if type(measure) == m21.stream.Measure:
        sliding_window.append("BAR")
        while sliding_window_size > self._window_size:
          if sliding_window.pop(0) != "BAR":
            sliding_window_size -= 1
        for note in measure.notesAndRests:
          if not note.isNote:
            note_rep = 'R'
          else:
            note_rep = mutil.get_pitch_rep(note)
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
    lm.set_ngram_size(self._window_size)
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
    num_limit_fails = 0

    for path in tqdm(self._training_paths):
      try:
        composition = m21.converter.parse(path)
      except:
        print("Could not parse %s, skipping" % path) 
        continue
      part_names = [p.partName for p in composition.parts]

      if self._part in part_names:
        for composition_chunk in mutil.chunk_by_key(composition):
          try:
            limits = (mutil.get_min_pitch(composition_chunk, self._part), mutil.get_max_pitch(composition_chunk, self._part))
          except:
            num_limit_fails += 1
            
          try:
            transposed_composition = composition_chunk # mutil.transpose(composition_chunk, "C")
            harmony = transposed_composition.parts[self._part]
            self._update_counts(harmony, limits)
          except m21.analysis.discrete.DiscreteAnalysisException:
            num_transpose_fails += 1

      else:
        num_songs_without_part += 1

    print("Number of limit failures: {0}".format(num_limit_fails))
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
                         help="Path to directory of songs to train on")
  argparser.add_argument("--output_dir", required=True, type=str, help="Directory in which to write the model")
  argparser.add_argument("--ngram_size", default=3, type=int, help="Size of ngrams in the model. Default is 3")
  args = argparser.parse_args()

  lm_generator = LanguageModelGenerator(part=args.part_name, window_size=args.ngram_size, training_dir=args.training_dir)
  lm = lm_generator.generate_lm()
  lm.save('{0}/{1}_language_model.txt'.format(args.output_dir, args.part_name))


if __name__ == "__main__":
  main()
