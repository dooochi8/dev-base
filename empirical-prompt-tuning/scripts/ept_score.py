import json
import sys


def read_input():
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            return json.load(f)
    return json.load(sys.stdin)


def result_score(result):
    if result == "ok":
        return 1.0
    if result == "partial":
        return 0.5
    return 0.0


def validate_scenario(scenario):
    if not isinstance(scenario, dict):
        raise ValueError("シナリオはオブジェクトで指定してください")
    name = scenario.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("シナリオ名は空でない文字列にしてください")
    requirements = scenario.get("requirements")
    if not isinstance(requirements, list) or not 3 <= len(requirements) <= 7:
        raise ValueError("各シナリオに固定要件を3〜7項目指定してください")
    texts = set()
    for req in requirements:
        if not isinstance(req, dict):
            raise ValueError("各要件はオブジェクトで指定してください")
        text = req.get("text")
        if not isinstance(text, str) or not text.strip() or text.strip() in texts:
            raise ValueError("要件のtextには空でない一意な固定文言を指定してください")
        texts.add(text.strip())
        if type(req.get("critical")) is not bool or req.get("result") not in ("ok", "partial", "ng"):
            raise ValueError("要件にはcriticalの真偽値とok/partial/ngを指定してください")
    if not any(r["critical"] for r in requirements):
        raise ValueError("critical要件がありません")
    for key in ("tool_uses", "duration_ms", "retries", "new_unclear"):
        if type(scenario.get(key)) is not int or scenario[key] < 0:
            raise ValueError("実測値の欠測を0として埋めず、非負の整数を指定してください")
    return [(r["critical"], r["text"]) for r in requirements]


def validate_input(data):
    if not isinstance(data, dict) or not isinstance(data.get("iterations"), list) or not data["iterations"]:
        raise ValueError("iterationsには実行結果を1回以上指定してください")
    baseline = None
    for iteration in data["iterations"]:
        if not isinstance(iteration, dict):
            raise ValueError("各回はオブジェクトで指定してください")
        scenarios = iteration.get("scenarios")
        if not isinstance(scenarios, list) or len(scenarios) < 2:
            raise ValueError("各回に2本以上のシナリオが必要です")
        signature = {}
        for scenario in scenarios:
            fixed_requirements = validate_scenario(scenario)
            name = scenario["name"].strip()
            if name in signature:
                raise ValueError("シナリオ名は一意にしてください")
            signature[name] = fixed_requirements
        if baseline is not None and signature != baseline:
            raise ValueError("シナリオと固定要件が前回から変わっています")
        baseline = signature
    if "holdout" in data:
        validate_scenario(data["holdout"])
        if data["holdout"]["name"].strip() in baseline:
            raise ValueError("holdoutには通常評価で使っていないシナリオ名を指定してください")


def scenario_metrics(scenario):
    requirements = scenario.get("requirements", [])
    critical = [r for r in requirements if r.get("critical") is True]
    success = bool(critical) and all(r.get("result") == "ok" for r in critical)
    if requirements:
        accuracy = sum(result_score(r.get("result")) for r in requirements) / len(requirements) * 100.0
    else:
        accuracy = 0.0
    return success, accuracy


def iteration_summary(iteration):
    scenarios = iteration.get("scenarios", [])
    count = len(scenarios)
    accuracies = []
    steps = 0
    duration = 0
    unclear = 0
    for scenario in scenarios:
        _, accuracy = scenario_metrics(scenario)
        accuracies.append(accuracy)
        steps += int(scenario.get("tool_uses", 0))
        duration += int(scenario.get("duration_ms", 0))
        unclear += int(scenario.get("new_unclear", 0))
    avg_accuracy = sum(accuracies) / count if count else 0.0
    return {
        "accuracy": avg_accuracy,
        "steps": steps,
        "duration": duration,
        "unclear": unclear,
        "success": count >= 2 and all(scenario_metrics(s)[0] for s in scenarios),
    }


