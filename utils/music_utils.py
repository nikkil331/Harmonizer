from collections import namedtuple
from fractions import Fraction
import copy

import music21 as m21

lm_hypothesis = namedtuple("lm_hypothesis", "notes, context, lm_logprob")


def get_score(tm_score, lm_score):
  return tm_score + lm_score


def get_lm_score(lm, context, note):
  return lm.get_probability(context, note)


def get_tm_score(tm, m_note, h_note):
  return tm.get_probability(m_note, h_note)


def update_lm_hypothesis(lm, curr_hyp, note):
  new_notes = curr_hyp.notes[:]
  new_notes.append(note)
  new_context = list(curr_hyp.context)
  if new_context[-1] != "R":
    new_context.append(note)

  new_context = tuple(new_context[-lm.ngram_size:])

  new_lm_logprob = curr_hyp.lm_logprob + get_lm_score(lm, curr_hyp.context, note)

  return lm_hypothesis(new_notes, new_context, new_lm_logprob)


def update_tm_hypothesis(tm, curr_hyp, m_note, h_note):
  return curr_hyp + get_tm_score(tm, m_note, h_note)


def get_pitch_rep(note):
  if type(note) == m21.stream.Measure:
    return "BAR"
  if type(note) == m21.bar.Barline and note.style == 'final':
    return "END"
  elif note.isChord:
    return ','.join([get_pitch_rep(n) for n in note])
  elif note.isNote:
    if note.pitch.accidental and note.pitch.accidental.fullName not in ['sharp', 'flat']:
      note.pitch.getEnharmonic(inPlace=True)
    return note.nameWithOctave
  else:
    return "R"


def get_note_rep(note):
  if type(note) == m21.stream.Measure:
    return "BAR"
  if type(note) == m21.bar.Barline and note.style == 'final':
    return "END"
  elif note.isChord:
    return ','.join([get_pitch_rep(n) for n in note]) + ':{0}'.format(float(note.quarterLength))
  elif note.isNote:
    if note.pitch.accidental and (note.pitch.accidental.fullName == 'double-flat' or
                                  note.pitch.accidental.fullName == 'double-sharp'):
      note.pitch.getEnharmonic(inPlace=True)
    return note.nameWithOctave + ':{0}'.format(float(note.quarterLength))
  else:
    return 'R:{0}'.format(float(note.quarterLength))


def get_phrase_rep(phrase):
  return tuple([get_note_rep(note) for note in phrase])


def transpose_helper(stream, new_key, start, i):
  key_sig = stream.measures(start, i).analyze('key')
  curr_pitch = key_sig.tonic.name
  sc = m21.scale.ChromaticScale(curr_pitch + '5')
  sc_pitches = [str(p)[:-1] for p in sc.pitches]
  num_halfsteps = sc_pitches.index(new_key)
  if num_halfsteps >= 6:
    num_halfsteps -= 12
  stream.measures(start, i).transpose(num_halfsteps, inPlace=True)


def transpose(stream, new_key):
  new_key = new_key.upper()
  curr_key_signature = stream.parts[0][1].keySignature
  start = 0
  for i, t in enumerate(stream.parts[0].getElementsByClass(['Measure'])):
    if t.keySignature and t.keySignature != curr_key_signature:
      transpose_helper(stream, new_key, start, i - 1)
      start = i
      curr_key_signature = t.keySignature
  transpose_helper(stream, new_key, start, len(stream.parts[0].getElementsByClass(['Measure'])))


def get_harmony_notes(melodyNote, harmonyStream):
  melody_offset = melodyNote.offset
  melody_duration = melodyNote.duration.quarterLength
  harmony_section = harmonyStream.getElementsByOffset(melody_offset, offsetEnd=melody_offset + melody_duration,
                                                      mustFinishInSpan=False, mustBeginInSpan=False)
  return harmony_section.flat.notesAndRests


def make_stream_from_notes(notes):
  s = m21.stream.Stream()
  for n in notes:
    s.append(n)
  return s


def make_stream_from_strings(notes):
  s = m21.stream.Stream()
  for n_rep in notes:
    note_pitches = [n.split(":")[0] for n in n_rep.split(",")]
    duration = n_rep.split(":")[1]
    if "R" in note_pitches:
      n = m21.note.Rest(quarterLength=float(duration))
    else:
      if len(note_pitches) > 1:
        n = m21.chord.Chord([m21.note.Note(p, duration) for p in note_pitches])
      else:
        n = m21.note.Note(note_pitches[0], quarterLength=float(duration))
    s.append(n)

  return s


