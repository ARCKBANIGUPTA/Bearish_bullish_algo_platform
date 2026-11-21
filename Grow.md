Groww Trade API DocumentationThis reference documents the Groww Trade API (https://groww.in/trade-api/docs), consolidating specifications for both the Python SDK (growwapi) and the REST/cURL interface (https://api.groww.in). It covers portal structure, prerequisites, OAuth 2.0 and TOTP authentication, category-based rate limits, instrument master downloads, equity and derivatives orders, GTT/OCO smart orders, portfolio holdings and positions, margin checks, live market data and Greeks, historical and backtesting candles, real-time NATS WebSocket feeds, user profiles, annexures, exceptions, and the SDK changelog.Full parameter schemas, code samples, and JSON payloads are documented below for SDK setup, REST authentication, Orders, Live Data, Margin, Backtesting, Historical Data, Feed WebSockets, Annexures, and Exceptions. Where the available documentation lacked complete subpage details—specifically individual cURL endpoint definitions beyond authentication, /v1/order/create, /v1/order/detail/{groww_order_id}, and the Instrument CSV URL; full create_smart_order / modify-smart-order method signatures; trailing schema fields in Instruments, Portfolio, and User Profile; and detailed release notes for SDK versions 0.0.5 and 0.0.7 through 1.5.0—those boundaries are noted explicitly rather than inferred.1. Portal Architecture, Prerequisites, and SDK SetupThe main Groww API documentation portal (https://groww.in/trade-api/docs) routes developers to the API Key management portal (https://groww.in/trade-api/api-keys), the Python SDK documentation (https://groww.in/trade-api/docs/python-sdk), and the cURL REST documentation (https://groww.in/trade-api/docs/curl). Both documentation tracks share the same sidebar module structure: Introduction, Instruments, Orders, Smart Orders, Portfolio, Margin, Live Data, Historical Data, Backtesting, Feed (Python SDK), User, Annexures, Exceptions (Python SDK), and Changelog.Platform disclosures on the main portal list the operating entity as Groww Invest Tech Pvt. Ltd. (formerly Nextbillion Technology Pvt. Ltd.; CIN: U65100KA2016PTC092879; SEBI Reg. No.: INZ000301838 for NSE & BSE Membership; CDSL Depository Participant Reg. No.: IN-DP-417-2019; AMFI Reg. No.: ARN-111686; BSE Star MF Member Code 11724), headquartered at Vaishnavi Tech Park, South Tower, 3rd Floor, Sarjapur Main Road, Bellandur, Bengaluru - 560103, Karnataka.Exchange Support CaveatWhile the Python SDK introduction notes support for equity (CASH) and derivatives (FNO) across NSE, BSE, and MCX, the Annexures reference lists exchange constants only for NSE (EXCHANGE_NSE) and BSE (EXCHANGE_BSE), and the SDK changelog records a documentation update adding an MCX-not-supported note across portfolio, annexures, and index sections. Additionally, initial v0.0.1 release notes mention Currency segment and ETF support in instrument master data. Developers targeting MCX or currency contracts should verify live contract availability in the downloaded instrument CSV before trading.PrerequisitesAn active Groww account.Basic familiarity with Python and REST APIs.A development environment running Python 3.9+.An active Trading API Subscription purchased from https://groww.in/user/profile/trading-apis.InstallationInstall or upgrade the Python SDK via pip, and install pyotp if authenticating via the TOTP flow:Bashpip install growwapi
pip install --upgrade growwapi
pip install pyotp
2. Authentication and REST API ConventionsAll REST endpoints resolve against the base URL https://api.groww.in. Groww provides three authentication flows across its Web UI, Python SDK, and REST endpoints:Authentication MethodCredential / Token SourceApproval & Expiry RulesRequired Inputs / HeadersSupported InterfacesDirect Access Token (Web UI)Generated via Profile -> Settings -> Trading APIs -> Generate API keys -> Select Access TokenExpires daily at 6:00 AMPassed as Bearer {ACCESS_TOKEN} on API requestsWeb UI / RESTAPI Key and Secret FlowGenerated on Groww Cloud API Keys pageRequires daily approval on the Cloud API Keys page; REST epoch timestamp valid for 10 minuteskey_type: "approval", checksum (SHA-256 of secret + timestamp), timestamp (10-digit epoch seconds), Bearer <USER_API_KEY>Python SDK & RESTTOTP FlowTOTP token & secret (or authenticator QR code) from Generate TOTP token dropdownNo expirykey_type: "totp", totp code, Bearer <USER_API_KEY>Python SDK & RESTPython SDK Authentication FlowsApproach 1: API Key and Secret FlowNavigate to https://groww.in/trade-api/api-keys and log in to your Groww account.Click Generate API key, enter a key name, and click Continue.Copy the API Key and Secret (note that daily approval on the Cloud API Keys page is required).Exchange the credentials for an access token via GrowwAPI.get_access_token:Pythonfrom growwapi import GrowwAPI
import pyotp

api_key = "YOUR_API_KEY"
secret = "YOUR_API_SECRET"

access_token = GrowwAPI.get_access_token(api_key=api_key, secret=secret)
# Use access_token to initiate GrowwAPI
groww = GrowwAPI(access_token)
Approach 2: TOTP FlowNavigate to https://groww.in/trade-api/api-keys and log in.Select Generate TOTP token from the dropdown beside Generate API Key, enter a key name, and click Continue.Copy the TOTP token and Secret, or scan the QR code into a third-party authenticator app.Ensure pyotp is installed (pip install pyotp), then generate a live code and initialize GrowwAPI:Pythonfrom growwapi import GrowwAPI
import pyotp

api_key = "YOUR_TOTP_TOKEN"

# TOTP can be obtained using an authenticator app or generated dynamically:
totp_gen = pyotp.TOTP('YOUR_TOTP_SECRET')
totp = totp_gen.now()

access_token = GrowwAPI.get_access_token(api_key=api_key, totp=totp)
# Use access_token to initiate GrowwAPI
groww = GrowwAPI(access_token)
REST Authentication, Headers, and cURL ExamplesToken issuance uses POST https://api.groww.in/v1/token/api/access with Authorization: Bearer <USER_API_KEY> and Content-Type: application/json. All general trading and data requests require Authorization: Bearer {ACCESS_TOKEN}, Accept: application/json, and X-API-VERSION: 1.0, plus Content-Type: application/json on POST endpoints.ParameterTypeRequiredFlowDescriptionkey_typestringYesBoth"approval" for API Key/Secret flow or "totp" for TOTP flowchecksumstringYesApprovalSHA-256 hash of concatenated secret + timestamp (in epoch seconds)timestampstringYesApproval10-digit Unix epoch timestamp in seconds (valid for 10 minutes)totpstringYesTOTPCurrent TOTP code from a third-party authenticator or pyotpSuccessful calls to /v1/token/api/access return token (string), tokenRefId (string), sessionName (string), expiry (ISO date-time string), and isActive (boolean). Documented cURL requests cover token generation, order creation, and order detail lookup:Bash# Generate Access Token (API Key & Secret Flow)
curl -X POST "https://api.groww.in/v1/token/api/access" \
  -H "Authorization: Bearer <USER_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
  "key_type": "approval",
  "checksum": "<Checksum>",
  "timestamp": "1719830400"
  }'

