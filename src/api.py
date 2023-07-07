import argparse
import json
import requests
import os
import time

HOST = 'https://api.icfpcontest.com'

with open('api_key.txt', 'r') as f:
    TOKEN = f.read().strip()

s = requests.Session()
s.headers.update({'Authorization': f'Bearer {TOKEN}'})

def expect_ok(r, msg):
    if not r.ok:
        raise RuntimeError(f'Got error {r.status_code} at {msg}\n{r.content}')

def sync_problems(args):
    r = s.get(f'{HOST}/problems')
    expect_ok(r, '/problems')
    j = r.json()
    n = j['number_of_problems']
    print(f'There are {n} problems.')
    os.makedirs('problems', exist_ok=True)
    for i in range(1,n+1):
        prob_fname = f'problems/{i}.json'
        if os.path.exists(prob_fname):
            if not args.force:
                print(f'Skipping {prob_fname}')
                continue
            else:
                print(f'Overwriting {prob_fname}')
        r = s.get(f'{HOST}/problem?problem_id={i}')
        expect_ok(r, f'/problem?problem_id={i}')
        j = r.json()
        if not 'Success' in j:
            raise RuntimeError(f'failure loading problem {i}')
        with open(prob_fname, 'w') as f:
            f.write(j['Success'])
        print(f'Wrote {prob_fname}')
    print(f'Done.')

def get_score(sub_id):
    r = s.get(f'{HOST}/submission?submission_id={sub_id}')
    expect_ok(r, '/submission')
    j = r.json()
    if not 'Success' in j:
        return None
    return j['Success']['submission']['score']

def submit(args):
    i = args.i
    sol_fname = f'solutions/{i}.json'
    print(f'Loading {sol_fname}')
    if not os.path.exists(sol_fname):
        raise RuntimeError(f'Error: solution does not exist {sol_fname}')
    with open(sol_fname, 'r') as f:
        sol = f.read()
    print(f'Submitting {sol_fname}')
    r = s.post(f'{HOST}/submission', json={
        'problem_id': i,
        'contents': sol
    })
    expect_ok(r, '/submission')
    sub_id = r.json()
    N_TRY = 10
    for i in range(N_TRY):
        time.sleep(1.0)
        score = get_score(sub_id)
        if score is not None:
            print(score)
            return
        print('.')
    print(f'Could not get score after {N_TRY} tries. Giving up.')

def update_username(args):
    username = args.username
    r = s.post(f'{HOST}/username/update_username', json={
        'username': username
    })
    expect_ok(r, '/username/update_username')
    if 'Success' not in r.json():
        raise RuntimeError('Username update failed')
    print('Done.')

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    p_sync = sub.add_parser('sync')
    p_sync.add_argument('--force', action='store_true')
    p_submit = sub.add_parser('submit')
    p_submit.add_argument('i', type=int)
    p_upd_username = sub.add_parser('upd_username')
    p_upd_username.add_argument('--username', type=str, required=True)

    args = parser.parse_args()
    if args.cmd == 'sync':
        sync_problems(args)
    elif args.cmd == 'submit':
        submit(args)
    elif args.cmd == 'upd_username':
        update_username(args)
    else:
        raise RuntimeError(f'invalid cmd {cmd}')

if __name__ == '__main__':
    main()
