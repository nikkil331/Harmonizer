MelTS is an automatic harmonization system that creates multi-part arrangements
in the style of the data on which it is trained. The system approaches the problem
of harmonization from a machine tranlsation perspective, modeling the melody of a song
as the source language and each harmony as a target language. Below is a step-by-step guide 
to training the models and generating a simple composition.

Before using MelTS, first set the PYTHONPATH environment variable to include MelTS
with the following command:

```
echo PYTHONPATH=$PYTHONPATH:/path/to/melts/evaluate:path/to/melts/train:path/to/melts/compose:path/to/melts/utils
```

MelTS relies on language and translation models to create compositions. The system requires a language model for each harmony voice to be generated in addition to a translation model between the melody voice and every harmony voice and translation models between each of the harmony voices. The models are saved in text files after they are generated so that they can be used repeatedly for future compositions. For example models, see the models/bach/major directory which contains all the translation and language models required to create, from a given Soprano part, the Alto, Tenor, and Bass parts in the major mode and in the style of Bach.

All scripts related to training the models are located in the train/ directory.

To train a MelTS translation model from the Soprano part to the Bass part, the following basic command can be used:

```
python translation_model_generator.py --melody=Soprano --harmony=Bass --training_paths=major_bach_training_paths.txt --output_dir=/path/of/output/directory
```

Similarly, to train a MelTS language model for the Bass part, use the command:

```
python language_model_generator.py --part_name=Bass --training_paths=major_bach_training_paths.txt --output_dir=/path/of/output/directory
```

After the models are trained, you can train weights for the respective models by typing the command:

```
python weight_trainer.py --training_songs=major_bach_optimization_paths.txt --model_directory=/path/to/models --melodies=Soprano --harmony=Bass
```

```weight_trainer.py``` is an implementation of the Powell algorithm. You can optimize on the harmonization from multiple melodies to one harmony, although optimizing for just one melody to one harmony seems to suffice. It is recommended that you train the weights on a held-out set of data. Trained weights usually result in a higher quality system based on overall perplexity scores. However, the system can run without trained weights, in which case each model will be weighed equally.

MelTS offers a perplexity metric calculator to evaluate the trained models. The script that calculates these scores is located in the evaluate/ directory. To get perplexity scores for your models over a held out test set, use the following command:

```
python evaluator.py major_bach_test_paths.txt --melody=Soprano --harmonies=Bass --directory=/path/to/models --tm_phrase_weight=1 --tm_note_weight=1 --lm_weight=1
```

Finally, compose/composition.py is used to create a full composition based on a melody. Run composition.py with the following command:

```
python composition.py /path/to/melody --melody_name=Soprano --harmony_names=Bass --directory=/path/to/models --output_file=mycomposition.xml
```

The composition script accepts a path to a music xml file containing the melody line to be harmonized. The name of the melody voice and the harmony voices to be generated are also specified. The final composition will be saved to mycomposition.xml.