# Generate Access Token (TOTP Flow)
curl -X POST "https://api.groww.in/v1/token/api/access" \
  -H "Authorization: Bearer <USER_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
  "key_type": "totp",
  "totp": "<TOTP_CODE>"
  }'

# Create Order (POST)
curl -X POST https://api.groww.in/v1/order/create \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  -H 'Authorization: Bearer {ACCESS_TOKEN}' \
  -H 'X-API-VERSION: 1.0' \
  -d '{
  "validity": "DAY",
  "exchange": "NSE",
  "transaction_type": "BUY",
  "order_type": "MARKET",
  "price": 0,
  "product": "CNC",
  "quantity": 1,
  "segment": "CASH",
  "trading_symbol": "IDEA"
  }'

# Fetch Order Details (GET)
curl -X GET https://api.groww.in/v1/order/detail/{groww_order_id}?segment=CASH \
  -H 'Accept: application/json' \
  -H 'Authorization: Bearer YOUR_GENERATED_ACCESS_TOKEN' \
  -H 'X-API-VERSION: 1.0'
(Coverage note: Additional individual cURL endpoint documentation pages—such as REST URLs for smart orders, portfolio, margin, live data, historical candles, and user profile—were not included in the available cURL documentation beyond /v1/token/api/access, /v1/order/create, /v1/order/detail/{groww_order_id}, and the Instrument CSV download URL.)3. Rate LimitsGroww applies rate limits at the category (type) level rather than per individual endpoint. Every operation within a category shares a single pool; exhausting the quota for one API throttles all other APIs in that category until the window resets.Type / CategoryRequests IncludedLimit (Per Second)Limit (Per Minute)Additional Limits & NotesAuthenticationGenerate access token (/v1/token/api/access)530Hard limit of 150 requests per 24 hoursOrdersCreate, Modify, and Cancel Order10250Shared quota across order mutationsLive DataMarket Quote, LTP, OHLC10300Per-call batch limit of up to 50 instruments on get_ltp and get_ohlcNon TradingOrder Status, Order list, Trade list, Positions, Holdings, Margin20500Shared quota across account and status readsFor WebSocket streaming through GrowwFeed, up to 1,000 subscriptions are permitted simultaneously.4. Instruments Master DataThe Instruments API provides daily master metadata for stocks, futures, options, indices, and ETFs, supplying the trading_symbol, groww_symbol, and exchange_token values needed across order placement, backtesting, and WebSocket feeds.Downloading and Querying InstrumentsDownload the master CSV directly via cURL or wget, or use GrowwAPI methods and DataFrame loaders in Python:Bashcurl -X GET https://growwapi-assets.groww.in/instruments/instrument.csv
Pythonfrom growwapi import GrowwAPI
import pandas as pd

API_AUTH_TOKEN = "your_token"
groww = GrowwAPI(API_AUTH_TOKEN)

# Look up a single instrument by Groww symbol
selected = groww.get_instrument_by_groww_symbol(groww_symbol="NSE-RELIANCE")
print(selected)

# Combine instrument metadata with Live Data
ltp_response = groww.get_ltp(
    exchange_trading_symbols="NSE_" + selected['trading_symbol'],
    segment=selected['segment'],
)
print("Live Data:", ltp_response)

# Load all instruments as a pandas DataFrame
instruments_df = groww.get_all_instruments()
print(instruments_df.head())

# Alternative manual CSV load
instrument_df = pd.read_csv(groww.INSTRUMENT_CSV_URL)
# OR: instrument_df = groww._load_instruments()
print(instrument_df.head())
Documented Instrument FieldsThe official Instruments schema documents the fields listed below (additional fields such as segment—accessed via selected['segment'] in the SDK sample above—appear between groww_symbol and series in the full CSV schema but were omitted in the available documentation text):Field NameTypeDescriptionexchangestringExchange where the instrument tradesexchange_tokenstringUnique token assigned to the instrument by the exchangetrading_symbolstringExchange trading symbol used to place ordersgroww_symbolstringGroww-standardized identifier for the instrumentseriesstringInstrument series (e.g., EQ, A, B)isinstringInternational Securities Identification Numberunderlying_symbolstringUnderlying symbol for derivatives (empty for stocks and indices)underlying_exchange_tokenstringExchange token of the underlying assetlot_sizenumberMinimum trading lot sizeexpiry_datestringDerivative expiry datestrike_pricenumberOption strike price5. Orders APIThe Orders API provides full lifecycle control for CASH and FNO orders: placement, modification, cancellation, trade fill retrieval, status checks by Groww order ID or user reference ID, daily order listing, and single-order detail inspection.Place Order (place_order)Registers a new order and returns a unique groww_order_id alongside its initial status.Pythonfrom growwapi import GrowwAPI

API_AUTH_TOKEN = "your_token"
groww = GrowwAPI(API_AUTH_TOKEN)

place_order_response = groww.place_order(
    trading_symbol="WIPRO",
    quantity=1,
    validity=groww.VALIDITY_DAY,
    exchange=groww.EXCHANGE_NSE,
    segment=groww.SEGMENT_CASH,
    product=groww.PRODUCT_CNC,
    order_type=groww.ORDER_TYPE_LIMIT,  # Also ORDER_TYPE_MARKET, ORDER_TYPE_STOP_LOSS, ORDER_TYPE_STOP_LOSS_MARKET
    transaction_type=groww.TRANSACTION_TYPE_BUY,
    price=250,           # Optional: Price of the stock (for Limit orders)
    trigger_price=245,   # Optional: Trigger price (if applicable)
    order_reference_id="Ab-654321234-1628190"  # Optional: 8-20 length alphanumeric reference ID
)
print(place_order_response)
ParameterTypeRequiredDescriptiontrading_symbolstringYesExchange-defined trading symbolquantityintYesQuantity to orderpricefloatNoLimit price in rupeestrigger_pricefloatNoTrigger price in rupeesvaliditystringYesOrder validity (DAY)exchangestringYesStock exchange (NSE, BSE)segmentstringYesSegment (CASH, FNO)productstringYesProduct type (CNC, MIS, NRML)order_typestringYesOrder type (LIMIT, MARKET, SL, SL_M)transaction_typestringYesTrade side (BUY, SELL)order_reference_idstringNoUser-provided 8–20 character alphanumeric string with at most two hyphens (-)Example response (returns groww_order_id, order_status, order_reference_id, and remark strings):JSON{
  "groww_order_id": "GMK39038RDT490CCVRO",
  "order_status": "OPEN",
  "order_reference_id": "Ab-654321234-1628190",
  "remark": "Order placed successfully"
}
Modify Order (modify_order) and Cancel Order (cancel_order)Both methods operate on open or pending orders and return groww_order_id (string) and order_status (string).Python# Modify an open order
modify_order_response = groww.modify_order(
    quantity=1,
    order_type=groww.ORDER_TYPE_MARKET,  # Also ORDER_TYPE_LIMIT, ORDER_TYPE_STOP_LOSS, ORDER_TYPE_STOP_LOSS_MARKET
    segment=groww.SEGMENT_CASH,
    groww_order_id="GMK39038RDT490CCVRO",
)

