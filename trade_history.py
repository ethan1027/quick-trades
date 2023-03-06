from typing import Literal
from statistics import mean 

from interface import Quote


class Order:
  def __init__(self, order_json: dict):
    self.order_json = order_json
    self.order_id = order_json["OrderID"]
    self.order_type = order_json["OrderType"]

    leg = order_json["Legs"][0]
    self.symbol = leg["Symbol"]
    self.execution_price = leg["ExecutionPrice"]
    self.buy_or_sell: BuyOrSell = leg["BuyOrSell"]
    self.open_or_close: OpenOrClose = leg["OpenOrClose"]
    self.execution_quantity = int(leg["ExecQuantity"])

class Trade:
  def __init__(self, order: Order):
    self.orders = [order]
    self.symbol = order.symbol

  def update_trade(self, orders: list[Order]):
    for order in orders:
      if self.is_trade_open():
        if order.symbol == self.symbol:
          self.orders.append(order)

  def avg_entry_price(self):
    return mean([order.execution_price for order in self.orders if order.open_or_close == 'Open'])
  
  def entry_quantity(self):
    return sum([order.execution_price for order in self.orders if order.open_or_close == 'Open'])

  def risk(self):
    pass

  def is_trade_open(self):
    shares_open = 0
    for order in self.orders:
      if order.open_or_close == "Open":
        shares_open += order.execution_quantity
      else:
        shares_open -= order.execution_quantity
    if shares_open < 0:
      raise Exception('Trade exception: shares open should not be negative')
    return False if shares_open == 0 else True

  def risk_amount(self):
    pass

  def realized_reward(self):
    pass

  def unrealized_reward(self, quote: Quote):
    pass

  def unrealized_position_adjusted_reward(self, quote: Quote):
    pass




BuyOrSell = Literal["Buy", "Sell", "SellShort", "BuyToCover"]
OpenOrClose = Literal["Open", "Close"]