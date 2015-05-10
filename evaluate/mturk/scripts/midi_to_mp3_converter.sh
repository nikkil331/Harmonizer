for f in $(ls $1/*.mid);
	do timidity $f -Ow -o - | lame - -b 64 $2/${(basename f)%.*}.mp3;
done