from typing import Literal
from statistics import mean
from collections import OrderedDict, defaultdict

from interface import Quote


class Order:
  def __init__(self, order_json: dict):
    self.order_json = order_json
    self.order_id = order_json["OrderID"]
    self.order_type = order_json["OrderType"]
    self.status = order_json["Status"]
    self.status_description = order_json["StatusDescription"] if order_json["StatusDescription"] != "UROut" else "Cancelled"
    self.filled_price = float(order_json["FilledPrice"]) or None
    self.stop_price = float(order_json["StopPrice"]) if "StopPrice" in order_json else None
    self.opened_date_time = order_json["OpenedDateTime"]
    self.commission_fee = float(order_json["CommissionFee"])

    leg = order_json["Legs"][0]
    self.symbol = leg["Symbol"]
    # self.execution_price = leg["ExecutionPrice"]
    self.buy_or_sell: BuyOrSell = leg["BuyOrSell"]
    self.open_or_close: OpenOrClose = leg.get("OpenOrClose")
    self.execution_quantity = int(leg["ExecQuantity"])
    self.ordered_quantity = int(leg["QuantityOrdered"])

  @property
  def is_open(self):
    return True if self.open_or_close == "Open" else False
  
  @property
  def is_filled(self):
    return True if self.status == "FLL" else False
  
  @property
  def conditional_order_id(self):
    conditional_orders = self.order_json.get("ConditionalOrders")
    if conditional_orders:
      return conditional_orders[0]["OrderID"]
    else:
      return None
  
  def __repr__(self) -> str:
    fill_str = f" @ ${self.filled_price}" if self.filled_price else ""
    stop_str = f" with StopPrice @ ${self.stop_price}" if self.stop_price else ""
    return f"{self.opened_date_time} {self.order_id} {self.symbol} {self.open_or_close} {self.buy_or_sell} {self.order_type} order is {self.status_description} for {self.execution_quantity}/{self.ordered_quantity}{fill_str}{stop_str}"
  

class Trade:
  def __init__(self, order: Order):
    self.orders = [order]
    self.symbol = order.symbol

  def append(self, order: Order):
    if self.is_opened(order) and order.symbol == self.symbol:
      self.orders.append(order)
      return True
    return False

  @property
  def entry_amount(self):
    return sum([order.filled_price * order.execution_quantity for order in self.orders if order.is_open and order.is_filled])
  
  @property
  def entry_quantity(self):
    return sum([order.execution_quantity for order in self.orders if order.is_open and order.is_filled])

  @property
  def exit_amount(self):
    return sum([order.filled_price * order.execution_quantity for order in self.orders if not order.is_open and order.is_filled])

  @property
  def exit_quantity(self):
    return sum([order.execution_quantity for order in self.orders if not order.is_open and order.is_filled])

  @property
  def commission_fee(self):
    commission = round(sum([order.commission_fee for order in self.orders if order.is_filled]), 2)
    return commission if self.initial_stop_order.buy_or_sell == 'Sell' else -commission

  @property
  def opened_shares(self):
    shares_open = 0
    for order in self.orders:
      if order.is_open:
        shares_open += order.execution_quantity
      else:
        shares_open -= order.execution_quantity
    return shares_open

  def is_opened(self, order: Order = None):
    if order == None:
      return self.opened_shares > 0
    return self.opened_shares > 0 or order.order_id == self.latest_stop_order.conditional_order_id
  
  @property
  def side_factor(self):
    return 1 if self.initial_stop_order.buy_or_sell == "Sell" else -1

  @property
  def risk_amount(self):
    return round(self.entry_amount - self.initial_stop_order.stop_price * self.entry_quantity, 2) * self.side_factor
  @property
  def initial_stop_order(self):
    return [order for order in self.orders if order.order_type == 'StopMarket'][0]
  
  @property
  def latest_stop_order(self):
    return [order for order in self.orders if order.order_type == 'StopMarket'][-1]

  @property
  def realized_amount(self):
    return round(self.exit_amount - self.entry_amount - self.commission_fee, 2) * self.side_factor
  
  @property
  def realized_reward(self):
    return round(self.realized_amount / self.risk_amount, 2)

  def resolve_quote(self, quote: Quote):
    entry_order = [order for order in self.orders if order.is_open and order.is_filled][0]
    return quote.bid if entry_order.buy_or_sell == "Buy" else quote.ask

  def unrealized_reward(self, quote: Quote):
    quote_price = self.resolve_quote(quote)
    profit_loss_amount = (quote_price - self.entry_amount) * self.opened_shares
    return profit_loss_amount / self.risk_amount

  def reward_position(self, quote: Quote):
    quote_price = self.resolve_quote(quote)
    avg_entry_price = self.entry_amount / self.entry_quantity
    return (quote_price - avg_entry_price) / (avg_entry_price - self.initial_stop_order.stop_price)

  def __repr__(self) -> str:
    trade_str = f"{self.symbol}:\n"
    for order in self.orders:
      trade_str += f"  {order}\n"
    trade_str += f"  {self.realized_reward}R, Risk: {self.risk_amount}, Reward: {self.realized_amount} ($)\n"
    return trade_str


class TradeHistory:
  def __init__(self):
    self.trade_history: dict[str, list[Trade]] = defaultdict(lambda: [])
    self.order_history = []

  def append(self, order: Order):
    trades_by_symbol = self.trade_history[order.symbol]
    if len(trades_by_symbol) != 0 and trades_by_symbol[-1].is_opened(order):
      trades_by_symbol[-1].append(order)
    else:
      trades_by_symbol.append(Trade(order))

  def get_stop_order(self, symbol: str):
    return self.trade_history[symbol][-1].latest_stop_order
  
  def get_positions(self) -> dict[str, Trade]:
    positions = {}
    for symbol, trades in self.trade_history.items():
      if len(trades) > 0 and trades[-1].is_opened():
        positions[symbol] = trades[-1]
    return positions

  
  def __repr__(self) -> str:
    trade_str = "Trade History:\n"
    realized_pnl = 0
    for trades in self.trade_history.values():
      for trade in trades:
        trade_str += f"{trade}\n"
        realized_pnl += trade.realized_amount

    trade_str += f"Daily Realized PnL: ${round(realized_pnl, 2)}"
    return trade_str


BuyOrSell = Literal["Buy", "Sell", "SellShort", "BuyToCover"]
OpenOrClose = Literal["Open", "Close"]