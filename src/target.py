# target function to optimize

import numpy as np
import scipy as sp
from scipy.ndimage import map_coordinates

# docs.scipy.org/doc/scipy/tutorial/interpolate/ND_regular_grid.html#uniformly-spaced-data
class CartesianGridInterpolator:
    def __init__(self, points, values, method='linear'):
        self.limits = np.array([[min(x), max(x)] for x in points])
        self.values = np.asarray(values, dtype=float)
        self.order = {'linear': 1, 'cubic': 3, 'quintic': 5}[method]
    def __call__(self, xi):
        xi = np.asarray(xi).T
        ns = self.values.shape
        coords = [(n-1)*(val - lo) / (hi - lo)
                  for val, n, (lo, hi) in zip(xi, ns, self.limits)]
        return map_coordinates(self.values, coords, order=self.order, cval=-np.inf)

class TargetTastesNoBlocking:
    """ target function for audience tastes without blocking """
    def __init__(self, prob, *, NGRID=10):
        self.prob = prob
        xs = np.linspace(
                prob.spos[0] + 10.0, prob.spos[0] + prob.swidth - 10.0, num=NGRID, endpoint=True)
        ys = np.linspace(
                prob.spos[1] + 10.0, prob.spos[1] + prob.sheight - 10.0, num=NGRID, endpoint=True)
        grid_x, grid_y = np.meshgrid(xs, ys, indexing='ij')
        self.value_grid = []
        self.init_positions = []
        for i,tastes in enumerate(prob.tastes):
            values = np.zeros((len(xs), len(ys)))
            assert len(prob.positions) == len(tastes)
            for (x,y),ti in zip(prob.positions, tastes):
                d2 = (grid_x - x)**2 + (grid_y - y)**2
                values += ti/d2
            i_max = np.argmax(values)
            self.init_positions.append(
                (grid_x.flatten()[i_max],
                grid_y.flatten()[i_max]))
            self.value_grid.append(CartesianGridInterpolator(
                (xs, ys), values, method='linear'))
            
    def __call__(self, sol):
        value = 0.0
        for i,(x,y) in enumerate(sol):
            value_grid = self.value_grid[self.prob.musicians[i]]
            value += value_grid([(x,y)])[0]
        return value

class TargetSpherePacking:
    def __init__(self, prob, *, init_beta=1.0, R=9.5):
        self.R = R
        self.prob = prob
        self.beta = init_beta
    def cost_from_pair(self, c1, c2):
        d2 = (c1[0]-c2[0])**2 + (c1[1]-c2[1])**2
        if d2 >= 15.0**2:
            return 0.0
        if d2 == 0.0:
            return -1000000
        return -100/d2
    def cost_within_bin(self, coords):
        value = 0.0
        for i in range(len(coords)):
            for j in range(i+1, len(coords)):
                value += self.cost_from_pair(coords[i], coords[j])
        return value
    def cost_between_bins(self, coords1, coords2):
        value = 0.0
        for i in range(len(coords1)):
            for j in range(len(coords2)):
                value += self.cost_from_pair(coords1[i], coords2[j])
        return value
    def __call__(self, sol):
        BIN_SIZE = 10.0
        EPS = 1e-4
        nbins_x = int((EPS + self.prob.swidth) / BIN_SIZE)
        nbins_y = int((EPS + self.prob.sheight) / BIN_SIZE)
        find_bin_x = lambda x: int((x - self.prob.spos[0]) / BIN_SIZE)
        find_bin_y = lambda y: int((y - self.prob.spos[1]) / BIN_SIZE)
        grid = [[[] for _ in range(nbins_y)] for _ in range(nbins_x)]
        for i,(x,y) in enumerate(sol):
            grid[find_bin_x(x)][find_bin_y(y)].append(i)
        # HACK: check only for bin intersections for now
        value = 0.0
        for i in range(nbins_x):
            for j in range(nbins_y):
                value += self.cost_within_bin(sol[grid[i][j]])
                if i > 0:
                    value += self.cost_between_bins(
                        sol[grid[i-1][j]], sol[grid[i][j]])
                    if j > 0:
                        value += self.cost_between_bins(
                            sol[grid[i-1][j-1]], sol[grid[i][j]])
                elif j > 0:
                    value += self.cost_between_bins(
                        sol[grid[i][j-1]], sol[grid[i][j]])
                    if i < nbins_x-1:
                        value += self.cost_between_bins(
                            sol[grid[i+1][j-1]], sol[grid[i][j]])
        return 0.0

class MultiTarget:
    def __init__(self, targets):
        self.targets = targets
    def __call__(self, sol):
        return sum(target(sol) for target in self.targets)


def evaluate(prob, sol):
    """ full evaluation of problem score """
    assert len(prob.musicians) == len(sol)
    bounds = [
        (prob.spos[0] + 10, prob.spos[0] + prob.swidth - 10),
        (prob.spos[1] + 10, prob.spos[1] + prob.sheight - 10) ]
    def in_bounds(x,y):
        return (
            x >= bounds[0][0] and x <= bounds[0][1]
            and y >= bounds[1][0] and y <= bounds[1][1] )

    value = 0.0
    for k,(x,y) in enumerate(sol):
        if not in_bounds(x,y):
            return dict(msg=f'player {k} out of bounds {(x,y)}', value=0)
        for i,(xp,yp) in enumerate(prob.positions):
            t = prob.tastes[prob.musicians[k]][i]
            d2 = (x-xp)**2 + (y-yp)**2
            value += int(np.ceil(1000000*t/d2))
        for k2,(x2,y2) in enumerate(sol):
            if k2 == k: continue
            d2 = (x-x2)**2 + (y-y2)**2
            if d2 < 10.0**2:
                return dict(msg=f'players {k} {k2} intersect (d2={d2})', value=0)
    # TODO: blocking
    return dict(msg='ok', value=value)
