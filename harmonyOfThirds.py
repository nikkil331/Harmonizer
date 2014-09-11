from music21 import *

handelmovement = corpus.parse("handel/hwv56")
vio = handelmovement[1]
harmony = stream.Stream()
keySig = vio.getKeySignatures()[0]
harmony.append(keySig)
scaleFromKey = scale.MajorScale(keySig.pitchAndMode[0]) 
for note in vio.flat.notesAndRests:
	if note.isNote:
		degree = scaleFromKey.getScaleDegreeFromPitch(note)
		if degree is None: 
			harmony.append(note)
		else:
			inter = interval.notesToInterval(note, scaleFromKey.pitchFromDegree(degree + 2))
			harmony.append(note.transpose(inter.intervalClass))
	else:
		harmony.append(note)
score = stream.Score([harmony,vio])

score.show()