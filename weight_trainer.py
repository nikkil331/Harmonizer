from music21 import *
from music_utils import *
from translation_model import TranslationModel
from language_model import LanguageModel
from decoder import Decoder

lm_file = 'data/bass_language_model_major.txt'
tm_phrases_file = ['data/Soprano_Bass_translation_model_major_rhythm.txt']
tm_notes_file =	 ['data/Soprano_Bass_translation_model_major.txt']

def get_n_best_lists(initial_params, n):
	num_songs_translated = 0
	n_best_lists = {}
	for path in corpus.getBachChorales()[20:]:		
			n_best_lists[path] = []
			training_song = corpus.parse(path);
			keySig = training_song.analyze('key')
			if keySig.pitchAndMode[1] != "major":
				continue
			num_songs_translated += 1
			transpose(training_song)
			lm = LanguageModel("Bass", lm_file)
			tms = []
			for (phrases, notes) in zip(tm_phrases_file, tm_notes_file):
				tm = TranslationModel("Bass", "Soprano", phrases, notes)
				tms.append(tm)
			d = Decoder([("Soprano", training_song.parts["Soprano"])], lm, tms,
						 initial_params[0], initial_params[1], initial_params[2])
			print n
			n_best_lists[path] = d.decode(n)
	print num_songs_translated
	return get_n_best_lists

def get_score_for_n_best_lists(n_best_lists):
	return sum([hyps[0].tm_phrases_logprob + hyps[0].tm_notes_logprob + hyps[0].lm_logprob
				for _, hyps in n_best_lists.values()])

def get_line_from_hyp(hyp, param_id):
	if param_id == 0:
		return (harmony_hyp.tm_phrases_logprob, 
			 	harmony_hyp.tm_notes_logprob + harmony_hyp.lm_logprob)
	elif param_id == 1:
		return (harmony_hyp.tm_notes_logprob, 
			 	harmony_hyp.tm_phrases_logprob + harmony_hyp.lm_logprob)
	else:
		return (harmony_hyp.lm_notes_logprob, 
			 	harmony_hyp.tm_phrases_logprob + harmony_hyp.tm_notes_logprob)

def get_intersection(l1, l2):
	return float(l2[1] - l1[1]) / float(l1[0] - l2[0])

def get_threshold_points(param_id, n_best_lists):
	threshold_points = set()
	for song_path in n_best_lists:
		translation_lines = []
		for harmony_hyp in n_best_lists[song_path]:
			translation_lines.append(get_line_from_hyp(harmony_hyp, param_id))
		translation_lines = sorted(translation_lines, reverse=True)
		prev_boundary = -float('inf')
		curr_line_index = 0
		l = translation_lines[curr_line_index]
		while curr_line_index < len(translation_lines):
			smallest_intersection = float('inf')
			line_idx = curr_line_index
			for (j, l2) in enum(translation_lines[curr_line_index + 1:]):
				intersection = get_intersection(l, l2)
				if intersection > prev_boundary and intersection < smallest_intersection:
					smallest_intersection = intersection
					line_idx = j
			threshold_points.add(smallest_intersection)
			curr_line_index = line_idx
	return threshold_points

def is_converged(params1, params2):
	for i in range(3):
		if abs(params1[i] - params2[i]) > 0.01:
			return False
	return True

def powell(params, no_iters):
	for i in range(no_iters):
		num_songs_translated = 0
		n_best_lists = get_n_best_lists(params, 10)
		converged = False
		while not converged:
			original_params = params
			for i in range(2):
				threshold_points = get_threshold_points(i, n_best_lists)
				threshold_points = sorted(list(threshold_points))
				params_list = list(params)
				current_best_score = get_score_for_n_best_lists(n_best_lists)
				for t in threshold_points:
					params_list[i] = t
					best_hyps = get_n_best_lists(tuple(params_list), 1)
					score = get_score_for_n_best_lists(best_hyps)
					if score > current_best_score:
						current_best_score = score
				params_list[i] = current_best_score
				params = tuple(params_list)
			converged = is_converged(original_params, params)
		return params

print powell((1, 1, 1), 5)







			


