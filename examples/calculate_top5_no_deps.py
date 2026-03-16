from __future__ import annotations


def normalize(values: list[float]) -> list[float]:
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        return [0.0 for _ in values]
    return [(v - min_v) / (max_v - min_v) for v in values]


def calculate_top5(records: list[dict], w1: float = 0.4, w2: float = 0.4, w3: float = 0.2) -> list[dict]:
    frag = [r["fragmentation_score"] for r in records]
    base = [r["base_score"] for r in records]
    iso = [r["isotope_score"] for r in records]

    frag_n = normalize(frag)
    base_n = normalize(base)
    iso_n = normalize(iso)

    for i, r in enumerate(records):
        r["frag_norm"] = frag_n[i]
        r["base_norm"] = base_n[i]
        r["iso_norm"] = iso_n[i]
        r["final_score"] = w1 * frag_n[i] + w2 * base_n[i] + w3 * iso_n[i]

    prior_total = sum(r["base_norm"] + 1e-9 for r in records)
    for r in records:
        r["prior_probability"] = (r["base_norm"] + 1e-9) / prior_total
        r["likelihood"] = (r["frag_norm"] + 1e-9) * (r["base_norm"] + 1e-9) * (r["iso_norm"] + 1e-9)

    evidence = sum(r["likelihood"] * r["prior_probability"] for r in records)
    for r in records:
        numerator = r["likelihood"] * r["prior_probability"]
        r["posterior_probability"] = numerator / evidence if evidence > 0 else 0.0

    sorted_records = sorted(records, key=lambda x: x["final_score"], reverse=True)
    for idx, r in enumerate(sorted_records, start=1):
        r["ranking"] = idx

    return [r for r in sorted_records if r["ranking"] <= 5]


def main():
    signal_458 = [
        {"signal_id": 458, "molecule_name": "Quercetin", "fragmentation_score": 0.92, "base_score": 0.89, "isotope_score": 0.95},
        {"signal_id": 458, "molecule_name": "Luteolin", "fragmentation_score": 0.88, "base_score": 0.84, "isotope_score": 0.90},
        {"signal_id": 458, "molecule_name": "Kaempferol", "fragmentation_score": 0.85, "base_score": 0.81, "isotope_score": 0.88},
        {"signal_id": 458, "molecule_name": "Apigenin", "fragmentation_score": 0.80, "base_score": 0.79, "isotope_score": 0.85},
        {"signal_id": 458, "molecule_name": "Myricetin", "fragmentation_score": 0.91, "base_score": 0.83, "isotope_score": 0.91},
        {"signal_id": 458, "molecule_name": "Genistein", "fragmentation_score": 0.78, "base_score": 0.75, "isotope_score": 0.80},
    ]

    top5 = calculate_top5(signal_458)

    print("signal_id | ranking | molecule_name | final_score | posterior_probability")
    for r in top5:
        print(
            f"{r['signal_id']} | {r['ranking']} | {r['molecule_name']} | "
            f"{r['final_score']:.6f} | {r['posterior_probability']:.6f}"
        )


if __name__ == "__main__":
    main()
