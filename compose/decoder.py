from collections import namedtuple

import music21 as m21
import utils.music_utils as mutil
from tqdm import tqdm

hypothesis = namedtuple("hypothesis",
                        ["notes", "duration", "context", "context_size", "tm_phrase_logprob", "tm_notes_logprob", "lm_logprob"])
PartSlice = namedtuple("PartSlice", ["name", "stream"])


def get_score(hyp, tm_phrase_weight=0.5726547297805934, tm_notes_weight=0.061101102321016725,
              lm_weight=0.0020716756164958113):
  return ((tm_phrase_weight * hyp.tm_phrase_logprob) +
          (tm_notes_weight * hyp.tm_notes_logprob) +
          (lm_weight * hyp.lm_logprob)) / float(hyp.duration)


def get_lm_score(lm, context, phrase):
  return lm.get_probability(tuple(context), phrase)


def get_tm_score(tm, m_phrase, h_phrase):
  return tm.get_probability(m_phrase, h_phrase)


class Decoder(object):
  def __init__(self, parts, lm, tms, tm_phrase_weight=1,
               tm_notes_weight=1, lm_weight=1, beam_size=10):
    self._parts = parts
    self._lm = lm
    self._tms = tms
    self._tm_phrase_weight = tm_phrase_weight
    self._tm_notes_weight = tm_notes_weight
    self._lm_weight = lm_weight
    self._beam_size = beam_size

  # returns (new_context, new_context_size) based on the old
  # context and size and the added phrase
  def update_context(self, curr_context, curr_context_size, h_phrase):
    new_context = list(curr_context + h_phrase)
    new_context_size = curr_context_size + len([h for h in h_phrase if h != "BAR" and h != "END"])
    while new_context_size > self._lm.ngram_size:
      popped = new_context.pop(0)
      if popped != "BAR" and popped != "END":
        new_context_size -= 1
    return tuple(new_context), new_context_size

  def _update_hypothesis(self, curr_hyp, phrases, prev_note, h_phrase):
    new_notes = curr_hyp.notes + h_phrase
    new_duration = curr_hyp.duration + mutil.get_phrase_length_from_rep(h_phrase)
    new_context, new_context_size = self.update_context(curr_hyp.context, curr_hyp.context_size, h_phrase)
    new_tm_phrase_logprob = curr_hyp.tm_phrase_logprob
    new_tm_notes_logprob = curr_hyp.tm_notes_logprob
    for part_name, phrase in phrases.items():
      if phrase:
        (phrase_prob_1, note_prob_1) = self._tms[part_name].get_probability(phrase, h_phrase)
        if prev_note:
          (phrase_prob_2, _) = self._tms[part_name].get_probability((mutil.get_note_rep(prev_note),
                                                                    phrase[0]),
                                                                   (curr_hyp.notes[-1], h_phrase[0]))
        else:
          phrase_prob_2 = 0
        new_tm_phrase_logprob += phrase_prob_1 + phrase_prob_2
        new_tm_notes_logprob += note_prob_1
    new_lm_logprob = curr_hyp.lm_logprob + self._lm.get_probability(curr_hyp.context, h_phrase)
    return hypothesis(new_notes, new_duration, new_context, new_context_size, new_tm_phrase_logprob,
                      new_tm_notes_logprob, new_lm_logprob)

  def _grow_hyps_in_beam(self, phrases, prev_note, main_phrase_part, hyp):
    new_beam = []
    # get_harmonies always returns at least one harmony
    if phrases[main_phrase_part] == ("END",):
      possible_harmony_phrases = {("END",)}
    else:
      possible_harmony_phrases = set(self._tms[main_phrase_part] \
                                     .get_harmonies(phrases[main_phrase_part]))
    for h in possible_harmony_phrases:
      new_hyp = self._update_hypothesis(hyp, phrases, prev_note, h)
      new_beam.append(new_hyp)
    return new_beam

  def get_phrases_after_offset(self, phrase_start, measure_slice, melody_part):
    phrases = {}
    semi_flat_part = melody_part.stream.flat
    first_note = semi_flat_part.notesAndRests.getElementAtOrBefore(phrase_start)
    if first_note is None:
      return None
    second_note = semi_flat_part.getElementAfterElement(first_note, [m21.note.Note, m21.note.Rest])
    if second_note:
      phrase_end = second_note.offset + second_note.quarterLength
    else:
      phrase_end = first_note.offset + first_note.quarterLength

    melody_phrase = mutil.trim_stream(semi_flat_part, phrase_start, phrase_end)
    phrases[melody_part.name] = mutil.get_phrase_rep(melody_phrase)
    for curr_part in measure_slice:
      if curr_part.name != melody_part.name:
        section = mutil.get_phrase_rep(mutil.trim_stream(curr_part.stream, phrase_start, phrase_end))
        if len(section) == 0:
          section = None
        phrases[curr_part.name] = section
    return phrases

  def _decode_measure_slice(self, measure_slice, n_best_hyps):
    beam = {0.0: [hypothesis((), 0.0, (), 0, 0.0, 0.0, 0.0)]}
    new_beam = {}
    continue_growing_hyps = True
    canonical_part = measure_slice[0]
    full_duration = canonical_part.stream.duration.quarterLength
    while continue_growing_hyps:
      continue_growing_hyps = False
      for hyp_dur in beam:
        if abs(full_duration - (canonical_part.stream[0].offset + hyp_dur)) < 1e-12:
          new_beam[hyp_dur] = beam[hyp_dur]
        elif full_duration < canonical_part.stream[0].offset + hyp_dur:
          continue # ignore hyps that are too long
        else:
          continue_growing_hyps = True
          for part_slice in measure_slice:
            # {part_idx: phrase}
            phrase_offset = canonical_part.stream[0].offset + hyp_dur
            melody_phrases = self.get_phrases_after_offset(phrase_offset, measure_slice, part_slice)
            prev_note = canonical_part.stream.getElementAtOrBefore(phrase_offset - 0.1)
            for hyp in beam[hyp_dur]:
              new_hyps = self._grow_hyps_in_beam(melody_phrases, prev_note, part_slice.name, hyp)
              for new_hyp in new_hyps:
                if new_hyp.duration not in new_beam:
                  new_beam[new_hyp.duration] = []
                new_beam[new_hyp.duration].append(new_hyp)
      if continue_growing_hyps:
        all_new_hyps = [i for j in new_beam.values() for i in j]
        consolidated_all_new_hyps = []
        notes_set = set()
        for h in all_new_hyps:
          note_tup = tuple(h.notes)
          if note_tup not in notes_set:
            consolidated_all_new_hyps.append(h)
            notes_set.add(note_tup)
        all_new_hyps = sorted(consolidated_all_new_hyps,
                              key=lambda hyp: get_score(hyp, self._tm_phrase_weight,
                                                        self._tm_notes_weight,
                                                        self._lm_weight),
                              reverse=True)[:self._beam_size]
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
                        key=lambda hyp: get_score(hyp, self._tm_phrase_weight,
                                                  self._tm_notes_weight,
                                                  self._lm_weight),
                        reverse=True)[:self._beam_size]
    return final_hyps[:max(n_best_hyps, 10)]

  def _get_measure_slice(self):
    measures_by_part =  {part.name: part.stream.getElementsByClass(m21.stream.Measure).stream() for part in self._parts}
    num_measures = max([len(measures) for measures in measures_by_part.values()])
    for i in range(0, num_measures, 4):
      end_idx = min(i + 4, num_measures)
      yield [PartSlice(name=part_name, stream=part[i:end_idx]) for part_name, part in measures_by_part.items()]

  def decode(self, n_best_hyps):
    with tqdm(desc='decoding') as pbar:
      best_hyps_so_far = [hypothesis((), 0.0, (), 0, 0.0, 0.0, 0.0)]
      for measure_slice in self._get_measure_slice():
        best_hyps_continuation = self._decode_measure_slice(measure_slice, n_best_hyps)
        new_best_hyps = []
        for prefix_hyp in best_hyps_so_far[:n_best_hyps]:
          for suffix_hyp in best_hyps_continuation:
            new_notes = prefix_hyp.notes + suffix_hyp.notes
            new_tm_phrase_logprob = prefix_hyp.tm_phrase_logprob + suffix_hyp.tm_phrase_logprob
            new_tm_notes_logprob = prefix_hyp.tm_notes_logprob + suffix_hyp.tm_notes_logprob
            new_lm_logprob = prefix_hyp.lm_logprob + suffix_hyp.lm_logprob
            new_duration = prefix_hyp.duration + suffix_hyp.duration
            new_best_hyps.append(
              hypothesis(new_notes, new_duration, suffix_hyp.context, suffix_hyp.context_size,
                         new_tm_phrase_logprob, new_tm_notes_logprob, new_lm_logprob))
        best_hyps_so_far = sorted(new_best_hyps,
                                  key=lambda hyp: get_score(hyp, self._tm_phrase_weight,
                                                            self._tm_notes_weight,
                                                            self._lm_weight),
                                  reverse=True)
        pbar.update(best_hyps_so_far[0].duration)

      final_hyps = []
      for hyp in best_hyps_so_far:
        new_beams = self._grow_hyps_in_beam({p.name: ("END",) for p in self._parts}, None, self._parts[0].name, hyp)
        final_hyps.extend(new_beams)

      consolidated_final_hyps = []
      notes_set = set()
      for h in final_hyps:
        if tuple(h.notes) not in notes_set:
          consolidated_final_hyps.append(h)
          notes_set.add(tuple(h.notes))

      final_hyps = sorted(consolidated_final_hyps,
                          key=lambda hyp: get_score(hyp, self._tm_phrase_weight,
                                                    self._tm_notes_weight,
                                                    self._lm_weight),
                          reverse=True)[:n_best_hyps]
      return final_hyps[:n_best_hyps]

  def hyp_to_stream(self, hyp):
    notes = [n for n in hyp.notes if n != "BAR" and n != "END"]
    # translate note sequence into music21 stream
    measure_stream = self._parts[0].stream.getElementsByClass(m21.stream.Measure)
    notes_stream = mutil.make_stream_from_strings(notes)

    return mutil.put_notes_in_measures(measure_stream, notes_stream)
