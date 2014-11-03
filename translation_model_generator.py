from music21 import *
import optparse
import re
import sys

optparser = optparse.OptionParser()
optparser.add_option("-m", "--mode", dest="mode", default="major", help="Mode of the music to model")
optparser.add_option("-f", "--file_output", dest="file", default="data/translation_model_major.txt", help="File to write the language model to")
(opts, _) = optparser.parse_args()

mode = 'minor' if opts.mode == 'minor' else 'major'
output_file = opts.file

tm = {}
bach_paths = corpus.getComposer('bach')
bach_paths += corpus.getComposer('handel')


def transposeToKey(stream, curr_key, new_key):
	sc = scale.ChromaticScale(curr_key.pitchAndMode[0].name + '5')
	sc_pitches = [str(p) for p in sc.pitches]
	num_halfsteps = 0
	pattern = re.compile(new_key.upper() + '\d')
	for pitch in sc_pitches:
		if pattern.match(pitch):
			break
		else:
			num_halfsteps = num_halfsteps + 1
	stream.flat.transpose(num_halfsteps, inPlace=True)

for path in bach_paths:
	sys.stderr.write('.')
	composition = corpus.parse(path)
	#if len(composition.parts) < 4:
	#	continue
	keySig = composition.analyze('key')
	if keySig.pitchAndMode[1] != mode:
		continue
	if mode == 'major':
		scaleFromMode = scale.MajorScale(keySig.pitchAndMode[0])
		transposeToKey(composition, keySig, 'c')
	else:
		scaleFromMode = scale.MinorScale(keySig.pitchAndMode[0])
		transposeToKey(composition, keySig, 'a')
	melody = composition.parts[0]
	harmony = composition.parts[-1]

	for harmony_note in harmony.flat.notesAndRests:
		if not harmony_note.isNote:
			harmony_rep = 'R'
		else:
			harmony_rep = harmony_note.nameWithOctave
		harmony_offset = harmony_note.offset
		melody_notes = melody.getElementsByOffset(harmony_offset, offsetEnd=harmony_offset + harmony_note.duration.quarterLength, 
											     mustFinishInSpan=False, mustBeginInSpan=False)
		if harmony_rep not in tm:
			d = {}
			for melody_note in melody_notes.flat.notesAndRests:
				if not melody_note.isNote:
					melody_rep = 'R'
				else:
					melody_rep = melody_note.nameWithOctave
				d[melody_rep] = 1
			tm[harmony_rep] = d
		else:
			for melody_note in melody_notes.flat.notesAndRests:
				if not melody_note.isNote:
					melody_rep = 'R'
				else:
					melody_rep = melody_note.nameWithOctave
				if melody_rep not in tm[harmony_rep]:
					tm[harmony_rep][melody_rep] = 1
				else:
					tm[harmony_rep][melody_rep] = tm[harmony_rep][melody_rep] + 1

f = open(output_file, 'w')
for harmony_note in tm:
	total_notes_harmonized = 0
	for melody_note in tm[harmony_note]:
		total_notes_harmonized = total_notes_harmonized + tm[harmony_note][melody_note]
	for melody_note in tm[harmony_note]:
		prob = tm[harmony_note][melody_note] / float(total_notes_harmonized)
		output_line = ''.join([str(melody_note), ' ||| ', str(harmony_note), ' ||| ', str(prob), '\n'])
		f.write(output_line)