# Cancel an open order
cancel_order_response = groww.cancel_order(
    segment=groww.SEGMENT_CASH,
    groww_order_id="GMK39038RDT490CCVRO",
)
MethodParameterTypeRequiredDescriptionmodify_orderquantityintYesUpdated quantitymodify_orderpricefloatNoUpdated limit price in rupeesmodify_ordertrigger_pricefloatNoUpdated trigger price in rupeesmodify_orderorder_typestringYesUpdated order typemodify_ordersegmentstringYesSegment (CASH, FNO)modify_ordergroww_order_idstringYesGroww-generated order IDcancel_ordersegmentstringYesSegment (CASH, FNO)cancel_ordergroww_order_idstringYesGroww-generated order IDExample response returned by modify_order and cancel_order:JSON{
  "groww_order_id": "GMK39038RDT490CCVRO",
  "order_status": "OPEN"
}
Get Trades for Order (get_trade_list_for_order)Fetches paginated execution fills for a specific order, up to a maximum page_size of 50. Note an internal inconsistency in the official docs: inline code comments describe page and page_size as optional (default 50), whereas the Request Schema table marks both as required.Pythontrade_list_response = groww.get_trade_list_for_order(
    groww_order_id="GMK39038RDT490CCVRO",
    segment=groww.SEGMENT_CASH,
    page=0,
    page_size=50
)
print(trade_list_response)
Response payload (trade_list array, prices in rupees) and field schema:JSON{
  "trade_list": [
    {
      "price": 250,
      "isin": "INE075A01022",
      "quantity": 1,
      "groww_order_id": "GMK39038RDT490CCVRO",
      "groww_trade_id": "",
      "exchange_trade_id": "202402120123456789",
      "exchange_order_id": "1100000057528630",
      "trade_status": "EXECUTED",
      "trading_symbol": "WIPRO",
      "remark": "Order placed successfully",
      "exchange": "NSE",
      "segment": "CASH",
      "product": "CNC",
      "transaction_type": "BUY",
      "created_at": "2019-08-24T14:15:22Z",
      "trade_date_time": "2019-08-24T14:15:22Z",
      "settlement_number": "2024052"
    }
  ]
}
FieldTypeDescriptionpriceintExecution price in rupeesisinstringISIN of the traded instrumentquantityintShares or contracts executedgroww_order_idstringGroww-generated order IDgroww_trade_idstringUnique trade ID inside Groww's systemexchange_trade_idstringTrade ID assigned by the exchangeexchange_order_idstringOrder ID assigned by the exchangetrade_statusstringStatus of the tradetrading_symbolstringTrading symbolremarkstringRemark field present in the response payloadexchangestringStock exchangesegmentstringInstrument segmentproductstringProduct typetransaction_typestringTrade directioncreated_atstring (date-time)Order creation timestamptrade_date_timestring (date-time)Exchange execution timestampsettlement_numberstringSettlement ID associated with the tradeGet Order Status (get_order_status and get_order_status_by_reference)Look up order execution progress either by groww_order_id or by client-assigned order_reference_id, along with the required segment parameter.Pythonorder_status_response = groww.get_order_status(
    groww_order_id="GMK39038RDT490CCVRO",
    segment=groww.SEGMENT_CASH,
)

order_status_by_ref_response = groww.get_order_status_by_reference(
    order_reference_id="Ab-654321234-1628190",
    segment=groww.SEGMENT_CASH,
)
Both methods return groww_order_id (string), order_status (string), remark (string), filled_quantity (int), and order_reference_id (string).Get Order List (get_order_list) and Get Order Details (get_order_detail)get_order_list retrieves all orders placed during the day (with optional segment, page, and page_size filters), while get_order_detail retrieves full details for a single groww_order_id and segment. Note an inconsistency in the official get_order_list documentation: the method summary and Python code comments specify a default and maximum page_size of 100, whereas the Request Schema table lists a default and maximum page_size of 25.Python# All orders across CASH and FNO
order_list_response = groww.get_order_list(page=0, page_size=100)

# CASH-segment orders only
cash_order_list_response = groww.get_order_list(
    segment=groww.SEGMENT_CASH,
    page=0,
    page_size=100
)

# Detailed single order
order_detail_response = groww.get_order_detail(
    groww_order_id="GMK39038RDT490CCVRO",
    segment=groww.SEGMENT_CASH,
)
Each item in order_list (for get_order_list) and the top-level object returned by get_order_detail share the same 22-field schema (all prices in rupees):JSON{
  "groww_order_id": "GMK39038RDT490CCVRO",
  "trading_symbol": "WIPRO",
  "order_status": "OPEN",
  "remark": "Order placed successfully",
  "quantity": 100,
  "price": 250,
  "trigger_price": 245,
  "filled_quantity": 100,
  "remaining_quantity": 10,
  "average_fill_price": 250,
  "deliverable_quantity": 10,
  "amo_status": "PENDING",
  "validity": "DAY",
  "exchange": "NSE",
  "order_type": "MARKET",
  "transaction_type": "BUY",
  "segment": "CASH",
  "product": "CNC",
  "created_at": "2019-08-24T14:15:22Z",
  "exchange_time": "2019-08-24T14:15:22Z",
  "trade_date": "2019-08-24T14:15:22Z",
  "order_reference_id": "Ab-654321234-1628190"
}
FieldTypeDescriptiongroww_order_idstringGroww-generated order IDtrading_symbolstringGroww-specific trading symbolorder_statusstringCurrent status of the orderremarkstringStatus remarkquantityintOrdered quantitypriceintLimit price in rupeestrigger_priceintTrigger price in rupeesfilled_quantityintExecuted quantityremaining_quantityintRemaining unfilled quantityaverage_fill_priceintAverage fill price in rupeesdeliverable_quantityintShares eligible for deliveryamo_statusstringAfter-market order status (not applicable during market hours)validitystringOrder validity (DAY)exchangestringStock exchange (NSE, BSE)order_typestringOrder type (MARKET, LIMIT, SL, SL_M)transaction_typestringTrade direction (BUY, SELL)segmentstringSegment (CASH, FNO)productstringProduct type (CNC, MIS, NRML)created_atstring (date-time)Order creation timestampexchange_timestring (date-time)Exchange acknowledgment/processing timestamptrade_datestring (date-time)Date on which trade took placeorder_reference_idstringClient tracking reference ID6. Smart Orders APISmart Orders automate conditional entries and exits for CASH and FNO instruments through two structures:GTT (Good Till Triggered): Triggers a single order when market price crosses the defined trigger threshold.OCO (One Cancels the Other): Pairs a profit target leg and a stop-loss leg so that execution of one automatically cancels the other.OCO orders are meant to exit an existing position: in FNO, the account must already hold the contract under NRML, whereas in CASH, OCO supports MIS. Ordered quantity must satisfy quantity <= abs(net_position_quantity). Creation requires a client-supplied reference_id (8–20 alphanumeric characters with at most two hyphens -) serving as an idempotency key.Verified Smart Order Methods and SignaturesComplete code samples were captured for canceling, retrieving, and listing smart orders. For create_smart_order and smart-order modification, the official documentation text truncated portions of the trailing arguments and the modify method prefix, so verified documented parameters are detailed in the schema tables below.Python# Cancel a Smart Order
cancel_response = groww.cancel_smart_order(
    segment=groww.SEGMENT_CASH,
    smart_order_type=groww.SMART_ORDER_TYPE_GTT,
    smart_order_id="gtt_91a7f4"
)
print(cancel_response)

