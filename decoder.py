from nltk.model.ngram import *
from nltk.probability import LidstoneProbDist
import optparse

optparser = optparse.OptionParser()
optparser.add_option("--training", dest="train", default="data/major_text.txt", help="File to read training data from")
optparser.add_option("--test", dest="test", default="data/major_test_text.txt", help="File to read test data from")
optparser.add_option("--n", dest="n", default='3', help="N-gram size")
(opts, _) = optparser.parse_args()

train = opts.train
test = opts.test
n = int(opts.n)

def get_song_list(file_path):
    f = open(train, 'r')
    songs = (f.read()).split('\n|||\n')
    return [song.split() for song in songs[:-1]]

def get_language_model():
    est = lambda fdist, bins: LidstoneProbDist(fdist, 0.2)
    songs = get_song_list(train)
    lm = NgramModel(n, songs, estimator=est)
    return lm

def get_perplexity(lm):
    songs = get_song_list(test)
    perplexity = 0
    for song in songs:
    	perplexity = perplexity + lm.perplexity(song)
    return perplexity

lm = get_language_model()
print "LM: " + str(lm)
print "Perplexity: " + str(get_perplexity(lm))

