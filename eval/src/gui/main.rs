use iced::executor;
use iced::widget::{button, column, text};
use iced::{Alignment, Application, Command, Element, Settings, Theme};
use icfp::*;
use serde_json;
use std::env;
use std::fs;
use std::io;

struct GuiApp {
  hall: hall::State,
  sol: Sol,
  prob: Prob,
}
#[derive(Default)]
struct GuiInput {
  init_sol: Option<Sol>,
  prob: Option<Prob>,
}
impl Application for GuiApp {
  type Executor = executor::Default;
  type Flags = GuiInput;
  type Message = ();
  type Theme = Theme;

  fn new(flags: Self::Flags) -> (GuiApp, Command<Self::Message>) {
    (
      GuiApp {
        hall: hall::State::default(),
        sol: flags.init_sol.unwrap(),
        prob: flags.prob.unwrap(),
      },
      Command::none(),
    )
  }

  fn title(&self) -> String {
    String::from("ICFP 2023")
  }

  fn update(&mut self, _message: Self::Message) -> Command<Self::Message> {
    Command::none()
  }

  fn view(&self) -> Element<Self::Message> {
    column![self.hall.view(&self.sol, &self.prob).map(|msg| ())]
      .padding(20)
      .spacing(20)
      .align_items(Alignment::Center)
      .into()
  }
}

mod hall {
  use super::{Prob, Sol};
  use iced::mouse;
  use iced::widget::canvas::event::{self, Event};
  use iced::widget::canvas::{
    self, Canvas, Cursor, Frame, Geometry, Path, Stroke,
  };
  use iced::{Color, Element, Length, Point, Rectangle, Renderer, Size, Theme};

  #[derive(Default)]
  pub struct State {
    cache: canvas::Cache,
  }

  impl State {
    pub fn view<'a>(
      &'a self,
      sol: &'a Sol,
      prob: &'a Prob,
    ) -> Element<'a, CanvasMsg> {
      Canvas::new(Hall {
        state: self,
        sol,
        prob,
      })
      .width(Length::Fill)
      .height(Length::Fill)
      .into()
    }
  }

  struct Hall<'a> {
    state: &'a State,
    sol: &'a Sol,
    prob: &'a Prob,
  }

  pub enum CanvasMsg {}

  struct Transform {
    scaling: f32,
    off_x: f32,
    off_y: f32,
  }

  fn get_transform(prob: &Prob, bounds: &Rectangle) -> Transform {
    let aspect_game = (prob.room_width / prob.room_height) as f32;
    let aspect_screen = bounds.width / bounds.height;
    let mut off_x = 0.0;
    let mut off_y = 0.0;
    let mut scaling = 1.0;
    // narrow game
    if aspect_game > aspect_screen {
      scaling = bounds.width / prob.room_width as f32;
      off_y = (bounds.height - scaling * prob.room_height as f32) / 2.0;
    }
    // tall game
    else {
      scaling = bounds.height / prob.room_height as f32;
      off_x = (bounds.width - scaling * prob.room_width as f32) / 2.0;
    }
    Transform {
      scaling,
      off_x,
      off_y,
    }
  }

  fn game_to_screen_coord(x: (f32, f32), transform: &Transform) -> (f32, f32) {
    (
      x.0 * transform.scaling + transform.off_x,
      x.1 * transform.scaling + transform.off_y,
    )
  }

  fn tup_to_pt(x: (f32, f32)) -> Point {
    Point::new(x.0, x.1)
  }

  impl<'a> canvas::Program<CanvasMsg> for Hall<'a> {
    type State = ();

    fn draw(
      &self,
      state: &Self::State,
      _theme: &Theme,
      bounds: Rectangle,
      cursor: Cursor,
    ) -> Vec<Geometry> {
      let transform = get_transform(&self.prob, &bounds);
      let content =
        self.state.cache.draw(bounds.size(), |frame: &mut Frame| {
          let orig = tup_to_pt(game_to_screen_coord((0.0, 0.0), &transform));
          let size = Size::<f32>::new(
            transform.scaling * self.prob.room_width as f32,
            transform.scaling * self.prob.room_height as f32,
          );
          frame.stroke(
            &Path::rectangle(orig, size),
            Stroke::default().with_width(2.0),
          );
          let stage_orig = tup_to_pt(game_to_screen_coord(
            (
              self.prob.stage_bottom_left.0 as f32,
              self.prob.stage_bottom_left.1 as f32,
            ),
            &transform,
          ));
          let stage_size = Size::<f32>::new(
            transform.scaling * self.prob.stage_width as f32,
            transform.scaling * self.prob.stage_height as f32,
          );
          frame.fill(
            &Path::rectangle(stage_orig, stage_size),
            Color::from_rgb8(0x40, 0x40, 0x40),
          );
          for i in 0..self.prob.attendees.len() {
            let a = &self.prob.attendees[i];
            let pt = tup_to_pt(game_to_screen_coord(
              (a.x as f32, a.y as f32),
              &transform,
            ));
            frame
              .fill(&Path::circle(pt, 2.0), Color::from_rgb8(0x10, 0x10, 0x10));
          }
        });
      // TODO: UI elements
      vec![content]
    }
  }
}

fn main() -> io::Result<()> {
  let args: Vec<String> = env::args().collect();
  if args.len() < 2 {
    println!("Usage: {} prob.json [sol.json]", args[0]);
    return Ok(());
  }
  let prob_fname = &args[1];
  let prob_file = fs::File::open(prob_fname)?;
  let prob: Prob = serde_json::from_reader(io::BufReader::new(prob_file))?;
  let init_sol: Sol = if args.len() >= 3 {
    let sol_fname = &args[2];
    let sol_file = fs::File::open(sol_fname)?;
    serde_json::from_reader(io::BufReader::new(sol_file))?
  } else {
    Sol::new(&prob)
  };

  let mut settings = Settings {
    flags: GuiInput {
      prob: Some(prob),
      init_sol: Some(init_sol),
    },
    ..Settings::default()
  };
  let res = GuiApp::run(settings);
  match res {
    Ok(_) => Ok(()),
    Err(e) => Err(io::Error::new(io::ErrorKind::Other, e)),
  }
}
