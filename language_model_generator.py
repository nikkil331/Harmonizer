from music21 import *
import optparse
import re

optparser = optparse.OptionParser()
optparser.add_option("-m", "--mode", dest="mode", default="major", help="Mode of the music to model")
optparser.add_option("-f", "--file_output", dest="file", default="data/language_model_major.txt", help="File to write the language model to")
(opts, _) = optparser.parse_args()

mode = 'minor' if opts.mode == 'minor' else None
output_file = opts.file

num_songs = 0
lm = {}
bach_paths = corpus.getComposer('bach')


def transposeToKey(stream, curr_key, new_key):
	sc = scale.ChromaticScale(curr_key.pitchAndMode[0].name + '5')
	sc_pitches = [str(p) for p in sc.pitches]
	print sc_pitches
	num_halfsteps = 0
	pattern = re.compile(new_key.upper() + '\d')
	for pitch in sc_pitches:
		if pattern.match(pitch):
			print pitch
			break
		else:
			num_halfsteps = num_halfsteps + 1
	print num_halfsteps
	stream.flat.transpose(num_halfsteps, inPlace=True)

for path in bach_paths[:20]:
	composition = corpus.parse(path)
	keySig = composition.analyze('key')
	print keySig.pitchAndMode
	if keySig.pitchAndMode[1] != mode:
		continue
	if len(composition) < 3:
		continue
	num_songs = num_songs + 1
	if not mode:
		scaleFromMode = scale.MajorScale(keySig.pitchAndMode[0])
		transposeToKey(composition, keySig, 'c')
	else:
		scaleFromMode = scale.MinorScale(keySig.pitchAndMode[0])
		transposeToKey(composition, keySig, 'a')
	harmony = composition[2]

	sliding_window = ('S',)
	for note in harmony.flat.notesAndRests:
		if not note.isNote:
			note_rep = 'R'
		else:
			note_rep = note.nameWithOctave
		if sliding_window not in lm:
			lm[sliding_window] = {note_rep: 1}
		else:
			if note_rep not in lm[sliding_window]:
				lm[sliding_window][note_rep] = 1
			else:
				lm[sliding_window][note_rep] = lm[sliding_window][note_rep] + 1
		list_window = list(sliding_window)
		if not (list_window[-1] is 'R' and note_rep is 'R'):
			list_window.append(note_rep)
		if len(list_window) > 3:
			list_window.pop(0)
		sliding_window = tuple(list_window)

print num_songs

f = open(output_file, 'w')
for context in lm:
	total_notes_after_context = 0
	for note in lm[context]:
		total_notes_after_context = total_notes_after_context + lm[context][note]
	for note in lm[context]:
		prob = lm[context][note] / float(total_notes_after_context)
		output_line = ''.join([str(context), ' ||| ', str(note), ' ||| ', str(prob), '\n'])
		f.write(output_line)



