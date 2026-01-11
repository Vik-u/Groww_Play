# Groww API SDK Reference (local)

This file is generated from the installed `growwapi` SDK in this project. It lists all public `GrowwAPI` methods, their signatures, and the first line of their docstring. It does not include private methods (names starting with `_`).

## Auth flows

- **Approval flow (API key + secret)**: uses `GrowwAPI.get_access_token(api_key=..., secret=...)`. Requires daily approval on Groww console.
- **TOTP flow**: uses `GrowwAPI.get_access_token(api_key=totp_token, totp=6-digit)`. No expiry; OTP rotates.

## Why quote fields can be null

Some `get_quote` fields are not applicable to every instrument/segment (e.g., OI/IV fields are for derivatives; market depth may be absent for illiquid instruments). Fields can also be null outside market hours or when the exchange doesn’t provide that datapoint for the instrument.

## Method index
- `cancel_order(self, groww_order_id: str, segment: str, timeout: int | None = None) -> dict` — Cancel an existing order.
- `cancel_smart_order(self, segment: str, smart_order_type: str, smart_order_id: str, timeout: int | None = None) -> dict` — Cancel a smart order.
- `create_smart_order(self, smart_order_type: str, segment: str, trading_symbol: str, quantity: int, product_type: str, exchange: str, duration: str, reference_id: str | None = None, trigger_price: str | None = None, trigger_direction: str | None = None, order: dict | None = None, child_legs: dict | None = None, net_position_quantity: int | None = None, target: dict | None = None, stop_loss: dict | None = None, transaction_type: str | None = None, timeout: int | None = None) -> dict` — Create a smart order (GTT or OCO).
- `generate_socket_token(self, key_pair) -> dict`
- `get_access_token(api_key: str, totp: str | None = None, secret: str | None = None) -> dict` — Args:
- `get_all_instruments(self) -> pandas.core.frame.DataFrame` — Get a dataframe containing all the instruments.
- `get_available_margin_details(self, timeout: int | None = None) -> dict` — Get the available margin details for the user.
- `get_contracts(self, exchange: str, underlying_symbol: str, expiry_date: str, timeout: int | None = None) -> dict` — Get contracts for a given exchange, symbol and expiry date.
- `get_expiries(self, exchange: str, underlying_symbol: str, year: int | None = None, month: int | None = None, timeout: int | None = None) -> dict` — Get expiry dates for a given exchange, symbol, year and optionally month.
- `get_greeks(self, exchange: str, underlying: str, trading_symbol: str, expiry: str) -> dict` — Fetch the Greeks data for an option instrument.
- `get_historical_candle_data(self, trading_symbol: str, exchange: str, segment: str, start_time: str, end_time: str, interval_in_minutes: int | None = None, timeout: int | None = None) -> dict` — Get the historical data for an instrument.
- `get_historical_candles(self, exchange: str, segment: str, groww_symbol: str, start_time: str, end_time: str, candle_interval: str, timeout: int | None = None) -> dict` — Get bulk historical candle data for an instrument with V2 response format.
- `get_holdings_for_user(self, timeout: int | None = None) -> dict` — Get the holdings for the user.
- `get_instrument_by_exchange_and_trading_symbol(self, exchange: str, trading_symbol: str) -> dict` — Get the instrument details for a trading symbol on an exchange.
- `get_instrument_by_exchange_token(self, exchange_token: str) -> dict` — Get the instrument details for the exchange_token.
- `get_instrument_by_groww_symbol(self, groww_symbol: str) -> dict` — Get the instrument details for the groww_symbol.
- `get_ltp(self, exchange_trading_symbols: Tuple[str], segment: str, timeout: int | None = None) -> dict` — Fetch the LTP data for a list of instruments.
- `get_ohlc(self, exchange_trading_symbols: Tuple[str], segment: str, timeout: int | None = None) -> dict` — Fetch the OHLC data for a list of instruments.
- `get_option_chain(self, exchange: str, underlying: str, expiry_date: str, timeout: int | None = None) -> dict` — Fetch the option chain data for FNO (Futures and Options) contracts.
- `get_order_detail(self, segment: str, groww_order_id: str, timeout: int | None = None) -> dict` — Get the details of an order.
- `get_order_list(self, page: int | None = 0, page_size: int | None = 25, segment: str | None = None, timeout: int | None = None) -> dict` — Get a list of orders.
- `get_order_margin_details(self, segment: str, orders: list[dict], timeout: int | None = None) -> dict`
- `get_order_status(self, segment: str, groww_order_id: str, timeout: int | None = None) -> dict` — Get the status of an order.
- `get_order_status_by_reference(self, segment: str, order_reference_id: str, timeout: int | None = None) -> dict` — Get the status of an order by reference ID.
- `get_position_for_trading_symbol(self, trading_symbol: str, segment: str, timeout: int | None = None) -> dict` — Get the positions for a symbol.
- `get_positions_for_user(self, segment: str | None = None, timeout: int | None = None) -> dict` — Get the positions for the user for all the symbols they have positions in.
- `get_quote(self, trading_symbol: str, exchange: str, segment: str, timeout: int | None = None) -> dict` — Fetch the latest quote data for an instrument.
- `get_smart_order(self, segment: str, smart_order_type: str, smart_order_id: str, timeout: int | None = None) -> dict` — Get a smart order by internal ID.
- `get_smart_order_list(self, smart_order_type: str | None = None, segment: str | None = None, status: str | None = None, page: int | None = None, page_size: int | None = None, start_date_time: str | None = None, end_date_time: str | None = None, timeout: int | None = None) -> dict` — List smart orders with filters.
- `get_trade_list_for_order(self, groww_order_id: str, segment: str, page: int | None = 0, page_size: int | None = 25, timeout: int | None = None) -> dict` — Get the list of trades for a specific order.
- `get_user_profile(self, timeout: int | None = None) -> dict` — Get the user profile details.
- `modify_order(self, order_type: str, segment: str, groww_order_id: str, quantity: int, price: float | None = None, trigger_price: float | None = None, timeout: int | None = None) -> dict` — Modify an existing order.
- `modify_smart_order(self, smart_order_id: str, smart_order_type: str, segment: str, quantity: int | None = None, duration: str | None = None, trigger_price: str | None = None, trigger_direction: str | None = None, order: dict | None = None, child_legs: dict | None = None, product_type: str | None = None, target: dict | None = None, stop_loss: dict | None = None, timeout: int | None = None) -> dict` — Modify a smart order (GTT or OCO).
- `place_order(self, validity: str, exchange: str, order_type: str, product: str, quantity: int, segment: str, trading_symbol: str, transaction_type: str, order_reference_id: str | None = None, price: float | None = 0.0, trigger_price: float | None = None, timeout: int | None = None) -> dict` — Place a new order.

