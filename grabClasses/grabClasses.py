import requests
import time
import ddddocr
from bs4 import BeautifulSoup
import execjs
import json
import os

# 登录相关信息
username = "学号"
password = "密码"
# 设置定时查询和预订的时间范围（示例：2024-01-01 11:40:00 到 2024-01-01 12:20:00）
start_time = "2024-11-26 15:20:00"
end_time = "2024-11-26 15:30:00"

# 目标登录网址
login_url = "https://authserver.nuist.edu.cn/authserver/login?service=https://nxdyjs.nuist.edu.cn/gmis5/oauthLogin/njxxgcdx"
captcha_url = "https://authserver.nuist.edu.cn/authserver/getCaptcha.htl?" + str(time.time())
encrypt_js_url = "https://authserver.nuist.edu.cn/authserver/NuistT6Theme/static/common/encrypt.js?v=20240606.193058"
doLogin_url = "https://authserver.nuist.edu.cn/authserver/login?service=https%3A%2F%2Fnxdyjs.nuist.edu.cn%2Fgmis5%2FoauthLogin%2Fnjxxgcdx"
getxscardinfo_url = "https://nxdyjs.nuist.edu.cn/gmis5/student/default/getxscardinfo?_=1732518397364"
xsxx_jbxx_url = "https://nxdyjs.nuist.edu.cn/gmis5/student/grgl/xsxx_jbxx?_=" + str(time.time())
# 查询可选课程和报名课程的URL
list_url = "https://nxdyjs.nuist.edu.cn/gmis5/student/yggl/kwhdbm_list"
signup_url = "https://nxdyjs.nuist.edu.cn/gmis5/student/yggl/kwhdbm_bm"
# 设置请求头
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
}
# 创建会话
session = requests.Session()

# 保存Cookies的文件名
cookies_file = "cookies.json"

def save_cookies(cookies):
    """将Cookies保存到本地文件"""
    with open(cookies_file, "w") as f:
        json.dump(cookies.get_dict(), f)

def load_cookies():
    """从本地文件加载Cookies"""
    if os.path.exists(cookies_file):
        with open(cookies_file, "r") as f:
            cookies = requests.utils.cookiejar_from_dict(json.load(f))
            session.cookies = cookies
            return True
    return False

def login():
    """登录系统并获取登录后的Cookies"""
    # 尝试加载本地Cookies
    if load_cookies():
        try:
            # 验证Cookies是否有效
            xsxx_jbxx_result = session.get(xsxx_jbxx_url)
            xsxx_jbxx_result_json = xsxx_jbxx_result.json()
            if xsxx_jbxx_result_json["jbxx"]["xh"] == username:
                print("使用本地Cookies登录成功")
                return True
        except Exception as e:
            print("本地Cookies失效，重新登录")
            return False

    # 获取登录页面，获取form相关值
    response = session.get(login_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    form = soup.find('form', id='pwdFromId')
    execution = form.find('input', attrs={'name': 'execution'})['value']
    pwdEncryptSalt = form.find('input', attrs={'id': 'pwdEncryptSalt'})['value']

    # 获取图片验证码
    r = session.get(captcha_url)
    img_bytes = r.content

    # 识别图片验证码
    ocr = ddddocr.DdddOcr()
    res = ocr.classification(img_bytes)

    # 读取并编译加密js
    js_content = session.get(encrypt_js_url).text
    ctx = execjs.compile(js_content)
    encrypted = ctx.call("encryptPassword", password, pwdEncryptSalt)

    # 构造登录表单数据
    data = {
        "username": username,
        "password": encrypted,
        "captcha": res,
        "rememberMe": "true",
        "_eventId": "submit",
        "cllt": "userNameLogin",
        "dllt": "generalLogin",
        "ls": "",
        "execution": execution
    }

    # 发送登录请求
    login_result = session.post(doLogin_url, data=data)

    # 验证是否登录成功
    try:
        xsxx_jbxx_result = session.get(xsxx_jbxx_url)
        xsxx_jbxx_result_json = xsxx_jbxx_result.json()
        if xsxx_jbxx_result_json["jbxx"]["xh"] == username:
            print("登录成功")
            save_cookies(session.cookies)  # 保存Cookies到本地
            return True
        else:
            print("登录失败")
            return False
    except Exception as e:
        print("登录失败")
        return False

def get_available_courses():
    """查询可选课程列表"""
    try:
        response = session.post(list_url, headers=headers, json={})
        response.raise_for_status()
        data = response.json()
        return data.get("rows", [])
    except Exception as e:
        print(f"查询课程列表失败: {e}")
        return []

def sign_up_course(course_id):
    """尝试报名指定课程"""
    payload = {"id": course_id}
    try:
        response = session.post(signup_url, headers=headers, data=payload)
        response.raise_for_status()
        result = response.json()
        if result.get("zt") == "0":
            print(f"报名失败：{result.get('msg')}")
        else:
            print("报名成功！")
    except Exception as e:
        print(f"报名请求失败: {e}")

def main():
    # 登录并获取Cookies
    successFlag = login()
    if successFlag == False:
        print("登录失败，请检查用户名或密码是否正确！")
        return

    while True:
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        if current_time >= end_time:
            print("已超出预订时间范围，程序停止。")
            break

        if start_time <= current_time <= end_time:
            # 先循环查询课程
            while True:
                current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                if current_time >= end_time:
                    print("查询课程超时，程序停止。")
                    break

                try:
                    courses = get_available_courses()
                    print("课程列表：" + str(courses))
                    if courses:
                        break
                    else:
                        print("查询课程列表为空，等待3秒后继续查询...")
                        time.sleep(3)
                except Exception as e:
                    print(f"查询课程列表出现异常: {e}")
                    time.sleep(2)

            # 再循环预订课程
            loop_count = 0
            while loop_count < 1000:
                current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                if current_time >= end_time:
                    print("预订课程超时，程序停止。")
                    break

                try:
                    for course in courses:
                        if course["bmrs"] < course["xzrs"]:
                            print(f"找到可报名课程：{course['hdmc']}，开始预订...")
                            sign_up_course(course["id"])
                            return
                        else:
                            print(f"课程 {course['hdmc']} 已满，继续查询...")
                    # 等待几秒再重新查询
                    time.sleep(2)
                    loop_count += 1
                except Exception as e:
                    print(f"预订课程出现异常: {e}")
                    continue

        else:
            time.sleep(1)

if __name__ == "__main__":
    main()
