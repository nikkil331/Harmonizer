for f in $(ls clips/us_phrase_based_weighted/midis);
	do timidity clips/us_phrase_based_weighted/midis/$f -Ow -o - | lame - -b 64 clips/us_phrase_based_weighted/mp3_chunks/${f%.*}.mp3;
done