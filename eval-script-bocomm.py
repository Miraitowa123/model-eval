import json
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import time
import requests
import traceback

# =========================
# 简单日志函数（统一格式）
# =========================
def log(level, msg):
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] [{level}] {msg}")


# =========================
# 模型调用函数（永远返回结构）
# =========================
def chat_with_deepseek_ai_office(text: str, row_index: int):
    url = "http://12.244.66.225/qwen72b/v1/chat/completions"
    headers = {"Content-Type": "application/json"}

    log("INFO", f"行 {row_index} - 开始模型调用")

    try:
        data = json.loads(text)
    except Exception as e:
        log("ERROR", f"行 {row_index} - 输入不是合法 JSON：{e}")
        return {
            "tool_name": "输入解析失败",
            "tool_args": str(e),
            "raw_response": "",
            "status": "INPUT_ERROR"
        }

    try:
        start = time.time()
        res = requests.post(url, json=data, headers=headers, timeout=30)
        cost = round(time.time() - start, 2)

        status_code = res.status_code
        res_json = res.json()

        message = res_json.get("choices", [{}])[0].get("message", {})
        tool_calls = message.get("tool_calls")

        if tool_calls:
            function = tool_calls[0].get("function", {})
            tool_name = function.get("name", "")
            tool_args = function.get("arguments", "")
            log("INFO", f"行 {row_index} - 模型返回 tool_call，耗时 {cost}s")
        else:
            # 没有调用工具信息，就返回LLM自然语言
            tool_name = ""
            tool_args = message.get("content", "")
            log("INFO", f"行 {row_index} - 模型返回文本，耗时 {cost}s")

        return {
            "tool_name": tool_name,
            "tool_args": tool_args,
            "raw_response": json.dumps(res_json, ensure_ascii=False),
            "status": f"HTTP_{status_code}"
        }

    except Exception as e:
        log("ERROR", f"行 {row_index} - 模型调用异常：{e}")
        return {
            "tool_name": "模型调用失败",
            "tool_args": str(e),
            "raw_response": traceback.format_exc(),
            "status": "REQUEST_ERROR"
        }


# =========================
# 单行处理（顺序安全）
# =========================
def process_row(index, row):
    question = str(row.get("问题", "")).strip()

    log("INFO", f"行 {index} - 开始处理")

    result = chat_with_deepseek_ai_office(question, index)

    log(
        "INFO",
        f"行 {index} - 处理完成 | 状态={result['status']} | 工具={result['tool_name']}"
    )

    return {
        "index": index,
        "问题": question,
        "调用的工具": result["tool_name"],
        "工具识别的参数": result["tool_args"],
        "状态": result["status"],
        "原始响应": result["raw_response"]
    }


# =========================
# 主流程
# =========================
def main():
    input_file = r"D:\Workspace\ai_office\questions\request_body.csv"
    output_file = r"D:\Workspace\ai_office\questions\response_body.xlsx"

    chunksize = 100
    max_workers = 1

    all_results = []

    log("INFO", "程序启动")

    for chunk_idx, chunk in enumerate(
        pd.read_csv(input_file, chunksize=chunksize, encoding="gbk"),
        start=1
    ):
        log("INFO", f"开始处理第 {chunk_idx} 个 chunk（{len(chunk)} 行）")

        if "问题" not in chunk.columns:
            raise ValueError("CSV 中必须包含【问题】列")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(process_row, idx, row)
                for idx, row in chunk.iterrows()
            ]

            for future in futures:
                result = future.result()
                all_results.append(result)

        log("INFO", f"第 {chunk_idx} 个 chunk 处理完成，累计 {len(all_results)} 行")

    # 恢复原始顺序（双保险）
    df = pd.DataFrame(all_results)
    df = df.sort_values("index").drop(columns=["index"])

    log("INFO", "开始写入 Excel")
    df.to_excel(output_file, index=False)

    log("INFO", f"全部完成，总行数：{len(df)}")
    log("INFO", f"结果文件：{output_file}")


if __name__ == "__main__":
    main()