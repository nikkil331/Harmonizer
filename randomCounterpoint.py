from music21 import *
import random

handelmovement = corpus.parse("handel/hwv56")
vio = handelmovement[1]
harmony = stream.Stream()
keySig = vio.getKeySignatures()[0]
harmony.append(keySig)
scaleFromKey = scale.MajorScale(keySig.pitchAndMode[0]) 
chordTones = [2,4,7]
for note in vio.flat.notesAndRests:
	if note.isNote:
		degree = scaleFromKey.getScaleDegreeFromPitch(note)
		if degree is None: 
			harmony.append(note)
		else:
			chordTone = random.choice(chordTones)
			harmonyDegree = (((degree - 1) + chordTone) % 7) + 1
			harmonyNote = note.transpose(0)
			harmonyNote.pitch.nameWithOctave = str(scaleFromKey.pitchFromDegree(harmonyDegree))
			harmony.append(harmonyNote)
	else:
		harmony.append(note)
score = stream.Score([harmony,vio])

score.show()