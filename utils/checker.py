import os
import asyncio
import random
import logging
import json
from datetime import datetime
from typing import List, Dict
from dataclasses import dataclass

import httpx

from .wallets import WalletGenerator
from .ai import AIFilter
from .pricing import PriceFetcher
from config import Config

@dataclass
class WalletResult:
    address: str
    private_key: str
    chain: str
    total_usdt: float
    tokens: List[Dict]
    score: str
    timestamp: datetime

class WalletChecker:
    def __init__(self, cfg: Config, price_fetcher: PriceFetcher):
        self.networks = cfg.NETWORKS
        self.price_fetcher = price_fetcher

    async def _check_evm(self, addr: str, prices: dict, min_usdt: float) -> List[WalletResult]:
        found = []
        async with httpx.AsyncClient() as client:
            for name, info in self.networks.items():
                if "rpc" not in info:
                    continue
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "alchemy_getTokenBalances",
                    "params": [addr]
                }
                try:
                    r = await client.post(info["rpc"], json=payload, timeout=10)
                    toks = r.json().get("result", {}).get("tokenBalances", [])
                except Exception as e:
                    logging.debug(f"EVM check failed {name}: {e}")
                    continue

                total, tokens = 0.0, []
                for t in toks:
                    try:
                        bal = int(t["tokenBalance"], 16) / 1e18
                    except:
                        continue
                    if bal <= 0:
                        continue
                    key = name.lower().replace(" ", "")
                    price = prices.get(key, {}).get("usd", 0)
                    val = bal * price
                    total += val
                    tokens.append({
                        "symbol": t["contractAddress"][:6] + "…" + t["contractAddress"][-4:],
                        "balance": round(bal, 6),
                        "value_usd": round(val, 2)
                    })

                if total >= min_usdt:
                    score = AIFilter.classify_wallet({
                        "total_usdt": total,
                        "num_tokens": len(tokens),
                        "avg_token_value": total / len(tokens) if tokens else 0,
                        "max_token_value": max([t["value_usd"] for t in tokens]) if tokens else 0
                    })
                    found.append(WalletResult(
                        address=addr,
                        private_key="(hidden)",  # سيُضاف لاحقًا
                        chain=name,
                        total_usdt=round(total, 2),
                        tokens=tokens,
                        score=score,
                        timestamp=datetime.now()
                    ))
        return found

    async def _check_utxo(self, addr: str, prices: dict, min_usdt: float, chain: str) -> List[WalletResult]:
        info = self.networks[chain]
        url = f"{info['api']}/{addr}/balance"
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(url, timeout=10)
            sat = r.json().get("balance", 0)
        except Exception as e:
            logging.debug(f"UTXO check failed {chain}: {e}")
            return []
        bal = sat / 1e8
        val = bal * prices.get(chain.lower(), {}).get("usd", 0)
        if val < min_usdt:
            return []
        score = AIFilter.classify_wallet({
            "total_usdt": val,
            "num_tokens": 1,
            "avg_token_value": val,
            "max_token_value": val
        })
        return [WalletResult(
            address=addr,
            private_key="(hidden)",
            chain=chain,
            total_usdt=round(val, 2),
            tokens=[{
                "symbol": chain.upper(),
                "balance": round(bal, 6),
                "value_usd": round(val, 2)
            }],
            score=score,
            timestamp=datetime.now()
        )]

    async def gen_and_check(self, min_usdt: float, concurrency: int = 1000) -> List[WalletResult]:
        prices = await self.price_fetcher.fetch()
        sem = asyncio.Semaphore(concurrency)
        results: List[WalletResult] = []

        common_mnemonics = [
            "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
            "legal winner thank year wave sausage worth useful legal winner thank yellow",
            "letter advice cage absurd amount doctor acoustic avoid letter advice cage above"
        ]

        async def worker():
            async with sem:
                try:
                    mode = random.choices(["eth", "btc", "hd"], weights=[0.5, 0.2, 0.3])[0]

                    if mode == "eth":
                        addr, priv = WalletGenerator.generate_eth()
                        found = await self._check_evm(addr, prices, min_usdt)
                    elif mode == "btc":
                        addr, priv = WalletGenerator.generate_btc()
                        found = await self._check_utxo(addr, prices, min_usdt, "Bitcoin")
                    else:
                        mnemonic = random.choice(common_mnemonics)
                        addr, priv = WalletGenerator.generate_hd(mnemonic, coin="ETH")
                        found = await self._check_evm(addr, prices, min_usdt)

                    for w in found:
                        w.private_key = priv
                        results.append(w)
                except Exception as e:
                    logging.warning(f"Worker error: {e}")

        await asyncio.gather(*[worker() for _ in range(concurrency)])
        logging.info(f"gen_and_check completed, found {len(results)} wallets")

        # حفظ النتائج
        output = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results": [w.__dict__ for w in results]
        }

        try:
            if os.path.exists("results.json"):
                with open("results.json", "r", encoding="utf-8") as f:
                    existing = json.load(f)
                existing.append(output)
            else:
                existing = [output]
        except Exception as e:
            logging.warning(f"Failed to load results.json: {e}")
            existing = [output]

        with open("results.json", "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)

        return results