## Detailed method docs

### cancel_order(self, groww_order_id: str, segment: str, timeout: int | None = None) -> dict

Cancel an existing order.

```

Args:
    groww_order_id (str): The Groww order ID.
    segment (str): The segment of the order.
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The cancelled order response.

Raises:
    GrowwAPIException: If the request fails.
```

### cancel_smart_order(self, segment: str, smart_order_type: str, smart_order_id: str, timeout: int | None = None) -> dict

Cancel a smart order.

```

Args:
    segment (str): Market segment (e.g., CASH, FNO).
    smart_order_type (str): Smart order type (GTT or OCO).
    smart_order_id (str): The smart order identifier.
    timeout (Optional[int]): Request timeout in seconds.

Returns:
    dict: The cancelled smart order details.

Raises:
    GrowwAPIException: If the request fails.
```

### create_smart_order(self, smart_order_type: str, segment: str, trading_symbol: str, quantity: int, product_type: str, exchange: str, duration: str, reference_id: str | None = None, trigger_price: str | None = None, trigger_direction: str | None = None, order: dict | None = None, child_legs: dict | None = None, net_position_quantity: int | None = None, target: dict | None = None, stop_loss: dict | None = None, transaction_type: str | None = None, timeout: int | None = None) -> dict

Create a smart order (GTT or OCO).

