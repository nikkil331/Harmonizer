import optparse
from language_model import LanguageModel
from translation_model import TranslationModel
from music21 import *
from collections import namedtuple
import sys
import re
import math

optparser = optparse.OptionParser()
optparser.add_option("--tm", dest="tm_path", default="data/translation_model_major.txt", help="File containing translation model")
optparser.add_option("--lm", dest="lm_path", default="data/language_model_major.txt", help="File containing language model")
optparser.add_option("--output", dest="output_file", default="evaluation_scores.txt", help="Destination of results")
(opts, _) = optparser.parse_args()

lm = LanguageModel(path=opts.lm_path, part="Bass")
tm = TranslationModel(path=opts.tm_path, melody_part="Soprano", harmony_part="Bass")

def get_score(tm_score, lm_score):
    return tm_score + lm_score

def get_lm_score(context, note):
    return math.log(lm.get_probability(context, note))
    
def get_tm_score(m_note, h_note):
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

def get_note_rep(note):
    if note.isNote:
        return note.nameWithOctave
    else:
        return "R"

def transpose(stream, mode):
	curr_pitch = stream.analyze('key').pitchAndMode[0].name
	new_pitch = 'C' if mode == 'major' else 'A'
	# what is 5 and does this generalize to the bass part???
	sc = scale.ChromaticScale(curr_pitch + '5')
	sc_pitches = [str(p) for p in sc.pitches]
	num_halfsteps = 0
	pattern = re.compile(new_pitch + '\d')
	for pitch in sc_pitches:
		if pattern.match(pitch):
			break
		else:
			num_halfsteps = num_halfsteps + 1
	stream.flat.transpose(num_halfsteps, inPlace=True)

results = {}

testSongs = corpus.getBachChorales()[50:]
hypothesis = namedtuple("hypothesis", "notes, context, tm_logprob, lm_logprob")

songsSkipped = 0
for path in testSongs:
	try:
		sys.stderr.write('.')
		song = corpus.parse(path)
		keySig = song.analyze('key')
		transpose(song, keySig.pitchAndMode[1])

		melody = song.parts[tm.melody_part].flat.notesAndRests
		harmony = song.parts[tm.harmony_part].flat.notesAndRests

		hyp = hypothesis(["S"], ("S"), 0.0, 0.0)
		for m in melody:
			melody_offset = m.offset
			harmony_notes = harmony.notesAndRests.getElementsByOffset(melody_offset, offsetEnd=melody_offset + m.duration.quarterLength, 
													     mustFinishInSpan=False, mustBeginInSpan=False)
			m_rep = get_note_rep(m)
			for h in harmony_notes:
				h_rep = get_note_rep(h)
				hyp = update_hypothesis(hyp,m_rep,h_rep)

		results[path] = (float(hyp.tm_logprob)/len(melody.flat.notesAndRests), 
			float(hyp.lm_logprob)/len(melody.flat.notesAndRests))

	except KeyError, e:
		songsSkipped +=1

print "Songs skipped: {0}".format(songsSkipped)

tm_score = sum([r[0] for r in results.values()])/len(results)
lm_score = sum([r[1] for r in results.values()])/len(results)
print "TM score: {0}".format(tm_score)
print "LM score: {0}".format(lm_score)
