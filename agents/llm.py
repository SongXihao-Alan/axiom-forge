"""
统一 LLM 客户端:支持 MiniMax-M3,也可平滑切换到其他 OpenAI 兼容服务。
"""
from __future__ import annotations
import os
import json
import httpx
from typing import List, Dict, Any


class M3Client:
    def __init__(self, model: str | None = None, temperature: float = 0.3):
        self.api_key = os.environ["MINIMAX_API_KEY"]
        self.base_url = os.environ.get("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1").rstrip("/")
        self.model = model or os.environ.get("MINIMAX_MODEL", "MiniMax-M3")
        self.temperature = temperature

    def chat(
        self,
        messages: List[Dict[str, str]],
        json_mode: bool = False,
        max_tokens: int = 2048,
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        with httpx.Client(timeout=300) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        return data["choices"][0]["message"]["content"]

    def chat_json(self, system: str, user: str, max_tokens: int = 2048) -> Dict[str, Any]:
        """便捷 JSON 模式调用。
        M3 默认会先吐 <think>...</think>,然后才输出最终 JSON;
        先剥掉 think 块,再尝试解析。
        """
        import re

        # 在 user 末尾追加强约束,让 M3 把 JSON 放在唯一一行
        user_augmented = (
            user.rstrip()
            + "\n\n===REMINDER===\n"
            "把你的最终答案——并且**只**有最终答案——作为一个 JSON 对象输出。"
            "不要把 JSON 包在 ```json``` 里;不要输出任何额外解释。"
        )
        raw = self.chat(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user_augmented}],
            json_mode=True,
            max_tokens=max_tokens,
        )

        # 1) 删掉所有 <think>...</think> 块
        cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

        # 2) 去 ```json ... ``` 围栏(有的模型会自己加)
        # 注意:不能用 .*? 非贪婪——JSON 里有多个 },非贪婪会卡在第一个
        fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, flags=re.DOTALL)
        if fence:
            cleaned = fence.group(1).strip()

        # 3) 尝试严格解析
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 4) 兜底:从 cleaned 中截取第一个 { 到最后一个 }
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = cleaned[start : end + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                pass

        return {"_raw": raw, "_cleaned": cleaned}
