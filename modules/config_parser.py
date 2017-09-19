import argparse
import os

parser = argparse.ArgumentParser(description = 'Content Shim.')
parser.add_argument('-c', '--config', default=os.path.dirname(__file__) + "/../config/local.yaml", help='Configuration file path.')

args = parser.parse_args()
