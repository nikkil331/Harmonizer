import math

import os


class LanguageModel(object):
  def __init__(self, part, path=None):
    self._lm = {}
    self.part = part
    if path:
      self._read_file(path)

  def _read_file(self, path):
    f = open(path, 'r')
    self.set_ngram_size(int(f.readline()))
    for line in f:
      context_string, note, prob = line.strip().split(" ||| ")
      context = tuple(context_string.split())
      self.add_to_model(context, note, float(prob))

  def set_ngram_size(self, ngram_size):
    self.ngram_size = ngram_size

  def add_to_model(self, context, note, prob):
    if context not in self._lm:
      self._lm[context] = {note: prob}
    else:
      self._lm[context][note] = prob

  def get_probability(self, context, phrase):
    total_prob = 0
    context_tuple = tuple([s.split(":")[0] for s in context])
    context_size = len([n for n in context_tuple if n != "BAR" and n != "END"])
    for note in phrase:
      note_rep = note.split(":")[0]
      if note_rep == "BAR":
        context_tuple += ("BAR",)
      else:
        if context_tuple not in self._lm:
          total_prob += math.log(1e-10)
        elif note_rep not in self._lm[context_tuple]:
          total_prob += math.log(self._lm[context_tuple]["<UNK>"])
        else:
          total_prob += math.log(self._lm[context_tuple][note_rep])
        context_tuple = list(context_tuple)
        context_tuple.append(note_rep)
        context_size += 1
        while context_size > self.ngram_size:
          if context_tuple.pop(0) != "BAR":
            context_size -= 1
        context_tuple = tuple(context_tuple)
    return total_prob

  def get_contexts(self):
    return self._lm.keys()

  def get_notes_for_context(self, context):
    if context not in self._lm:
      return []
    return self._lm[context].items()

  def save(self, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    f = open(path, 'w')
    f.write(str(self.ngram_size) + '\n')
    for context in self._lm:
      for note in self._lm[context]:
        context_str = ' '.join(context)
        prob = self._lm[context][note]
        output_line = '{0} ||| {1} ||| {2}\n'.format(context_str, note, prob)
        f.write(output_line)
