import pandas as pd

from etl.score import calculate_score, select_top5


def main():
    data = [
        {"signal_id": 458, "molecule_name": "Quercetin", "fragmentation_score": 0.92, "base_score": 0.89, "isotope_score": 0.95},
        {"signal_id": 458, "molecule_name": "Luteolin", "fragmentation_score": 0.88, "base_score": 0.84, "isotope_score": 0.90},
        {"signal_id": 458, "molecule_name": "Kaempferol", "fragmentation_score": 0.85, "base_score": 0.81, "isotope_score": 0.88},
        {"signal_id": 458, "molecule_name": "Apigenin", "fragmentation_score": 0.80, "base_score": 0.79, "isotope_score": 0.85},
        {"signal_id": 458, "molecule_name": "Myricetin", "fragmentation_score": 0.91, "base_score": 0.83, "isotope_score": 0.91},
        {"signal_id": 458, "molecule_name": "Genistein", "fragmentation_score": 0.78, "base_score": 0.75, "isotope_score": 0.80},
    ]

    df = pd.DataFrame(data)
    scored = calculate_score(df, w1=0.4, w2=0.4, w3=0.2)
    top5 = select_top5(scored)

    cols = [
        "signal_id",
        "molecule_name",
        "final_score",
        "prior_probability",
        "posterior_probability",
        "ranking",
    ]
    print(top5.sort_values(["signal_id", "ranking"])[cols].to_string(index=False))


if __name__ == "__main__":
    main()