def get_duration_of_stream(s):
  return sum([n.duration.quarterLength for n in s.notesAndRests])


def trim_stream(s, begin_offset, end_offset):
  acceptable_classes = {m21.note.Note, m21.chord.Chord, m21.note.Rest, m21.stream.Measure}

  section = s.getElementsByOffset(begin_offset, offsetEnd=end_offset, \
                                  mustBeginInSpan=False, includeEndBoundary=False, \
                                  includeElementsThatEndAtStart=False)
  section = [elem for elem in section if type(elem)in acceptable_classes]
  if len(section) > 0:
    # trim beginning
    if type(section[0]) == m21.stream.Measure and section[0].offset != section[1].offset:
      section.pop(0)

    if type(section[0]) == m21.stream.Measure:
      section[0].offset = begin_offset

      section[1].quarterLength -= (begin_offset - section[1].offset)
      section[1].offset = begin_offset
    else:
      section[0].quarterLength -= (begin_offset - section[0].offset)
      section[0].offset = begin_offset

    if type(section[-1]) == m21.stream.Measure:
      section.pop(len(section) - 1)
    # trim end
    section[-1].quarterLength = end_offset - section[-1].offset
  return section


def get_note_pitch_from_rep(n_rep):
  n_rep = n_rep.decode('utf8') if type(n_rep) == bytes else n_rep
  return n_rep.split(":")[0]


def get_note_length_from_rep(n_rep):
  n_rep = n_rep.decode('utf8') if type(n_rep) == bytes else n_rep
  return float(Fraction(n_rep.split(":")[1])) if n_rep != "BAR" and n_rep != "END" else 0


def get_phrase_length_from_rep(p_rep):
  return sum([get_note_length_from_rep(n) for n in p_rep])


def notes_and_rests(phrase_rep):
  return [n for n in phrase_rep if n != "BAR" and n != "END"]


# assumed that playing_notes and sounding_notes are lined up
def notes_playing_while_sounding(playing_notes, sounding_notes, sounding_note_start_idx, sounding_note_end_idx):
  sounding_note_length = get_note_length_from_rep(sounding_notes[sounding_note_start_idx])
  if sounding_note_start_idx != sounding_note_end_idx:
    sounding_note_length += get_note_length_from_rep(sounding_notes[sounding_note_end_idx])
  sounding_note_offset = 0
  for i in range(sounding_note_start_idx):
    sounding_note_offset += get_note_length_from_rep(sounding_notes[i])
  notes_to_return = []
  for n in playing_notes:
    n_length = get_note_length_from_rep(n)
    sounding_note_offset -= n_length
    if sounding_note_offset < 0:
      notes_to_return.append(n)
      if abs(sounding_note_offset) >= sounding_note_length:
        break
  return notes_to_return


def put_notes_in_measures(measure_stream, note_stream):
  curr_measure_template = measure_stream[0]
  curr_measure = m21.stream.Measure()
  new_stream = m21.stream.Stream()
  for (j, n) in enumerate(note_stream):
    curr_measure.append(n)
    if curr_measure.duration.quarterLength >= curr_measure_template.duration.quarterLength:
      new_measure = m21.stream.Measure()

      if curr_measure.duration.quarterLength > curr_measure_template.duration.quarterLength:
        new_note = copy.deepcopy(curr_measure[-1])
        overshoot = curr_measure.duration.quarterLength - curr_measure_template.duration.quarterLength
        curr_measure.duration.quarterLength -= overshoot
        curr_measure[-1].duration.quarterLength -= overshoot
        curr_measure[-1].tie = m21.tie.Tie("start")
        new_note.tie = m21.tie.Tie("stop")
        new_note.duration.quarterLength = overshoot
        new_measure.append(new_note)

      new_stream.append(curr_measure)
      curr_measure_template = curr_measure_template.next()
      new_measure.offset = curr_measure_template.offset
      curr_measure = new_measure

  return new_stream


def get_max_pitch(song, part):
  p = song[part].flat.notes
  p = [max(n).pitch if n.isChord else n.pitch for n in p]
  return max(p)


def get_min_pitch(song, part):
  p = song[part].flat.notes
  p = [min(n).pitch if n.isChord else n.pitch for n in p]
  return min(p)
