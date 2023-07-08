import argparse
import json
import matplotlib.pyplot as plt
import numpy as np
import os
import subprocess

def run(args):
    probs = []
    values = []
    for i in range(1, args.max_i+1):
        prob_fname = f'problems/{i}.json'
        sol_fname = f'solutions/{i}.json'
        if not os.path.exists(sol_fname):
            continue
        res = subprocess.check_output([
            'eval/target/release/icfp2023-eval', prob_fname, sol_fname])
        res = json.loads(res)
        probs.append(i)
        values.append(res['value'])
        print(f'{i} => {res["value"]}')
    fig, axes = plt.subplots(2,2)
    axes[0,0].plot(probs, values, marker='o')
    axes[0,1].pie(values, labels=probs)
    axes[1,1].plot(np.cumsum(np.flip(np.sort(values))), marker='x')
    plt.show()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('max_i', type=int)
    args = parser.parse_args()
    run(args)

if __name__ == '__main__':
    main()
