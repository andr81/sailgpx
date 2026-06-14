import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
from sailrecall.core import find_similar, score, _card_match, _bucket_match

fail = 0
def check(c, m):
    global fail
    if not c:
        print("FAIL:", m); fail = 1

check(_card_match("W", "W") == 2, "card same")
check(_card_match("W", "NW") == 1, "card adjacent")
check(_card_match("W", "E") == 0, "card opposite")
check(_bucket_match("10-15", "10-15") == 2, "bucket same")
check(_bucket_match("10-15", "5-10") == 1, "bucket adjacent")
check(_bucket_match("10-15", "20+") == 0, "bucket far")

index = {"races": {
    "r-exact": {"venue": "minskoe-more", "wind_dir_card": "W", "wind_bucket": "10-15",
                "course_type": "windward-leeward", "class": "Laser", "distance_nm": 5.0, "date": "2025-06-01"},
    "r-close": {"venue": "minskoe-more", "wind_dir_card": "NW", "wind_bucket": "5-10",
                "course_type": "windward-leeward", "class": "Laser", "distance_nm": 4.8, "date": "2025-05-01"},
    "r-other-venue": {"venue": "other", "wind_dir_card": "W", "wind_bucket": "10-15",
                      "course_type": "windward-leeward", "class": "Laser", "distance_nm": 5.0, "date": "2025-04-01"},
    "r-far": {"venue": "minskoe-more", "wind_dir_card": "E", "wind_bucket": "20+",
              "course_type": "distance", "class": "Open 800", "distance_nm": 12.0, "date": "2025-03-01"},
}}
query = {"venue": "minskoe-more", "wind_dir_card": "W", "wind_bucket": "10-15",
         "course_type": "windward-leeward", "class": "Laser", "distance_nm": 5.0}

res = find_similar(index, query)
slugs = [r["slug"] for r in res]
check(slugs and slugs[0] == "r-exact", f"exact match ranked first, got {slugs}")
check("r-close" in slugs, f"close match included, got {slugs}")
# r-far: venue +3 only (wind/course/class/dist all differ) = 3 → проходит min_score, но последним
check(res[0]["score"] > res[-1]["score"], "exact scores higher than far")
# exclude текущей гонки
res2 = find_similar(index, query, exclude="r-exact")
check("r-exact" not in [r["slug"] for r in res2], "exclude works")

print("PASS test_recall" if fail == 0 else "TESTS FAILED")
sys.exit(fail)
