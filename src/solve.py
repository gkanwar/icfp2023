import argparse
import json
import numpy as np
import tqdm
from target import *
from sa import *

class Problem:
    def __init__(self, spec):
        self.width = spec['room_width']
        self.height = spec['room_height']
        self.swidth = spec['stage_width']
        self.sheight = spec['stage_height']
        self.spos = spec['stage_bottom_left']
        self.musicians = np.array(spec['musicians'])
        positions = []
        tastes = [[] for _ in range(np.max(self.musicians)+1)]
        for person in spec['attendees']:
            x = person['x']
            y = person['y']
            positions.append((x,y))
            t = person['tastes']
            assert len(t) == len(tastes), f'{len(t)=} vs {len(tastes)=}'
            for i,ti in enumerate(t):
                tastes[i].append(ti)
        self.positions = np.array(positions)
        self.tastes = np.array(tastes)

def sol_to_json(sol):
    return { 'placements': [ {'x': x, 'y': y} for (x,y) in sol ] }

def make_hexagonal_packing(width, height, *, rot):
    # make a hexagonal circle packing
    # -> a triangular lattice of center points
    if rot == 'ud': # option 1: up/down triangles
        nx = int(width / 10) + 1
        ny = int(height / (10*np.sqrt(3)/2)) + 1
        coords = []
        for i in range(nx):
            for j in range(ny):
                x = i*10.0
                y = j*10.0000001*np.sqrt(3)/2
                if j % 2 == 1:
                    x += 5.0
                if x <= width and y <= height:
                    coords.append((x,y))
        return coords
    elif rot == 'lr': # option 2: left/right triangles
        nx = int(width / (10*np.sqrt(3)/2)) + 1
        ny = int(height / 10) + 1
        coords = []
        for i in range(nx):
            for j in range(ny):
                x = i*10.0*np.sqrt(3)/2
                y = j*10.0000001
                if i % 2 == 1:
                    y += 5.0
                if x <= width and y <= height:
                    coords.append((x,y))
        return coords
    else:
        raise RuntimeError(f'Unknown rot {rot}')

def sa_fixed_coords(prob, coords):
    coords = np.array(coords)
    # values by instrument and coord
    value_grid = []
    # preferences for pos by instrument
    pos_rank_grid = []
    # coord index for each person
    cur_sol = np.zeros(len(prob.musicians), dtype=int)
    print('Building taste fields')
    for inst,tastes in enumerate(tqdm.tqdm(prob.tastes)):
        values = np.zeros(len(coords))
        assert len(prob.positions) == len(tastes)
        for (x,y),ti in zip(prob.positions, tastes):
            d2 = (coords[:,0] - x)**2 + (coords[:,1] - y)**2
            values += ti/d2
        inds = np.argsort(values)
        pos_rank_grid.append(np.flip(inds))
        value_grid.append(values)
    print('Assigning instrument locs by priority')
    used_coords = set([])
    for i,inst in enumerate(tqdm.tqdm(prob.musicians)):
        j = 0
        while pos_rank_grid[inst][j] in used_coords:
            j += 1
            assert j < len(pos_rank_grid[inst])
        cur_sol[i] = pos_rank_grid[inst][j]
        used_coords.add(cur_sol[i])
        pos_rank_grid[inst] = pos_rank_grid[inst][j+1:]
    # TODO: SA improvements
    sol = coords[cur_sol]
    eval_res = evaluate(prob, sol)
    print(f'{eval_res=}')
    value = eval_res['value']
    return dict(sol=sol, value=value)

def strategy1(prob):
    inner_w = prob.swidth - 20
    inner_h = prob.sheight - 20
    res = dict(msg='no valid packing', value=0, sol=None)
    for rot in ['ud', 'lr']:
        coords = make_hexagonal_packing(inner_w, inner_h, rot='ud')
        if len(coords) < len(prob.musicians):
            continue
        coords = np.array([
            (x+prob.spos[0]+10, y+prob.spos[1]+10) for (x,y) in coords])
        next_res = sa_fixed_coords(prob, coords)
        if next_res['value'] > res['value']:
            res = next_res
    return res

def solve(args):
    i = args.i
    with open(f'problems/{i}.json', 'r') as f:
        prob = Problem(json.load(f))
    res = strategy1(prob)
    print(f'Got res {res}')
    true_value = evaluate(prob, res['sol'])
    print(f'Found sol with value {true_value}')
    with open(f'solutions/{i}.json', 'w') as f:
        json.dump(sol_to_json(res['sol']), f)
    print('Done.')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('i', type=int)
    args = parser.parse_args()
    solve(args)

if __name__ == '__main__':
    main()
