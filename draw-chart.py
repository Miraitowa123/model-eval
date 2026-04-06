import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import json
from collections import defaultdict

matplotlib.rcParams["font.sans-serif"] = ["SimHei", "Arial Unicode MS", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False


def extract_error_code(raw_response):
    """Extract error.code from raw response JSON."""
    if pd.isna(raw_response) or raw_response == "":
        return "unknown_code"
    try:
        data = json.loads(raw_response)
        error = data.get("error", {})
        code = error.get("code")
        if code is None or code == "":
            return "unknown_code"
        return code
    except Exception:
        return "parse_failed"


def main():
    input_file = r"/Users/roxy/Documents/06WorkSpace/modelScope-eval/response_body_final.xlsx"
    output_file = (
        r"/Users/roxy/Documents/06WorkSpace/modelScope-eval/accuracy_chart.png"
    )

    df = pd.read_excel(input_file)

    models = df["模型"].unique()

    # Collect all possible error codes from HTTP_400 responses first
    all_error_codes = set()
    for _, row in df[df["状态"] == "HTTP_400"].iterrows():
        code = extract_error_code(row["原始响应"])
        all_error_codes.add(code)
    all_error_codes = sorted(all_error_codes)

    stats = []
    for model in models:
        model_df = df[df["模型"] == model]
        # Total for accuracy: exclude request errors (REQUEST_ERROR, HTTP_400, HTTP_429)
        # These are request/API level errors, not model capability errors
        model_df_for_accuracy = model_df[
            (model_df["状态"] != "REQUEST_ERROR")
            & (~model_df["状态"].str.startswith("HTTP_4"))
        ]
        total = len(model_df_for_accuracy)
        correct = (
            model_df_for_accuracy["调用的工具"].notna()
            & (model_df_for_accuracy["调用的工具"] != "")
        ).sum()
        accuracy = correct / total * 100 if total > 0 else 0

        empty_tool = model_df["调用的工具"].isna() | (model_df["调用的工具"] == "")
        http429 = (model_df["状态"] == "HTTP_429").sum()
        no_tool_call = ((model_df["状态"] == "HTTP_200") & empty_tool).sum()
        request_error = (model_df["状态"] == "REQUEST_ERROR").sum()

        # Count HTTP_400 errors by error.code
        error_code_counts = defaultdict(int)
        http400_rows = model_df[model_df["状态"] == "HTTP_400"]
        for _, row in http400_rows.iterrows():
            code = extract_error_code(row["原始响应"])
            error_code_counts[code] += 1

        # Build the stats entry
        stat_entry = {
            "model": model,
            "accuracy": accuracy,
            "correct": correct,
            "total": total,
            "http_429": http429,
            "no_tool_call": no_tool_call,
            "request_error": request_error,
        }
        # Add each error code as a column
        for code in all_error_codes:
            stat_entry[code] = error_code_counts.get(code, 0)

        stats.append(stat_entry)

    stats_df = pd.DataFrame(stats)
    stats_df = stats_df.sort_values("accuracy", ascending=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 10))

    colors = plt.cm.RdYlGn(stats_df["accuracy"] / 100)

    bars = ax1.barh(
        stats_df["model"],
        stats_df["accuracy"],
        color=colors,
        edgecolor="black",
        linewidth=0.8,
    )

    for bar, acc, correct, total in zip(
        bars, stats_df["accuracy"], stats_df["correct"], stats_df["total"]
    ):
        width = bar.get_width()
        ax1.text(
            width + 1,
            bar.get_y() + bar.get_height() / 2,
            f"{acc:.1f}% ({correct}/{total})",
            ha="left",
            va="center",
            fontsize=9,
        )

    ax1.set_xlabel("Accuracy (%)", fontsize=12)
    ax1.set_title("【行外】办公助手测试集模型表现", fontsize=14, fontweight="bold")
    ax1.set_xlim(0, 115)
    ax1.axvline(x=80, color="red", linestyle="--", alpha=0.5, label="80%")
    ax1.grid(axis="x", alpha=0.3)
    ax1.legend()

    # Prepare error columns: dynamic based on collected error codes
    error_columns = []
    error_labels_map = {}
    # Add all HTTP_400 error codes first
    for code in all_error_codes:
        error_columns.append(code)
        error_labels_map[code] = code
    # Add the original fixed error categories
    error_columns.extend(["http_429", "no_tool_call", "request_error"])
    error_labels_map["http_429"] = "HTTP_429"
    error_labels_map["no_tool_call"] = "NO_TOOl_CALL"
    error_labels_map["request_error"] = "REQUEST_ERROR"

    # Generate distinct colors
    # Use a colormap for dynamic number of error codes
    from matplotlib import cm
    import numpy as np

    n_colors = len(error_columns)
    colors_stack = matplotlib.colormaps["tab20"](np.linspace(0, 1, n_colors))

    error_data = stats_df[error_columns]
    error_labels = stats_df["model"]

    bottom = [0] * len(error_labels)

    for i, col in enumerate(error_columns):
        color = colors_stack[i] if n_colors > 1 else ["#FF6B6B"]
        ax2.barh(
            error_labels,
            error_data[col],
            left=bottom,
            color=color,
            edgecolor="black",
            linewidth=0.5,
            label=error_labels_map[col],
        )
        bottom = [b + v for b, v in zip(bottom, error_data[col])]

    ax2.set_xlabel("Error Count", fontsize=12)
    ax2.set_title("错误分布情况", fontsize=14, fontweight="bold")
    ax2.legend(loc="lower right", fontsize=9)
    ax2.grid(axis="x", alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    print(f"图表已保存至: {output_file}")

    print("\n========== 统计汇总 ==========")
    # Build header dynamically
    header = f"{'模型':<30} {'准确率':>10} {'正确':>6} {'总计':>6}"
    for code in all_error_codes:
        header += f" {code:>20}"
    header += f" {'http_429':>8} {'未调用工具':>8}"
    print(header)
    print("-" * (30 + 10 + 6 + 6 + sum(21 for _ in all_error_codes) + 8 + 8))
    for _, row in stats_df.sort_values("accuracy", ascending=False).iterrows():
        line = f"{row['model']:<30} {row['accuracy']:>9.1f}% {row['correct']:>6} {row['total']:>6}"
        for code in all_error_codes:
            line += f" {row[code]:>20}"
        line += f" {row['http_429']:>8} {row['no_tool_call']:>8}"
        print(line)


if __name__ == "__main__":
    main()
