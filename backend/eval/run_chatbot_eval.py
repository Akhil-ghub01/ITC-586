import json
from pathlib import Path
import time

import requests

API_BASE = "http://127.0.0.1:8000"  # adjust if needed


def call_endpoint(path: str, query: str):
  payload = {
      "query": query,
      "history": []
  }
  start = time.time()
  resp = requests.post(f"{API_BASE}{path}", json=payload, timeout=120)
  latency = time.time() - start
  if resp.status_code != 200:
      return {
          "error": f"status {resp.status_code}",
          "latency_sec": latency,
          "reply": None,
      }
  data = resp.json()
  return {
      "error": None,
      "latency_sec": latency,
      "reply": data.get("reply", ""),
  }


def main() -> None:
  here = Path(__file__).resolve().parent
  test_file = here / "chatbot_testset.json"

  tests = json.loads(test_file.read_text(encoding="utf-8"))

  results = []
  for item in tests:
      qid = item["id"]
      query = item["query"]

      print(f"\n=== {qid} ===")
      print("Q:", query)

      baseline = call_endpoint("/chatbot/query-baseline", query)
      rag = call_endpoint("/chatbot/query", query)

      print("\n[BASELINE]")
      print("Reply:", baseline["reply"])
      print(f"Latency: {baseline['latency_sec']:.2f}s", "(error:" , baseline["error"], ")")

      print("\n[RAG]")
      print("Reply:", rag["reply"])
      print(f"Latency: {rag['latency_sec']:.2f}s", "(error:" , rag["error"], ")")

      results.append(
          {
              "id": qid,
              "query": query,
              "baseline": baseline,
              "rag": rag,
          }
      )

  out_path = here / "chatbot_eval_results.json"
  out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
  print(f"\nSaved raw results to: {out_path}")


if __name__ == "__main__":
  main()
