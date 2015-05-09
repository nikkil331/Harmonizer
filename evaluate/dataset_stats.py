from music21 import *

major_songs = 0
minor_songs = 0
maj_soprano_notes = 0
maj_alto_notes = 0
maj_tenor_notes = 0
maj_bass_notes = 0
min_soprano_notes = 0
min_alto_notes = 0
min_tenor_notes = 0
min_bass_notes = 0

for path in corpus.getBachChorales()[50:]:
    training_song = corpus.parse(path);
    keySig = training_song.analyze('key')
    if keySig.pitchAndMode[1] == "major":
        isMajor = True
        major_songs += 1
    else:
        isMajor = False
        minor_songs += 1
    if isMajor:
        maj_soprano_notes += len(training_song.parts["Soprano"].flat.notesAndRests)
        maj_alto_notes += len(training_song.parts["Alto"].flat.notesAndRests)
        maj_tenor_notes += len(training_song.parts["Tenor"].flat.notesAndRests)
        maj_bass_notes += len(training_song.parts["Bass"].flat.notesAndRests)
    else:
        min_soprano_notes += len(training_song.parts["Soprano"].flat.notesAndRests)
        min_alto_notes += len(training_song.parts["Alto"].flat.notesAndRests)
        min_tenor_notes += len(training_song.parts["Tenor"].flat.notesAndRests)
        min_bass_notes += len(training_song.parts["Bass"].flat.notesAndRests)

print "# Major Songs: ", major_songs
print "# Minor Songs: ", minor_songs
print "# Major Soprano Notes: ", maj_soprano_notes
print "# Major Alto Notes: ", maj_alto_notes
print "# Major Tenor Notes: ", maj_tenor_notes
print "# Major Bass Notes: ", maj_bass_notes
print "# Minor Soprano Notes: ", min_soprano_notes
print "# Minor Alto Notes: ", min_alto_notes
print "# Minor Tenor Notes: ", min_tenor_notes
print "# Minor Bass Notes: ", min_bass_notes