```

For GTT orders, provide: trigger_price, trigger_direction, order (and optionally child_legs).
For OCO orders, provide: net_position_quantity, target, stop_loss, transaction_type.

Args:
    smart_order_type (str): Smart order type (GTT or OCO).
    segment (str): Market segment (e.g., CASH, FNO).
    trading_symbol (str): Trading symbol of the instrument.
    quantity (int): Quantity for the order.
    product_type (str): Product type (e.g., CNC, MIS).
    exchange (str): Exchange (e.g., NSE, BSE).
    duration (str): Validity (e.g., DAY, GTC).
    reference_id (Optional[str]): Unique reference ID to track the smart order. Defaults to a random 8-digit number.
    trigger_price (Optional[str]): GTT: Trigger price as a decimal string.
    trigger_direction (Optional[str]): GTT: Direction to monitor (UP or DOWN).
    order (Optional[dict]): GTT: Order details with keys: order_type, price (optional), transaction_type.
    child_legs (Optional[dict]): GTT: Optional child legs for bracket orders.
    net_position_quantity (Optional[int]): OCO: Current net position in this symbol.
    target (Optional[dict]): OCO: Target leg with keys: trigger_price, order_type, price (optional).
    stop_loss (Optional[dict]): OCO: Stop-loss leg with keys: trigger_price, order_type, price (optional).
    transaction_type (Optional[str]): OCO: Transaction type (BUY or SELL).
    timeout (Optional[int]): Request timeout in seconds.

Returns:
    dict: The created smart order details.

Raises:
    GrowwAPIException: If the request fails.
```

### generate_socket_token(self, key_pair) -> dict

### get_access_token(api_key: str, totp: str | None = None, secret: str | None = None) -> dict

Args:

```
    api_key (str): Bearer token or API key for the Authorization header.
    totp (str): If TOTP api key is provided. The TOTP code as a string.
    secret (str): If approval api key is provided. The secret value as a string.
Returns:
    dict: The JSON response from the API.
Raises:
    requests.HTTPError: If the request fails.
```

### get_all_instruments(self) -> pandas.core.frame.DataFrame

Get a dataframe containing all the instruments.

```
:return: DataFrame
```

### get_available_margin_details(self, timeout: int | None = None) -> dict

Get the available margin details for the user.

```

Args:
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The user's margin details response.

Raises:
    GrowwAPIException: If the request fails.
```

### get_contracts(self, exchange: str, underlying_symbol: str, expiry_date: str, timeout: int | None = None) -> dict

Get contracts for a given exchange, symbol and expiry date.

```

Args:
    exchange (str): The exchange to fetch contracts from.
    underlying_symbol (str): The underlying symbol to fetch contracts for (1-20 characters).
    expiry_date (str): The expiry date to fetch contracts for (YYYY-MM-DD format).
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The list of contracts.

Raises:
    GrowwAPIException: If the request fails.
```

### get_expiries(self, exchange: str, underlying_symbol: str, year: int | None = None, month: int | None = None, timeout: int | None = None) -> dict

Get expiry dates for a given exchange, symbol, year and optionally month.

```

Args:
    exchange (str): The exchange to fetch expiries from.
    underlying_symbol (str): The underlying symbol to fetch expiries for.
    year (Optional[int]): The year to fetch expiries for (must be between 2000 and 5000). If not provided, current year is used.
    month (Optional[int]): The month to fetch expiries for (1-12). If not provided, gets all expiries for the year.
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The list of expiry dates.

Raises:
    GrowwAPIException: If the request fails.
```

### get_greeks(self, exchange: str, underlying: str, trading_symbol: str, expiry: str) -> dict

Fetch the Greeks data for an option instrument.