# Retrieve a single Smart Order
order_details = groww.get_smart_order(
    segment=groww.SEGMENT_CASH,
    smart_order_type=groww.SMART_ORDER_TYPE_GTT,
    smart_order_id="gtt_91a7f4"
)
print(order_details)

# List Smart Orders with filters and pagination
orders_list = groww.get_smart_order_list(
    segment=groww.SEGMENT_FNO,
    smart_order_type=groww.SMART_ORDER_TYPE_OCO,
    status=groww.SMART_ORDER_STATUS_ACTIVE,
    page=0,
    page_size=10,
    start_date_time="2025-01-16T09:15:00",
    end_date_time="2025-01-16T15:30:00"
)
print(orders_list)
Documented parameter groups for create_smart_order (GTT and OCO) from the SDK examples:Order TypeVerified Parameters in SDK DocumentationExample Values / NotesGTT (create_smart_order)smart_order_type, reference_id, segment, trading_symbol, quantity, product_type, exchange, duration, trigger_price, trigger_directionExample sets SMART_ORDER_TYPE_GTT, reference_id="gtt-ref-unique123", PRODUCT_CNC, VALIDITY_DAY, trigger_price="3985.00"; trailing parameters after trigger_direction were truncated in the source documentationOCO (create_smart_order)smart_order_type, reference_id, segment, trading_symbol, quantity, product_type, exchange, duration, net_position_quantity, transaction_type, target, stop_lossExample sets SMART_ORDER_TYPE_OCO, PRODUCT_NRML, net_position_quantity=50, TRANSACTION_TYPE_SELL, target={"trigger_price": "120.50", "order_type": groww.ORDER_TYPE_LIMIT, "price": "121.00"}, and stop_loss starting with trigger_price="95.00" (trailing stop_loss keys truncated)Modification Rules vs. Cancel-and-RecreateGroww documents specific mutability rules distinguishing GTT from OCO modifications:Attribute to UpdateGTTOCORequired ActionQuantityModifiableModifiableModifyTrigger priceModifiableModifiable (both legs)ModifyTrigger directionModifiableN/AModifyOrder typeModifiableNot modifiableGTT: modify; OCO: cancel + createLimit priceModifiableNot modifiableGTT: modify; OCO: cancel + createDuration / validityNot modifiableModifiableOCO: modify; GTT: cancel + createProduct typeNot modifiableModifiableOCO: modify; GTT: cancel + createSymbol / contractNot modifiableNot modifiableCancel + createExchangeNot modifiableNot modifiableCancel + createSegmentNot modifiableNot modifiableCancel + createSmart order type (GTT vs OCO)Not modifiableNot modifiableCancel + createNote that while the exact smart-order modification method name prefix was truncated immediately before its keyword arguments (smart_order_type=groww.SMART_ORDER_TYPE_OCO, segment=groww.SEGMENT_FNO, ...), the complete parameter specification was captured:Modifiable GTT fields: trigger_price, trigger_direction, order.order_type, order.price (required for LIMIT/SL; set to None for MARKET/SL_M), and optional child_legs (all child leg fields are modifiable when provided).OCO modification parameters: Required routing fields are smart_order_id (str, e.g., "oco_a12bc3"), smart_order_type ("OCO"), and segment ("FNO" or "CASH"). Modifiable fields are duration, quantity, product_type (NRML for F&O; MIS for CASH), target["trigger_price"] (decimal string), and stop_loss["trigger_price"] (decimal string). Leg order_type and price fields remain immutable.List Smart Orders Parameters and ResponseParameters for get_smart_order_list:ParameterTypeConstraints / ValuesDescriptionsegmentstrFNO, CASH (optional)Segment filtersmart_order_typestrOCO, GTT (optional)Smart order type filterstatusstrACTIVE, TRIGGERED, CANCELLED, COMPLETED (optional)Status filterpageintMin 0, Max 500Zero-based page indexpage_sizeintMin 1, Max 50Records per pagestart_date_timestrISO 8601 (e.g., 2025-01-16T09:15:00)Inclusive window startend_date_timestrISO 8601; >= start_date_time; max 1-month rangeInclusive window endThe get_smart_order_list response wraps records in an orders list:JSON{
  "orders": [
    {
      "smart_order_id": "gtt_91a7f4",
      "smart_order_type": "GTT",
      "status": "ACTIVE",
      "trading_symbol": "TCS",
      "exchange": "NSE",
      "quantity": 10
    }
  ]
}
(Coverage note: Complete response schemas for create_smart_order, smart-order modification, cancel_smart_order, and get_smart_order were not fully captured in the available Smart Orders documentation.)7. Portfolio APIThe Portfolio module retrieves Demat holdings and segment-level trading positions across CASH and FNO (noting the changelog's MCX-not-supported advisory for portfolio endpoints).Pythonfrom growwapi import GrowwAPI

API_AUTH_TOKEN = "your_token"
groww = GrowwAPI(API_AUTH_TOKEN)

# Fetch Demat holdings (optional timeout parameter)
holdings_response = groww.get_holdings_for_user(timeout=5)
print(holdings_response)

# Fetch all positions, or filter by segment
all_positions = groww.get_positions_for_user()
cash_positions = groww.get_positions_for_user(segment=groww.SEGMENT_CASH)
fno_positions = groww.get_positions_for_user(segment=groww.SEGMENT_FNO)

# Fetch position for a specific trading symbol and segment
symbol_position = groww.get_position_for_trading_symbol(
    trading_symbol="RELIANCE",
    segment=groww.SEGMENT_CASH
)
print(symbol_position)
Documented fields in the holdings array include isin, trading_symbol, quantity, average_price, pledge_quantity, demat_locked_quantity, groww_locked_quantity, repledge_quantity, t1_quantity, demat_free_quantity, corporate_action_additional_quantity, and active_demat_transfer_quantity (int).Documented fields in the positions array (all prices in rupees) include trading_symbol, segment, exchange, credit_quantity, credit_price, debit_quantity, debit_price, carry_forward_credit_quantity (int), carry_forward_credit_price (int), carry_forward_debit_quantity (int), carry_forward_debit_price, net_carry_forward_price (int), and realised_pnl (added per the SDK changelog). A net average price field immediately preceding net_carry_forward_price, along with trailing fields in the holdings and positions schemas, were truncated in the captured Portfolio documentation.8. Margin APIThe Margin module provides account-wide available balances and pre-trade margin estimation for individual orders or F&O baskets.Get Available Margin Details (get_available_margin_details)Pythonfrom growwapi import GrowwAPI

API_AUTH_TOKEN = "your_token"
groww = GrowwAPI(API_AUTH_TOKEN)

available_margin_details_response = groww.get_available_margin_details()
print(available_margin_details_response)
In the JSON response sample, F&O fields appear nested under fno_margin_details ({"clear_cash": 96.21, ..., "fno_margin_details": {"net_fno_margin_used": 0.0, "span_margin_used": 0.0, "exposure_margin_used": 0.0, "future_balance_available": 94.41, ...}}), while the documentation's Response Schema table lists all 17 fields flatly:FieldTypeDescriptionclear_cashfloatClear cash availablenet_margin_usedfloatNet margin usedbrokerage_and_chargesfloatBrokerage and chargescollateral_usedfloatCollateral usedcollateral_availablefloatCollateral availableadhoc_marginfloatAd-hoc margin availablenet_fno_margin_usedfloatNet F&O margin usedspan_margin_usedfloatSPAN margin used (for F&O)exposure_margin_usedfloatExposure margin used (for F&O)future_balance_availablefloatFuture balance availableoption_buy_balance_availablefloatOption buy balance availableoption_sell_balance_availablefloatOption sell balance availablenet_equity_margin_usedfloatNet equity margin usedcnc_margin_usedfloatCNC margin usedmis_margin_usedfloatMIS margin usedcnc_balance_availablefloatCNC balance availablemis_balance_availablefloatMIS balance availableRequired Margin for Order (get_order_margin_details)Calculates required margin for a single order or a basket of orders; basket orders are supported only for the FNO segment. (Note: The exact Python usage snippet showing how single vs. basket arguments are structured in get_order_margin_details was omitted in the available documentation text.)Request schema:FieldTypeRequiredDescriptiontrading_symbolstringYesExchange-defined trading symbolquantityintegerYesQuantity to orderpricedecimalNoPrice in rupees (for Limit orders)segmentstringYesInstrument segment (CASH, FNO)exchangestringYesStock exchangeproductstringYesProduct typeorder_typestringYesOrder typetransaction_typestringYesTransaction type (BUY, SELL)Response payload and schema (all amounts in rupees):JSON{
  "exposure_required": 0.0,
  "span_required": 0.0,
  "option_buy_premium": 0.0,
  "brokerage_and_charges": 0.2,
  "total_requirement": 100.2,
  "cash_cnc_margin_required": 100.0,
  "physical_delivery_margin_requirement": 0.0
}
FieldTypeDescriptionexposure_requiredfloatMargin required to cover trade exposurespan_requiredfloatSPAN margin for F&O trades (not applicable for CASH)option_buy_premiumfloatOption premium required for buying optionsbrokerage_and_chargesfloatTotal brokerage and exchange-related chargestotal_requirementfloatTotal margin requirement including all chargescash_cnc_margin_requiredfloatMargin required for CNC orders in CASHcash_mis_margin_requiredfloatMargin required for MIS orders in CASHphysical_delivery_margin_requirementfloatAdditional margin required for physical settlement of derivatives9. Live Market Data APIThe Live Data module exposes five methods returning real-time market snapshots and derivatives analytics in Indian Rupees. Note the parameter naming difference between get_option_chain (which accepts expiry_date) and get_greeks (which accepts expiry), and note that get_ohlc returns current-day snapshot OHLC values rather than interval candles.MethodRequired ParametersBatch LimitOutput Scopeget_quoteexchange, segment, trading_symbol1 instrumentFull quote, bid/offer, depth, circuits, OI, volume, 52-week boundsget_ltpsegment, exchange_trading_symbolsUp to 50Dictionary mapping EXCHANGE_SYMBOL to float priceget_ohlcsegment, exchange_trading_symbolsUp to 50Real-time snapshot open, high, low, close per EXCHANGE_SYMBOLget_option_chainexchange, underlying, expiry_date (YYYY-MM-DD)Full chainunderlying_ltp and strike-indexed CE/PE contracts with Greeksget_greeksexchange, underlying, trading_symbol, expiry (YYYY-MM-DD)1 contractdelta, gamma, theta, vega, rho, and ivPython SDK Usage ExamplesPythonfrom growwapi import GrowwAPI

