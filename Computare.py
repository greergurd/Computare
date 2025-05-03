from flask import Flask, request, render_template
import sqlite3
import os
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

# Maps for decoding integer fields
TYPE_MAP = {1: 'Gaming Laptop', 2: 'Thin and Light Laptop', 3: '2 in 1 Laptop', 4: 'Notebook'}
PROCESSOR_BRAND_MAP = {1: 'Intel', 2: 'AMD', 3: 'Qualcomm', 4: 'Apple', 5: 'MediaTek'}
OS_MAP = {1: 'Windows', 2: 'Chrome OS', 3: 'DOS', 4: 'macOS', 5: 'Ubuntu'}
COMPANY_MAP = {1: 'Asus', 2: 'HP', 3: 'Lenovo', 4: 'Dell', 5: 'MSI', 6: 'Realme', 7: 'Avita'}
BOOLEAN_MAP = {0: 'No', 1: 'Yes'}

DB_FILE = "laptop_database.sqlite"

# Define exchange rate (1 INR = 0.012 USD)
EXCHANGE_RATE = 0.012

def convert_to_usd(price_in_inr):
    """Convert INR to USD"""
    return price_in_inr * EXCHANGE_RATE

@app.route('/')
def search():
    return render_template('search.html',
        type_options=TYPE_MAP.items(),
        os_options=OS_MAP.items(),
        company_options=COMPANY_MAP.items()
    )

@app.route("/stats")
def stats():
    import pandas as pd
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM laptops", conn)
    conn.close()

    # Average Rating Calculations
    brand_avg_rating = {bid: df[df['company'] == bid]['user_rating'].mean() for bid in df['company'].unique() if bid in COMPANY_MAP}
    type_avg_rating = {tid: df[df['type'] == tid]['user_rating'].mean() for tid in df['type'].unique() if tid in TYPE_MAP}
    os_avg_rating = {oid: df[df['OS'] == oid]['user_rating'].mean() for oid in df['OS'].unique() if oid in OS_MAP}

    # Average Price Calculations
    brand_avg_price = {bid: df[df['company'] == bid]['price'].mean() for bid in df['company'].unique() if bid in COMPANY_MAP}
    type_avg_price = {tid: df[df['type'] == tid]['price'].mean() for tid in df['type'].unique() if tid in TYPE_MAP}
    os_avg_price = {oid: df[df['OS'] == oid]['price'].mean() for oid in df['OS'].unique() if oid in OS_MAP}

    # Convert prices to USD
    brand_avg_price_usd = {bid: convert_to_usd(price) for bid, price in brand_avg_price.items()}
    type_avg_price_usd = {tid: convert_to_usd(price) for tid, price in type_avg_price.items()}
    os_avg_price_usd = {oid: convert_to_usd(price) for oid, price in os_avg_price.items()}

    def create_bar_chart(data_dict, labels_map, x_axis_label, title, ylabel, color):
        fig, ax = plt.subplots(figsize=(10, 6))
        labels = [labels_map.get(k, str(k)) for k in data_dict.keys()]
        values = list(data_dict.values())
        ax.bar(labels, values, color=color)
        ax.set_title(title)
        ax.set_xlabel(x_axis_label)  # Use the dynamic x-axis label
        ax.set_ylabel(ylabel)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        plt.tight_layout()
        img = io.BytesIO()
        plt.savefig(img, format="png")
        img.seek(0)
        encoded = base64.b64encode(img.getvalue()).decode("utf-8")
        plt.close(fig)
        return encoded

    # Average User Ratings graphs (no titles)
    brand_rating_graph = create_bar_chart(brand_avg_rating, COMPANY_MAP, "Brand", "Average Rating", "Average Rating", "skyblue")
    type_rating_graph = create_bar_chart(type_avg_rating, TYPE_MAP, "Type", "Average Rating", "Average Rating", "lightgreen")
    os_rating_graph = create_bar_chart(os_avg_rating, OS_MAP, "Operating System", "Average Rating", "Average Rating", "lightcoral")

    # Average Price graphs (USD) (no titles)
    brand_price_graph = create_bar_chart(brand_avg_price_usd, COMPANY_MAP, "Brand", "Average Price (USD)", "Average Price (USD)", "gold")
    type_price_graph = create_bar_chart(type_avg_price_usd, TYPE_MAP, "Type", "Average Price (USD)", "Average Price (USD)", "orange")
    os_price_graph = create_bar_chart(os_avg_price_usd, OS_MAP, "Operating System", "Average Price (USD)", "Average Price (USD)", "salmon")

    return render_template("stats.html",
        brand_graph=brand_rating_graph,
        type_graph=type_rating_graph,
        os_graph=os_rating_graph,
        brand_price_graph=brand_price_graph,
        type_price_graph=type_price_graph,
        os_price_graph=os_price_graph
    )

