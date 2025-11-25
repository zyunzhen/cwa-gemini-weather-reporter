import requests
import streamlit as st
from google import genai
from google.genai import types

# --- 1. 設定與金鑰 (請務必替換為您的實際金鑰) ---
CWA_API_KEY = "CWA-5C636786-F06B-450C-9A28-2DD82C40BC98" 
GEMINI_API_KEY = "AIzaSyAfaJ1h7rv8KrPGG3fejTYkiGNj8Jb2Mec"

# --- Streamlit 頁面設定 ---
st.set_page_config(layout="wide", page_title="AI 氣象報告生成器")
st.title("🤖 PaaS + API-first 氣象報告生成服務")
st.markdown("此應用程式擷取 CWA 天氣數據，並由 Gemini 模型生成溫和的語音報告。")

# --- 選擇城市 ---
# 使用中文城市名稱，這是 CWA F-C0032-001 資料集的正確格式
LOCATION = st.selectbox("選擇城市", ["臺北市", "臺中市", "高雄市"]) 

# 簡短的金鑰檢查
if "您的" in CWA_API_KEY or "YOUR_GEMINI_API_KEY" in GEMINI_API_KEY:
    st.error("🚨 請將 CWA_API_KEY 和 GEMINI_API_KEY 替換為您的實際金鑰。")
    st.stop()


# --- [步驟 1] 從雲端取得資料 (CWA API) ---

@st.cache_data(ttl=600) # 使用 Streamlit 緩存，避免每秒都呼叫 API
def fetch_weather_data(api_key, location):
    """從 CWA API 獲取 36 小時天氣預報資料"""
    st.info("🔄 步驟 1: 正在從中央氣象署獲取資料...")
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={api_key}&locationName={location}"
    # 由於 Streamlit Cloud 部署可能遇到 SSLError，我們加上 verify=False
    res = requests.get(url, verify=False)
    res.raise_for_status() # 檢查 HTTP 狀態碼
    data = res.json()
    
    # 簡化資料，只擷取 LLM 需要的關鍵元素
    location_data = data["records"]["location"][0]
    
    formatted_data = f"城市: {location_data['locationName']} 36小時預報\n"
    for element in location_data["weatherElement"]:
        name = element["elementName"]
        # 只取第一個時間點的預報值 (最近的預報)
        value = element["time"][0]["parameter"]["parameterName"]
        formatted_data += f"{name}: {value}\n"
        
    return formatted_data

# --- [步驟 2] 把資料丟給 LLM 處理 (Gemini) ---

@st.cache_data(ttl=600)
def generate_report(gemini_key, data_string):
    """使用 Gemini API 處理天氣資料並生成報告"""
    st.info("🧠 步驟 2: Gemini 正在分析數據並撰寫報告...")
    try:
        # 初始化 Gemini Client
        client = genai.Client(api_key=gemini_key)
        
        # 設定系統指令 (確保語氣和內容符合作業要求)
        system_instruction = (
            "您是一位專業的天氣報告主播，請根據提供的數據，"
            "以溫和、親切、帶有問候的語氣，為聽眾總結這份天氣預報。"
            "報告中必須包含天氣現象、最高溫、最低溫、降雨機率和舒適度建議。"
            "請以繁體中文撰寫，內容約 50-80 字。"
        )

        # 組合給 LLM 的 Prompt
        prompt = f"請為這份天氣預報數據生成一份溫暖的報告:\n\n---\n{data_string}"

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        return response.text
    except Exception as e:
        # 如果 API 失敗，返回錯誤訊息
        return f"❌ Gemini API 呼叫失敗: {e}"

# --- 執行流程 ---

try:
    # 1. 執行 CWA 資料獲取
    weather_data_string = fetch_weather_data(CWA_API_KEY, LOCATION)
    
    st.subheader(f"✅ 步驟 1: CWA 資料擷取完成 ({LOCATION})")
    st.text_area("原始輸入數據 (送給 LLM 處理)", weather_data_string, height=150)
    st.markdown("---")

    # 2. 執行 LLM 生成報告
    llm_report = generate_report(GEMINI_API_KEY, weather_data_string)
    
    # 3. 輸出 LLM 結果
    st.header("📢 步驟 3: 最終 AI 報告輸出")
    st.markdown("---")
    st.markdown(llm_report)

except Exception as e:
    # 處理頂層錯誤，如網路、解析失敗等
    st.error(f"應用程式執行中發生錯誤: {e}")
