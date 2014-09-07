from music21 import *

handelmovement = corpus.parse("handel/hwv56")
vio = handelmovement[1]
harmony = stream.Stream()
third = interval.GenericInterval(3)