```

Args:
    exchange (str): The exchange to fetch the data from.
    underlying (str): The underlying symbol of the option.
    trading_symbol (str): The trading symbol of the option.
    expiry (str): The expiry date of the option in yyyy-MM-dd format.
Returns:
    dict: The Greeks data.
Raises:
    GrowwAPIException: If the request fails.
```

### get_historical_candle_data(self, trading_symbol: str, exchange: str, segment: str, start_time: str, end_time: str, interval_in_minutes: int | None = None, timeout: int | None = None) -> dict

Get the historical data for an instrument.

```

Args:
    trading_symbol (str): The symbol to fetch the data for.
    exchange (str): The exchange to fetch the data from.
    segment (str): The segment to fetch the data from.
    start_time (str): The start time in epoch milliseconds or yyyy-MM-dd HH:mm:ss format.
    end_time (str): The end time in epoch milliseconds or yyyy-MM-dd HH:mm:ss format.
    interval_in_minutes (Optional[int]): The interval in minutes.
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The historical data.

Raises:
    GrowwAPIException: If the request fails.
```

### get_historical_candles(self, exchange: str, segment: str, groww_symbol: str, start_time: str, end_time: str, candle_interval: str, timeout: int | None = None) -> dict

Get bulk historical candle data for an instrument with V2 response format.

```

Args:
    exchange (str): The exchange to fetch the data from.
    segment (str): The segment to fetch the data from.
    groww_symbol (str): The Groww symbol to fetch the data for.
    start_time (str): The start time in yyyy-MM-dd HH:mm:ss format.
    end_time (str): The end time in yyyy-MM-dd HH:mm:ss format.
    candle_interval (str): The candle interval (e.g., "1minute", "5minute", "1day").
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The bulk historical candle data in V2 format.

Raises:
    GrowwAPIException: If the request fails.
```

### get_holdings_for_user(self, timeout: int | None = None) -> dict

Get the holdings for the user.

```

Args:
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The user's holdings response.

Raises:
    GrowwAPIException: If the request fails.
```

### get_instrument_by_exchange_and_trading_symbol(self, exchange: str, trading_symbol: str) -> dict

Get the instrument details for a trading symbol on an exchange.

```
:param exchange:
:param trading_symbol:
:return: dict
```

### get_instrument_by_exchange_token(self, exchange_token: str) -> dict

Get the instrument details for the exchange_token.

```
:param exchange_token:
:return:
```

### get_instrument_by_groww_symbol(self, groww_symbol: str) -> dict

Get the instrument details for the groww_symbol.

```
:param groww_symbol:
:return: dict
```

### get_ltp(self, exchange_trading_symbols: Tuple[str], segment: str, timeout: int | None = None) -> dict

Fetch the LTP data for a list of instruments.

```

Args:

    exchange_trading_symbol (str): A list of exchange_trading_symbols to fetch the ltp for. Example: "NSE_RELIANCE, NSE_INFY" or  ("NSE_RELIANCE", "NSE_INFY")
    segment (Segment): The segment to fetch the data from.
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The LTP data.

Raises:
    GrowwAPIException: If the request fails.
```

### get_ohlc(self, exchange_trading_symbols: Tuple[str], segment: str, timeout: int | None = None) -> dict

Fetch the OHLC data for a list of instruments.

```

Args:
    exchange_trading_symbol (str): A list of exchange_trading_symbols to fetch the ohlc for. Example: "NSE:RELIANCE, NSE:INFY" or  ("NSE:RELIANCE", "NSE:INFY")
    segment (str): The segment to fetch the data from.
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The OHLC data.

Raises:
    GrowwAPIException: If the request fails.
```

### get_option_chain(self, exchange: str, underlying: str, expiry_date: str, timeout: int | None = None) -> dict

Fetch the option chain data for FNO (Futures and Options) contracts.

```

Args:
    exchange (str): The exchange to fetch the data from.
    underlying (str): The underlying symbol for the contract such as NIFTY, BANKNIFTY, RELIANCE etc.
    expiry_date (str): Expiry date of the contract in YYYY-MM-DD format.
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).
Returns:
    dict: The option chain data including Greeks for all strikes.
Raises:
    GrowwAPIException: If the request fails.
```

