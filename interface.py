from typing import Literal


class StopOrder:
  def __init__(self, initial_stop_price: float, order_id: str, risk: int):
    self.initial_stop_price = initial_stop_price
    self.risk = risk
    self.order_id = order_id
    self.raw_order_details = None


class Position:
  def __init__(self, position_json: dict):
    self.position_json = position_json
    self.initial_quantity = int(position_json["Quantity"])

  def update_position(self, position_json):
    self.position_json = position_json

  @property
  def quantity(self):
    return self.position_json["Quantity"]

  @property
  def long_short(self):
    return self.position_json["LongShort"]

  @property
  def position_id(self):
    return self.position_json["PositionID"]

  @property
  def symbol(self):
    return self.position_json["Symbol"]

  @property
  def unrealized(self):
    return float(self.position_json["UnrealizedProfitLoss"])

class Quote:
  def __init__(self, quote_json):
    self.position_json = quote_json

  def update_quote(self, quote_change):
    self.position_json = { **self.position_json, **quote_change }

  @property
  def bid(self):
    return float(self.position_json.get("Bid") or self.position_json["Last"])

  @property
  def ask(self):
    return float(self.position_json.get("Ask") or self.position_json["Last"])



EnterAction = Literal["BUY", "SELLSHORT"]
ExitAction = Literal["BUYTOCOVER", "SELL"]
Side = Literal["Long", "Short"]