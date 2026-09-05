#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Публикация Instagram Reels с чистого IP GitHub Actions.
Читает due.json; для каждого элемента, у которого срок наступил и он не done:
хостит mp4 (litterbox) -> создаёт REELS-контейнер (video_url + cover_url) -> ждёт FINISHED -> публикует.
Токен/ig_user_id берутся из переменных окружения (GitHub Secrets). Метки done пишутся обратно в due.json."""
import json, os, time, sys
from datetime import datetime, timezone, timedelta
import requests

TOKEN = os.environ["IG_ACCESS_TOKEN"]
IGID  = os.environ["IG_USER_ID"]
V     = os.environ.get("GRAPH_VERSION", "v21.0")
GRAPH = f"https://graph.facebook.com/{V}"
MSK   = timezone(timedelta(hours=3))
MAX_PER_RUN = int(os.environ.get("MAX_PER_RUN", "3"))  # не заливать залпом весь бэклог
DUE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "due.json")
ROOT  = os.path.dirname(os.path.abspath(__file__))

def now_msk():
    return datetime.now(MSK)

def host_public(path, ttl="72h"):
    """Заливаем файл на litterbox, получаем публичный URL (TTL до 72ч; постим сразу же)."""
    for attempt in range(4):
        try:
            with open(path, "rb") as f:
                r = requests.post(
                    "https://litterbox.catbox.moe/resources/internals/api.php",
                    data={"reqtype": "fileupload", "time": ttl},
                    files={"fileToUpload": f}, timeout=180)
            url = r.text.strip()
            if url.startswith("http"):
                return url
            print(f"  host retry {attempt+1}: {url[:80]}", flush=True)
        except Exception as e:
            print(f"  host err {attempt+1}: {str(e)[:80]}", flush=True)
        time.sleep(5)
    raise RuntimeError(f"host failed: {path}")

def graph_post(path, data):
    r = requests.post(f"{GRAPH}/{path}", data={**data, "access_token": TOKEN}, timeout=120)
    j = r.json()
    if "error" in j:
        raise RuntimeError(f"{path}: {j['error'].get('message')}")
    return j

def graph_get(path, params):
    r = requests.get(f"{GRAPH}/{path}", params={**params, "access_token": TOKEN}, timeout=120)
    return r.json()

def wait_finished(cid):
    for _ in range(60):
        st = graph_get(cid, {"fields": "status_code"}).get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {st}")
        time.sleep(5)
    raise RuntimeError("timeout: контейнер не FINISHED")

def publish(item):
    mp4 = os.path.join(ROOT, item["mp4"])
    if not os.path.exists(mp4):
        raise RuntimeError(f"нет файла {item['mp4']}")
    video_url = host_public(mp4)
    cover_url = None
    cov = item.get("cover")
    if cov and os.path.exists(os.path.join(ROOT, cov)):
        cover_url = host_public(os.path.join(ROOT, cov))
    params = {"media_type": "REELS", "video_url": video_url,
              "caption": item.get("caption", ""), "share_to_feed": "true"}
    if cover_url:
        params["cover_url"] = cover_url
    cid = graph_post(f"{IGID}/media", params)["id"]
    wait_finished(cid)
    return graph_post(f"{IGID}/media_publish", {"creation_id": cid}).get("id")

def main():
    due = json.load(open(DUE, encoding="utf-8"))
    items = due if isinstance(due, list) else due.get("items", [])
    now = now_msk()
    changed = False
    posted = 0
    for it in items:
        if it.get("done"):
            continue
        try:
            when = datetime.strptime(it["when"], "%Y-%m-%d %H:%M").replace(tzinfo=MSK)
        except Exception:
            print(f"пропуск {it.get('id')}: плохой when", flush=True); continue
        if now < when:
            continue
        print(f"ПУБЛИКУЮ {it.get('id')} (слот {it['when']})", flush=True)
        try:
            mid = publish(it)
            it["done"] = True; it["media_id"] = mid; changed = True; posted += 1
            print(f"  OK media_id {mid}", flush=True)
        except Exception as e:
            print(f"  ОШИБКА {it.get('id')}: {str(e)[:160]}", flush=True)
        time.sleep(3)
        if posted >= MAX_PER_RUN:
            print(f"достигнут лимit {MAX_PER_RUN} за запуск — остальное в следующий", flush=True)
            break
    if changed:
        json.dump(due, open(DUE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"готово, опубликовано: {posted}", flush=True)

if __name__ == "__main__":
    main()
