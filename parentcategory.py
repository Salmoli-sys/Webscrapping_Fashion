import pandas as pd

def main():
    # 1) read your CSV (assumes URLs in the first column)
    df = pd.read_csv('product_urls.csv')
    urls = df.iloc[:, 0].dropna().astype(str).tolist()

    # 2) pull the slug before “-item” and take its last token as a candidate
    slugs = [u.split('/')[-1].split('-item')[0] for u in urls]
    candidates = [s.split('-')[-1] for s in slugs]

    # 3) count frequencies
    freq = pd.Series(candidates).value_counts().reset_index()
    freq.columns = ['category_candidate', 'count']

    # 4) show top 20
    top20 = freq.head(20)
    print("Top 20 category candidates:\n")
    print(top20.to_string(index=False))

    # 5) save full list (optional)
    freq.to_csv('category_candidates.csv', index=False)
    print("\nWrote full frequency list to category_candidates.csv")

if __name__ == '__main__':
    main()
