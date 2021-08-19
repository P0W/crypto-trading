* Sample crypto bot, requires a [_binance account_](https://accounts.binance.com/en/register?ref=BG3REVNI) ( for API_KEY & SECERET_KEY) to execute trades.

* Installation

  * Create a _virtualenv_


  ```virtualenv crypto-bot

  source ~/crypto-bot/bin/activate

  pip install -r reqs.txt

  ```

  * **ccxtbt** package has to be installed [**_from_**](https://github.com/Dave-Vallance/bt-ccxt-store.git) using ```python setup.py```

* Backtest strategy on real coin values of all coins listed on binance.
