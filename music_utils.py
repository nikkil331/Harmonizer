from collections import namedtuple
from music21 import *
import math
import re


lm_hypothesis = namedtuple("lm_hypothesis", "notes, context, lm_logprob")

def get_score(tm_score, lm_score):
    return tm_score + lm_score

def get_lm_score(lm, context, note):
    return math.log(lm.get_probability(context, note))
    
def get_tm_score(tm, m_note, h_note):
    return math.log(tm.get_probability(m_note, h_note))

def update_hypothesis(curr_hyp, m_note, h_note):
    # update note list
    new_notes = curr_hyp.notes[:]
    new_notes.append(h_note)

    # update context sliding window
    new_context = list(curr_hyp.context)
    if m_note != "R" or new_context[-1] != "R":
        new_context.append(h_note)
    #get last n
    new_context = tuple(new_context[-lm.ngram_size:])

    # update logprob scores
    new_tm_logprob = curr_hyp.tm_logprob + get_tm_score(m_note, h_note)
    new_lm_logprob = curr_hyp.lm_logprob + get_lm_score(curr_hyp.context, h_note) 
    return hypothesis(new_notes, new_context, new_tm_logprob, new_lm_logprob)

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


def get_note_rep(note):
    if note.isNote:
        return note.nameWithOctave + ":" + str(note.duration.quarterLength)
    else:
        return "R:" + note.duration.quarterLength

def get_phrase_rep(phrase):
	return tuple([get_note_rep(note) for note in phrase])


def transpose(stream):
	keySig = stream.analyze('key')
	curr_pitch = keySig.pitchAndMode[0].name
	new_pitch = 'C' if keySig.pitchAndMode[1] == "major" else 'A'
	sc = scale.ChromaticScale(curr_pitch + '5')
	sc_pitches = [str(p)[:-1] for p in sc.pitches]
	num_halfsteps = sc_pitches.index(new_pitch)
	stream.flat.transpose(num_halfsteps, inPlace=True)


def get_harmony_notes(melodyNote, harmonyStream):
	melody_offset = melodyNote.offset
	melody_duration = melodyNote.duration.quarterLength
	harmony_section = harmonyStream.getElementsByOffset(melody_offset, offsetEnd=melody_offset + melody_duration, 
													     mustFinishInSpan=False, mustBeginInSpan=False)
	return harmony_section.flat.notesAndRests