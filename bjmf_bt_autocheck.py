import random
import re
import os
import time
from datetime import datetime
from bs4 import BeautifulSoup

try:
    from curl_cffi import requests
except ImportError:
    import requests

# ==================== 环境变量配置 ====================
def get_env(key, default=""):
    return os.environ.get(key, default)

ClassID = get_env("BJMF_CLASS_ID")
X = get_env("BJMF_LAT")
Y = get_env("BJMF_LNG")
ACC = get_env("BJMF_ACC", "35")
# =====================================================

def modify_decimal_part(num):
    try:
        num = float(num)
        offset = random.uniform(-0.00005, 0.00005)
        return f"{num + offset:.15f}"
    except:
        return str(num)

def start_checkin(cookie_list):
    base_url = "https://bjmf.k8n.cn"
    success_count = 0
    
    for uid, raw_cookie in enumerate(cookie_list):
        if not raw_cookie.strip(): continue
        
        # 提取 SID
        sid_match = re.search(r'remember_student_[^=]*=(\d+)', raw_cookie)
        sid = sid_match.group(1) if sid_match else ""
        
        # 使用 curl_cffi 模拟微信指纹，若无则退回 requests
        try:
            session = requests.Session(impersonate="safari_ios")
        except:
            session = requests.Session()

        # 严格同步你抓包中的微信 Headers
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.66(0x18004237) NetType/4G Language/zh_CN',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
            'Cookie': raw_cookie.strip("'").strip('"'),
            'Connection': 'keep-alive'
        })

        print(f"\n👤 [用户 {uid+1}] SID: {sid} | 正在检索签到任务...")

        try:
            # Step 1: 访问 punchs 列表页
            # 注意：这里我们允许自动重定向 (allow_redirects=True 是默认的)
            list_url = f"{base_url}/student/course/{ClassID}/punchs"
            res_list = session.get(list_url, timeout=15)
            
            final_url = res_list.url
            print(f"  🔗 最终跳转地址: {final_url}")

            # 逻辑判定：
            # 如果发生了 302 跳转，final_url 会包含具体的签到 ID
            # 格式示例: /student/punchs/course/110141/4666899?sid=3245161
            match = re.search(rf'/course/{ClassID}/(\d+)', final_url)
            
            pids = []
            if match:
                pids.append(match.group(1))
            else:
                # 如果没跳转，则在页面内容里搜寻（备用逻辑）
                pids = re.findall(rf'/{ClassID}/(\d{{7,}})', res_list.text)
                pids = list(set(pids))

            if not pids:
                print(f"  ℹ️ 未发现进行中的签到。页面显示: {'--- 还没有数据 ---' if '还没有数据' in res_list.text else '无任务'}")
                continue

            for p_id in pids:
                punch_url = f"{base_url}/student/punchs/course/{ClassID}/{p_id}"
                if sid: punch_url += f"?sid={sid}"
                
                print(f"  🎯 识别到签到 ID: {p_id}，准备提交...")

                # Step 2: 模拟进入签到页（获取 Session 状态）
                session.get(punch_url, timeout=15)

                # Step 3: POST 提交坐标
                # 严格模拟你抓包中的 POST 数据
                lat_val = modify_decimal_part(X)
                lng_val = modify_decimal_part(Y)
                submit_data = {
                    'lat': lat_val,
                    'lng': lng_val,
                    'acc': ACC,
                    'res': ''
                }
                
                session.headers.update({
                    'Referer': punch_url,
                    'Origin': base_url,
                    'Content-Type': 'application/x-www-form-urlencoded'
                })
                
                # 执行提交
                response = session.post(punch_url, data=submit_data, timeout=20)
                
                if "签到成功" in response.text or "ok" in response.text:
                    print(f"  ✅ 成功！坐标: {lat_val}, {lng_val}")
                    success_count += 1
                else:
                    print(f"失败反馈: {response.text[:100]}")

        except Exception as e:
            print(f"运行报错: {str(e)}")

    return success_count

def main():
    print(f"======================================")
    print(f"🚀 班级魔方自动签到 - [302 重定向适配版]")
    print(f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    raw_cookies = get_env("BJMF_COOKIES")
    if not ClassID or not raw_cookies:
        print("变量配置不全")
        return
    
    cookie_list = [c.strip() for c in raw_cookies.replace('&', '\n').split('\n') if c.strip()]
    start_checkin(cookie_list)
    print(f"======================================")

if __name__ == "__main__":
    main()
