from music21 import *

handelmovement = corpus.parse("handel/hwv56")
vio = handelmovement[1]
harmony = stream.Stream()

for note in vio:
	harmony.append(note.transpose('M3'))

harmony.show()