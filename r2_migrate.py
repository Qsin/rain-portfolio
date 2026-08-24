#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""将 index.html 引用的腾讯云 COS 视频迁移到 Cloudflare R2。

读取 r2_secret.txt（key=value 格式），把 index.html 里引用的本地视频
上传到 R2（object key 保持原相对路径），并把 index.html 中的 COS URL
前缀整体替换为 R2 公开 URL 前缀。脚本幂等：重复运行只会覆盖上传。

用法:
  python r2_migrate.py --dry     # 只打印计划，不真正上传/改写
  python r2_migrate.py           # 执行上传 + 改写 index.html
"""
import os
import re
import sys
import boto3

ROOT = os.path.dirname(os.path.abspath(__file__))
SECRET_FILE = os.path.join(ROOT, "r2_secret.txt")
INDEX = os.path.join(ROOT, "index.html")
COS_BASE = "https://ovorain-video-1258891501.cos.ap-guangzhou.myqcloud.com/"


def load_secret():
    cfg = {}
    with open(SECRET_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            cfg[k.strip()] = v.strip()
    return cfg


def extract_keys():
    with open(INDEX, encoding="utf-8") as f:
        html = f.read()
    pat = re.escape(COS_BASE) + r'([^\"\'\)\s>]+)'
    keys = re.findall(pat, html)
    seen, out = set(), []
    for k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def main():
    dry = "--dry" in sys.argv
    cfg = load_secret()
    account_id = cfg["account_id"]
    ak = cfg["access_key_id"]
    sk = cfg["secret_access_key"]
    bucket = cfg["bucket"]
    public_base = cfg["public_base"].rstrip("/")
    new_prefix = public_base + "/"

    client = boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=ak,
        aws_secret_access_key=sk,
        region_name="auto",
    )

    keys = extract_keys()
    print(f"待迁移视频数: {len(keys)}")
    for key in keys:
        local = os.path.join(ROOT, key)
        if not os.path.exists(local):
            print(f"  [缺失] 本地找不到: {local} -> 跳过")
            continue
        if dry:
            print(f"  [dry] 将上传: {key}")
            continue
        client.upload_file(local, bucket, key, ExtraArgs={"ContentType": "video/mp4"})
        print(f"  [ok] 已上传: {key}")

    if dry:
        print("dry-run 结束，未做任何改动。")
        return

    with open(INDEX, encoding="utf-8") as f:
        html = f.read()
    new_html, n = re.subn(re.escape(COS_BASE), new_prefix, html)
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(new_html)
    print(f"index.html 已替换 {n} 处 COS 引用 -> {new_prefix}")


if __name__ == "__main__":
    main()
