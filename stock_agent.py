import os
import yfinance as yf
import requests
import ujson
from anthropic import Anthropic

# 1. 設定你的追蹤標的與持有股數
portfolio = {
    "2542.TW": {"name": "興富發", "shares": 42200},
    "2618.TW": {"name": "長榮航", "shares": 4000},
    "2887.TW": {"name": "台新新光金", "shares": 17000},
    "3617.TW": {"name": "碩天", "shares": 0}  # 僅追蹤，未持有
}

def fetch_stock_data():
    """使用 yfinance 抓取台股最新的市場公開數據"""
    stock_summary = ""
    total_value = 0

    for ticker, info in portfolio.items():
        stock = yf.Ticker(ticker)
        # 抓取最近一日的歷史數據
        hist = stock.history(period="1d")
        if not hist.empty:
            close_price = hist['Close'].iloc[0]
            stock_summary += f"- {info['name']} ({ticker.replace('.TW', '')}): 收盤價 {close_price:.2f} 元"
            
            if info['shares'] > 0:
                market_value = close_price * info['shares']
                total_value += market_value
                stock_summary += f" (目前持股市值: {market_value:,.0f} 元)\n"
            else:
                stock_summary += "\n"
    
    return stock_summary, total_value

def generate_report():
    """將數據餵給 Claude 進行語意化與紀律分析"""
    stock_summary, total_value = fetch_stock_data()
    
    # 構建提供給 Claude 的提示詞
    prompt = f"""
    你是一個冷靜、理性的個人財務管家。請根據以下台股最新的收盤數據，為我撰寫一份簡短的睡前投資摘要。
    
    【今日市場數據】
    {stock_summary}
    總持有市值估算：{total_value:,.0f} 元
    
    【撰寫嚴格要求】
    1. 簡短回報資產與股價狀態。
    2. 以理性、毫無情緒波動的語氣，用一句話提醒我保持長期投資紀律，不隨單日市場波動起舞。
    3. 總字數嚴格控制在 150 字以內，絕對不要有任何客套、寒暄或結尾問候語。
    """

    # 呼叫 Claude 進行推論 (API 預設不將此資料用於模型訓練)
    client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    response = client.messages.create(
        model="claude-4-6-sonnet-latest",
        max_tokens=250,
        system="你是一個專門服務高資產客戶的理性 AI 財務顧問。說話精準、客觀，不帶感情色彩。",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

def send_to_line(message):
    """將 Claude 產出的報告透過 LINE Messaging API 推播至用戶手機"""
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
            "messages": [
                {
                    "type": "text",
                    "text": message
                }
            ]
        }
        
        # 使用 ujson 進行高效且嚴格的 JSON 序列化
        response = requests.post(url, headers=headers, data=ujson.dumps(payload))
        
        if response.status_code == 200:
            print("✅ 報告已成功推播至 LINE")
        else:
            print(f"❌ LINE 推播失敗，錯誤碼: {response.status_code}, 回應: {response.text}")
    else:
        print("⚠️ 未偵測到完整的 LINE 環境變數，印出本地測試結果：\n", message)

if __name__ == "__main__":
    report = generate_report()
    send_to_line(report)
