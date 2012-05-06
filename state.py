from db import Base, get_session
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text, Table, distinct
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql.expression import desc, asc
import datetime
import json

def get_all_high_scores(num_scores, leaderboard_type, player):
  filter_map = {
    "alltime" : Score.date >= datetime.datetime.min,
    "thisweek" : Score.date >= datetime.datetime.now() - datetime.timedelta(days=7),
    "today" : Score.date >= datetime.datetime.now() - datetime.timedelta(days=1),
  }

  session = get_session()
  time_filter = filter_map[leaderboard_type]
  numbers_query = session.query(distinct(Score.num_players), Score.game_type).filter(time_filter)
  if player is not None:
    numbers_query = numbers_query.filter(Score.players.any(name=player))
  numbers = list(numbers_query)
  ret = {'3tau' : {}, '6tau' : {}}
  for (number3, game_type) in numbers:
    top_scores = session.query(Score).filter_by(num_players=number3,game_type=game_type).filter(time_filter).order_by(asc(Score.elapsed_time))
    if player is not None:
      top_scores = top_scores.filter(Score.players.any(name=player))
    ret[game_type][number3] = list(top_scores.limit(num_scores))
  return ret

def get_high_scores(num_players, num_scores, game_type):
  session = get_session()
  return session.query(Score).filter_by(num_players=num_players,game_type=game_type).order_by(desc(Score.elapsed_time)).limit(num_scores)

def get_or_create_dbplayer(session, name):
  player = session.query(DBPlayer).filter_by(name=name).first()
  if player:
    return player
  else:
    player = DBPlayer(name)
    session.add(player)
    return player

def save_game(game):
  session = get_session()
  db_game = DBGame("3tau" if game.size == 3 else "6tau")
  name_to_player_map = {}
  player_to_score_map = {}
  last_elapsed_time = 0
  for (board, tau) in zip(game.boards, game.taus):
    (elapsed_time, total_taus, player, cards) = tau
    if player in name_to_player_map:
      db_player = name_to_player_map[player]
      player_to_score_map[player] += 1
    else:
      db_player = get_or_create_dbplayer(session, player)
      player_to_score_map[player] = 1
    name_to_player_map[db_player.name] = db_player

    state = State(elapsed_time, board, cards, db_player)
    db_game.states.append(state)
    last_elapsed_time = elapsed_time
  score = Score(last_elapsed_time, datetime.datetime.now(), db_game, name_to_player_map.values(), player_to_score_map)
  session.add(score)
  session.add(db_game)
  session.commit()

class DBGame(Base):
  __tablename__ = 'games'

  id = Column(Integer, primary_key=True)
  game_type = Column(String)

  def __init__(self, game_type):
    self.game_type = game_type

  def __repr__(self):
    return "<DBGame('%s')>" % (self.game_type)

score_players = Table("score_players", Base.metadata,
    Column('score_id', Integer, ForeignKey('scores.id')),
    Column('player_id', Integer, ForeignKey('players.id')))

class DBPlayer(Base):
  __tablename__ = 'players'

  id = Column(Integer, primary_key=True)
  name = Column(String)

  scores = relationship('Score', secondary=score_players, backref='players')

  def __init__(self, name):
    self.name = name

  def __repr__(self):
    return "<DBPlayer('%s')>" % (self.name)

class Score(Base):
  __tablename__ = 'scores'

  id = Column(Integer, primary_key=True)
  elapsed_time = Column(Float)
  num_players = Column(Integer)
  game_id = Column(Integer, ForeignKey('games.id'))
  game = relationship("DBGame", uselist=False, backref=backref('score'))
  game_type = Column(String)
  date = Column(DateTime)
  player_scores_json = Column(String)

  def __init__(self, elapsed_time, date, game, players, player_scores):
    self.elapsed_time = elapsed_time
    self.date = date
    self.game = game
    self.players = players
    self.num_players = len(players)
    self.game_type = game.game_type
    self.player_scores_json = json.dumps(player_scores)

  def __repr__(self):
    return "<Score(%f, %s, %s, %s, %s)>" % (self.elapsed_time, repr(self.date), self.game, self.players, repr(self.player_scores()))

  def player_scores(self):
    return json.loads(self.player_scores_json)

# Represents the state just before a tau is taken, and
# the tau that was taken.
class State(Base):
  __tablename__ = 'states'

  id = Column(Integer, primary_key=True)
  elapsed_time = Column(Float)
  board_json = Column(String)
  cards_json = Column(String)

  # foreign keys
  game_id = Column(Integer, ForeignKey('games.id'))
  game = relationship("DBGame", backref=backref('states'))
  player_id = Column(Integer, ForeignKey('players.id'))
  player = relationship("DBPlayer")

  def __init__(self, elapsed_time, board, cards, player):
    self.elapsed_time = elapsed_time
    self.board_json = json.dumps(board)
    self.cards_json = json.dumps(cards)
    self.player = player

  def board(self):
    return json.loads(board_json)

  def cards(self):
    return json.loads(cards_json)