from collections import namedtuple

import music21 as m21
import os
import argparse
from compose import decoder
from compose.translation_model import TranslationModel
from compose.language_model import LanguageModel
import utils.music_utils as mutil

Part = namedtuple('Part', ['name', 'score', 'stream'])

class Composition(object):
  def __init__(self):
    self._parts = []

  def add_part(self, part):
    self._parts.append(part)

  def play(self):
    score = m21.stream.Score([part[1] for part in self._parts])
    score.show()

  def create_part(self, name, lm, tms):
    d = decoder.Decoder(self._parts, lm, tms, tm_phrase_weight=1, tm_notes_weight=1, lm_weight=1)
    hyp = d.decode(1)[0]
    new_part = d.hyp_to_stream(hyp)
    return Part(name=name, stream=new_part, score=decoder.get_score(hyp))

  def best_new_part(self, parts, directory):
    best_part = None
    for part in parts:
      lm = LanguageModel(path=os.path.join(directory, '{0}_language_model.txt'.format(part)), part=part)
      tms = {}
      for existing_part in self._parts:
        existing_part_name = existing_part.name
        tm = TranslationModel(existing_part_name, part,
                              phrase_path=os.path.join(directory, '{0}_{1}_translation_model_rhythm.txt'.format(existing_part_name, part)),
                              note_path=os.path.join(directory, '{0}_{1}_translation_model.txt'.format(existing_part_name, part)))
        tms[existing_part_name] = tm
      new_part = self.create_part(part, lm, tms)
      if best_part is None:
        best_part = new_part
      elif new_part.score > best_part.score:
        best_part = new_part
    return best_part


  def save(self, name):
    score = m21.stream.Score([part.stream for part in self._parts])
    with open(name ,'w') as f:
      exporter = m21.musicxml.m21ToXml.GeneralObjectExporter(score)
      f.write(exporter.parse().decode('utf-8'))


def main():
  argparser = argparse.ArgumentParser()
  argparser.add_argument("--source_melody", type=str, required=True,
                         help="Path to the composition from which to pull the melody line")
  argparser.add_argument("--melody_name", default="Soprano", help="Name of melody part")
  argparser.add_argument("--harmony_names", dest="harmony_names", default="Alto,Tenor,Bass",
                         help="Names of parts to generate.")
  argparser.add_argument("--output", dest="output", default="output.xml", help="Path to write the composition to")
  argparser.add_argument("--model_dir", required=True, type=str,
                         help="Directory where models live. Default is the current directory.")

  args = argparser.parse_args()

  test_song = m21.converter.parse(args.source_melody)
  transposed_test_song = mutil.transpose(test_song, "C")
  parts = args.harmony_names.split(",")
  c = Composition()
  c.add_part(Part(name=args.melody_name, stream=transposed_test_song.parts[args.melody_name], score=-1.0))
  while parts:
    best_new_part = c.best_new_part(parts, args.model_dir)
    c.add_part(best_new_part)
    parts.remove(best_new_part.name)

  c.save(args.output)


if __name__ == "__main__":
  main()