# Convert rupees to dollars in the results route before rendering
def convert_rupees_to_dollars(price_in_rupees):
    conversion_rate = 0.012  # Example rate, you may want to use a dynamic conversion rate.
    return round(price_in_rupees * conversion_rate, 2)

@app.route('/results', methods=['POST'])
def results():
    selected_type = request.form.get('type')
    selected_os = request.form.get('os')
    selected_company = request.form.get('company')
    sort_options = request.form.getlist('sort')

    filters = []
    params = []

    if selected_type:
        filters.append("type = ?")
        params.append(int(selected_type))
    if selected_os:
        filters.append("OS = ?")
        params.append(int(selected_os))
    if selected_company:
        filters.append("company = ?")
        params.append(int(selected_company))

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    sort_clause = []
    sort_label_parts = []

    if "price" in sort_options:
        sort_clause.append("price ASC")
        sort_label_parts.append("Price")
    if "rating" in sort_options:
        sort_clause.append("user_rating DESC")
        sort_label_parts.append("User Rating")

    order_clause = f"ORDER BY {', '.join(sort_clause)}" if sort_clause else ""
    sort_label = "Sorted Laptops" + (" by " + " and ".join(sort_label_parts) if sort_label_parts else "")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.execute(f'''
        SELECT * FROM laptops
        {where_clause}
        {order_clause}
    ''', params)
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    conn.close()

    mapped_rows = []
    for row in rows:
        row = list(row)
        col_idx = {col: i for i, col in enumerate(columns)}
        
        # Process price to USD
        if 'price' in col_idx:
            row[col_idx['price']] = convert_rupees_to_dollars(row[col_idx['price']])

        # Decode other fields as before
        if 'type' in col_idx:
            row[col_idx['type']] = TYPE_MAP.get(row[col_idx['type']], row[col_idx['type']])
        if 'processor_brand' in col_idx:
            row[col_idx['processor_brand']] = PROCESSOR_BRAND_MAP.get(row[col_idx['processor_brand']], row[col_idx['processor_brand']])
        if 'OS' in col_idx:
            row[col_idx['OS']] = OS_MAP.get(row[col_idx['OS']], row[col_idx['OS']])
        if 'company' in col_idx:
            row[col_idx['company']] = COMPANY_MAP.get(row[col_idx['company']], row[col_idx['company']])
        if 'SSD' in col_idx:
            row[col_idx['SSD']] = BOOLEAN_MAP.get(row[col_idx['SSD']], row[col_idx['SSD']])
        if 'touchscreen' in col_idx:
            row[col_idx['touchscreen']] = BOOLEAN_MAP.get(row[col_idx['touchscreen']], row[col_idx['touchscreen']])

        # Modify the laptop name to remove everything after the first hyphen
        if 'name' in col_idx:
            name = row[col_idx['name']]
            # Truncate the name to everything before the first hyphen
            row[col_idx['name']] = name.split(" -")[0] if " - " in name else name

        mapped_rows.append(row)

    return render_template('results.html',
        laptops=mapped_rows,
        columns=columns,
        sort_label=sort_label
    )



if __name__ == '__main__':
    app.run(debug=True)
