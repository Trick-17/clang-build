import argparse

parser = argparse.ArgumentParser()

parser.add_argument("-V", action='store_true')
group = parser.add_mutually_exclusive_group()
group.add_argument("-a", action='store_true')
group.add_argument("-l", type=str, nargs="*", default=set())

args = parser.parse_args()

print(args)