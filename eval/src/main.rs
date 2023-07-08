use serde::{Deserialize, Serialize};
use serde_json;
use std::env;
use std::fs;
use std::io;

#[derive(Debug, Serialize, Deserialize)]
struct Point {
  x: f64,
  y: f64,
}
#[derive(Debug, Serialize, Deserialize)]
struct Sol {
  placements: Vec<Point>,
}

#[derive(Debug, Serialize, Deserialize)]
struct Attendee {
  x: f64,
  y: f64,
  tastes: Vec<f64>,
}
#[derive(Debug, Serialize, Deserialize)]
struct Prob {
  room_width: f64,
  room_height: f64,
  stage_width: f64,
  stage_height: f64,
  stage_bottom_left: (f64, f64),
  musicians: Vec<usize>,
  attendees: Vec<Attendee>,
}

#[derive(Debug, Serialize, Deserialize)]
#[allow(dead_code)]
struct EvalResult {
  msg: String,
  value: i64,
}

// is the line a-b blocked by x?
fn is_blocked(a: (f64, f64), b: (f64, f64), x: (f64, f64)) -> bool {
  const RAD: f64 = 5.0;
  const RADSQ: f64 = RAD * RAD;
  let ax = (x.0 - a.0, x.1 - a.1);
  let ab = (b.0 - a.0, b.1 - a.1);
  let ab_norm = (ab.0.powi(2) + ab.1.powi(2)).sqrt();
  let ab_hat = (ab.0 / ab_norm, ab.1 / ab_norm);
  let ab_dot_ax = ab_hat.0 * ax.0 + ab_hat.1 * ax.1;
  if ab_dot_ax < 0.0 || ab_dot_ax > ab_norm {
    return false;
  }
  let ax_proj = (ax.0 - ab_hat.0 * ab_dot_ax, ax.1 - ab_hat.1 * ab_dot_ax);
  ax_proj.0.powi(2) + ax_proj.1.powi(2) < RADSQ
  /* VERSION B
  let d = (b.0 - a.0, b.1 - a.1);
  let f = (a.0 - x.0, a.1 - x.1);
  let d2 = d.0.powi(2) + d.1.powi(2);
  let fd = 2.0 * f.0 * d.0 + 2.0 * f.1 * d.1;
  let f2_r2 = f.0.powi(2) + f.1.powi(2) - RADSQ;
  let disc = fd * fd - 4.0 * d2 * f2_r2;
  if disc < 0.0 {
    return false;
  }
  let disc_rt = disc.sqrt();
  let t1 = (-fd - disc_rt) / (2.0 * d2);
  let t2 = (-fd + disc_rt) / (2.0 * d2);
  t1 >= 0.0 && t1 <= 1.0 || t2 >= 0.0 && t2 <= 1.0
  */
}

fn evaluate(prob: &Prob, sol: &Sol) -> EvalResult {
  let sol = &sol.placements;
  assert_eq!(prob.musicians.len(), sol.len());
  let bounds = vec![
    prob.stage_bottom_left.0 + 10.0,
    prob.stage_bottom_left.0 + prob.stage_width - 10.0,
    prob.stage_bottom_left.1 + 10.0,
    prob.stage_bottom_left.1 + prob.stage_height - 10.0,
  ];
  let in_bounds =
    |x, y| x >= bounds[0] && x <= bounds[1] && y >= bounds[2] && y <= bounds[3];
  let mut value: i64 = 0;
  for k in 0..sol.len() {
    let x = sol[k].x;
    let y = sol[k].y;
    // player out of bounds
    if !in_bounds(x, y) {
      return EvalResult {
        msg: std::format!("player {} out of bounds ({},{})", k, x, y),
        value: 0,
      };
    }
    // happiness
    let inst = prob.musicians[k];
    for i in 0..prob.attendees.len() {
      let xp = prob.attendees[i].x;
      let yp = prob.attendees[i].y;
      // blocked
      let mut blocked = false;
      for k2 in 0..sol.len() {
        if k2 == k {
          continue;
        }
        let x2 = sol[k2].x;
        let y2 = sol[k2].y;
        if is_blocked((x, y), (xp, yp), (x2, y2)) {
          blocked = true;
          break;
        }
      }
      if blocked {
        continue;
      }
      let t = prob.attendees[i].tastes[inst];
      let d2 = (x - xp).powi(2) + (y - yp).powi(2);
      value += (1_000_000.0 * t / d2).ceil() as i64;
    }
    // player intersection
    for k2 in 0..sol.len() {
      if k2 == k {
        continue;
      }
      let x2 = sol[k2].x;
      let y2 = sol[k2].y;
      let d2 = (x - x2).powi(2) + (y - y2).powi(2);
      if d2 < 10.0_f64.powi(2) {
        return EvalResult {
          msg: std::format!("players {} {} intersect (d2={})", k, k2, d2),
          value: 0,
        };
      }
    }
  }
  EvalResult {
    msg: "".into(),
    value,
  }
}

fn main() -> io::Result<()> {
  let args: Vec<String> = env::args().collect();
  if args.len() < 3 {
    println!("Usage: {} prob.json sol.json", args[0]);
  }
  let prob_fname = &args[1];
  let sol_fname = &args[2];
  let prob_file = fs::File::open(prob_fname)?;
  let sol_file = fs::File::open(sol_fname)?;
  let prob: Prob = serde_json::from_reader(io::BufReader::new(prob_file))?;
  let sol: Sol = serde_json::from_reader(io::BufReader::new(sol_file))?;
  let res = evaluate(&prob, &sol);
  println!("{}", serde_json::to_string_pretty(&res)?);
  Ok(())
}
