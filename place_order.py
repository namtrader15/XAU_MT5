import MetaTrader5 as mt5
from atr_check import atr_stop_loss_finder  # Hàm tính ATR từ MetaTrader 5 (MT5)

# Thông tin tài khoản MT5
MT5_ACCOUNT = 7510016
MT5_PASSWORD = "7lTa+zUw"
MT5_SERVER = "VantageInternational-Demo"

# Hàm kết nối với MT5
def connect_mt5():
    if not mt5.initialize():
        print("Lỗi khi khởi động MT5:", mt5.last_error())
        return False
    
    authorized = mt5.login(MT5_ACCOUNT, password=MT5_PASSWORD, server=MT5_SERVER)
    if not authorized:
        error_code, error_message = mt5.last_error()
        print(f"Lỗi kết nối đến MT5: Mã lỗi {error_code} - {error_message}")
        mt5.shutdown()
        return False
    
    print("Kết nối thành công đến MT5 với tài khoản:", MT5_ACCOUNT)
    return True

# Hàm lấy giá mark từ MT5
def get_realtime_price_mt5(symbol="XAUUSD"):
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        return tick.ask  # Giá mua (ask)
    else:
        print(f"Không thể lấy giá hiện tại cho {symbol}.")
        return None

# Hàm tính khối lượng giao dịch dựa trên mức rủi ro mong muốn
def calculate_volume_based_on_risk(symbol, risk_amount, market_price, stop_loss_price):
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"Không thể lấy thông tin cho {symbol}")
        return None

    # Kích thước hợp đồng giao dịch
    contract_size = symbol_info.trade_contract_size

    # Khoảng cách từ giá vào lệnh đến Stop Loss
    distance = abs(market_price - stop_loss_price)

    # Tính khối lượng giao dịch (Volume)
    volume = risk_amount / (distance * contract_size)

    # Làm tròn volume theo bước lot tối thiểu của broker
    volume_step_decimal_places = len(str(symbol_info.volume_step).split(".")[-1])
    volume = max(symbol_info.volume_min, round(volume, volume_step_decimal_places))
    
    print(f"Volume tính toán: {volume} lots cho rủi ro {risk_amount} USD")
    return volume

# Hàm thực hiện lệnh Market trên MT5 với tính toán volume, Stop Loss và Take Profit
def place_order_mt5(client, order_type, symbol="XAUUSD", risk_amount=60, risk_reward_ratio=1.7):
    global last_order_status
    
    # Lấy giá mark hiện tại từ MT5 để đặt lệnh
    mark_price = get_realtime_price_mt5(symbol="XAUUSD")
    if mark_price is None:
        return

    # Sử dụng hàm ATR để lấy stop_loss dựa trên ATR từ MetaTrader 5 (MT5)
    atr_symbol = "XAUUSD"  # Đổi thành XAUUSD cho MT5
    atr_short_stop_loss, atr_long_stop_loss = atr_stop_loss_finder(atr_symbol)
    
    # Xác định giá trị SL
    if order_type == "buy":
        stop_loss_price = atr_long_stop_loss
    else:
        stop_loss_price = atr_short_stop_loss
    
    # Định dạng giá trị SL thành dạng thập phân
    stop_loss_price = float(f"{stop_loss_price:.2f}")

    # Tính khối lượng giao dịch dựa trên mức rủi ro và giá trị ATR
    volume = calculate_volume_based_on_risk("XAUUSD", risk_amount, mark_price, stop_loss_price)
    if volume is None or volume <= 0:
        print("Số lượng giao dịch không hợp lệ. Hủy giao dịch.")
        return

    # Tính toán Take Profit
    risk_distance = abs(mark_price - stop_loss_price)  # Khoảng cách Risk
    reward_distance = risk_distance * risk_reward_ratio  # Khoảng cách Reward
    
    if order_type == "buy":
        take_profit_price = mark_price + reward_distance
    else:
        take_profit_price = mark_price - reward_distance

    # Định dạng TP thành dạng thập phân
    take_profit_price = float(f"{take_profit_price:.2f}")

    # In các giá trị để kiểm tra
    print(f"Giá hiện tại từ MT5: {mark_price}")
    print(f"Stop Loss dựa trên ATR: {stop_loss_price}")
    print(f"Take Profit: {take_profit_price}")
    print(f"Khối lượng giao dịch: {volume} lots")

    # Thiết lập và gửi lệnh Market trên MT5 với IOC filling mode
    order = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": "XAUUSD",  # Thay đổi symbol thành XAUUSD
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY if order_type == "buy" else mt5.ORDER_TYPE_SELL,
        "price": mark_price,
        "sl": stop_loss_price,  # Giá trị Stop Loss
        "tp": take_profit_price,  # Giá trị Take Profit
        "deviation": 20,
        "magic": 234000,
        "type_filling": mt5.ORDER_FILLING_IOC,  # Chế độ khớp lệnh IOC
    }

    # Gửi lệnh và kiểm tra lỗi
    result = mt5.order_send(order)
    if result is None:
        print("Gửi lệnh thất bại. Kiểm tra các thông số lệnh:")
        print("Order:", order)
        print("Lỗi:", mt5.last_error())
    elif result.retcode != mt5.TRADE_RETCODE_DONE:
        print("Lệnh không thành công. Mã lỗi:", result.retcode)
        print("Thông tin chi tiết:", result)
    else:
        last_order_status = f"Đã {order_type} {volume} lots XAUUSD ở giá {mark_price:.2f} với Stop Loss: {stop_loss_price:.2f} và Take Profit: {take_profit_price:.2f}."
        print(last_order_status)

# Chương trình chính để kiểm tra
if __name__ == "__main__":
    # Khởi tạo Binance client (nếu cần)
    # client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
    
    # Kết nối MT5 và thực hiện lệnh Market mẫu
    if connect_mt5():
        print("Thực hiện lệnh Market với tính toán volume từ mức rủi ro và ATR stop loss.")
        place_order_mt5(None, "buy", "XAUUSD", risk_amount=60)  # Thay symbol thành "XAUUSD"
        mt5.shutdown()
    else:
        print("Không thể kết nối đến MT5.")
