import argparse
import json
import numpy as np
import queue
import subprocess
import tempfile
import tqdm
# from target import *
from sa import *

def evaluate(prob, sol):
    f_prob = tempfile.NamedTemporaryFile(mode='w')
    f_sol = tempfile.NamedTemporaryFile(mode='w')
    json.dump(prob.json, f_prob)
    json.dump(sol_to_json(sol), f_sol)
    f_prob.flush()
    f_sol.flush()
    res = subprocess.check_output([
        'eval/target/release/icfp2023-eval', f_prob.name, f_sol.name])
    return json.loads(res)

class Problem:
    def __init__(self, spec):
        self.json = spec
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

def init_sol_fixed_coords(prob, coords):
    coords = np.array(coords)
    # preferences for pos by instrument
    assign_prioq = queue.PriorityQueue()
    # coord index for each person
    cur_sol = np.zeros(len(prob.musicians), dtype=int)
    print('Building taste fields')
    for inst,tastes in enumerate(tqdm.tqdm(prob.tastes)):
        values = np.zeros(len(coords))
        assert len(prob.positions) == len(tastes)
        for (x,y),ti in zip(prob.positions, tastes):
            d2 = (coords[:,0] - x)**2 + (coords[:,1] - y)**2
            values += ti/d2
        for j,value in enumerate(values):
            assign_prioq.put((-value, inst, j))
    print('Assigning instrument locs by priority')
    used_coords = set([])
    remaining = [[] for _ in range(len(prob.tastes))]
    for i,inst in enumerate(prob.musicians):
        remaining[inst].append(i)
    while len(used_coords) < len(prob.musicians) and assign_prioq:
        value, inst, j = assign_prioq.get()
        if len(remaining[inst]) > 0 and j not in used_coords:
            i = remaining[inst].pop()
            cur_sol[i] = j
            used_coords.add(j)
    return cur_sol

def sa_fixed_coords(prob, coords, *, n_iter=100):
    person_to_coord = init_sol_fixed_coords(prob, coords)
    coord_to_person = -1*np.ones(len(coords), dtype=int)
    for person,coord in enumerate(person_to_coord):
        coord_to_person[coord] = person
    sol = coords[person_to_coord]
    # this all sort of sucks and is slow
    '''
    value = evaluate(prob, sol)['value']
    print(f'init value = {value}')
    NORM = 1000000.0
    for i in tqdm.tqdm(range(n_iter)):
        beta = 1000.0*i + 10.0*(n_iter-i)
        k1 = np.random.randint(len(person_to_coord))
        k2 = None
        if np.random.random() < 0.50:
            while k2 is None or k2 == k1:
                k2 = np.random.randint(len(person_to_coord))
        j1 = person_to_coord[k1]
        if k2 is None:
            j2 = np.random.randint(len(coords))
        else:
            j2 = person_to_coord[k2]
        if coord_to_person[j2] < 0: # empty target
            assert k2 is None
            print(f'propose person {k1} move {j1} -> {j2}')
            sol[k1] = coords[j2]
        else:
            print(f'propose swap {k1} {k2} coords {j1} <-> {j2}')
            k2 = coord_to_person[j2]
            sol[k1] = coords[j2]
            sol[k2] = coords[j1]
        value_p = evaluate(prob, sol)['value']
        print(f'normalized dv = {(value_p - value)/NORM}')
        if np.random.random() < np.exp(beta*(value_p - value)/NORM):
            # accept
            print('accept')
            person_to_coord[k1] = j2
            coord_to_person[j2] = k1
            if k2 is not None:
                person_to_coord[k2] = j1
                coord_to_person[j1] = k2
            value = value_p
        else:
            # reject
            print('reject')
            sol[k1] = coords[j1]
            if k2 is not None:
                sol[k2] = coords[j2]
        print(f'value = {value}')
    '''
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
    # print(f'Got res {res}')
    true_value = evaluate(prob, res['sol'])
    print(f'Found sol with value {true_value}')
    with open(f'solutions/{i}.json', 'w') as f:
        json.dump(sol_to_json(res['sol']), f)
    print('Done.')

def info(args):
    i = args.i
    with open(f'problems/{i}.json', 'r') as f:
        prob = Problem(json.load(f))
    print(f'== Problem {i} ==')
    n = len(prob.musicians)
    print(f'Musicians: {n}')
    na = len(prob.positions)
    print(f'Attendees: {na}')
    area = prob.swidth * prob.sheight
    print(f'Stage area: {area}')
    musician_area = n * np.pi * 10.0**2
    packable_area = area * np.pi / (2*np.sqrt(3))
    print(f'Packing fraction: {musician_area / packable_area}')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('i', type=int)
    parser.add_argument('--cmd', choices=['solve', 'info'], default='solve')
    args = parser.parse_args()
    if args.cmd == 'solve':
        solve(args)
    elif args.cmd == 'info':
        info(args)
    else:
        raise RuntimeError(f'Invalid cmd {args.cmd}')

if __name__ == '__main__':
    main()
