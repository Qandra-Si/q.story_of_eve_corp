""" Q.StoryOfEveCorp

Prerequisites:
    * Have a Python 3 environment available to you (possibly by using a
      virtual environment: https://virtualenv.pypa.io/en/stable/).
    * Run pip install -r requirements.txt with this directory as your root.
    * Change render.py settings and mood for your needs.

To run this program, make sure you have completed the prerequisites and then
run the following command from this directory as the root:

$ chcp 65001 & @rem on Windows only!
$ python eve_sde_tools.py
$ python story_of_eve_corp.py -i ./input -o ./output -v
$ ffmpeg -i ./output/%05d.png -vf "scale=3840:2160,fps=24" out.mp4

"""
import os
import argparse
import render


__version__ = '0.0.1'
__author__ = 'Qandra Si'


def usage():
    '''Prints command line'''
    print('Usage: story_of_eve_corp.py -i input_dir -o output_dir [-f] from_date [-t] to_date [-v]')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', action="store", dest="inputdir", help='Input directory for events to render')
    parser.add_argument('-o', action="store", dest="outdir", help='Output directory for video frames')
    parser.add_argument('-f', action="store", dest="datefrom", help='Date from which processing should start')
    parser.add_argument('-t', action="store", dest="dateto", help='Date on which processing should be completed')
    parser.add_argument('-v', action="store_true", dest="verbose", help='Verbose mode')

    args = parser.parse_args()

    if not args.outdir or not args.inputdir:
        usage()
        exit(-1)

    cwd: str = os.path.dirname(os.path.realpath(__file__))
    render.render_base_image(cwd, args.inputdir, args.outdir, date_from=args.datefrom, date_to=args.dateto, verbose=args.verbose)
