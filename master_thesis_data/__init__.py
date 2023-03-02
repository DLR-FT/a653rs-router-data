from sys import argv
from pandas import DataFrame, read_csv

def decode():
  df = read_csv(argv[1])
  gpio = df[["Time [s]"] + ["Channel %d" % c for c in range(0, 8)]]
  print(gpio)