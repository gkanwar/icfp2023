# OLD: solution by simulated annealing according to a target function
import numpy as np
import tqdm

class ConstantSched:
    def __init__(self, n_iter, t):
        self.n_iter = n_iter
        self.t = t
    def __call__(self, i):
        return self.t

class LinearSched:
    def __init__(self, n_iter, ti, tf):
        self.n_iter = n_iter
        self.ti = ti
        self.tf = tf
    def __call__(self, i):
        return self.tf*(i/self.n_iter) + self.ti*(1.0 - i/self.n_iter)

SCALE = 0.01 # get everything to a reasonable scale
basic_sched = LinearSched(1000, 1.0, 1e-2)
# basic_sched = ConstantSched(1000, 0.1)
def simulated_annealing(init_sol, target, *, sched=basic_sched):
    sol = np.copy(init_sol)
    value = target(sol)
    for i in tqdm.tqdm(range(sched.n_iter)):
        t = basic_sched(i)
        j = np.random.randint(len(sol))
        old_sol_j = np.copy(sol[j])
        sol[j] += 0.1*np.random.normal(size=2)
        value_p = target(sol)
        print(f'{value_p=} {value=}')
        print(f'{(value_p - value)/SCALE=}')
        if np.random.random() >= np.exp((value_p - value)/(t*SCALE)):
            sol[j] = old_sol_j
        else:
            value = value_p
        print(f'{value=}')
    return dict(sol=sol, value=value)
