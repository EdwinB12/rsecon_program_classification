"""Check submission URLs for Oxford Abstracts event and save valid ones."""

import time

import httpx

BASE_URL = "https://virtual.oxfordabstracts.com/event/75166/submission"
OUTPUT_FILE = "valid_urls.txt"

if __name__ == "__main__":
    with open(OUTPUT_FILE, "w") as f:
        for i in range(2, 3):
            url = f"{BASE_URL}/{i:03d}"
            try:
                response = httpx.get(url, timeout=10)
                print(response.text)
                f.write(response.text + "\n")
                if "Submission not found" not in response.text:
                    print(f"[FOUND] {url}")
                    f.write(url + "\n")
                    f.flush()
                else:
                    print(f"[NOT FOUND] {url}")
            except httpx.HTTPError as e:
                print(f"[ERROR] {url}: {e}")
            time.sleep(1)

            if i > 1:
                break

    print(f"\nDone. Valid URLs written to {OUTPUT_FILE}")
