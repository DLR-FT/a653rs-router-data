from sys import argv
from pandas import DataFrame, Series, read_csv

def decode():
  df = read_csv(argv[1])
  df['data'] = df[channel_labels(0, 4)].apply(decode_bytes, axis=1)
  df['event'] = df[channel_labels(4, 8)].apply(decode_bytes, axis=1)
  df = df[["Time [s]", "event", "data"]]
  df = df.loc[(df['event'].shift() != df['event']) & (df['data'].shift() != df['data'])]
  print(df.head(100))

def decode_bytes(c: Series) -> int:
  return sum(x<<i for i, x in enumerate(c))

def channel_labels(start, stop) -> [str]:
  return ["Channel %d" % c for c in range(start, stop)]