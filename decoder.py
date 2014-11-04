from music21 import *
import sys
import optparse
import copy
import math
from collections import namedtuple

optparser = optparse.OptionParser()
optparser.add_option("--training", dest="train", default="data/major_text.txt", help="File to read training data from")
optparser.add_option("--test", dest="test", default="data/major_test_text.txt", help="File to read test data from")
optparser.add_option("--tm", dest="tm", default="data/translation_model_major.txt", help="File containing translation model")
optparser.add_option("--lm", dest="lm", default="data/language_model_major.txt", help="File containing language model")
optparser.add_option("--n", dest="n", default='5', help="N-gram size")
(opts, _) = optparser.parse_args()

train = opts.train
test = opts.test
tm_file = opts.tm
lm_file = opts.lm
n = int(opts.n)

def get_song_list(file_path):
    f = open(file_path, 'r')
    songs = (f.read()).split('\n|||\n')
    return [song.split() for song in songs[:-1]]

def get_language_model():
    lm = {}
    f = open(lm_file, 'r')
    for line in f:
        (context, note, prob) = line.split("|||")
        context = tuple(context.strip().split(" "))
        note = note.strip()
        prob = float(prob.strip())
        if context not in lm:
            lm[context] = {}
        lm[context][note] = prob
    return lm

def get_translation_model():
    tm = {}
    f = open(tm_file, 'r')
    for line in f:
        (melody, harmony, prob) = line.split("|||")
        melody = melody.strip()
        harmony = harmony.strip()
        prob = float(prob.strip())
        if melody not in tm:
            tm[melody] = {}
        tm[melody][harmony] = prob
    return tm


lm = get_language_model()
tm = get_translation_model()
test_song = corpus.parse("bach/bwv390")
melody = test_song.parts[0]

for m in melody.flat.notesAndRests:
    if m.isNote:
        m_rep = m.nameWithOctave
    else:
        m_rep = "R"
    if m_rep not in tm:
        tm[m_rep] = {m_rep: 1.0}
        missing_in_tm = missing_in_tm + 1

missing_in_lm = 0
hypothesis = namedtuple("hypothesis", "notes, context, tm_logprob, lm_logprob")
beam = [hypothesis(["S"], ["S"], 0.0, 0.0)]
for m in melody.flat.notesAndRests:
    beam_copy = beam[:]
    for hyp in beam_copy:
        beam.remove(hyp)
        if m.isNote:
            m_rep = m.nameWithOctave
        else:
            m_rep = "R"
        context_seen = tuple(hyp.context) in lm
        tm_probs = tm[m_rep].values()
        avg_tm_prob = sum(tm_probs)/float(len(tm_probs))
        max_tm_prob = max(tm_probs)
        min_tm_prob = min(tm_probs)
        if context_seen:
            lm_probs = lm[tuple(hyp.context)].values()
            avg_lm_prob = sum(lm_probs)/float(len(lm_probs))
            max_lm_prob = max(lm_probs)
            min_lm_prob = min(lm_probs)
        for h in tm[m_rep]:
            p_tm = abs(tm[m_rep][h] - avg_tm_prob) / float(max_tm_prob - min_tm_prob)
            if context_seen:
                if h in lm[tuple(hyp.context)]:
                    p_lm = abs(lm[tuple(hyp.context)][h] - avg_lm_prob) / float(max_lm_prob - min_lm_prob)
                else: 
                    p_lm = abs(lm[tuple(hyp.context)]["<UNK>"] - avg_lm_prob) / float(max_lm_prob - min_lm_prob)
            else:
                p_lm = 1e-6
                missing_in_lm = missing_in_lm + 1
            new_notes = hyp.notes[:]
            new_notes.append(h)
            new_context = hyp.context[:]
            if m_rep != "R" or new_context[-1] != "R":
                new_context.append(h)
            new_context = new_context[-n:]
            new_hyp = hypothesis(new_notes, new_context, hyp.tm_logprob + math.log(p_tm), hyp.lm_logprob + math.log(p_lm))
            beam.append(new_hyp)
    sys.stderr.write (".")
    beam = sorted(beam, key = lambda hyp: hyp.tm_logprob + hyp.lm_logprob, reverse=True)[:500]

print "Missing in LM:", missing_in_lm
winner = beam[0].notes
#harmony = stream.Stream()
i = 1

print "winner length:", len(winner)
print "melody length:", len(melody.flat.notesAndRests)
harmony = copy.deepcopy(melody)
for h in harmony.flat.notesAndRests:
    if winner[i] == "R":
        length = h.quarterLength
        h = note.Rest()
        h.quarterLength = length
    else:
        #h = copy.deepcopy(m)
        h.pitch = pitch.Pitch(winner[i])
    i = i + 1

score = stream.Score([melody, harmony])
score.show()






