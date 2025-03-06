import time
import json
import requests
from bs4 import BeautifulSoup
from DrissionPage import Chromium, ChromiumOptions
from dotenv import load_dotenv
import os
import pathlib
import sys
import random

# 获取当前脚本所在目录
SCRIPT_DIR = pathlib.Path(__file__).parent.absolute()

# 加载环境变量，强制从.env文件加载
env_path = os.path.join(SCRIPT_DIR, '.env')
load_dotenv(env_path, override=True)

def get_env_var(key):
    """从.env文件获取环境变量"""
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"环境变量 {key} 未在.env文件中找到")
    return value

def get_ai_response(question, instruction=None):
    """调用AI获取答案"""
    api_url = get_env_var('AI_API_ENDPOINT')
    api_key = get_env_var('AI_API_KEY')
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    prompt_template = get_env_var('AI_PROMPT_TEMPLATE')
    
    prompt = prompt_template.format(
        instruction=instruction,
        question=question
    )
    
    try:
        response = requests.post(api_url, 
                               json={
                                   "model": get_env_var('AI_MODEL'),
                                   "messages": [
                                       {"role": "user", "content": prompt}
                                   ]
                               },
                               headers=headers)
        
        if response.status_code == 200:
            response_data = response.json()
            try:
                return response_data['choices'][0]['message']['content'].strip()
            except (KeyError, IndexError):
                print(f"API响应格式异常: {response.text}")
                return None
        
        print(f"API响应异常: {response.text}")
        return None
    
    except Exception as e:
        print(f"AI请求出错：{e}")
        return None

# 创建浏览器配置对象
co = ChromiumOptions()
co.set_argument('--incognito')  # 设置无痕模式

# 创建浏览器对象
browser = Chromium(co)

# 获取标签页对象
tab = browser.latest_tab

