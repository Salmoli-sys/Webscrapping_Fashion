import os
import pandas as pd

# Fallback category for uncategorized URLs
tFallback = 'others'


def load_parent_categories(filepath='category_candidate.csv'):
    """
    Read parent categories from a CSV file (first column).
    Returns a list of category strings sorted by descending length.
    """
    df = pd.read_csv(filepath, header=None)
    categories = df.iloc[:, 0].dropna().astype(str).tolist()
    # sort by length to match longer tokens first
    categories.sort(key=len, reverse=True)
    return categories


def categorize_urls(urls, categories):
    """
    Assign each URL to the first matching category (by substring).
    URLs with no match go into the fallback category.
    """
    categorized = {cat: [] for cat in categories}
    categorized[tFallback] = []
    for url in urls:
        url_lower = url.lower()
        matched = False
        for cat in categories:
            if cat.lower() in url_lower:
                categorized[cat].append(url)
                matched = True
                break
        if not matched:
            categorized[tFallback].append(url)
    return categorized


def write_categories(categorized, base_dir=None):
    """
    Create a directory per category and write its URLs into links.txt.
    """
    if base_dir is None:
        base_dir = os.getcwd()
    for cat, urls in categorized.items():
        dir_path = os.path.join(base_dir, cat)
        os.makedirs(dir_path, exist_ok=True)
        file_path = os.path.join(dir_path, 'links.txt')
        with open(file_path, 'w', encoding='utf-8') as f:
            for u in urls:
                f.write(u + '\n')
    print(f"Created {len(categorized)} categories under {base_dir}.")


def main():
    # 1) load parent categories
    parent_file = 'category_candidates.csv'
    if not os.path.exists(parent_file):
        print(f"Parent categories file '{parent_file}' not found.")
        return
    categories = load_parent_categories(parent_file)

    # 2) load product URLs
    input_csv = 'product_urls.csv'
    if not os.path.exists(input_csv):
        print(f"Product URLs file '{input_csv}' not found.")
        return
    df = pd.read_csv(input_csv, header=None)
    urls = df.iloc[:, 0].dropna().astype(str).tolist()

    # 3) categorize and write
    categorized = categorize_urls(urls, categories)
    write_categories(categorized)


if __name__ == '__main__':
    main()
