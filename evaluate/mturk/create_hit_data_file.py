import sys
import os
import itertools
import random
import math
import argparse

argparser = argparse.ArgumentParser()
argparser.add_argument("output_file", help="path to file in which to write the HIT")
requiredNamed = argparser.add_argument_group('required named arguments')
requiredNamed.add_argument("--clips", dest="clips", help="Directory containing mturkclips")
args = argparser.parse_args()

mturk_base_dir = args.clips
audio_chunks = [f for f in os.listdir(mturk_base_dir + "/bach/mp3_chunks")]
systems = [f for f in os.listdir(mturk_base_dir) if os.path.isdir(mturk_base_dir + "/" + f)]
controls = ["best.mp3", "worst.mp3"]

def system_and_song_toString(system, song):
	if "control" in system:
		return system
	else:
		return system + "/" + song

with open(args.output_file, "w") as f:
	for j in range(2):
		for i in range(4):
			f.write("clip_" +str(j) + "_" + str(i))
			if j*4 + i == 7:
				f.write("\n")
			else:
				f.write(", ") 


	systems_per_hit = list(itertools.combinations(systems, 4))
	edited_systems_per_hit = []
	for system_set in systems_per_hit:
		if "control" in system_set:
			if random.random() < 0.3:
				others = [s for s in system_set if s != "control"]
				for c in controls:
					others.append("control/" + c)
					edited_systems_per_hit.append(tuple(others))
					others.pop(-1)
		else:
			edited_systems_per_hit.append(system_set)
	systems_per_hit = edited_systems_per_hit
	print "Number of system combinations: " + str(len(systems_per_hit))
	random.shuffle(systems_per_hit)
	systems_and_song_per_hit = list(itertools.product(systems_per_hit, audio_chunks))
	random.shuffle(systems_and_song_per_hit)
	numLines = 0
	firstInPair = True
	for (systems, song) in systems_and_song_per_hit:
		for i in range(3):
			f.write(system_and_song_toString(systems[i], song))
			f.write(", ")
		if firstInPair:
			f.write(system_and_song_toString(systems[3], song))
			f.write(", ")
		else:
			f.write(system_and_song_toString(systems[3], song))
			f.write("\n")
			numLines+=1
		firstInPair = not firstInPair
	print "Num Lines: " + str(numLines)