API_AUTH_TOKEN = "your_token"
groww = GrowwAPI(API_AUTH_TOKEN)

# 1. Single-instrument full quote
quote_response = groww.get_quote(
    exchange=groww.EXCHANGE_NSE,
    segment=groww.SEGMENT_CASH,
    trading_symbol="NIFTY"
)

# 2. Batch LTP (accepts a single string or a tuple of up to 50 EXCHANGE_SYMBOL strings)
multiple_ltp_response = groww.get_ltp(
    segment=groww.SEGMENT_CASH,
    exchange_trading_symbols=("NSE_NIFTY", "NSE_RELIANCE")
)

# 3. Batch OHLC snapshot (CASH for stocks/indices, FNO for derivatives; up to 50 symbols)
multiple_ohlc_response = groww.get_ohlc(
    segment=groww.SEGMENT_CASH,
    exchange_trading_symbols=("NSE_NIFTY", "NSE_RELIANCE")
)

# 4. Option Chain with Greeks
option_chain_response = groww.get_option_chain(
    exchange=groww.EXCHANGE_NSE,
    underlying="NIFTY",
    expiry_date="2025-11-28"
)

# 5. Option Greeks for an individual contract
greeks_response = groww.get_greeks(
    exchange=groww.EXCHANGE_NSE,
    underlying="NIFTY",
    trading_symbol="NIFTY25O1425100CE",
    expiry="2025-10-14"
)
Response Payloads and SchemasExample get_quote payload:JSON{
  "average_price": 150.25,
  "bid_quantity": 1000,
  "bid_price": 150,
  "day_change": -0.5,
  "day_change_perc": -0.33,
  "upper_circuit_limit": 151,
  "lower_circuit_limit": 148.5,
  "ohlc": {
    "open": 149.50,
    "high": 150.50,
    "low": 148.50,
    "close": 149.50
  },
  "depth": {
    "buy": [{"price": 100.5, "quantity": 1000}],
    "sell": [{"price": 100.5, "quantity": 1000}]
  },
  "high_trade_range": 150.5,
  "implied_volatility": 0.25,
  "last_trade_quantity": 500,
  "last_trade_time": 1633072800000,
  "low_trade_range": 148.25,
  "last_price": 149.5,
  "market_cap": 5000000000,
  "offer_price": 150.5,
  "offer_quantity": 2000,
  "oi_day_change": 100,
  "oi_day_change_percentage": 0.5,
  "open_interest": 2000,
  "previous_open_interest": 1900,
  "total_buy_quantity": 5000,
  "total_sell_quantity": 4000,
  "volume": 10000,
  "week_52_high": 160,
  "week_52_low": 140
}
Example get_ltp and get_ohlc payloads (get_ltp schema names the price value ltp (float), while JSON keys are the requested EXCHANGE_SYMBOL strings):JSON{
  "NSE_RELIANCE": 2500.5,
  "NSE_NIFTY": 22962.10
}
JSON{
  "NSE_NIFTY": {
    "open": 22516.45,
    "high": 22613.3,
    "low": 22526.4,
    "close": 22547.55
  },
  "NSE_RELIANCE": {
    "open": 1212.8,
    "high": 1215.0,
    "low": 1201.0,
    "close": 1204.0
  }
}
Example get_option_chain payload (truncated to strike 23400; full responses include all available strikes) and get_greeks payload:JSON{
  "underlying_ltp": 25641.7,
  "strikes": {
    "23400": {
      "CE": {
        "greeks": {
          "delta": 0.9936,
          "gamma": 0,
          "theta": -1.0787,
          "vega": 0.6943,
          "rho": 5.1802,
          "iv": 25.3409
        },
        "trading_symbol": "NIFTY25N1823400CE",
        "ltp": 2200,
        "open_interest": 7,
        "volume": 5
      },
      "PE": {
        "greeks": {
          "delta": -0.0064,
          "gamma": 0,
          "theta": -1.0787,
          "vega": 0.6943,
          "rho": -0.0373,
          "iv": 25.3409
        },
        "trading_symbol": "NIFTY25N1823400PE",
        "ltp": 2.05,
        "open_interest": 7453,
        "volume": 9339
      }
    }
  }
}
JSON{
  "greeks": {
    "delta": 0.6006,
    "gamma": 0.0014,
    "theta": -8.1073,
    "vega": 13.1433,
    "rho": 2.7333,
    "iv": 8.2383
  }
}
Summary of Live Data response fields:MethodFieldTypeDescriptionget_quoteaverage_price, last_price, day_change, day_change_percfloatAverage price, LTP, price change, and percentage changeget_quotebid_price, bid_quantity, offer_price, offer_quantityfloat / intBid and offer price and quantityget_quoteupper_circuit_limit, lower_circuit_limit, high_trade_range, low_trade_rangefloatHigh/low circuit limits and daily trade range boundsget_quoteopen, high, low, close (inside ohlc)floatSession opening, high, low, and closing pricesget_quoteprice, quantity (inside depth.buy / depth.sell)float / intOrder book depth price and quantityget_quoteimplied_volatility, market_cap, week_52_high, week_52_lowfloatImplied volatility, market cap, and 52-week high/lowget_quotelast_trade_quantity, last_trade_time, volumeintLast trade size, epoch-ms timestamp, and cumulative volumeget_quoteopen_interest, previous_open_interest, oi_day_change, oi_day_change_percentagefloatOpen interest and day-over-day OI changesget_quotetotal_buy_quantity, total_sell_quantityfloatTotal resting buy and sell book quantitiesget_ltpltp (value per EXCHANGE_SYMBOL key)floatLast traded priceget_ohlcopen, high, low, close (per EXCHANGE_SYMBOL key)floatReal-time OHLC snapshotget_option_chainunderlying_ltp, strikes, trading_symbol, ltp, open_interest, volumefloat / object / str / intUnderlying LTP and strike-wise CE/PE contract metricsget_option_chain, get_greeksdelta, gamma, theta, vega, rho, ivfloatOption Greeks (delta per Re 1 move, vega per 1% IV change, iv in %)10. Historical Data and Backtesting APIGroww currently supports two historical candle APIs: the current Backtesting API (get_historical_candles, paired with get_expiries and get_contracts), and the deprecated Historical Data API (get_historical_candle_data). Backtesting APIs support CASH and FNO segments with historical data for Equities, Indices, and F&O available from 2020.Groww Symbol Construction RulesBacktesting queries require a groww_symbol formed from Exchange, Trading Symbol, and—for derivatives—Expiry Date (DDMmmYY, e.g., 23Jan25), Strike Price, and Option Type (CE, PE, FUT):Segment / TypeConstruction ComponentsOfficial ExamplesEquityExchange + Trading SymbolNSE-WIPRO, BSE-RELIANCEIndexExchange + Trading SymbolNSE-NIFTY, BSE-SENSEXFutureExchange + Trading Symbol + Expiry Date + FUTNSE-NIFTY-30Sep25-FUT, BSE-SENSEX-25Sep25-FUTCall OptionExchange + Trading Symbol + Expiry Date + Strike Price + CENSE-NIFTY-30Sep25-24650-CE, BSE-SENSEX-25Sep25-79500-CEPut OptionExchange + Trading Symbol + Expiry Date + Strike Price + PENSE-NIFTY-30Sep25-24650-PE, BSE-SENSEX-25Sep25-79500-PEBacktesting Methods (get_expiries, get_contracts, get_historical_candles)Pythonfrom growwapi import GrowwAPI

