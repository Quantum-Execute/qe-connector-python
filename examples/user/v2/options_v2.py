"""Inspect a published option and preview an order; --submit explicitly submits.

Run from the repository root after installing the SDK with pip install -e .:
python examples/user/v2/options_v2.py --symbol YOUR_PUBLISHED_OPTION_SYMBOL \
    --quantity 10 --premium-limit 0.125
"""
import argparse
import json
import os

from qe.lib.trading_v2_types import CreateMasterOrderV2Request
from qe.pub import Pub
from qe.user import User


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True, help="Full name from the published OPTION list")
    parser.add_argument("--quantity", required=True, help="Base-asset quantity, not contracts")
    parser.add_argument("--premium-limit", required=True, help="Premium per base asset, in USDC/BTC/ETH")
    parser.add_argument("--side", choices=["buy", "sell"], default="buy")
    parser.add_argument("--submit", action="store_true", help="Submit a real order using QE_API_KEY/QE_API_SECRET/QE_EXCHANGE_API_KEY_ID")
    args = parser.parse_args()
    base_url = os.getenv("QE_BASE_URL", "https://api.quantumexecute.com")
    public = Pub(base_url=base_url)
    try:
        reply = public.trading_pairs_v2(exchange="Deribit", marketType="OPTION", symbol=args.symbol)
    finally:
        public.session.close()
    items = reply.get("items", [])
    if len(items) != 1 or items[0]["symbol"] != args.symbol or not items[0].get("rulesReady") or items[0].get("status") == "EXPIRED":
        raise SystemExit("Published active option with executable price rules required")
    print("Contract rules:")
    print(json.dumps(items[0], indent=2))
    request = CreateMasterOrderV2Request(
        apiKeyId=os.getenv("QE_EXCHANGE_API_KEY_ID", "YOUR_EXCHANGE_API_KEY_ID"),
        exchange="Deribit", marketType="OPTION", symbol=args.symbol,
        side=args.side, algorithm="TWAP", executionDurationSeconds=1800,
        totalQuantity=args.quantity, worstPrice=args.premium_limit,
        mustComplete=False, tailOrderProtection=False,
    )
    print("Order preview (the server will revalidate quantity, ticks and expiry):")
    print(json.dumps(request.to_payload(), indent=2))
    if not args.submit:
        print("Preview only. Add --submit to place this order.")
        return
    for key in ("QE_API_KEY", "QE_API_SECRET", "QE_EXCHANGE_API_KEY_ID"):
        if not os.getenv(key):
            raise SystemExit(f"Missing {key}")
    client = User(os.environ["QE_API_KEY"], os.environ["QE_API_SECRET"], base_url=base_url)
    try:
        result = client.create_master_order_v2(request)
        print(json.dumps(result, indent=2))
    finally:
        client.session.close()


if __name__ == "__main__":
    main()
