#!/usr/bin/env python3.11
import sys
import json
import os
from pathlib import Path

# Добавляем путь к боту
BOT_ROOT = '/Users/max/kleinanzeigen_bot'
sys.path.insert(0, os.path.join(BOT_ROOT, 'src'))
sys.path.insert(0, os.path.join(BOT_ROOT, 'tools'))

# Форсируем использование venv-пакетов, если они есть, или путей пользователя
sys.path.insert(0, '/opt/homebrew/lib/python3.11/site-packages')

try:
    from kleinanzeigen_adapter import KleinanzeigenAdapter
    adapter = KleinanzeigenAdapter()
    
    command = sys.argv[1] if len(sys.argv) > 1 else 'list'
    
    if command == 'list':
        ads = adapter.get_my_ads()
        result = []
        for ad in ads:
            result.append({
                "id": ad.id,
                "title": ad.title,
                "price": ad.price,
                "status": ad.status,
                "link": ad.link
            })
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == 'stats':
        stats = adapter.get_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        
    elif command == 'details':
        if len(sys.argv) < 3:
            print(json.dumps({"error": "Missing ad_id"}, ensure_ascii=False))
            sys.exit(1)
        ad = adapter.get_ad(sys.argv[2])
        if ad:
            # Выводим все атрибуты
            import dataclasses
            if dataclasses.is_dataclass(ad):
                print(json.dumps(dataclasses.asdict(ad), ensure_ascii=False, indent=2))
            elif hasattr(ad, "__dict__"):
                print(json.dumps(ad.__dict__, ensure_ascii=False, indent=2, default=str))
            else:
                print(json.dumps(ad, ensure_ascii=False, indent=2, default=str))
        else:
            print(json.dumps({"error": "Ad not found"}, ensure_ascii=False))

except Exception as e:
    print(json.dumps({"error": str(e)}, ensure_ascii=False))
    sys.exit(1)