API_AUTH_TOKEN = "your_token"
groww = GrowwAPI(API_AUTH_TOKEN)

# 1. Historical candles for Cash / Equities
historical_candles_response = groww.get_historical_candles(
    exchange=groww.EXCHANGE_NSE,
    segment=groww.SEGMENT_CASH,
    groww_symbol="NSE-WIPRO",
    start_time="2025-09-24 10:56:00",
    end_time="2025-09-24 12:00:00",
    candle_interval=groww.CANDLE_INTERVAL_MIN_30
)

# 2. Discover expiries -> contracts -> historical F&O candles
jan2024_nifty_expiries = groww.get_expiries(
    exchange=groww.EXCHANGE_NSE,
    underlying_symbol="NIFTY",
    year=2024,
    month=1
)

nifty_24_jan_contracts = groww.get_contracts(
    exchange=groww.EXCHANGE_NSE,
    underlying_symbol="NIFTY",
    expiry_date=jan2024_nifty_expiries['expiries'][0]
)

candles = groww.get_historical_candles(
    exchange=groww.EXCHANGE_NSE,
    segment=groww.SEGMENT_FNO,
    groww_symbol=nifty_24_jan_contracts['contracts'][0],
    start_time="2024-01-01 09:15:00",
    end_time="2024-01-10 15:30:00",
    candle_interval=groww.CANDLE_INTERVAL_MIN_15
)
(Documentation note: In the official Backtesting page's Example 2 code snippet, jan2024_nifty_expiries['expiries'] and nifty_24_jan_contracts['contracts'] are passed without [0] indexing despite get_expiries returning array[string] and get_contracts returning array[string] while expiry_date and groww_symbol expect string inputs; the snippet above indexes [0] to match the documented request schemas.)Request schemas for all three Backtesting methods:MethodParameterTypeRequiredDescriptionget_expiriesexchangestringYesNSE or BSEget_expiriesunderlying_symbolstringYesUnderlying symbol (e.g., NIFTY, BANKNIFTY, RELIANCE)get_expiriesyearintegerNo2020 to current year (defaults to current year)get_expiriesmonthintegerNo1–12 (if omitted, returns expiries for the entire year)get_contractsexchangestringYesNSE or BSEget_contractsunderlying_symbolstringYesUnderlying symbol (1–20 characters)get_contractsexpiry_datestringYesExpiry date in YYYY-MM-DD formatget_historical_candlesexchangestringYesNSE or BSEget_historical_candlessegmentstringYesCASH, FNO, etc.get_historical_candlesgroww_symbolstringYesStandardized Groww symbolget_historical_candlesstart_timestringYesyyyy-MM-dd HH:mm:ss or epoch secondsget_historical_candlesend_timestringYesyyyy-MM-dd HH:mm:ss or epoch secondsget_historical_candlescandle_intervalstringYesCandle interval constant (e.g., CANDLE_INTERVAL_MIN_15)get_expiries returns {"expiries": ["2024-01-25", ...]} and get_contracts returns {"contracts": ["NSE-NIFTY-02Jan25-28500-PE", ...]}. get_historical_candles returns candles, closing_price (float), start_time (string), end_time (string), and interval_in_minutes (int), where each candle row is [timestamp, open, high, low, close, volume, open_interest] (open_interest is populated for FNO and null otherwise):JSON{
  "candles": [
    ["2025-09-24T10:30:00", 245.95, 246.15, 245.05, 245.6, 735060, null],
    ["2025-09-24T11:00:00", 245.64, 245.66, 244.8, 244.94, 682373, null],
    ["2025-09-24T11:30:00", 244.95, 245.28, 244.6, 245.13, 353800, null],
    ["2025-09-24T12:00:00", 245.12, 245.5, 244.9, 245.4, 254058, null]
  ],
  "closing_price": 245.40,
  "start_time": "2025-09-24 10:30:00",
  "end_time": "2025-09-24 12:00:00",
  "interval_in_minutes": 30
}
Deprecated Historical Method and Data Range Limitsget_historical_candle_data is formally marked deprecated for future removal in favor of get_historical_candles. It accepts trading_symbol, exchange, segment, start_time / end_time (YYYY-MM-DD HH:mm:ss or epoch milliseconds), and optional interval_in_minutes, returning 6-element candle rows [epoch_second, open, high, low, close, volume] without open interest:Python# DEPRECATED: Prefer groww.get_historical_candles()
historical_data_response = groww.get_historical_candle_data(
    trading_symbol="RELIANCE",
    exchange=groww.EXCHANGE_NSE,
    segment=groww.SEGMENT_CASH,
    start_time=start_time,
    end_time=end_time,
    interval_in_minutes=5
)
Maximum duration per request and historical lookback differ markedly between the Backtesting API and the deprecated endpoint:Candle IntervalBacktesting (get_historical_candles) Max Duration & HistoryDeprecated (get_historical_candle_data) Max Duration & History1 min30 days per request; data since 20207 days per request; last 3 months2 min, 3 min30 days per request; data since 2020Not listed5 min30 days per request; data since 202015 days per request; last 3 months10 min90 days per request; data since 202030 days per request; last 3 months15 min, 30 min90 days per request; data since 2020Not listed1 hour (60 min)180 days per request; data since 2020150 days per request; last 3 months4 hours (240 min)180 days per request; data since 2020365 days per request; last 3 months1 day (1440 min)180 days per request; data since 20201080 days (~3 years); full history1 week (10080 min)180 days per request; data since 2020No limit; full history1 month180 days per request; data since 2020Not listed11. Real-Time WebSocket FeedGrowwFeed streams live LTP, index values, market depth, order updates, and F&O position updates over NATS WebSocket using Protobuf payloads. Market-data subscriptions accept an instruments_list of dictionaries (exchange, segment, and exchange_token from the instruments CSV), up to 1,000 instruments subscribed simultaneously.Initialization, Callback Flow, and Polling FlowGrowwFeed supports asynchronous callbacks (on_data_received(meta) triggered after calling the blocking feed.consume() method) or synchronous polling via feed.get_*() methods:Pythonimport time
from growwapi import GrowwAPI, GrowwFeed

