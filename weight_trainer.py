import sys
from music21 import *
from music_utils import *
from translation_model import TranslationModel
from language_model import LanguageModel
from decoder import Decoder

lm_file = 'Harmonizer/data/barbershop/models/2_language_model_major_threshold_2_tag.txt'
tm_phrases_file = ['Harmonizer/data/barbershop/models/1_2_translation_model_major_rhythm_threshold_2_tag.txt']
tm_notes_file =	 ['Harmonizer/data/barbershop/models/1_2_translation_model_major_threshold_2_tag.txt']

def get_n_best_lists(initial_params, n):
        sys.stderr.write("Getting n best lists...\n")
	num_songs_translated = 0
	n_best_lists = {}
	i = 0
        for path in get_barbershop_data():
        #for path in corpus.getBachChorales()[:20]:
		if i == 50:
                        break
                if "classic_tags" not in path:
                        continue
                training_song = converter.parse(path);
                keySig = training_song.analyze('key')
                if keySig.pitchAndMode[1] != "major":
                        continue
                num_songs_translated += 1
                transpose(training_song)
                sys.stderr.write("transposed " + path + "\n")
                lm = LanguageModel(2, lm_file)
                tms = []
                for (phrases, notes) in zip(tm_phrases_file, tm_notes_file):
                        tm = TranslationModel(2, 1, phrases, notes)
                        tms.append(tm)
                d = Decoder([(1, training_song.parts[1])], lm, tms,
                              tm_phrase_weight=initial_params[0], tm_notes_weight=initial_params[1], 
                              lm_weight=initial_params[2])
                try:
                        hyps = d.decode(n)
                        sys.stderr.write("num hyps: " + str(len(hyps)))
                        n_best_lists[path] = hyps
                        sys.stderr.write("decoded " + path + "\n")
                        i+=1
                except Exception as e:
                        sys.stderr.write(str(e))
                        
        return n_best_lists

def get_score_for_n_best_lists(n_best_lists):
	return sum([hyps[0].tm_phrase_logprob + hyps[0].tm_notes_logprob + hyps[0].lm_logprob
                    for hyps in n_best_lists.values()])

def get_line_from_hyp(hyp, param_id):
	if param_id == 0:
		return (hyp.tm_phrase_logprob, 
                        hyp.tm_notes_logprob + hyp.lm_logprob)
	elif param_id == 1:
		return (hyp.tm_notes_logprob, 
                        hyp.tm_phrase_logprob + hyp.lm_logprob)
	else:
		return (hyp.lm_logprob, 
                        hyp.tm_phrase_logprob + hyp.tm_notes_logprob)

def get_intersection(l1, l2):
        if l1[0] == l2[0]:
                return None
	return float(l2[1] - l1[1]) / float(l1[0] - l2[0])

def get_threshold_points(param_id, n_best_lists):
	sys.stderr.write("Getting threshold points...\n")
        threshold_points = set()
	for song_path in n_best_lists:
		translation_lines = []
		for harmony_hyp in n_best_lists[song_path]:
			translation_lines.append(get_line_from_hyp(harmony_hyp, param_id))
		if len(translation_lines) == 0:
                        sys.stderr.write(song_path + "has no translations")
                        continue
                translation_lines = sorted(translation_lines, reverse=True)
                prev_boundary = 0.01
		curr_line_index = 0
		l = translation_lines[curr_line_index]
                found_all_intersections = False
		while not found_all_intersections:
			smallest_intersection = float('inf')
			line_idx = curr_line_index
			for (j, l2) in enumerate(translation_lines[curr_line_index + 1:]):
				intersection = get_intersection(l, l2)
                                if not intersection:
                                        continue
                                if intersection > prev_boundary and intersection < smallest_intersection:
					smallest_intersection = intersection
					line_idx = j + curr_line_index + 1
                        if smallest_intersection == float('inf'):
                                found_all_intersections = True
                        else:
                                threshold_points.add(smallest_intersection)
                                curr_line_index = line_idx
                                l = translation_lines[curr_line_index]
	return threshold_points

def is_converged(params1, params2):
        sys.stderr.write("Checking convergence between: " + str(params1) + str(params2) + "\n")
	for i in range(3):
		if abs(params1[i] - params2[i]) > 0.001:
			return False
	return True

def get_score_from_hyps(n_best_lists, params):
        score_total = 0
        for hyps in n_best_lists.values():
                scores = []
                for h in hyps:
                        tm_phrase_logprob = params[0]*(h.tm_phrase_logprob)
                        tm_notes_logprob = params[1]*(h.tm_notes_logprob)
                        lm_logprob = params[2]*(h.lm_logprob)
                        scores.append(tm_phrase_logprob + tm_notes_logprob + lm_logprob)
                if len(scores) > 0:
                        score_total += max(scores)
        return score_total

def powell(initial_params, no_iters):
        for _ in range(no_iters):
                sys.stderr.write("Starting new iteration with params: " + str(initial_params) + "\n")
		num_songs_translated = 0
		n_best_lists = get_n_best_lists(initial_params, 10)
		converged = False
                num_iterations = 0
                prev_params = initial_params
                while not converged:
                        new_params_list = list(prev_params)
                        for i in range(3):
                                sys.stderr.write("Param Index: " + str(i) + "\n")
                                threshold_points = get_threshold_points(i, n_best_lists)
                                threshold_points = sorted(list(threshold_points))
                                if len(threshold_points) > 0:
                                        current_best_score = get_score_from_hyps(n_best_lists, initial_params)
                                        current_best_param_val = prev_params[i]
                                        curr_params_list = list(prev_params)
                                        curr_params_list[i] = threshold_points[0] - 0.01
                                        score = get_score_from_hyps(n_best_lists, tuple(curr_params_list))
                                        if score > current_best_score:
                                                current_best_score = score
                                                current_best_param_val = curr_params_list[i]
                                        for t in threshold_points:
                                                curr_params_list[i] = t + 0.01
                                                score = get_score_from_hyps(n_best_lists, tuple(curr_params_list))
                                                if score > current_best_score:
                                                        current_best_score = score
                                                        current_best_param_val = curr_params_list[i]
                                        new_params_list[i] = current_best_param_val
                        num_iterations += 1
                        sys.stderr.write("Num_iterations: " + str(num_iterations) + "\n")
                        new_params = tuple(new_params_list)
			converged = is_converged(prev_params, new_params) or num_iterations >= 15
                        prev_params = new_params
		initial_params = prev_params
        return initial_params

def main():
        sys.stderr.write("Beginning...\n")
        sys.stderr.write(str(powell((1, 1, 1), 5)) + "\n")

if __name__ == '__main__':
        main()






			


