import tkinter as tk
import customtkinter
from trading_backend import TradingBackend

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")


# class PositionFrame(customtkinter.CTkFrame):
#     def __init__(self, master, **kwargs):
#         super().__init__(master, **kwargs)

#         self.label = customtkinter.CTkLabel(self)
#         self.label.grid(row=0, column=0, padx=20)

# class OrderFrame(customtkinter.CTkScrollableFrame):
#     def __init__(self, master, **kwargs):
#         super().__init__(master, **kwargs)

#         self.label = customtkinter.CTkLabel(self)
#         self.label.grid(row=0, column=0, padx=20)

class TradingApp(TradingBackend):
  def __init__(self):
    super().__init__()
    self.geometry("300x600")
    self.title("Quick Trades")
    self.minsize(300, 400)
    self.attributes("-topmost", True)
    self.columnconfigure((0, 1, 2, 3), weight=1)

    self.symbol_input = customtkinter.CTkEntry(
      master=self,
      textvariable=self.symbol,
      placeholder_text="Symbol",
      border_width=2
    )
    self.symbol_input.grid(row=0, column=0, columnspan=2, padx=2, pady=8)
    self.symbol_input.bind("<Return>", self.set_symbol)
    self.symbol_input.bind("<Button-1>", self.enable_symbol_input)
    
    self.stop_loss_input = customtkinter.CTkEntry(
      master=self,
      textvariable=self.stop_loss,
      placeholder_text="Stop Loss",
      border_width=2
    )
    self.stop_loss_input.grid(row=0, column=2, columnspan=2, padx=2, pady=4)
    
    self.order_type_button = customtkinter.CTkSegmentedButton(
      master=self,
      values=["Market", "Limit"],
      command=self.set_order_type
    )
    self.order_type_button.grid(row=1, column=0, columnspan=2, padx=2, pady=4)
    
    self.risk_input = customtkinter.CTkEntry(
      master=self,
      textvariable=self.risk,
      placeholder_text="Risk",
      border_width=2
    )
    self.risk_input.grid(row=1, column=2, columnspan=2, padx=2, pady=4)
    self.sell_button = customtkinter.CTkButton(master=self, text="Sell", fg_color="tomato3", hover_color="tomato2", command=self.sell)
    self.sell_button.grid(row=2, column=0, columnspan=2, padx=2, pady=4)
    self.buy_button = customtkinter.CTkButton(master=self, text="Buy", fg_color="sea green", hover_color="medium sea green", command=self.buy)
    self.buy_button.grid(row=2, column=2, columnspan=2, padx=2, pady=4)

    self.exit25 = customtkinter.CTkButton(master=self, text="25%", fg_color="cyan4", hover_color="cyan3", command=self.place_exit_order(0.25))
    self.exit25.grid(row=3, column=0, padx=2, pady=4)
    self.exit33 = customtkinter.CTkButton(master=self, text="33%", fg_color="cyan4", hover_color="cyan3", command=self.place_exit_order(0.33))
    self.exit33.grid(row=3, column=1, padx=2, pady=4)
    self.exit50 = customtkinter.CTkButton(master=self, text="50%", fg_color="cyan4", hover_color="cyan3", command=self.place_exit_order(0.50))
    self.exit50.grid(row=3, column=2, padx=2, pady=4)
    self.exit75 = customtkinter.CTkButton(master=self, text="75%", fg_color="cyan4", hover_color="cyan3", command=self.place_exit_order(0.75))
    self.exit75.grid(row=3, column=3, padx=2, pady=4)

    self.cancel_order = customtkinter.CTkButton(master=self, text="Cancel Order", state="disabled", fg_color="SlateGray4", hover_color="SlateGray3", command=self.cancel_order)
    self.cancel_order.grid(row=4, column=0, columnspan=2, padx=2, pady=4)
    self.close_position = customtkinter.CTkButton(master=self, text="Close Position", fg_color="SlateGray4", hover_color="SlateGray3", command=self.place_exit_order(1))
    self.close_position.grid(row=4, column=2, columnspan=2, padx=2, pady=4)
    
    self.position_box = customtkinter.CTkTextbox(master=self, width=300, corner_radius=0)
    self.position_box.grid(row=5, column=0, rowspan=3, columnspan=4, sticky="nsew")
    self.position_box.insert("0.0", "Position!\n" * 5)

    self.order_box = customtkinter.CTkTextbox(master=self, width=300, corner_radius=0)
    self.order_box.grid(row=8, column=0, rowspan=10, columnspan=4, sticky="nsew")
    self.order_box.insert("0.0", "Orders!\n" * 20)



  def set_symbol(self, _):
    self.current_symbol = self.symbol_input.get()
    if self.is_current_symbol_valid:
      self.symbol.set(self.symbol.get().upper())
      self.symbol_input.configure(state="disabled", text_color="deep sky blue")
    else:
      self.symbol_input.configure(text_color="coral1")
    

  def enable_symbol_input(self, _):
    self.symbol_input.configure(state="normal", text_color="white")

  def set_order_type(self, value):
      print("segmented button clicked:", value)

  def cancel_order(self):
    print("cancel latest order")

  def toggle_buy(self):
    state = "normal" if self.is_bid_greater_than_stop() else "disabled"
    self.buy_button.configure(state=state)

  def toggle_sell(self):
    state = "normal" if self.is_ask_less_than_stop() else "disabled"
    self.sell_button.configure(state=state)

  def toggle_exit(self):
    state = "normal" if self.is_in_position() else "disabled"
    self.exit25.configure(state=state)
    self.exit33.configure(state=state)
    self.exit50.configure(state=state)
    self.exit75.configure(state=state)
    self.close_position.configure(state=state)
