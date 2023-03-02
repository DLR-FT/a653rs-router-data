from sys import argv
from pandas import DataFrame, Series, read_csv

def decode():
  df = read_csv(argv[1])
  gpios = df[["Channel %d" % c for c in range(1, 8)]]
  df['decoded'] = gpios.apply(decode_bytes, axis=1)
  df = df[["Time [s]", "decoded"]]
  df = df.loc[df['decoded'].shift() != df['decoded']]
  print(df)

def decode_bytes(c: Series) -> int:
  return sum(x<<i for x, i in enumerate(c[::-1]))
