import logging
import time

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

API_URL = "http://localhost:8000"


def make_request(url: str) -> dict:
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        resp = resp.json()
        logging.info(f"{url} response: {str(resp)[:100]}")
        return resp
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
        return None


def main():
    test_metagraph()
    test_weights()


def test_metagraph():
    latest_block = make_request(f"{API_URL}/latest_block")
    block_number = latest_block.get("block")
    if block_number is None:
        logging.error("Could not extract block number from /latest_block response.")
        return

    metagraph = make_request(f"{API_URL}/metagraph")
    if metagraph.get("neurons"):
        logging.info(f"Neurons: {len(metagraph.get('neurons'))}")

    N = 10
    times = []
    for j in range(2):
        start = time.time()
        for i in range(N):
            b = block_number - i
            metagraph = make_request(f"{API_URL}/metagraph/{b}")
            assert metagraph is not None
            assert len(metagraph.get("neurons")) > 0
        elapsed = time.time() - start
        times.append(elapsed)
        logging.info(f"Round {j + 1}: Queried {N} metagraph blocks in {elapsed:.2f} seconds")
    # second time should be much faster
    assert times[1] * 5 < times[0]


def test_weights():
    test_hotkey = "test_hotkey_123"

    # Set weight
    set_payload = {"hotkey": test_hotkey, "weight": 42.0}
    set_resp = requests.put(f"{API_URL}/set_weight", json=set_payload)
    set_resp.raise_for_status()
    logging.info(f"/set_weight response: {set_resp.json()}")

    # Update weight (increment by 8.0)
    update_payload = {"hotkey": test_hotkey, "weight_delta": 8.0}
    update_resp = requests.put(f"{API_URL}/update_weight", json=update_payload)
    update_resp.raise_for_status()
    logging.info(f"/update_weight response: {update_resp.json()}")

    # Fetch raw weights for current epoch
    raw_weights_url = f"{API_URL}/raw_weights"
    raw_resp = requests.get(raw_weights_url)
    raw_resp.raise_for_status()
    raw = raw_resp.json()
    logging.info(f"/raw_weights response: {raw}")

    # Check that our hotkey is present and has the correct weight (42.0 + 8.0 = 50.0)
    logging.info(f"raw weights: {raw['weights']}")
    w = dict(raw.get("weights", {}))
    assert len(w.keys()) == 1
    assert w[test_hotkey] == 50.0
    logging.info(f"Verified hotkey {test_hotkey} has weight {w[test_hotkey]}")


if __name__ == "__main__":
    main()