API_AUTH_TOKEN = "your_token"
groww = GrowwAPI(API_AUTH_TOKEN)
feed = GrowwFeed(groww)

instruments_list = [
    {"exchange": "NSE", "segment": "CASH", "exchange_token": "2885"},
    {"exchange": "NSE", "segment": "FNO", "exchange_token": "35241"}
]

# Option A: Event-driven callback (feed.consume() blocks execution)
def on_data_received(meta):
    print("Metadata received:", meta)

feed.subscribe_ltp(instruments_list, on_data_received=on_data_received)
feed.consume()
Python# Option B: Synchronous polling without callbacks
feed.subscribe_ltp(instruments_list)

for i in range(10):
    time.sleep(3)
    print(feed.get_ltp())

feed.unsubscribe_ltp(instruments_list)
When callbacks are used, on_data_received(meta) receives a dictionary containing exchange (str, e.g., "NSE", "BSE"), segment (str, e.g., "CASH", "FNO"), feed_type (str, e.g., "ltp", "order_updates", "position_updates"), and feed_key (str, exchange token / feed topic key).Feed Subscriptions MatrixFeed StreamSubscribe MethodPoll MethodUnsubscribe MethodTarget ParameterEquity & Derivatives LTPsubscribe_ltp(instruments_list, on_data_received=None)get_ltp()unsubscribe_ltp(instruments_list)instruments_list (exchange, segment, exchange_token)Index Valuesubscribe_index_value(instruments_list, on_data_received=None)get_index_value()unsubscribe_index_value(instruments_list)instruments_list (e.g., exchange_token="NIFTY" or "1")Market Depthsubscribe_market_depth(instruments_list, on_data_received=None)get_market_depth()unsubscribe_market_depth(instruments_list)instruments_listDerivatives Order Updatessubscribe_fno_order_updates(on_data_received=None)get_fno_order_update()unsubscribe_fno_order_updates()Account-level streamEquity Order Updatessubscribe_equity_order_updates(on_data_received=None)get_equity_order_update()unsubscribe_equity_order_updates()Account-level streamDerivatives Position Updatessubscribe_fno_position_updates(on_data_received=None)get_fno_position_update()unsubscribe_fno_position_updates()Account-level streamFeed Output PayloadsNotice that in market-data response schemas, tsInMillis is documented as int (epoch milliseconds) while example JSON payloads display float notation (1746174479582.0). Representative payloads for each stream are shown below:Equity & F&O LTP (get_ltp):JSON{
  "ltp": {
    "NSE": {
      "CASH": {
        "2885": {"tsInMillis": 1746174479582.0, "ltp": 1419.1}
      },
      "FNO": {
        "35241": {"tsInMillis": 1746174479582.0, "ltp": 26111.10}
      }
    }
  }
}
Indices Live Data (get_index_value):JSON{
  "NSE": {
    "CASH": {
      "NIFTY": {"tsInMillis": 1746174582295.0, "value": 24386.7}
    }
  },
  "BSE": {
    "CASH": {
      "1": {"tsInMillis": 1746174582295.0, "value": 73386.7}
    }
  }
}
Market Depth (get_market_depth, optional buyBook and sellBook dicts keyed by price level):JSON{
  "NSE": {
    "CASH": {
      "2885": {
        "tsInMillis": 1746156600.0,
        "buyBook": {
          "1": {"price": 1418.8, "qty": 113.0},
          "2": {"price": 1418.7, "qty": 23.0},
          "3": {"price": 1418.6, "qty": 206.0},
          "4": {"price": 1418.5, "qty": 774.0},
          "5": {"price": 1418.4, "qty": 1055.0}
        },
        "sellBook": {
          "1": {"price": 1418.9, "qty": 3.0},
          "2": {"price": 1419.0, "qty": 472.0},
          "3": {"price": 1419.3, "qty": 212.0},
          "4": {"price": 1419.4, "qty": 138.0},
          "5": {"price": 1419.5, "qty": 895.0}
        }
      }
    }
  }
}
Derivatives Order Update (get_fno_order_update) and Equity Order Update (get_equity_order_update):JSON{
  "qty": 75,
  "price": "130",
  "filledQty": 75,
  "avgFillPrice": "110",
  "growwOrderId": "GMKFO250214150557M2HR6EJF2HSE",
  "exchangeOrderId": "1400000179694433",
  "orderStatus": "EXECUTED",
  "duration": "DAY",
  "exchange": "NSE",
  "segment": "FNO",
  "product": "NRML",
  "contractId": "NIFTY2522025400CE"
}
JSON{
  "qty": 3,
  "filledQty": 3,
  "avgFillPrice": "145",
  "growwOrderId": "GMK250502123553ZXM5BKVXX9LM",
  "exchangeOrderId": "1100000051248116",
  "orderStatus": "EXECUTED",
  "duration": "DAY",
  "exchange": "NSE",
  "contractId": "INE221H01019"
}
Derivatives Position Update (get_fno_position_update):JSON{
  "symbolIsin": "NIFTY2550824800CE",
  "exchangePosition": {
    "BSE": {},
    "NSE": {
      "creditQty": 300.0,
      "creditPrice": 3555.0,
      "debitQty": 75.0,
      "debitPrice": 5475.0
    }
  }
}
In order updates, contractId represents the ISIN for equities and the contract symbol for derivatives; documented schema fields cover qty (int), filledQty (int), avgFillPrice (str), growwOrderId (str), exchangeOrderId (str), orderStatus (str), duration (str), exchange (str), and contractId (str). In position updates, exchangePosition holds BSE and NSE objects containing creditQty, creditPrice, debitQty, and debitPrice floats.12. User Profile APIget_user_profile() retrieves the authenticated user's account details, exchange permissions, enabled segments, and DDPI status.Pythonfrom growwapi import GrowwAPI