try:
    # 从环境变量获取登录URL
    login_url = get_env_var('LOGIN_URL')
    tab.get(login_url)

    username = get_env_var('USERNAME')
    password = get_env_var('PASSWORD')

    # 使用更精确的元素定位方式
    tab('tag:input@@placeholder:ID / 学工号 / 编号 / 手机号').input(username)
    tab('tag:input@type=password').input(password)
    tab('tag:button@class=ivu-btn ivu-btn-primary ivu-btn-large').click()

    # 等待登录成功后的元素出现
    tab.wait.ele_displayed('tag:a@@href=/vue/school/student', timeout=1)
    time.sleep(float(get_env_var('PAGE_LOAD_DELAY')))

    # 点击进入系统链接
    tab('tag:div@class=logined').ele('tag:a@@href=/vue/school/student').click()
    time.sleep(float(get_env_var('PAGE_LOAD_DELAY')))

    # 点击进入系统链接
    tab.ele('tag:a@@href=/vue/school/student/puce').click()

    # 开始监听网络请求
    api_endpoint = get_env_var('API_ENDPOINT')
    tab.listen.start(api_endpoint)
    packet = tab.listen.wait(timeout=int(get_env_var('API_TIMEOUT')))
    tab.refresh()

    if packet:
        response_data = packet.response.body
        print(f"接口响应数据：{response_data}")
        
        if not isinstance(response_data, dict) or 'data' not in response_data:
            print("接口数据格式错误")
            sys.exit(1)

        # 遍历所有问卷
        for test_info in response_data['data']:
            test_id = str(test_info['id'])
            test_name = test_info['name']
            print(f"\n开始处理问卷：{test_name}（ID: {test_id}）")
            
            time.sleep(float(get_env_var('PAGE_LOAD_DELAY')))
            
            try:
                test_button = tab(f'tag:li@@text():{test_name}').ele('tag:button')
                test_button.click()
                time.sleep(float(get_env_var('PAGE_LOAD_DELAY')))
                
                html_content = tab.html
                soup = BeautifulSoup(html_content, 'html.parser')
                
                instruction_text = soup.select_one('#lb-zhidaoyu .lang').text.strip()
                
                questions = []
                for question_div in soup.select('.q'):
                    question_text = question_div.select_one('.am-panel-hd .lang').text.strip()
                    question_id = question_div.get('id', '').replace('q_', '')
                    
                    # 解析选项
                    options = []
                    for option_li in question_div.select('.q-answer ul li'):
                        option_input = option_li.select_one('input[type="radio"]')
                        option_text = option_li.select_one('.lang').text.strip()
                        if option_input:
                            option_value = option_input.get('value')
                            options.append({
                                'text': option_text,
                                'value': option_value
                            })
                    
                    # 构建问题对象
                    question_obj = {
                        'id': question_id,
                        'text': question_text,
                        'options': options
                    }
                    questions.append(question_obj)
                
                print(f"共找到 {len(questions)} 个问题")
                
                result = {
                    'instruction': instruction_text,
                    'questions': questions
                }
                
                temp_json_file = f'questions_{test_id}.json'
                with open(temp_json_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                print(f"问题已保存到临时文件：{temp_json_file}")
                
                from gpt_process import process_anwser_with_gpt
                answers = process_anwser_with_gpt(temp_json_file)
                
                if answers:
                    print(f"\n开始写入问卷 {test_name} 的答案...")
                    
                    start_button = tab('tag:input@class=am-btn am-btn-success am-btn-sm btn-start')
                    if start_button:
                        start_button.click()
                        print("已点击开始按钮")
                        time.sleep(float(get_env_var('PAGE_LOAD_DELAY')))
                        
                        print(f"\n问卷 {test_name} 的答案：")
                        for i, answer in enumerate(answers, 1):
                            print(f"第{i}题答案: {answer}")
                            try:
                                question_div = tab(f'tag:div@id=q_{i}')
                                if question_div:
                                    radio_button = question_div(f'tag:input@value={answer}')
                                    if radio_button:
                                        radio_button.click()
                                        wait_time = random.uniform(
                                            float(get_env_var('MIN_ANSWER_DELAY')),
                                            float(get_env_var('MAX_ANSWER_DELAY'))
                                        )
                                        print(f"已点击第{i}题的选项{answer}，等待{wait_time:.1f}秒")
                                        time.sleep(wait_time)
                                    else:
                                        print(f"未找到第{i}题的选项{answer}，尝试随机选择...")
                                        # 获取所有可用选项
                                        available_options = question_div('tag:input@type=radio')
                                        if available_options:
                                            random_option = random.choice(available_options)
                                            random_value = random_option.attr('value')
                                            random_option.click()
                                            wait_time = random.uniform(
                                                float(get_env_var('MIN_ANSWER_DELAY')),
                                                float(get_env_var('MAX_ANSWER_DELAY'))
                                            )
                                            print(f"已随机选择第{i}题的选项{random_value}，等待{wait_time:.1f}秒")
                                            time.sleep(wait_time)
                                        else:
                                            print(f"第{i}题没有找到任何可选项")
                                else:
                                    print(f"未找到第{i}题的div元素")
                            except Exception as e:
                                print(f"点击第{i}题选项时出错：{str(e)}")
                        
                        print(f"\n共完成 {len(answers)} 个答案的选择")
                        print("请检查答案并点击'做完了'")
                        i = input("确认完成后请按回车键继续...")
                    else:
                        print("未找到开始按钮，请检查页面状态")
                else:
                    print(f"获取问卷 {test_name} 的答案失败")
                
                tab.back()
                time.sleep(float(get_env_var('PAGE_LOAD_DELAY')))
                
            except Exception as e:
                print(f"处理问卷 {test_name} 时发生错误：{str(e)}")
                tab.back()
                time.sleep(float(get_env_var('PAGE_LOAD_DELAY')))
                continue
            
        print("\n所有问卷处理完成")
    
    time.sleep(float(get_env_var('FINAL_DELAY')))

finally:
    browser.quit()