### get_order_detail(self, segment: str, groww_order_id: str, timeout: int | None = None) -> dict

Get the details of an order.

```

Args:
    segment (str): The segment of the order.
    groww_order_id (str): The Groww order ID.
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The order details response.

Raises:
    GrowwAPIException: If the request fails.
```

### get_order_list(self, page: int | None = 0, page_size: int | None = 25, segment: str | None = None, timeout: int | None = None) -> dict

Get a list of orders.

```

Args:
    page (Optonal[int]): The page number for the orders. Defaults to 0.
    page_size (Optional[int]): The number of orders per page. Defaults to 25.
    segment (Optional[str]): The segment of the orders.
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The list of orders response.

Raises:
    GrowwAPIException: If the request fails.
```

### get_order_margin_details(self, segment: str, orders: list[dict], timeout: int | None = None) -> dict

### get_order_status(self, segment: str, groww_order_id: str, timeout: int | None = None) -> dict

Get the status of an order.

```

Args:
    segment (str): The segment of the order.
    groww_order_id (str): The Groww order ID.
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The order status response.

Raises:
    GrowwAPIException: If the request fails.
```

### get_order_status_by_reference(self, segment: str, order_reference_id: str, timeout: int | None = None) -> dict

Get the status of an order by reference ID.

```

Args:
    segment (str): The segment of the order.
    order_reference_id (str): The reference ID of the order.
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The order status response.

Raises:
    GrowwAPIException: If the request fails.
```

### get_position_for_trading_symbol(self, trading_symbol: str, segment: str, timeout: int | None = None) -> dict

Get the positions for a symbol.

```

Args:
    trading_symbol (str): The trading symbol to get the positions for.
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).
    segment (str): The segment of the trading_symbol.

Returns:
    dict: The positions response for the symbol.

Raises:
    GrowwAPIException: If the request fails.
```

### get_positions_for_user(self, segment: str | None = None, timeout: int | None = None) -> dict

Get the positions for the user for all the symbols they have positions in.

```

Args:
    segment (str): The segment of the positions.
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The user's positions response.

Raises:
    GrowwAPIException: If the request fails.
```

### get_quote(self, trading_symbol: str, exchange: str, segment: str, timeout: int | None = None) -> dict

Fetch the latest quote data for an instrument.

```

Args:
    symbol (str): The symbol to fetch the data for.
    exchange (str): The exchange to fetch the data from.
    segment (str): The segment to fetch the data from.
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The latest quote data.

Raises:
    GrowwAPIException: If the request fails.
```

### get_smart_order(self, segment: str, smart_order_type: str, smart_order_id: str, timeout: int | None = None) -> dict

Get a smart order by internal ID.

```

Args:
    segment (str): Market segment (e.g., CASH, FNO).
    smart_order_type (str): Smart order type (GTT or OCO).
    smart_order_id (str): The smart order identifier.
    timeout (Optional[int]): Request timeout in seconds.

Returns:
    dict: The smart order details.

Raises:
    GrowwAPIException: If the request fails.
```

### get_smart_order_list(self, smart_order_type: str | None = None, segment: str | None = None, status: str | None = None, page: int | None = None, page_size: int | None = None, start_date_time: str | None = None, end_date_time: str | None = None, timeout: int | None = None) -> dict

List smart orders with filters.

```

Args:
    smart_order_type (Optional[str]): Smart order type (GTT or OCO).
    segment (Optional[str]): Market segment (e.g., CASH, FNO).
    status (Optional[str]): Status filter (e.g., ACTIVE, CANCELLED).
    page (Optional[int]): Page number (min: 0, max: 500).
    page_size (Optional[int]): Items per page (min: 1, max: 50).
    start_date_time (Optional[str]): Inclusive start time (ISO 8601 format).
    end_date_time (Optional[str]): Inclusive end time (ISO 8601 format).
    timeout (Optional[int]): Request timeout in seconds.

Returns:
    dict: List of smart orders.

Raises:
    GrowwAPIException: If the request fails.
```

