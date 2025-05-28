import requests
import logging

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
    latest_block = make_request(f"{API_URL}/latest_block")
    block_number = latest_block.get("block")
    if block_number is None:
        logging.error("Could not extract block number from /latest_block response.")
        return

    metagraph = make_request(f"{API_URL}/metagraph")
    if metagraph.get("neurons"):
        logging.info(f"Neurons: {len(metagraph.get('neurons'))}")

    import time

    N = 10
    for j in range(3):
        start = time.time()
        for i in range(N):
            b = block_number - i
            metagraph = make_request(f"{API_URL}/metagraph/{b}")
            assert metagraph is not None
            assert len(metagraph.get("neurons")) > 0
        elapsed = time.time() - start
        logging.info(f"Round {j + 1}: Queried {N} metagraph blocks in {elapsed:.2f} seconds")


if __name__ == "__main__":
    main()
