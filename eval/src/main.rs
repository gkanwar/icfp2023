use icfp::*;
use serde_json;
use std::env;
use std::fs;
use std::io;

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