def holdout_summary(final_iteration, scenario):
    success, accuracy = scenario_metrics(scenario)
    reference = iteration_summary(final_iteration)["accuracy"]
    drop = reference - accuracy
    return {
        "accuracy": accuracy,
        "reference_accuracy": reference,
        "drop": drop,
        "success": success,
        "passed": success and drop < 15.0,
    }


def pct(value):
    if value == int(value):
        return str(int(value)) + "%"
    return ("%.1f" % value) + "%"


def change_within(previous, current, limit):
    if previous == 0:
        return current == 0
    change = abs(current - previous) / previous * 100.0
    return change <= limit


def transition_clear(previous, current):
    accuracy_improvement = current["accuracy"] - previous["accuracy"]
    checks = {
        "critical要件を全件達成": previous["success"] and current["success"],
        "新規不明瞭点0件": current["unclear"] == 0,
        "精度悪化なし・改善+3pt以下": 0 <= accuracy_improvement <= 3.0,
        "steps±10%": change_within(previous["steps"], current["steps"], 10.0),
        "duration±15%": change_within(previous["duration"], current["duration"], 15.0),
    }
    return checks, all(checks.values())


def mark(ok):
    return "○" if ok else "×"


def main():
    data = read_input()
    validate_input(data)
    iterations = data.get("iterations", [])

    print("## シナリオ別結果")
    print()
    print("| Iteration | シナリオ | 成功/失敗 | 精度 | steps | duration_ms | retries | new_unclear |")
    print("|---|---|---|---:|---:|---:|---:|---:|")
    for index, iteration in enumerate(iterations, 1):
        for scenario in iteration.get("scenarios", []):
            success, accuracy = scenario_metrics(scenario)
            print(
                "| %s | %s | %s | %s | %s | %s | %s | %s |"
                % (
                    index,
                    scenario.get("name", ""),
                    mark(success),
                    pct(accuracy),
                    int(scenario.get("tool_uses", 0)),
                    int(scenario.get("duration_ms", 0)),
                    int(scenario.get("retries", 0)),
                    int(scenario.get("new_unclear", 0)),
                )
            )

    holdout_ok = True
    if "holdout" in data:
        holdout = holdout_summary(iterations[-1], data["holdout"])
        holdout_ok = holdout["passed"]
        print()
        print("## hold-out 判定")
        print()
        print("| シナリオ | critical全件達成 | 精度 | 直近通常平均 | 低下pt | 判定 |")
        print("|---|---|---:|---:|---:|---|")
        print("| %s | %s | %s | %s | %.1f | %s |" % (
            data["holdout"]["name"], mark(holdout["success"]), pct(holdout["accuracy"]),
            pct(holdout["reference_accuracy"]), holdout["drop"], mark(holdout_ok)))

    print()
    print("## 収束判定")
    print()
    print("| 条件 | 判定 |")
    print("|---|---|")
    converged = False
    if len(iterations) < 2:
        print("| 新規不明瞭点0件 | × |")
        print("| critical要件を全件達成 | 未判定 |")
        print("| 精度悪化なし・改善+3pt以下 | × |")
        print("| steps±10% | × |")
        print("| duration±15% | × |")
        print("| 連続クリア回数 | 0/2 |")
    else:
        summaries = [iteration_summary(iteration) for iteration in iterations]
        checks, latest_clear = transition_clear(summaries[-2], summaries[-1])
        consecutive = 0
        position = len(summaries) - 1
        while position > 0 and consecutive < 2:
            _, ok = transition_clear(summaries[position - 1], summaries[position])
            if not ok:
                break
            consecutive += 1
            position -= 1
        for label in ["critical要件を全件達成", "新規不明瞭点0件", "精度悪化なし・改善+3pt以下", "steps±10%", "duration±15%"]:
            print("| %s | %s |" % (label, mark(checks[label])))
        print("| 連続クリア回数 | %s/2 |" % consecutive)
        converged = latest_clear and consecutive >= 2
    print("| hold-out | %s |" % (mark(holdout_ok) if "holdout" in data else "未実施（重要なskillでは必須）"))
    print("| 総合判定 | %s |" % mark(converged and holdout_ok))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, TypeError, AttributeError, OSError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        sys.exit(1)
