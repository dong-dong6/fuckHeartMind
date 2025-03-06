import json
import openai
import re
import time
import os
from dotenv import load_dotenv

# 获取当前脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 加载环境变量，强制从.env文件加载
env_path = os.path.join(SCRIPT_DIR, '.env')
load_dotenv(env_path, override=True)

def get_env_var(key):
    """从.env文件获取环境变量"""
    value = os.getenv(key)
    if value is None:
        raise ValueError(f"环境变量 {key} 未在.env文件中找到")
    return value

def validate_response(response, expected_count):
    """验证API返回的答案是否符合要求"""
    try:
        if not response:
            print("响应为空")
            return False
            
        numbers = []
        for num in re.split(r'[,\s]+', response):
            if num.strip():
                try:
                    num_int = int(num.strip())
                    numbers.append(num_int)
                except ValueError:
                    print(f"无效的数字格式: {num}")
                    return False
        
        if len(numbers) != expected_count:
            print(f"答案数量不匹配: 期望 {expected_count}, 实际 {len(numbers)}")
            return False
            
        return True
        
    except Exception as e:
        print(f"验证响应时出错: {str(e)}")
        return False

def process_batch(questions, start_idx, batch_size, instruction):
    """处理一批问题
    Args:
        questions: 问题列表
        start_idx: 起始索引
        batch_size: 批次大小
        instruction: 问卷说明
    Returns:
        当前批次的答案列表
    """
    batch_questions = questions[start_idx:start_idx + batch_size]
    question_count = len(batch_questions)
    
    system_prompt = f"""你是一个测评助手。你的任务是模拟一个普通的大学生完成心理测评量表。

评分说明：
{instruction}

严格要求：
1. 必须输出{question_count}个数字答案
2. 答案必须严格按照每个问题的选项值进行选择
3. 所有数字用单个空格分隔
4. 不允许输出任何其他文字、标点或解释
5. 答案必须反映一个普通大学生的状态
6. 答案要符合实际情况，保持合理性"""

    user_prompt = f"""请对以下{question_count}个问题进行选择（第{start_idx + 1}题到第{start_idx + question_count}题）：

"""
    # 添加问题和选项信息
    for i, q in enumerate(batch_questions, 1):
        user_prompt += f"\n{i}. {q['text']}\n"
        for opt in q['options']:
            user_prompt += f"   {opt['value']}={opt['text']}\n"
    
    max_retries = int(get_env_var('MAX_RETRIES'))
    retry_count = 0
    
    # 设置OpenAI客户端配置
    openai.api_key = get_env_var('OPENAI_API_KEY')
    openai.base_url = get_env_var('OPENAI_BASE_URL')
    
    while retry_count < max_retries:
        try:
            # 调用API
            response = openai.chat.completions.create(
                model=get_env_var('GPT_MODEL'),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=float(get_env_var('TEMPERATURE'))
            )
            
            # 获取结果
            result = response.choices[0].message.content.strip()
            
            # 验证结果
            if validate_response(result, question_count):
                # 将结果转换为答案列表
                answers = []
                for num in re.split(r'[,\s]+', result):
                    if num.strip():
                        try:
                            num_int = int(num.strip())
                            answers.append(str(num_int))
                        except ValueError:
                            continue
                
                if len(answers) == question_count:
                    print(f"成功获取第{start_idx + 1}题到第{start_idx + question_count}题的答案")
                    return answers
                else:
                    print(f"答案数量不匹配：期望 {question_count}，实际 {len(answers)}")
            
            retry_count += 1
            retry_delay = float(get_env_var('RETRY_DELAY'))
            time.sleep(retry_delay)
            
        except Exception as e:
            print(f"第{retry_count + 1}次尝试发生错误：{str(e)}")
            retry_count += 1
            if retry_count >= max_retries:
                return None
            retry_delay = float(get_env_var('RETRY_DELAY'))
            time.sleep(retry_delay)
    
    return None

def process_anwser_with_gpt(questions_file):
    """
    一次性获取所有问题的答案，但分批处理
    Args:
        questions_file: 问卷JSON文件路径，必须传入
    Returns:
        答案列表，每个答案都是字符串类型
    """
    try:
        # 读取问卷数据
        with open(questions_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        questions = data['questions']
        total_questions = len(questions)
        batch_size = int(get_env_var('BATCH_SIZE'))
        
        all_answers = []
        
        # 分批处理问题
        for start_idx in range(0, total_questions, batch_size):
            print(f"\n处理第{start_idx + 1}题到第{min(start_idx + batch_size, total_questions)}题...")
            
            batch_answers = process_batch(
                questions=questions,
                start_idx=start_idx,
                batch_size=batch_size,
                instruction=data['instruction']
            )
            
            if batch_answers:
                all_answers.extend(batch_answers)
            else:
                print(f"处理第{start_idx + 1}题到第{min(start_idx + batch_size, total_questions)}题失败")
                return None
            
            # 批次之间添加延迟，避免请求过于频繁
            batch_delay = float(get_env_var('BATCH_DELAY'))
            time.sleep(batch_delay)
        
        print(f"\n所有答案处理完成，共 {len(all_answers)} 个答案")
        return all_answers
        
    except Exception as e:
        print(f"处理过程发生错误：{str(e)}")
        return None

if __name__ == "__main__":
    print("开始生成SCL-90量表答案...")
    answers = process_anwser_with_gpt()
    
    if answers:
        print("\n答案已生成，开始写入...")
        
        # 将答案写入文件以备份
        output_file = get_env_var('OUTPUT_FILE')
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(answers))
        print(f"答案已保存到 {output_file}")
        
        # 打印localStorage格式的答案
        print("\nLocalStorage格式的答案：")
        storage_key_prefix = get_env_var('STORAGE_KEY_PREFIX')
        for i, answer in enumerate(answers, 1):
            print(f'{storage_key_prefix}{i}: "{answer}"')
            
        print(f"\n共生成 {len(answers)} 个答案")
    else:
        print("\n生成答案失败，请检查网络连接或重试") 