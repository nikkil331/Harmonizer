from music21 import *
import optparse
import re
import sys

optparser = optparse.OptionParser()
optparser.add_option("-m", "--mode", dest="mode", default="major", help="Mode of the music to model")
optparser.add_option("-f", "--file_output", dest="file", default="data/major_text.txt", help="File to write text to")
(opts, _) = optparser.parse_args()

mode = 'minor' if opts.mode == 'minor' else 'major'
output_file = opts.file

bach_paths = corpus.getComposer('bach')

f = open(output_file, 'w')
num_songs = 0

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

for path in bach_paths[:300]:
	sys.stderr.write('.')
	composition = corpus.parse(path)
	if len(composition.parts) < 2:
		continue
	harmony = composition.parts[1]
	keySig = composition.analyze('key')
	if keySig.pitchAndMode[1] != mode:
		continue
	num_songs = num_songs + 1
	if mode == 'major':
		scaleFromMode = scale.MajorScale(keySig.pitchAndMode[0])
		transposeToKey(composition, keySig, 'c')
	else:
		scaleFromMode = scale.MinorScale(keySig.pitchAndMode[0])
		transposeToKey(composition, keySig, 'a')

	prev_note = None
	for note in harmony.flat.notesAndRests:
		if not note.isNote:
			note_rep = 'R'
		else:
			note_rep = note.nameWithOctave
		if not (prev_note == 'R' and note == 'R'):
			f.write(note_rep + ' ')
		prev_note = note_rep

	f.write('\n|||\n')

print num_songs
