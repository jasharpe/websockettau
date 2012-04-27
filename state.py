from db import Base, get_session
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text, Table, distinct
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql.expression import desc, asc
import datetime
import json

def get_all_high_scores(num_scores):
  session = get_session()
  numbers = list(session.query(distinct(Score.num_players), Score.game_type))
  ret = {'3tau' : {}, '6tau' : {}}
  for (number3, game_type) in numbers:
    top_scores = session.query(Score).filter_by(num_players=number3,game_type=game_type).order_by(asc(Score.elapsed_time)).limit(num_scores)
    ret[game_type][number3] = list(top_scores)
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
  last_elapsed_time = 0
  for (board, tau) in zip(game.boards, game.taus):
    (elapsed_time, total_taus, player, cards) = tau
    if player in name_to_player_map:
      db_player = name_to_player_map[player]
    else:
      db_player = get_or_create_dbplayer(session, player)
    name_to_player_map[db_player.name] = db_player
    state = State(elapsed_time, board, cards, db_player)
    db_game.states.append(state)
    last_elapsed_time = elapsed_time
  score = Score(last_elapsed_time, db_game, name_to_player_map.values())
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

  def __init__(self, elapsed_time, game, players):
    self.elapsed_time = elapsed_time
    self.game = game
    self.players = players
    self.num_players = len(players)
    self.game_type = game.game_type

  def __repr__(self):
    return "<Score(%f, %s, %s)>" % (self.elapsed_time, self.game, self.players)

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
