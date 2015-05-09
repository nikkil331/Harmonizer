import os
import random
import xml.etree.ElementTree as ET
from music21 import *

def get_octave_range(part):
    if part is "Soprano":
        return range(4, 7)
    elif part is "Alto" or part is "Tenor":
        return range (3, 6)
    elif part is "Bass":
        return range (2, 5)
    else:
        return range (2, 7)

def make_measure(p, length):
    rhythm_options = [0.25, 0.5, 1.0, 2.0, 4.0]
    pitch_options = ['A-', 'A', 'A#', 'B-', 'B', 'C', 'C#', 'D-', 'D', 'D#', 'E-', 'E', 'F', 'F#', 'G-', 'G', 'G#']
    octave_range = get_octave_range(p)

    measure = stream.Measure()
    curr_length = 0
    while (curr_length < length):
        rhythm = random.choice(rhythm_options)
        pitch = random.choice(pitch_options)
        octave = random.choice(octave_range)
        if rhythm + curr_length > length:
            rhythm = length - curr_length
        new_note = note.Note(pitch+str(octave), quarterLength=rhythm)
        measure.append(new_note)
        curr_length += rhythm
    return measure

def make_song():
    partNames = ['Soprano', 'Alto', 'Tenor', 'Bass']
    parts = []
    for p in partNames:
        part = stream.Part()
        part.id = p
        # 14 measures
        for i in range(14):
            m = make_measure(p, 4)
            part.append(m)
        parts.append(part)
    return stream.Score(parts)

def make_harmony(comp):
    try:
        melody = comp.parts['Soprano']
        partNames = ['Alto', 'Tenor', 'Bass']
        parts = [melody]
        measures = [e for e in melody.getElementsByClass("Measure")]
        for p in partNames:
            part = stream.Part()
            part.id = p
            for i in range(len(measures)):
                m = make_measure(p, measures[i].duration.quarterLength)
                part.append(m)
            parts.append(part)
        return stream.Score(parts)
    except KeyError, e:
        return None

def save_song(song, filename):
    xml = musicxml.m21ToString.fromMusic21Object(song)
    partNames = ['Soprano', 'Alto', 'Tenor', 'Bass']
    partMappings = {}
    root = ET.fromstring(xml)
    for (i, part) in enumerate(root.iter('score-part')):
        if i >= len(partNames):
            break
        name = partNames[i]
        partMappings[part.get('id')] = name
        part.set('id', name)
    for part in root.iter('part'):
        part.set('id', partMappings[part.get('id')])
    tree = ET.ElementTree(root)
    tree.write(filename)

def get_bach_test_songs():
    test_songs = []
    for s in corpus.getBachChorales()[:50]:
        comp = corpus.parse(s)
        keySig = comp.analyze('key')
        if keySig.pitchAndMode[1] == 'major':
            test_songs.append((s, comp))
    return test_songs

songs_to_harmonize = get_bach_test_songs()

songs_harmonized = 0
songs_skipped = 0
for path, comp in songs_to_harmonize:
    song = make_harmony(comp)
    if not song:
        print path
        songs_skipped += 1
    else:
        songs_harmonized += 1
        save_song(song, "harmonizations/{0}.xml".format(os.path.splitext(os.path.basename(path))[0]))

print "# Songs Harmonized: %d" % songs_harmonized
print "# Songs Skipped: %d" % songs_skipped
