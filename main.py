
from trading_app import TradingApp

if __name__ == "__main__":
  

  app = TradingApp()
  app.mainloop()
  print('ending streams and app')
  app.enable_streaming = False