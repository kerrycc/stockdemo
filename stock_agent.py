import os
import yfinance as yf
import requests
import ujson
from anthropic import Anthropic

# 1. 設定你的追蹤標的與持有股數
portfolio = {
    "0056.TW": {"name": "元大高股息", "shares": 8000},
    "009816.TW": {"name": "凱基50", "shares": 5000},
    "1402.TW": {"name": "遠東新", "shares": 2000},
    "2542.TW": {"name": "興富發", "shares": 42200},
    "2618.TW": {"name": "長榮航", "shares": 4000},
    "2887.TW": {"name": "台新新光金", "shares": 17000},
    "3617.TW": {"name": "碩天", "shares": 0}  # 僅追蹤，未持有
}

def fetch_stock_data():
    """抓取台股市場數據，並計算漲幅與當天損益"""
    stock_summary = ""
    total_market_value = 0
    total_daily_pnl = 0  # 當日總損益

    for ticker, info in portfolio.items():
        stock = yf.Ticker(ticker)
        # 修改為抓取最近 5 天的數據，確保能安全拿到前一個交易日的收盤價
        hist = stock.history(period="5d")
        
        if len(hist) >= 2:
            # 倒數第一筆為今日收盤，倒數第二筆為昨日收盤
            today_close = hist['Close'].iloc[-1]
            yesterday_close = hist['Close'].iloc[-2]
            
            # 計算漲幅百分比
            change_percent = ((today_close - yesterday_close) / yesterday_close) * 100
            
            # 格式化個別股票基本回報
            stock_summary += f"- {info['name']} ({ticker.replace('.TW', '')}): {today_close:.2f} 元 (漲跌幅: {change_percent:+.2f}%)"
            
            # 如果有持股，計算當天損益與目前市值
            if info['shares'] > 0:
                daily_pnl = (today_close - yesterday_close) * info['shares']
                market_value = today_close * info['shares']
                
                total_market_value += market_value
                total_daily_pnl += daily_pnl
                
                stock_summary += f" [持股今日損益: {daily_pnl:+,.0f} 元 / 市值: {market_value:,.0f} 元]\n"
            else:
                stock_summary += "\n"
                
    return stock_summary, total_market_value, total_daily_pnl

def generate_report():
    """將包含漲幅與損益的數據餵給 Claude 進行語意化分析"""
    stock_summary, total_market_value, total_daily_pnl = fetch_stock_data()
    
    prompt = f"""
    你是一個冷計、理性的個人財務管家。請根據以下台股最新的收盤數據（包含漲跌幅與持股當日損益），為我撰寫一份簡短的睡前投資摘要。
    
    【今日市場數據】
    {stock_summary}
    【整體資產狀態】
    持股總市值估算：{total_market_value:,.0f} 元
    今日資產總變動（損益）：{total_daily_pnl:+,.0f} 元
    
    【撰寫嚴格要求】
    1. 簡短回報個別股票的漲跌與資產整體的單日損益變動。
    2. 以理性、毫無情緒波動的語氣，用一句話提醒我保持長期投資紀律，不受單日損益數字大小而影響心情。
    3. 總字數嚴格控制在 200 字以內，絕對不要有任何客套、寒暄或結尾問候語。
    """

    # 呼叫 Claude 3.5 Sonnet
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-3-5-sonnet-latest", 
        max_tokens=300, # 稍微調高一些，留空間給符號與正負號的 Token 消耗
        system="你是一個專門服務高資產客戶的理性 AI 財務顧問。說話精準、客觀，不帶感情色彩。",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

def send_to_line(message):
    """將報告透過 LINE 推播"""
    line_token = os.environ.get("LINE_ACCESS_TOKEN")
    line_user_id = os.environ.get("LINE_USER_ID")
    
    if line_token and line_user_id:
        url = "https://api.line.me/v2/bot/message/push"
        headers = {
            "Authorization": f"Bearer {line_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "to": line_user_id,
            "messages": [{"type": "text", "text": message}]
        }
        response = requests.post(url, headers=headers, data=ujson.dumps(payload))
        if response.status_code == 200:
            print("✅ 報告已成功推播至 LINE")
        else:
            print(f"❌ LINE 推播失敗，錯誤碼: {response.status_code}")
    else:
        print("⚠️ 未偵測到 LINE 金鑰，測試結果：\n", message)

if __name__ == "__main__":
    report = generate_report()
    send_to_line(report)