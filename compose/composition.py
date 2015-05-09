from music21 import *
import argparse
import decoder
from translation_model import TranslationModel
from language_model import LanguageModel
from collections import namedtuple
from music_utils import *



class Composition(object):
    def __init__(self):
        self._parts = []

    def add_part(self, name, stream):
        self._parts.append((name, stream))


    def play(self):
        score = stream.Score([part[1] for part in self._parts])
        score.show()

    def save(self, name):
        score = stream.Score([part[1] for part in self._parts])
        f = open(name, 'w')
        f.write(musicxml.m21ToString.fromMusic21Object(score))
        f.close()


    '''
    Should only be called if there exist >= 1 part 
    in the composition already
    '''

    def create_part(self, name, lm_file, tm_phrase_files, tm_note_files):
        lm = LanguageModel(path=lm_file, part=name)
        tms = []
        for (i, (f1, f2)) in enumerate(zip(tm_phrase_files, tm_note_files)):
            tms.append(TranslationModel(phrase_path=f1, note_path=f2, harmony_part=name, melody_part=self._parts[i][0]))
        d = decoder.Decoder(self._parts, lm, tms, tm_phrase_weight=1, tm_notes_weight=1, lm_weight=1)
        hyp = d.decode(1)[0]
        new_part = d.hyp_to_stream(hyp)
        return (name, new_part, decoder.get_score(hyp))

    def best_new_part(self, parts, directory, lm_suffix, note_suffix, phrase_suffix):
        second_parts = map(lambda x: self.create_part(x, '{0}/{1}_{2}'.format(directory, x, lm_suffix),
                                            ['{0}/{1}_{2}_{3}'.format(directory, y[0],x, phrase_suffix) 
                                                for y in self._parts],
                                            ['{0}/{1}_{2}_{3}'.format(directory, y[0],x, note_suffix) 
                                                for y in self._parts]), 
                                        parts)
        winner = max(second_parts, key=lambda x: x[2])
        self._parts.append((winner[0], winner[1]))
        return winner[0]


    def save(self, name):
        score = stream.Score([part[1] for part in self._parts])
        f = open(name, 'w')
        f.write(musicxml.m21ToString.fromMusic21Object(score))
        f.close()


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("melody", help="Path to the composition from which to pull the melody line")
    argparser.add_argument("--melody_name", dest="melody_name", default="Soprano",
                    help="Name of melody part")
    argparser.add_argument("--part_names", dest="part_names", default="Alto,Tenor,Bass", 
                    help="Names of parts to generate")
    argparser.add_argument("--output_file", dest="output", default="output.xml",
                    help="Path to write the composition to")
    argparser.add_argument("--directory", dest="dir", default=".",
                    help="Directory where models live. Default is the current directory.")
    argparser.add_argument("--tm_note_suffix", dest="tm_note_suffix", default="translation_model_major.txt",
                     help="Filename suffix for note translation models")
    argparser.add_argument("--tm_phrase_suffix", dest="tm_phrase_suffix", default="translation_model_major_rhythm.txt",
                     help="Filename suffix for phrase translation models")
    argparser.add_argument("--lm_suffix", dest="lm_suffix", default="language_model_major.txt",
                     help="Filename suffix for language models")
    args = argparser.parse_args()

    test_song = corpus.parse(args.melody)
    transpose(test_song, "C")
    parts = args.part_names.split(",")
    c = Composition()
    c.add_part(args.melody_name, test_song.parts[args.melody_name])
    while parts:
        parts.remove(c.best_new_part(parts, args.dir, 
            args.lm_suffix, args.tm_note_suffix, args.tm_phrase_suffix))
    c.save(args.output)

if __name__ == "__main__":
    main()

