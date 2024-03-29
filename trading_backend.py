from collections import defaultdict
import os
from threading import Thread
import time
import requests
import json
import tkinter as tk
import customtkinter
from math import ceil
from interface import Position, EnterAction, Quote, StopOrder
from trade_history import Order, Trade, TradeHistory
from web_signin import signin

client_id = os.environ["CLIENT_ID"]
client_secret = os.environ["CLIENT_SECRET"]
redirect_url = os.environ["REDIRECT_URL"]

sigin_base_url = "https://signin.tradestation.com"
signin_url = f"""\
{sigin_base_url}/\
authorize?\
response_type=code\
&client_id={client_id}\
&redirect_uri={redirect_url}\
&audience=https://api.tradestation.com\
&scope=openid offline_access MarketData ReadAccount Trade
"""

api_url = "https://api.tradestation.com/v3" if os.environ["MODE"] == "LIVE" else "https://sim-api.tradestation.com/v3"

encoded_headers = { "content-type": "application/x-www-form-urlencoded" }
post_headers = lambda access_token: { "content-type": "application/json", "Authorization": f"Bearer {access_token}" }
get_headers = lambda access_token: {"Authorization": f"Bearer {access_token}"}

class TradingBackend(customtkinter.CTk):
  def __init__(self):
    super().__init__()
    self.access_token, self.refresh_token = self.get_tokens()
    print("live trading mode") if os.environ["MODE"] == "LIVE" else print("sim trading mode")
    self.accounts = self.get_accounts()
    self.tradeable_account_id = self.accounts["Margin"]["AccountID"]
    self.positions: dict[str, Trade] = {}
    # self.position_id_lookup: dict[str, str] = {}
    self.quotes: dict[str, Quote] = {}
    self.trade_history = TradeHistory()

    self.set_input()
    self.start_streaming()

  def set_input(self):
    self.symbol = tk.StringVar(value="SPY")
    self.current_symbol = self.symbol.get().upper()
    self.stop_loss = tk.DoubleVar()
    self.risk = tk.IntVar(value=100)
    self.is_current_symbol_valid = True

  def start_streaming(self):
    self.enable_streaming = True
    token_thread = Thread(target=self.run_refresh_token, daemon=True)
    token_thread.start()
    # positions_thread = Thread(target=self.stream_positions)
    # positions_thread.start()
    orders_thread = Thread(target=self.stream_orders)
    orders_thread.start()
    quotes_thread = Thread(target=self.stream_quotes)
    quotes_thread.start()


  @staticmethod
  def get_tokens():
    auth_code = signin(signin_url)
    
    response_json = requests.post("https://signin.tradestation.com/oauth/token", data={
      "grant_type": "authorization_code",
      "client_id": client_id,
      "client_secret": client_secret,
      "code": auth_code,
      "redirect_uri": redirect_url 
    }, headers=encoded_headers).json()
    return (response_json["access_token"], response_json["refresh_token"])

  def headers(self, content=None):
    if content == "encoded":
      return { "content-type": "application/x-www-form-urlencoded" }
    elif content == "json":
      return {
        "content-type": "application/json",
        "Authorization": f"Bearer {self.access_token}"
      }
    else:
      return {"Authorization": f"Bearer {self.access_token}"}

  def get_accounts(self):
    print("getting accounts")
    accounts = {}
    response_json = requests.get(f"{api_url}/brokerage/accounts", headers=self.headers()).json()
    for account in response_json["Accounts"]:
      print(account)
      if account["Status"] == "Active":
        accounts[account["AccountType"]] = account
    return accounts

  def get_account_ids(self):
    return ",".join([account["AccountID"] for _, account in self.accounts.items()])


  def buy(self):
    self.place_entry_order("BUY")

  def sell(self):
    self.place_entry_order("SELLSHORT")


  def place_entry_order(self, enter_action: EnterAction):
    price = self.quotes[self.current_symbol].ask if enter_action == "BUY" else self.quotes[self.current_symbol].bid
    shares = int(self.risk.get() // abs(self.stop_loss.get() - price))
    payload = {
      "AccountID": self.tradeable_account_id,
      "TimeInForce": {
        "Duration": "DAY"
      },
      "Quantity": str(shares),
      "OrderType": "Market",
      "Symbol": self.current_symbol,
      "TradeAction": enter_action,
      "Route": "Intelligent",
      "OSOs": [
        {
          "Type": "NORMAL",
          "Orders": [
            {
              "AccountID": self.tradeable_account_id,
              "TimeInForce": {
                "Duration": "GTC"
              },
              "Quantity": str(shares),
              "OrderType": "StopMarket",
              "Symbol": self.current_symbol,
              "TradeAction": "SELL" if enter_action == "BUY" else "BUYTOCOVER",
              "Route": "Intelligent",
              "StopPrice": str(self.stop_loss.get())
            }
          ]
        }
      ]
    }
    response = requests.post(f"{api_url}/orderexecution/orders", json=payload, headers=self.headers("json"))
    if response.status_code == 200:
      response_json = response.json()
      print(response_json)
      if "Errors" in response_json:
        print(response_json["Errors"])
      for order in response_json["Orders"]:
        print(order["Message"], order["OrderID"])
        if "Error" in order: 
          print(payload)
    else:
      print(response.status_code, response.text)

  def place_exit_order(self, percent):
    def exit_order_callback():
      if self.is_in_position():
        current_shares = abs(self.positions[self.current_symbol].opened_shares)
        shares_to_exit = ceil(int(current_shares) * percent)
        shares_to_keep = current_shares - shares_to_exit
        stop_order = self.trade_history.get_stop_order(self.current_symbol)
        if stop_order and stop_order.status_description != 'Cancelled':
          if shares_to_keep > 0:
            stop_order_payload = {
              "Quantity": str(shares_to_keep),
              "OrderType": "StopMarket",
              "StopPrice": str(stop_order.stop_price) 
            }
            print('modify stop order:', stop_order_payload)
            response = requests.put(f"{api_url}/orderexecution/orders/{stop_order.order_id}", json=stop_order_payload, headers=self.headers('json'))
          else:
            response = requests.delete(f"{api_url}/orderexecution/orders/{stop_order.order_id}", headers=self.headers())
          print(response.text)

        exit_order_payload = {
          "AccountID": self.tradeable_account_id,
          "TimeInForce": {
            "Duration": "DAY"
          },
          "Quantity": str(shares_to_exit),
          "OrderType": "Market",
          "Symbol": self.current_symbol,
          "TradeAction": "BUYTOCOVER" if self.positions[self.current_symbol].side_factor == -1 else "SELL",
          "Route": "Intelligent"
        }
        response = requests.post(f"{api_url}/orderexecution/orders", json=exit_order_payload, headers=self.headers("json"))
      else:
        print(f"not in any {self.current_symbol} position")
    return exit_order_callback

  def stream_orders(self, retry=1):
    if retry > 3:
      print('retried 2 times. terminating...')
      return
    try:
      response = requests.get(f"{api_url}/brokerage/stream/accounts/{self.get_account_ids()}/orders", headers=self.headers(), stream=True)
      for line in response.iter_lines():
        if self.enable_streaming and line:
          order_json = json.loads(line)
          if "OrderID" in order_json:
            # json_formatted_str = json.dumps(order_json, indent=2)
            # print(json_formatted_str)
            order = Order(order_json)
            print(order)
            self.trade_history.append(order)
            self.positions = self.trade_history.get_positions()
        else:
          break
      print(self.trade_history)
      print("closing order stream")
      response.close()
    except Exception as e:
      print("error streaming orders", e)
      e.with_traceback()
      if response:
        response.close()
      self.stream_orders(retry + 1)

  @property
  def current_symbol(self):
    return self._current_symbol


  @current_symbol.setter
  def current_symbol(self, symbol: str):
    response = requests.get(f"{api_url}/marketdata/symbols/{symbol}", headers=self.headers())
    json = response.json()
    self._current_symbol = symbol.upper()
    if response.status_code == 200 and len(json["Errors"]) == 0:
      self.symbol_info = json["Symbols"][0]

      asset_dict = {
        "STOCK": "Margin",
        "FUTURE": "Futures"
      }
      account = self.accounts.get(asset_dict[self.symbol_info["AssetType"]])
      if account:
        self.is_current_symbol_valid = True
        if account["AccountID"] != self.tradeable_account_id:
          print(f"switch to {account['AccountType']} account {account['AccountID']}")
        # quotes_thread = Thread(target=self.stream_quotes)
        # quotes_thread.start()
      else:
        print("no account to trade the asset")
        self.is_current_symbol_valid = False
    else:
      print("not a valid symbol")
      print(response.text)
      self.is_current_symbol_valid = False


  def get_live_symbols(self) -> str:
    symbols = set(self.positions.keys())
    symbols.add(self.current_symbol)
    return ",".join(sorted(symbols))

  def stream_quotes(self):
    retry = 0
    while retry < 3 and self.enable_streaming:
      try:
        symbols = self.get_live_symbols()
        response = requests.get(f"{api_url}/marketdata/stream/quotes/{symbols}", headers=self.headers(), stream=True)
        print(f"start streaming quotes for {symbols}", response.status_code)
        for line in response.iter_lines():
          if self.enable_streaming and line and symbols == self.get_live_symbols():
            # print(self.current_symbol, line)
            quote = json.loads(line)
            symbol = quote.get("Symbol")
            if symbol:
              if symbol in self.quotes:
                self.quotes[symbol].update_quote(quote)
              else:
                self.quotes[symbol] = Quote(quote)
            self.toggle_buy()
            self.toggle_sell()
          else:
            break
        print(f"closing quote stream for {symbol}")
        response.close()
      except Exception as e:
        print("error streaming quotes", e)
        retry += 1
        print('retry streaming quotes')
        if response:
          response.close()

  def is_ask_less_than_stop(self):
    return True if self.current_symbol in self.quotes and self.quotes[self.current_symbol].ask < self.stop_loss.get() else False

  def is_bid_greater_than_stop(self):
    return True if self.current_symbol in self.quotes and self.quotes[self.current_symbol].bid > self.stop_loss.get() else False

  def stream_positions(self, retry=1):
    if retry > 3:
      print('retried 2 times. terminating...')
      return
    try:
      response = requests.get(f"{api_url}/brokerage/stream/accounts/{self.get_account_ids()}/positions", headers=self.headers(), stream=True)
      print("start streaming positions", response.status_code)
      for line in response.iter_lines():
        if self.enable_streaming and line:
          position_json = json.loads(line)

          symbol_to_add = position_json.get("Symbol")
          print("position", position_json)
          if symbol_to_add:
            position = Position(position_json)
            self.positions[symbol_to_add] = position
            self.position_id_lookup[position.position_id] = symbol_to_add
          elif "Deleted" in position_json:
            print(position_json)
            # symbol_to_delete = self.position_id_lookup[position_json["PositionID"]]
            # print(f"deleting {symbol_to_delete} position")
            # self.positions.pop(symbol_to_delete, None)
          else:
            # print("position", position)
            pass
          self.toggle_exit()
        else:
          break
      print(f"closing positions stream")
      response.close()
    except Exception as e:
      print("error streaming positions", e)
      if response:
        response.close()
      self.stream_positions(retry + 1)

  def is_in_position(self):
    return True if self.current_symbol in self.positions else False


  def run_refresh_token(self):
    try:
      print("start interval task to refresh token")
      while self.enable_streaming:
        time.sleep(900)
        print("refreshing token...")
        response = requests.post("https://signin.tradestation.com/oauth/token", data={
          "grant_type": "refresh_token",
          "client_id": client_id,
          "client_secret": client_secret,
          "refresh_token": self.refresh_token
        }, headers=self.headers("encoded"))
        if response.status_code == 200:
          print("token refreshed")
        else:
          print("token refresh failed")
          print(response.status_code, response.text)
        self.access_token = response.json()["access_token"]
    except Exception as e:
      print("error refreshing token", e)

  
  def toggle_buy(self):
    pass

  def toggle_sell(self):
    pass

  def toggle_exit(self):
    pass