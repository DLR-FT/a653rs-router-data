import seaborn as sb
import matplotlib.pyplot as plt
import matplotlib
from sys import argv, stdin, stdout

from master_thesis_data import *


def plot_delays():
    if len(argv) > 1:
        input = argv[1]
    else:
        input = stdin
    df = read_csv(input)
    if len(argv) > 2:
        output = argv[2]
    else:
        output = "out.png"
    df = events_raw_delays(df)
    df = df.where(df["delay"].between(0, 0.01))
    df["type"] = df["type"].apply(lambda x: str(x).split(".")[-1])
    sb.boxplot(data=df, x="delay", y="type")
    plt.subplots_adjust(left=0.3)
    plt.savefig(output)

