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
        melody = tuple([m for m in melody if m != "BAR" and m != "END"])
        harmony = tuple([h for h in harmony if h != "BAR" and h != "END"])

        if not self._tm_phrases:
            return (math.log(1e-10), self.get_probability_notes(melody, harmony))
        elif melody not in self._tm_phrases:
            if harmony is not melody:
                return (math.log(1e-10), self.get_probability_notes(melody, harmony))
            else:
                return (0, 0)
        elif harmony not in self._tm_phrases[melody]:
            return (math.log(1e-10), self.get_probability_notes(melody, harmony))
        else:
            return (math.log(self._tm_phrases[melody][harmony]), self.get_probability_notes(melody, harmony))

    def get_probability_notes(self, melody, harmony):
        if not self._tm_notes:
            return -1
        total_prob = 0
        for (i, m_note) in enumerate(melody):
            if m_note != "BAR" and m_note != "END":  
                m_note = get_note_pitch_from_rep(m_note) 
                h_notes = notes_playing_while_sounding(harmony, melody, i, i)  
                for h_note in h_notes:
                    h_note = get_note_pitch_from_rep(h_note)
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
        note_pitches = note.split(":")[0].split(",")
        rhythm = note.split(":")[1]
        harmonies = []
        for pitch in note_pitches:
            if pitch in self._tm_notes:
                harmonies.extend([n + ":" + rhythm for n in self._tm_notes[pitch].keys()])
        if len(harmonies) == 0:
            return ["R:" + rhythm]
        return harmonies
        
    def insert_bars(self, melody, harmony):
        bar_offsets = []
        end_offset = None
        curr_offset = 0
        for m in melody:
            if m == "BAR":
                bar_offsets.append(curr_offset)
            elif m == "END":
                end_offset = curr_offset
            curr_offset += get_note_length_from_rep(m)

        curr_offset = 0
        new_harmony = []

        # bar_offsets is sorted in ascending order.
        # whenever a bar is added to the harmony, its
        # corresponding offset is popped from the front
        # of the list. there is an invariant that no offsets
        # in bar_offsets should be less than curr_offset.
        for h in harmony:
            if not bar_offsets:
                new_harmony.extend(harmony[harmony.index(h):])
                break

            h_pitch = get_note_pitch_from_rep(h)
            h_len = get_note_length_from_rep(h)
            # insert bar into new harmony before the current
            # harmony note
            if curr_offset == bar_offsets[0]:
                new_harmony.append("BAR")
                bar_offsets.pop(0)

            # split up current note to insert bars if necessary
            while len(bar_offsets) > 0 and curr_offset + h_len > bar_offsets[0]:
                note_before_bar_len = bar_offsets[0] - curr_offset
                note_after_bar_len = curr_offset + h_len - bar_offsets[0]
                
                new_harmony.append(h_pitch + ":" + str(note_before_bar_len))
                new_harmony.append("BAR")
                bar_offsets.pop(0)
                
                h_len = note_after_bar_len
                curr_offset += note_before_bar_len

            # append a potentially split version of the current note
            new_harmony.append(h_pitch + ":" + str(h_len))

            curr_offset += h_len

        if end_offset == curr_offset:
            new_harmony.append("END")

        return tuple(new_harmony)

    def get_harmonies(self, melody):
        melody_no_bars = tuple([m for m in melody if m != "BAR" and m != "END"])
        if not melody_no_bars:
            return []

        single_note_harmonies = []
	
        if len(melody_no_bars) < 2:
            single_note_harmonies = [(n,) for m in melody_no_bars for n in self.get_harmonies_note(m)]
        else:
            single_note_harmonies = list(product([n for n in self.get_harmonies_note(melody_no_bars[0])], [n for n in self.get_harmonies_note(melody_no_bars[1])]))
        if melody_no_bars not in self._tm_phrases:
            translations = single_note_harmonies
        else:
            translations = self._tm_phrases[melody_no_bars].keys() + single_note_harmonies

        translations = [self.insert_bars(melody, t) for t in translations if t]    
        return translations

    def write_to_file(self, model, path, phrase=True):
        f = open(path, 'w')
        for melody_phrase in model:
            for harmony_phrase in model[melody_phrase]:
	 	if phrase:
                	melody_string = ' '.join(melody_phrase)
                	harmony_string = ' '.join(harmony_phrase)
			output_line = ''.join([str(melody_string), ' ||| ', str(harmony_string), ' ||| ', \
                    		str(model[melody_phrase][harmony_phrase]), '\n'])
		else:
			output_line = ''.join([str(melody_phrase), ' ||| ', str(harmony_phrase), ' ||| ', \
                                str(model[melody_phrase][harmony_phrase]), '\n'])
                f.write(output_line)


def main():
    tm = TranslationModel("Bass", "Soprano", note_path="data/bass_translation_model_major.txt")
    print tm.get_harmonies("C5")

        
if __name__ == "__main__":
    main()