### get_trade_list_for_order(self, groww_order_id: str, segment: str, page: int | None = 0, page_size: int | None = 25, timeout: int | None = None) -> dict

Get the list of trades for a specific order.

```

Args:
    groww_order_id (str): The Groww order ID.
    segment (str): The segment of the order.
    page (Optional[int]): The page number for the trades. Defaults to 0.
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The list of trades response.

Raises:
    GrowwAPIException: If the request fails.
```

### get_user_profile(self, timeout: int | None = None) -> dict

Get the user profile details.

```

Args:
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The user profile details.

Raises:
    GrowwAPIException: If the request fails.
```

### modify_order(self, order_type: str, segment: str, groww_order_id: str, quantity: int, price: float | None = None, trigger_price: float | None = None, timeout: int | None = None) -> dict

Modify an existing order.

```

Args:
    order_type (str): The type of order.
    price (float): The price of the order in Rupee.
    quantity (int): The quantity of the order.
    segment (str): The segment of the order.
    groww_order_id (Optional[str]): The Groww order ID.
    trigger_price (float): The trigger price of the order in Rupee.
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The modified order response.

Raises:
    GrowwAPIException: If the request fails.
```

### modify_smart_order(self, smart_order_id: str, smart_order_type: str, segment: str, quantity: int | None = None, duration: str | None = None, trigger_price: str | None = None, trigger_direction: str | None = None, order: dict | None = None, child_legs: dict | None = None, product_type: str | None = None, target: dict | None = None, stop_loss: dict | None = None, timeout: int | None = None) -> dict

Modify a smart order (GTT or OCO).

```

For GTT orders, you can modify: quantity, trigger_price, trigger_direction, order, duration, child_legs.
For OCO orders, you can modify: quantity, product_type, target, stop_loss, duration.

Args:
    smart_order_id (str): The smart order identifier (e.g., gtt_91a7f4, oco_a12bc3).
    smart_order_type (str): Smart order type (GTT or OCO).
    segment (str): Market segment (e.g., CASH, FNO).
    quantity (Optional[int]): Updated quantity.
    duration (Optional[str]): Updated validity.
    trigger_price (Optional[str]): GTT: Updated trigger price.
    trigger_direction (Optional[str]): GTT: Updated trigger direction.
    order (Optional[dict]): GTT: Updated order details with keys: order_type, price, transaction_type.
    child_legs (Optional[dict]): GTT: Updated child legs for bracket orders.
    product_type (Optional[str]): OCO: Updated product type.
    target (Optional[dict]): OCO: Updated target leg with keys: trigger_price, order_type, price.
    stop_loss (Optional[dict]): OCO: Updated stop-loss leg with keys: trigger_price, order_type, price.
    timeout (Optional[int]): Request timeout in seconds.

Returns:
    dict: The modified smart order details.

Raises:
    GrowwAPIException: If the request fails.
```

### place_order(self, validity: str, exchange: str, order_type: str, product: str, quantity: int, segment: str, trading_symbol: str, transaction_type: str, order_reference_id: str | None = None, price: float | None = 0.0, trigger_price: float | None = None, timeout: int | None = None) -> dict

Place a new order.

```

Args:
    validity (str): The validity of the order.
    exchange (str): The exchange to place the order on.
    order_type (str): The type of order.
    price (float): The price of the order in Rupee.
    product (str): The product type.
    quantity (int): The quantity of the order.
    segment (str): The segment of the order.
    trading_symbol (str): The trading symbol to place the order for.
    transaction_type (str): The transaction type.
    order_reference_id (Optional[str]): The reference ID to track the order with. Defaults to a random 8-digit number.
    trigger_price (float): The trigger price of the order in Rupee.
    timeout (Optional[int]): The timeout for the request in seconds. Defaults to None (infinite).

Returns:
    dict: The placed order response.

Raises:
    GrowwAPIException: If the request fails.
```