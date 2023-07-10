# For some reason volumes were added with musicians *not* automatically at the
# loudest in v3 of the problem spec. Let's turn it up to 11!

import json

for i in range(1,55+1):
    try:
        print(f'Problem {i}')
        with open(f'solutions_novol/{i}.json', 'r') as f:
            sol = json.load(f)
        assert 'placements' in sol
        if 'volumes' not in sol:
            sol['volumes'] = [10.0]*len(sol['placements'])
        with open(f'solutions/{i}.json', 'w') as f:
            json.dump(sol, f)
    except Exception as e:
        print('Error, continuing')
