from music_utils import *
from itertools import *

class TranslationModel(object):

    def __init__(self, harmony_part, melody_part, phrase_path=None, note_path=None):
        self._tm_phrases = {}
        self._tm_notes = {}
        self.harmony_part = harmony_part
        self.melody_part = melody_part
        if phrase_path:
            self._read_file(phrase_path, phrases=True)
        if note_path:
            self._read_file(note_path, phrases=False)

    def _read_file(self, path, phrases):
        f = open(path, 'r')
        for line in f:
            melody_string, harmony_string, prob = line.strip().split(" ||| ")
            if phrases:
                melody_phrase = tuple(melody_string.split())
                harmony_phrase = tuple(harmony_string.split())
                self.add_to_model(melody_phrase, harmony_phrase, float(prob), self._tm_phrases)
            else:
                self.add_to_model(melody_string, harmony_string, float(prob), self._tm_notes)

    def add_to_model(self, melody, harmony, prob, model):
        if melody not in model:
            model[melody] = {harmony : prob}
        else:
            model[melody][harmony] = prob

    def get_probability(self, melody, harmony):
        if not self._tm_phrases:
            return self.get_probability_notes(melody, harmony)

        if melody not in self._tm_phrases:
            if harmony is not melody:
                return self.get_probability_notes(melody, harmony)
            else:
                return 0
        elif harmony not in self._tm_phrases[melody]:
            return self.get_probability_notes(melody, harmony)
        else:
            return math.log(self._tm_phrases[melody][harmony])

    def get_probability_notes(self, melody, harmony):
        if not self._tm_notes:
            return -1
        total_prob = 0
        for (i, m_note) in enumerate(melody):
            if m_note != "BAR" and m_note != "END":   
                h_notes = notes_playing_while_sounding(harmony, melody, i)  
                for h_note in h_notes:
                    if m_note not in self._tm_notes:
                        if h_note is not m_note:
                            total_prob += math.log(1e-10)
                        else:
                            total_prob += 0
                    elif h_note not in self._tm_notes[m_note]:
                        total_prob += math.log(1e-10)
                    else:
                        total_prob += math.log(self._tm_notes[m_note][h_note])

        return total_prob


    def get_harmonies_note(self, note):
        pitch, rhythm = note.split(":")
        if pitch not in self._tm_notes:
            return [tuple("R:" + rhythm)]
        else:
            return [n + ":" + rhythm for n in self._tm_notes[pitch].keys()]

    def get_harmonies(self, melody):
        melody = tuple([m for m in melody if m != "BAR" and m != "END"])
        if not melody:
            return []

        single_note_translation = []

        if len(melody) < 2:
            single_note_harmonies = [(n,) for m in melody for n in self.get_harmonies_note(m)]
        else:
            single_note_harmonies = list(product([n for n in self.get_harmonies_note(melody[0])], [n for n in self.get_harmonies_note(melody[1])]))

        if melody not in self._tm_phrases:
            single_note_harmonies
        else:
            translations = self._tm_phrases[melody].keys() + single_note_harmonies
            return translations

    def write_to_file(self,path):
        f = open(path, 'w')
        for melody_phrase in self._tm_phrases:
            for harmony_phrase in self._tm_phrases[melody_phrase]:
                melody_string = ' '.join(melody_phrase)
                harmony_string = ' '.join(harmony_phrase)
                output_line = ''.join([str(melody_string), ' ||| ', str(harmony_string), ' ||| ', \
                    str(self.get_probability(melody_phrase, harmony_phrase)), '\n'])
                f.write(output_line)


def main():
    tm = TranslationModel("Bass", "Soprano", note_path="data/bass_translation_model_major.txt")
    print tm.get_harmonies("C5")

        
if __name__ == "__main__":
    main()