API_AUTH_TOKEN = "your_token"
groww = GrowwAPI(API_AUTH_TOKEN)

user_profile_response = groww.get_user_profile()
print(user_profile_response)
Documented schema fields include an NSE-enabled boolean flag (whose exact key name—along with leading unique account identifier fields—was truncated prior to bse_enabled in the captured documentation), bse_enabled (boolean), ddpi_enabled (boolean, indicating whether Demat Debit and Pledge Instruction is active to permit selling or pledging Demat shares without per-transaction TPIN and OTP), and active_segments (array[string], such as CASH and FNO).13. Annexures and SDK ConstantsThe SDK defines class-level constants on GrowwAPI alongside fixed enumerations for order and instrument states.SDK Constants ReferenceCategorySDK ConstantValueDescriptionExchangeGrowwAPI.EXCHANGE_BSEBSEBombay Stock ExchangeExchangeGrowwAPI.EXCHANGE_NSENSENational Stock ExchangeSegmentGrowwAPI.SEGMENT_CASHCASHRegular equity cash segmentSegmentGrowwAPI.SEGMENT_FNOFNOFutures and Options derivatives segmentOrder TypeGrowwAPI.ORDER_TYPE_LIMITLIMITExact limit price orderOrder TypeGrowwAPI.ORDER_TYPE_MARKETMARKETImmediate market executionOrder TypeGrowwAPI.ORDER_TYPE_STOP_LOSSSLStop-loss limit orderOrder TypeGrowwAPI.ORDER_TYPE_STOP_LOSS_MARKETSL_MStop-loss market orderProductGrowwAPI.PRODUCT_CNCCNCCash and Carry (delivery equity)ProductGrowwAPI.PRODUCT_MISMISMargin Intraday Square-offProductGrowwAPI.PRODUCT_NRMLNRMLRegular margin for overnight positionsTransaction TypeGrowwAPI.TRANSACTION_TYPE_BUYBUYLong / buy positionTransaction TypeGrowwAPI.TRANSACTION_TYPE_SELLSELLShort / sell positionValidityGrowwAPI.VALIDITY_DAYDAYValid until same-day market closeAdditional constants verified across the Annexures, Smart Orders, and Backtesting documentation include CANDLE_INTERVAL_MIN_2 (2minute), CANDLE_INTERVAL_MIN_3 (3minute), CANDLE_INTERVAL_MIN_15, CANDLE_INTERVAL_MIN_30, SMART_ORDER_TYPE_GTT, SMART_ORDER_TYPE_OCO, and SMART_ORDER_STATUS_ACTIVE (the remaining CANDLE_INTERVAL_* entries on the Annexures page were truncated in the captured text).Fixed Enumeration ValuesEnumerationValuesOrder StatusNEW, ACKED, TRIGGER_PENDING, APPROVED, REJECTED, FAILED, EXECUTED, DELIVERY_AWAITED, CANCELLED, CANCELLATION_REQUESTED, MODIFICATION_REQUESTED, COMPLETEDAfter Market Order (AMO) StatusNA, PENDING, DISPATCHED, PARKED, PLACED, FAILED, MARKETInstrument TypeEQ (Equity), IDX (Index), FUT (Futures), CE (Call Option), PE (Put Option)14. Exception HierarchyCustom SDK exceptions are located in growwapi.groww.exceptions and descend from GrowwBaseException:Exception ClassParent ClassAttributesError ScenarioGrowwBaseExceptionExceptionmsg (str)Generic catch-all base class for SDK errorsGrowwAPIExceptionGrowwBaseExceptionmsg (str), code (str)Client-related errors (invalid requests, auth failures)GrowwAPIAuthenticationExceptionGrowwAPIExceptionmsg (str), code (str)Authentication failure with the Groww APIGrowwAPIAuthorisationExceptionGrowwAPIExceptionmsg (str), code (str)Authorization failure (API key lacks required permissions)GrowwAPIBadRequestExceptionGrowwAPIExceptionmsg (str), code (str)Malformed request payload or invalid parametersGrowwAPINotFoundExceptionGrowwAPIExceptionmsg (str), code (str)Requested resource does not existGrowwAPIRateLimitExceptionGrowwAPIExceptionmsg (str), code (str)API rate limit exceeded; requests must be throttledGrowwAPITimeoutExceptionGrowwAPIExceptionmsg (str), code (str)API request timed out due to network or server overloadGrowwFeedExceptionGrowwBaseExceptionmsg (str)Feed connection or subscription errorsGrowwFeedConnectionExceptionGrowwFeedExceptionmsg (str)Failure establishing or maintaining a feed connectionGrowwFeedNotSubscribedExceptionGrowwFeedExceptionmsg (str), topic (str)Attempted to retrieve data for an unsubscribed topic15. SDK ChangelogThe Python SDK Changelog lists releases from [0.0.1] (27 February 2025) through [1.5.0] (3 December 2025): 0.0.1 (27 Feb 2025), 0.0.4 (labeled [0.0.3] in one heading and [0.0.4] in another, 25 Mar 2025), 0.0.5 (21 Apr 2025), 0.0.7 (21 May 2025), 0.0.8 (11 Jun 2025), 0.0.9 (4 Sep 2025), 0.0.10 (22 Sep 2025), 1.0.0 (3 Oct 2025), 1.1.0 (8 Oct 2025), 1.2.0 (29 Oct 2025), 1.3.0 (24 Nov 2025), 1.4.0 (2 Dec 2025), and 1.5.0 (3 Dec 2025).Within the captured changelog notes, 0.0.1 introduced core order management (Market, Limit, Stop Loss, Stop Loss Market), portfolio holdings and positions, NATS WebSocket live feeds, instrument master downloads (Equity, F&O, Currency, ETF), historical candle retrieval, API key authentication, and custom exception classes for Python 3.9+. The 25 March 2025 release added multi-instrument feed support, the order margin API, bulk LTP support, the DataFrame instrument helper, and the segment parameter in get_position_for_trading_symbol, while setting the default page value to 0, renaming get_latest_price_data to get_quote, renaming GrowwClient to GrowwAPI, and fixing order detail retrieval and NATS feed handling. Unversioned captured patch notes from the later release stream also document fixes for parallel-thread feed execution, live-data unsubscribe responses, and Protobuf parsing, alongside documentation additions for the MCX-not-supported note and realised_pnl in positions. Detailed release notes for 0.0.5 and 0.0.7 through 1.5.0 were not present in the captured changelog text.