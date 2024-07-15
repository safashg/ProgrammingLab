from flask import Flask, render_template, request, jsonify
import pymysql
import pandas as pd
import logging
import joblib
import pandas as pd
import logging
import os
import hashlib

app = Flask(__name__, template_folder='../frontend/templates', static_folder='../frontend/static')
app.jinja_env.auto_reload = True
app.config['TEMPLATES_AUTO_RELOAD'] = True

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("query_log.log"),
        logging.StreamHandler()
    ]
)

log = logging.getLogger(__name__)

def get_db_connection():
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='Karamel2020',
        database='pizzadata'
    )
    return connection


def generate_cache_key(query, params):
    hash_object = hashlib.md5()
    hash_object.update(query.encode('utf-8'))
    if params:
        hash_object.update(str(params).encode('utf-8'))
    return hash_object.hexdigest()

# Create a directory for caching if it doesn't exist
cache_dir = 'query_cache'
os.makedirs(cache_dir, exist_ok=True)


def execute_query(query, params=None):
    """Hilfsfunktion zur Ausführung von SQL-Abfragen und Rückgabe als DataFrame"""
    try:
        # Generate a unique cache key for the query and parameters
        cache_key = generate_cache_key(query, params)
        cache_path = os.path.join(cache_dir, cache_key + '.pkl')

        # Check if the result is already cached
        if os.path.exists(cache_path):
            df = joblib.load(cache_path)
            logging.info(f"Loaded cached result")
        else:
            with get_db_connection() as conn:
                if params:
                    df = pd.read_sql(query, conn, params=params)
                else:
                    df = pd.read_sql(query, conn)
            # Cache the result
            joblib.dump(df, cache_path)
            logging.info(f"Cached result for query")

        return df
    except Exception as e:
        logging.error(f"Error executing query: {e}")
        return None


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/stores', methods=['GET'])
def stores():
    return render_template('stores.html')

@app.route('/orders', methods=['GET'])
def orders():
    return render_template('orders.html')


@app.route('/customer', methods=['GET'])
def customer():
    return render_template('customer.html')


@app.route('/categories', methods=['GET'])
def categories():
    return render_template('categories.html')


@app.route('/products', methods=['GET'])
def products():
    return render_template('products.html')


@app.route('/list', methods=['GET'])
def list():
    return render_template('list.html')

@app.route('/store_locations', methods=['GET'])
def store_locations():
    """Endpunkt für Standortdaten der Stores"""
    try:
        query = "SELECT storeID, latitude, longitude, city, state FROM stores"
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch store locations"}), 500

        store_data = df.to_dict(orient='records')
        return jsonify(store_data=store_data)
    except Exception as e:
        logging.error(f"Error in /store_locations endpoint: {e}")
        return jsonify({"error": "Error fetching store locations"}), 500


@app.route('/customer_locations', methods=['GET'])
def customer_locations():
    """Endpunkt für Standortdaten der Kunden"""
    try:
        query = "SELECT latitude, longitude FROM customers"
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch customer locations"}), 500

        customer_data = df.to_dict(orient='records')
        return jsonify(customer_data=customer_data)
    except Exception as e:
        logging.error(f"Error in /customer_locations endpoint: {e}")
        return jsonify({"error": "Error fetching customer locations"}), 500


@app.route('/overview', methods=['GET'])
def overview():
    try:
        query = """
            SELECT Name, Price, Category, Size, Ingredients, production_costs 
            FROM products
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch product overview data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /overview endpoint: {e}")
        return jsonify({"error": "Error fetching product list data"}), 500


# store analyse

@app.route('/total_items_sold_per_store', methods=['GET'])
def total_items_sold_per_store():
    """Endpunkt für Gesamtverkaufszahlen pro Store"""
    try:
        query = """
        SELECT storeID, SUM(Quantity) AS totalItemsSold
        FROM store_pizza_sales
        GROUP BY storeID
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch total items sold data"}), 500

        total_items_data = df.to_dict(orient='records')
        return jsonify(total_items_data=total_items_data)
    except Exception as e:
        logging.error(f"Error in /total_items_sold_per_store endpoint: {e}")
        return jsonify({"error": "Error fetching total items sold data"}), 500


# Endpoint für orders by weekday
@app.route('/store_orders_by_weekday', methods=['GET'])
def store_orders_by_weekday():
    try:
        weekday = request.args.get('weekday')  # Wochentag als Parameter
        where_clause = ""
        if weekday:
            where_clause = f"WHERE Weekday = '{weekday}'"

        query = f"""
        SELECT Weekday, storeID, SUM(NumberOfOrders) AS totalOrders
        FROM OrdersPerWeekday
        {where_clause}
        GROUP BY Weekday, storeID
        ORDER BY Weekday, storeID;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch orders by weekday data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /store_orders_by_weekday endpoint: {e}")
        return jsonify({"error": "Error fetching orders by weekday data"}), 500


@app.route('/order_activity_over_time', methods=['GET'])
def order_activity_over_time():
    """Endpunkt für Bestellaktivität über Zeiträume hinweg"""
    try:
        interval = request.args.get('interval',
                                    'week')  # Unterstützte Intervalle: 'day', 'week', 'month' -> ein diagramm wo der benutzer interaktiv entschiedet was er angezeigt haben möchte

        if interval == 'day':
            query = """
                SELECT storeID, DATE(period) AS period, SUM(order_count) AS order_count
                FROM order_activity
                GROUP BY storeID, DATE(period)
                ORDER BY storeID, DATE(period);
            """
        elif interval == 'month':
            query = """
                SELECT storeID, DATE_FORMAT(period, '%Y-%m') AS period, SUM(order_count) AS order_count
                FROM order_activity
                GROUP BY storeID, DATE_FORMAT(period, '%Y-%m')
                ORDER BY storeID, DATE_FORMAT(period, '%Y-%m');
            """
        else:  # week
            query = """
                SELECT storeID, DATE_FORMAT(period, '%Y') AS period, SUM(order_count) AS order_count
                FROM order_activity
                GROUP BY storeID, DATE_FORMAT(period, '%Y')
                ORDER BY storeID, DATE_FORMAT(period, '%Y');
            """

        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch order activity data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /order_activity_over_time endpoint: {e}")
        return jsonify({"error": "Error fetching order activity data"}), 500


@app.route('/only_years', methods=['GET'])
def only_years():
    """Jahre"""
    try:
        query = """
            SELECT DISTINCT DATE_FORMAT(period, '%Y') AS period
            FROM order_activity
            ORDER BY period;
        """
        df = execute_query(query)
        if df is None or df.empty:
            return jsonify({"error": "Failed to fetch years data"}), 500

        only_years_data = df.to_dict(orient='records')
        return jsonify(only_years=only_years_data)
    except Exception as e:
        logging.error(f"Error in /only_years endpoint: {e}")
        return jsonify({"error": "Error fetching years data"}), 500


@app.route('/store_sales_per_month', methods=['GET'])
def store_sales_per_month():
    """Endpunkt für Verkaufszahlen pro Monat"""
    try:
        order_month = request.args.get('orderMonth')
        query = f"""
        SELECT storeID, SUM(Quantity) AS totalItemsSold
        FROM store_pizza_sales
        WHERE DATE_FORMAT(orderDate, '%Y-%m') = '{order_month}'
        GROUP BY storeID
        ORDER BY storeID
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch sales per month data"}), 500

        store_monthly_sales_data = df.to_dict(orient='records')
        return jsonify(store_monthly_sales_data=store_monthly_sales_data)
    except Exception as e:
        logging.error(f"Error in /store_sales_per_month endpoint: {e}")
        return jsonify({"error": "Error fetching sales per month data"}), 500


@app.route('/order_month', methods=['GET'])
def order_month():
    """Endpunkt für OrderMonth"""
    try:
        query = """
        SELECT orderMonth
        FROM monthly_store_revenue
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch order month data"}), 500

        result = df.to_dict(orient='records')
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/store_revenue_and_profit_per_month', methods=['GET'])
def store_revenue_and_profit_per_month():
    """Endpunkt für Umsatz und Gewinn pro Monat"""
    try:
        order_month = request.args.get('orderMonth')
        query = f"""
        SELECT storeID, totalRevenue, totalProfit
        FROM monthly_store_revenue
        WHERE orderMonth = '{order_month}'
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch revenue and profit data"}), 500

        store_revenue_profit_data = df.to_dict(orient='records')
        return jsonify(store_revenue_profit_data=store_revenue_profit_data), 200
    except Exception as e:
        logging.error(f"Error in /store_revenue_and_profit_per_month endpoint: {e}")
        return jsonify({"error": "Error fetching revenue and profit data"}), 500


@app.route('/daily_order_stats', methods=['GET'])
def daily_order_stats():
    try:
        order_date = request.args.get('orderDate')
        where_clause = ""
        if order_date:
            where_clause = f"WHERE orderDate = '{order_date}'"

        query = f"""
            SELECT storeID, orderDate, NumberOfOrders, TotalItemsSold, AverageOrderValue
            FROM daily_store_order_stats
            {where_clause}
            ORDER BY orderDate
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch daily order stats"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /daily_order_stats endpoint: {e}")
        return jsonify({"error": "Error fetching daily order stats"}), 500


@app.route('/daily_average_order_value_per_store', methods=['GET'])
def daily_average_order_value_per_store():
    # durchschnittlichen Bestellwert pro Store, Nützlich für Balkendiagramme zur Darstellung der durchschnittlichen Bestellwerte.

    try:
        query = """
            SELECT storeID, AVG(AverageOrderValue) AS avgOrderValue
            FROM daily_store_order_stats
            GROUP BY storeID
            ORDER BY storeID
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch average order value per store"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /average_order_value_per_store endpoint: {e}")
        return jsonify({"error": "Error fetching average order value per store"}), 500


@app.route('/daily_order_intensity_heatmap', methods=['GET'])
def daily_order_intensity_heatmap():
    # Bestellintensitätsdaten, Nützlich für Heatmaps zur Visualisierung der Bestellintensität an verschiedenen Tagen.

    try:
        query = """
            SELECT storeID, orderDate, NumberOfOrders
            FROM daily_store_order_stats
            ORDER BY orderDate
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch order intensity heatmap data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /order_intensity_heatmap endpoint: {e}")
        return jsonify({"error": "Error fetching order intensity heatmap data"}), 500


@app.route('/daily_order_trends', methods=['GET'])
def daily_order_trends():
    try:
        order_year = request.args.get('orderYear')
        where_clause = ""
        if order_year:
            where_clause = f"WHERE YEAR(orderDate) = {order_year}"

        query = f"""
            SELECT orderDate, SUM(NumberOfOrders) AS totalOrders, SUM(TotalItemsSold) AS totalItemsSold,
                   AVG(AverageOrderValue) AS avgOrderValue
            FROM daily_store_order_stats
            {where_clause}
            GROUP BY orderDate
            ORDER BY orderDate
        """

        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch order trends data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /daily_order_trends endpoint: {e}")
        return jsonify({"error": "Error fetching order trends data"}), 500


@app.route('/daily_store_performance_benchmark', methods=['GET'])
def daily_store_performance_benchmark():
    # Vergleicht die durchschnittliche Bestellleistung zwischen den Stores, Nützlich für Radar-Charts zur Darstellung der Store-Performance
    try:
        query = """
            SELECT storeID,
                   AVG(NumberOfOrders) AS avgNumberOfOrders,
                   AVG(AverageOrderValue) AS avgOrderValue
            FROM daily_store_order_stats
            GROUP BY storeID
            ORDER BY storeID
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch store performance benchmark data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /store_performance_benchmark endpoint: {e}")
        return jsonify({"error": "Error fetching store performance benchmark data"}), 500


@app.route('/weekly_order_stats', methods=['GET'])
def weekly_order_stats():
    try:
        week_year = request.args.get('weekYear')
        where_clause = ""
        if week_year:
            where_clause = f"WHERE weekYear = '{week_year}'"

        query = f"""
                SELECT storeID, weekYear, NumberOfOrders, TotalItemsSold, AverageOrderValue
                FROM weekly_store_order_stats
                {where_clause}
                ORDER BY weekYear
                """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch weekly order stats"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /weekly_order_stats endpoint: {e}")
        return jsonify({"error": "Error fetching weekly order stats"}), 500


@app.route('/weekly_average_order_value_per_store', methods=['GET'])
def weekly_average_order_value_per_store():
    # Durchschnittlicher Bestellwert pro Store, Nützlich für Balkendiagramme zur Darstellung der durchschnittlichen Bestellwerte.

    try:
        query = """
                SELECT storeID, AVG(AverageOrderValue) AS avgOrderValue
                FROM weekly_store_order_stats
                GROUP BY storeID
                ORDER BY storeID
                """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch average order value per store"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /weekly_average_order_value_per_store endpoint: {e}")
        return jsonify({"error": "Error fetching average order value per store"}), 500


@app.route('/weekly_order_intensity', methods=['GET'])
def weekly_order_intensity_heatmap():
    # Bestellintensitätsdaten, Nützlich für Heatmaps zur Visualisierung der Bestellintensität an verschiedenen Wochen.

    try:
        query = """
                SELECT storeID, weekYear, NumberOfOrders
                FROM weekly_store_order_stats
                ORDER BY weekYear
                """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch order intensity heatmap data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /weekly_order_intensity endpoint: {e}")
        return jsonify({"error": "Error fetching order intensity data"}), 500


@app.route('/weekly_order_trends', methods=['GET'])
def weekly_order_trends():
    # Bestelltrends über Zeiträume hinweg, Nützlich für Bereichsdiagramme zur Darstellung der Entwicklung von Bestellungen, verkauften Artikeln und Bestellwerten.
    try:
        query = """
            SELECT weekYear, SUM(NumberOfOrders) AS totalOrders, SUM(TotalItemsSold) AS totalItemsSold,
                   AVG(AverageOrderValue) AS avgOrderValue
            FROM weekly_store_order_stats
            GROUP BY weekYear
            ORDER BY weekYear
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch order trends data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /weekly_order_trends endpoint: {e}")
        return jsonify({"error": "Error fetching order trends data"}), 500


@app.route('/weekly_store_performance_benchmark', methods=['GET'])
def weekly_store_performance_benchmark():
    # Vergleicht die durchschnittliche Bestellleistung zwischen den Stores, nützlich für Radar-Charts zur Darstellung der Store-Performance
    try:
        query = """
            SELECT storeID,
                   AVG(NumberOfOrders) AS avgNumberOfOrders,
                   AVG(AverageOrderValue) AS avgOrderValue
            FROM weekly_store_order_stats
            GROUP BY storeID
            ORDER BY storeID
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch store performance benchmark data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /weekly_store_performance_benchmark endpoint: {e}")
        return jsonify({"error": "Error fetching store performance benchmark data"}), 500


@app.route('/monthly_order_stats', methods=['GET'])
def monthly_order_stats():
    try:
        month_year = request.args.get('monthYear')
        where_clause = ""
        if month_year:
            where_clause = f"WHERE monthYear = '{month_year}'"

        query = f"""
                SELECT storeID, monthYear, NumberOfOrders, TotalItemsSold, AverageOrderValue
                FROM monthly_store_order_stats
                {where_clause}
                ORDER BY monthYear
                """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch monthly order stats"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /monthly_order_stats endpoint: {e}")
        return jsonify({"error": "Error fetching monthly order stats"}), 500


@app.route('/monthly_average_order_value_per_store', methods=['GET'])
def monthly_average_order_value_per_store():
    # Durchschnittlicher Bestellwert pro Store, nützlich für Balkendiagramme zur Darstellung der durchschnittlichen Bestellwerte.

    try:
        query = """
                SELECT storeID, AVG(AverageOrderValue) AS avgOrderValue
                FROM monthly_store_order_stats
                GROUP BY storeID
                ORDER BY storeID
                """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch average order value per store"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /monthly_average_order_value_per_store endpoint: {e}")
        return jsonify({"error": "Error fetching average order value per store"}), 500


@app.route('/monthly_order_intensity', methods=['GET'])
def monthly_order_intensity_heatmap():
    # Bestellintensitätsdaten, nützlich für Heatmaps zur Visualisierung der Bestellintensität an verschiedenen Monaten.

    try:
        query = """
                SELECT storeID, monthYear, NumberOfOrders
                FROM monthly_store_order_stats
                ORDER BY monthYear
                """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch order intensity data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /monthly_order_intensity endpoint: {e}")
        return jsonify({"error": "Error fetching order intensity data"}), 500


@app.route('/monthly_store_performance_benchmark', methods=['GET'])
def monthly_store_performance_benchmark():
    # Vergleicht die durchschnittliche Bestellleistung zwischen den Stores, nützlich für Radar-Charts zur Darstellung der Store-Performance
    try:
        query = """
            SELECT storeID,
                   AVG(NumberOfOrders) AS avgNumberOfOrders,
                   AVG(AverageOrderValue) AS avgOrderValue
            FROM monthly_store_order_stats
            GROUP BY storeID
            ORDER BY storeID
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch store performance benchmark data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /monthly_store_performance_benchmark endpoint: {e}")
        return jsonify({"error": "Error fetching store performance benchmark data"}), 500


@app.route('/monthly_order_trends', methods=['GET'])
def monthly_order_trends():
    # Bestelltrends über Zeiträume hinweg, nützlich für Bereichsdiagramme zur Darstellung der Entwicklung von Bestellungen, verkauften Artikeln und Bestellwerten.
    try:
        query = """
            SELECT monthYear, SUM(NumberOfOrders) AS totalOrders, SUM(TotalItemsSold) AS totalItemsSold,
                   AVG(AverageOrderValue) AS avgOrderValue
            FROM monthly_store_order_stats
            GROUP BY monthYear
            ORDER BY monthYear
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch order trends data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /monthly_order_trends endpoint: {e}")
        return jsonify({"error": "Error fetching order trends data"}), 500


@app.route('/unique_customers_per_store_table', methods=['GET'])
def unique_customers_per_store_table():
    """Endpunkt zur Abfrage der Tabelle wie viele customers per store"""
    try:
        query = """
            SELECT storeID, uniqueCustomers
            FROM unique_customers_per_store
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch unique customers per store data from table"}), 500

        unique_customers_data = df.to_dict(orient='records')
        return jsonify(unique_customers_data=unique_customers_data)
    except Exception as e:
        logging.error(f"Error in /unique_customers_per_store_table endpoint: {e}")
        return jsonify({"error": "Error fetching unique customers per store data from table"}), 500


@app.route('/only_stores', methods=['GET'])
def only_stores():
    """Stores"""
    try:
        query = """
            SELECT storeID    
            FROM PizzaSalesSummary
            GROUP BY storeID;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch store data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /only_stores: {e}")
        return jsonify({"error": "Error fetching  store data"}), 500


@app.route('/category_sales_comparison', methods=['GET'])
def category_sales_comparison():
    """Endpunkt für den Vergleich der Kategorie-Verkäufe zwischen Stores"""
    try:
        query = """
            SELECT Category, storeID, NumberOfPizzasSold
            FROM PizzaSalesSummary
            ORDER BY Category, storeID;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch category sales comparison data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /category_sales_comparison endpoint: {e}")
        return jsonify({"error": "Error fetching category sales comparison data"}), 500


@app.route('/top_categories_per_store', methods=['GET'])
def top_categories_per_store():
    """Endpunkt für die Top-Kategorien pro Store"""
    try:
        query = """
            SELECT storeID, Category, NumberOfPizzasSold
            FROM PizzaSalesSummary
            WHERE (storeID, NumberOfPizzasSold) IN (
                SELECT storeID, MAX(NumberOfPizzasSold)
                FROM PizzaSalesSummary
                GROUP BY storeID
            )
            ORDER BY storeID;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch top categories per store data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /top_categories_per_store endpoint: {e}")
        return jsonify({"error": "Error fetching top categories per store data"}), 500


@app.route('/seasonal_order_analysis', methods=['GET'])
def seasonal_order_analysis():
    """Endpunkt für die Analyse saisonaler Bestellungen"""
    try:
        query = """
            SELECT 
                OrderDate, 
                storeID, 
                TotalOrders,
                EXTRACT(MONTH FROM OrderDate) AS Month,
                EXTRACT(DAY FROM OrderDate) AS Day,
                CASE 
                    WHEN EXTRACT(MONTH FROM OrderDate) IN (12, 1, 2) THEN 'Winter'
                    WHEN EXTRACT(MONTH FROM OrderDate) IN (3, 4, 5) THEN 'Spring'
                    WHEN EXTRACT(MONTH FROM OrderDate) IN (6, 7, 8) THEN 'Summer'
                    WHEN EXTRACT(MONTH FROM OrderDate) IN (9, 10, 11) THEN 'Fall'
                    ELSE 'Unknown'
                END AS Season
            FROM TopOrderDates
            ORDER BY TotalOrders DESC, OrderDate, storeID;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch seasonal order analysis data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /seasonal_order_analysis endpoint: {e}")
        return jsonify({"error": "Error fetching seasonal order analysis data"}), 500

@app.route('/seasonal_order_details', methods=['GET'])
def seasonal_order_details():
    """Endpoint for seasonal order details"""
    try:
        season = request.args.get('season')
        if not season:
            return jsonify({"error": "Season parameter is required"}), 400

        query = f"""
            SELECT 
                OrderDate, 
                storeID, 
                TotalOrders
            FROM TopOrderDates
            WHERE CASE 
                    WHEN EXTRACT(MONTH FROM OrderDate) IN (12, 1, 2) THEN 'Winter'
                    WHEN EXTRACT(MONTH FROM OrderDate) IN (3, 4, 5) THEN 'Spring'
                    WHEN EXTRACT(MONTH FROM OrderDate) IN (6, 7, 8) THEN 'Summer'
                    WHEN EXTRACT(MONTH FROM OrderDate) IN (9, 10, 11) THEN 'Fall'
                    ELSE 'Unknown'
                END = %s
            ORDER BY TotalOrders DESC, OrderDate, storeID;
        """
        df = execute_query(query, params=[season])
        if df is None:
            return jsonify({"error": "Failed to fetch seasonal order details data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /seasonal_order_details endpoint: {e}")
        return jsonify({"error": "Error fetching seasonal order details data"}), 500


@app.route('/holiday_order_analysis', methods=['GET'])
def holiday_order_analysis():
    """Endpunkt für die Analyse von Bestellungen an Feiertagen"""
    try:
        query = f"""
           SELECT OrderDate, storeID, TotalOrders, HolidayName
            FROM TopOrderDates
            WHERE HolidayName IS NOT NULL
            ORDER BY HolidayName, OrderDate;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch holiday order analysis data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /holiday_order_analysis endpoint: {e}")
        return jsonify({"error": "Error fetching holiday order analysis data"}), 500


@app.route('/avg_orders_per_hour', methods=['GET'])
def avg_orders_per_hour():
    """Endpunkt für die durchschnittlichen Bestellungen pro Stunde (angepasste Zeit)"""
    try:
        query = """
            SELECT Hour, storeID, AvgOrdersPerHour
            FROM AvgOrdersPerHour
            ORDER BY storeID, Hour;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch average orders per hour data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /avg_orders_per_hour endpoint: {e}")
        return jsonify({"error": "Error fetching average orders per hour data"}), 500


@app.route('/avg_orders_per_hour_utc', methods=['GET'])
def avg_orders_per_hour_utc():
    """Endpunkt für die durchschnittlichen Bestellungen pro Stunde (UTC-Zeit)"""
    try:
        query = """
            SELECT Hour, storeID, AvgOrdersPerHour
            FROM AvgOrdersPerHourUTC
            ORDER BY storeID, Hour;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch average orders per hour (UTC) data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /avg_orders_per_hour_utc endpoint: {e}")
        return jsonify({"error": "Error fetching average orders per hour (UTC) data"}), 500


@app.route('/store_sales_comparison', methods=['GET'])
def store_sales_comparison():
    """Endpunkt für den Verkaufsvergleich zwischen Stores"""
    try:
        query = """
            SELECT ProductName, storeID, SUM(Quantity) AS TotalQuantity
            FROM daily_store_pizza_sales
            GROUP BY ProductName, storeID
            ORDER BY ProductName, storeID;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch store sales comparison data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /store_sales_comparison endpoint: {e}")
        return jsonify({"error": "Error fetching store sales comparison data"}), 500


@app.route('/store_sales_comparison_weekly', methods=['GET'])
def store_sales_comparison_weekly():
    """Endpunkt für den wöchentlichen Verkaufsvergleich zwischen Stores"""
    try:
        query = """
            SELECT yearWeek, PizzaName, storeID, SUM(Quantity) AS TotalQuantity
            FROM weekly_store_pizza_sales
            GROUP BY yearWeek, PizzaName, storeID
            ORDER BY yearWeek, PizzaName, storeID;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch store sales comparison weekly data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /store_sales_comparison_weekly endpoint: {e}")
        return jsonify({"error": "Error fetching store sales comparison weekly data"}), 500


# customer analyse
@app.route('/chart_data/top_customers', methods=['GET'])
def top_customers():
    """Endpunkt für die Top-Kunden nach Umsatz"""
    try:
        store_id = request.args.get('storeID')
        query = """
            SELECT customerID, total_spent
            FROM top_customers_per_store
            WHERE storeID = %s
            ORDER BY total_spent DESC
            LIMIT 10
        """
        df = execute_query(query, [store_id])
        if df is None:
            return jsonify({"error": "Failed to fetch top customers data"}), 500

        data = {
            "labels": df['customerID'].tolist(),
            "data": df['total_spent'].tolist()
        }
        return jsonify(data)
    except Exception as e:
        logging.error(f"Error in /chart_data/top_customers endpoint: {e}")
        return jsonify({"error": "Error fetching top customers data"}), 500


# product analyse
@app.route('/most_popular_products', methods=['GET'])
def most_popular_products():
    """Endpunkt für die beliebtesten Produkte, nach name und kategorie möglich"""
    try:
        query = """
            SELECT ProductName, Category, Frequency
            FROM product_order_frequency
            ORDER BY Frequency DESC;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch most popular products data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /most_popular_products endpoint: {e}")
        return jsonify({"error": "Error fetching most popular products data"}), 500

@app.route('/popular_products_by_store', methods=['GET'])
def popular_products_by_store():
    """Endpoint to get the most popular products by name and store just for one particular store"""
    try:
        store_id = request.args.get('storeID')
        query = f"""
            SELECT storeID, Name, size, total_items_sold_per_store
            FROM total_items_sold
            WHERE storeID = '{store_id}'
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch popular products data"}), 500

        data = df.to_dict(orient='records')
        print(data)  # Debug statement to check data
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /popular_products_by_store: {e}")
        return jsonify({"error": "Error fetching popular products data"}), 500


@app.route('/category_order_share', methods=['GET'])
def category_order_share():
    """Endpunkt für den Anteil jeder Kategorie an Anzahl der gesamten Bestellungen -> Kreisdiagramm"""
    try:
        query = """
            SELECT Category, SUM(Frequency) AS TotalFrequency,
                   ROUND(100.0 * SUM(Frequency) / (SELECT SUM(Frequency) FROM product_order_frequency), 2) AS Percentage
            FROM product_order_frequency
            GROUP BY Category
            ORDER BY TotalFrequency DESC;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch category order share data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /category_order_share endpoint: {e}")
        return jsonify({"error": "Error fetching category order share data"}), 500


@app.route('/product_order_share', methods=['GET'])
def product_order_share():
    """Endpunkt für den Anteil jedes Produktnamens an Anzahl der gesamten Bestellungen -> Kreisdiagramm"""
    try:
        category = request.args.get('category')
        query = f"""
                SELECT 
                    ProductName, 
                    Category, 
                    Frequency,
                    ROUND(100.0 * Frequency / (SELECT SUM(Frequency) FROM product_order_frequency), 2) AS Percentage
                FROM product_order_frequency
                WHERE Category = '{category}'
                ORDER BY Percentage DESC;
            """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": f"Failed to fetch product order share data for category {category}"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /product_order_share endpoint: {e}")
        return jsonify({"error": "Error fetching product order share data"}), 500


@app.route('/total_sales_per_category', methods=['GET'])
def total_sales_per_category():
    """Endpunkt für die Gesamtverkäufe pro Kategorie"""
    try:
        query = """
            SELECT Category, SUM(NumberOfPizzasSold) AS TotalPizzasSold
            FROM PizzaSalesSummary
            GROUP BY Category
            ORDER BY Category;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch total sales per category data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /total_sales_per_category endpoint: {e}")
        return jsonify({"error": "Error fetching total sales per category data"}), 500


@app.route('/weekly_sales_distribution', methods=['GET'])
def weekly_sales_distribution():
    """Endpunkt für die tägliche Verkaufsverteilung pro Produkt"""
    try:
        query = """
            SELECT DAYOFWEEK(orderDate) AS Weekday, ProductName, SUM(Quantity) AS TotalQuantity
            FROM daily_store_pizza_sales
            GROUP BY Weekday, ProductName
            ORDER BY Weekday, ProductName;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch weekly sales distribution data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /weekly_sales_distribution endpoint: {e}")
        return jsonify({"error": "Error fetching weekly sales distribution data"}), 500


@app.route('/sales_trend_by_size_only_date', methods=['GET'])
def sales_trend_by_size_only_date():
    """Datum gefiltert aus Endpunkt für Verkaufstrends nach Größe """
    try:
        query = """
            SELECT DISTINCT orderDate
            FROM daily_store_pizza_sales_with_size
            ORDER BY orderDate;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch sales trend by size data"}), 500

        data = df['orderDate'].tolist()
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /sales_trend_by_size_only_date endpoint: {e}")
        return jsonify({"error": "Error fetching sales trend by size data"}), 500


@app.route('/sales_trend_by_size', methods=['GET'])
def sales_trend_by_size():
    """Endpunkt für Verkaufstrends nach Größe """  # vllt extra tabelle erstellen wenns zu lange dauert
    try:
        query = """
            SELECT orderDate, Size, SUM(Quantity) AS TotalQuantity
            FROM daily_store_pizza_sales_with_size
            GROUP BY orderDate, Size
            ORDER BY orderDate, Size;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch sales trend by size data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /sales_trend_by_size endpoint: {e}")
        return jsonify({"error": "Error fetching sales trend by size data"}), 500


@app.route('/size_popularity', methods=['GET'])
def size_popularity():
    """Endpunkt für die Beliebtheit von Pizzagrößen"""
    try:
        query = """
            SELECT Size, SUM(Quantity) AS TotalQuantity
            FROM daily_store_pizza_sales_with_size
            GROUP BY Size
            ORDER BY TotalQuantity DESC;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch size popularity data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /size_popularity endpoint: {e}")
        return jsonify({"error": "Error fetching size popularity data"}), 500


@app.route('/popular_pizza_by_week_only_weeks', methods=['GET'])
def popular_pizza_by_week_only_weeks():
    """Endpunkt für die Wochen der der beliebtesten Pizza-Sorten pro Woche"""
    try:
        year_week = request.args.get('yearWeek')
        query = f"""
           SELECT yearWeek FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY yearWeek ORDER BY storeID) AS row_num
            FROM weekly_store_pizza_sales
            ) AS temp
            WHERE row_num = 1;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch week data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        return jsonify({"error": f"Error fetching week data: {e}"}), 500


@app.route('/popular_pizza_by_week', methods=['GET'])
def popular_pizza_by_week():
    """Endpunkt für die beliebtesten Pizza-Sorten pro Woche"""
    try:
        year_week = request.args.get('yearWeek')
        query = f"""
            SELECT yearWeek, PizzaName, SUM(Quantity) AS TotalQuantity
            FROM weekly_store_pizza_sales
            WHERE yearWeek = '{year_week}'
            GROUP BY yearWeek, PizzaName
            ORDER BY TotalQuantity DESC;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch popular pizza by week data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        return jsonify({"error": f"Error fetching popular pizza by week data: {e}"}), 500


@app.route('/total_profit_per_pizza', methods=['GET'])
def total_profit_per_pizza():
    """Endpunkt für den Gesamtprofit pro Pizza"""
    try:
        query = """
            SELECT SKU, Name, Size, Price, production_cost, profit
            FROM pizza_profit_analysis
            ORDER BY profit DESC;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch total profit per pizza data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /total_profit_per_pizza endpoint: {e}")
        return jsonify({"error": "Error fetching total profit per pizza data"}), 500


@app.route('/cost_structure_per_pizza', methods=['GET'])
def cost_structure_per_pizza():
    """Endpunkt für die Kostenstruktur pro Pizza"""
    try:
        query = """
            SELECT SKU, Name, Size, Price, production_cost, 
                   ROUND(production_cost / Price * 100, 2) AS CostPercentage
            FROM pizza_profit_analysis
            ORDER BY SKU, Size;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch cost structure per pizza data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /cost_structure_per_pizza endpoint: {e}")
        return jsonify({"error": "Error fetching cost structure per pizza data"}), 500


@app.route('/margin_analysis', methods=['GET'])
def margin_analysis():
    """Endpunkt für die Margenanalyse pro Pizza"""
    try:
        query = """
            SELECT SKU, Name, Size, Price, production_cost, 
                   ROUND((Price - production_cost) / Price * 100, 2) AS ProfitMargin
            FROM pizza_profit_analysis
            ORDER BY ProfitMargin DESC;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch margin analysis data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /margin_analysis endpoint: {e}")
        return jsonify({"error": "Error fetching margin analysis data"}), 500


@app.route('/size_cost_efficiency', methods=['GET'])
def size_cost_efficiency():
    """Endpunkt für die Kosteneffizienz der Pizzagrößen"""
    try:
        query = """
            SELECT SKU, Name, Size, Price, production_cost, 
                   ROUND(profit / production_cost, 2) AS CostEfficiency
            FROM pizza_profit_analysis
            ORDER BY SKU, Size;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch size cost efficiency data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /size_cost_efficiency endpoint: {e}")
        return jsonify({"error": "Error fetching size cost efficiency data"}), 500



@app.route('/weekly_orders', methods=['GET'])
def weekly_orders():
    """Endpoint to fetch weekly order counts"""
    try:
        store_id = request.args.get('storeID')
        year = request.args.get('year')
        month = request.args.get('month')

        query = """
        SELECT 
            storeID,
            weekday,
            year,
            month,
            SUM(order_count) AS order_count
        FROM 
            weekly_order_counts
        WHERE 1=1
        """

        conditions = []
        params = {}

        if store_id:
            conditions.append("storeID = %(storeID)s")
            params['storeID'] = store_id

        if year:
            conditions.append("year = %(year)s")
            params['year'] = year

        if month:
            conditions.append("month = %(month)s")
            params['month'] = month

        if conditions:
            query += " AND " + " AND ".join(conditions)

        query += """
        GROUP BY storeID, weekday, year, month
        ORDER BY storeID, FIELD(weekday, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'), year, month
        """

        df = execute_query(query, params=params)
        if df is None:
            return jsonify({"error": "Failed to fetch weekly orders data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /weekly_orders endpoint: {e}")
        return jsonify({"error": "Error fetching weekly orders data"}), 500

@app.route('/get_stores', methods=['GET'])
def get_stores():
    """Endpoint to fetch store IDs"""
    try:
        query = "SELECT DISTINCT storeID FROM stores ORDER BY storeID"
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch stores"}), 500

        data = df.to_dict(orient='records')
        return jsonify(stores=data)
    except Exception as e:
        logging.error(f"Error in /get_stores endpoint: {e}")
        return jsonify({"error": "Error fetching stores"}), 500

@app.route('/get_years', methods=['GET'])
def get_years():
    """Endpoint to fetch distinct years"""
    try:
        query = "SELECT DISTINCT year FROM weekly_order_counts ORDER BY year"
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch years"}), 500

        data = df.to_dict(orient='records')
        return jsonify(years=data)
    except Exception as e:
        logging.error(f"Error in /get_years endpoint: {e}")
        return jsonify({"error": "Error fetching years"}), 500

@app.route('/get_months', methods=['GET'])
def get_months():
    """Endpoint to fetch distinct months"""
    try:
        query = "SELECT DISTINCT month FROM weekly_order_counts ORDER BY month"
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch months"}), 500

        data = df.to_dict(orient='records')
        return jsonify(months=data)
    except Exception as e:
        logging.error(f"Error in /get_months endpoint: {e}")
        return jsonify({"error": "Error fetching months"}), 500


@app.route('/order_activity_per_month', methods=['GET'])
def order_activity_per_month():
    """Endpoint to fetch order activity per month"""
    try:
        store_id = request.args.get('storeID')
        year = request.args.get('year')

        query = """
        SELECT 
            storeID,
            year,
            month,
            order_count
        FROM 
            order_activity_per_month
        WHERE 1=1
        """

        params = {}
        if store_id and store_id != 'all':
            query += " AND storeID = %(storeID)s"
            params['storeID'] = store_id

        if year and year != 'all':
            query += " AND year = %(year)s"
            params['year'] = year

        query += """
        ORDER BY storeID, year, month
        """

        df = execute_query(query, params)
        if df is None:
            return jsonify({"error": "Failed to fetch order activity data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /order_activity_per_month endpoint: {e}")
        return jsonify({"error": "Error fetching order activity data"}), 500


@app.route('/order_activity_per_hour', methods=['GET'])
def order_activity_per_hour():
    """Endpoint to fetch order activity per hour of day"""
    try:
        store_id = request.args.get('storeID')
        year = request.args.get('year')
        month = request.args.get('month')
        week = request.args.get('week')  # Add week parameter if needed

        query = """
        SELECT 
            hour,
            SUM(order_count) AS order_count
        FROM 
            order_activity_per_hour
        WHERE 1=1
        """

        params = {}
        if store_id and store_id != 'all':
            query += " AND storeID = %(storeID)s"
            params['storeID'] = store_id

        if year and year != 'all':
            query += " AND year = %(year)s"
            params['year'] = year

        if month and month != 'all':
            query += " AND month = %(month)s"
            params['month'] = month

        if week and week != 'all':
            query += " AND WEEK(CONCAT(year, '-', month, '-', day)) = %(week)s"
            params['week'] = week

        query += """
        GROUP BY hour
        ORDER BY hour
        """

        logging.debug(f"Executing query: {query} with params: {params}")

        df = execute_query(query, params)
        if df is None:
            return jsonify({"error": "Failed to fetch order activity data"}), 500

        logging.debug(f"Fetched data: {df.head()}")  # Log only the first few rows for debugging

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /order_activity_per_hour endpoint: {e}")
        return jsonify({"error": "Error fetching order activity data"}), 500




@app.route('/sales_data', methods=['GET'])
def sales_data():
    """Endpoint to fetch weekly sales data from pre-aggregated table."""
    try:
        query = """
        SELECT product_name, year, month, total_sales
        FROM monthly_product_sales
        ORDER BY product_name, year, month;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch sales data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /sales_data endpoint: {e}")
        return jsonify({"error": "Error fetching sales data"}), 500



"""stores"""


@app.route('/store_performance', methods=['GET'])
def store_performance():
    """Endpoint to fetch store performance data"""
    try:
        store_id = request.args.get('storeID')
        year = request.args.get('year')
        month = request.args.get('month')
        week = request.args.get('week')

        query = """
        SELECT 
            storeID,
            year,
            month,
            week,
            total_sales
        FROM 
            store_performance
        WHERE 1=1
        """

        conditions = []
        params = {}

        if store_id and store_id != 'all':
            conditions.append("storeID = %(storeID)s")
            params['storeID'] = store_id

        if year:
            conditions.append("year = %(year)s")
            params['year'] = year

        if month:
            conditions.append("month = %(month)s")
            params['month'] = month

        if week:
            conditions.append("week = %(week)s")
            params['week'] = week

        if conditions:
            query += " AND " + " AND ".join(conditions)

        query += " ORDER BY year, month, week"

        df = execute_query(query, params=params)
        if df is None or df.empty:
            return jsonify({"error": "Failed to fetch store performance data"}), 500

        # Format the data for correct date representation
        df['date'] = df.apply(lambda row: f"{row['year']}-{row['month']:02d}", axis=1)
        df = df.groupby('date').agg({'total_sales': 'sum'}).reset_index()

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /store_performance endpoint: {e}")
        return jsonify({"error": "Error fetching store performance data"}), 500




@app.route('/sales_trends', methods=['GET'])
def sales_trends():
    """Endpoint to fetch sales trends data"""
    try:
        store_id = request.args.get('storeID')

        query = """
        SELECT 
            storeID,
            year,
            month,
            total_sales
        FROM 
            sales_trends
        WHERE 1=1
        """

        params = {}
        if store_id and store_id != 'all':
            query += " AND storeID = %(storeID)s"
            params['storeID'] = store_id

        query += " ORDER BY year, month"

        df = execute_query(query, params)
        if df is None:
            return jsonify({"error": "Failed to fetch sales trends data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /sales_trends endpoint: {e}")
        return jsonify({"error": "Error fetching sales trends data"}), 500






@app.route('/category_sales', methods=['GET'])
def category_sales():
    """Endpoint to fetch sales data by product category"""
    try:
        store_id = request.args.get('storeID')
        year = request.args.get('year')
        month = request.args.get('month')
        week = request.args.get('week')

        query = """
        SELECT 
            storeID,
            category,
            product_name,
            year,
            month,
            week,
            total_sales
        FROM 
            category_sales
        WHERE 1=1
        """

        conditions = []
        params = {}

        if store_id:
            conditions.append("storeID = %(storeID)s")
            params['storeID'] = store_id

        if year:
            conditions.append("year = %(year)s")
            params['year'] = year

        if month:
            conditions.append("month = %(month)s")
            params['month'] = month

        if week:
            conditions.append("week = %(week)s")
            params['week'] = week

        if conditions:
            query += " AND " + " AND ".join(conditions)

        query += " ORDER BY category, product_name, year, month, week"

        df = execute_query(query, params=params)
        if df is None:
            return jsonify({"error": "Failed to fetch category sales data"}), 500

        # Aggregate data by category and product name
        df['date'] = df.apply(lambda row: f"{row['year']}-{row['month']:02d}-W{str(row['week']).zfill(2)}", axis=1)
        grouped_df = df.groupby(['category', 'product_name']).agg({'total_sales': 'sum'}).reset_index()

        data = grouped_df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /category_sales endpoint: {e}")
        return jsonify({"error": "Error fetching category sales data"}), 500






@app.route('/store_profitability', methods=['GET'])
def store_profitability():
    """Endpoint to fetch store profitability data"""
    try:
        store_id = request.args.get('storeID')
        year = request.args.get('year')
        month = request.args.get('month')
        week = request.args.get('week')

        query = """
        SELECT 
            storeID,
            year,
            month,
            week,
            totalRevenue,
            totalProfit
        FROM 
            store_profitability
        WHERE 1=1
        """

        conditions = []
        params = {}

        if store_id:
            conditions.append("storeID = %(storeID)s")
            params['storeID'] = store_id

        if year:
            conditions.append("year = %(year)s")
            params['year'] = year

        if month:
            conditions.append("month = %(month)s")
            params['month'] = month

        if week:
            conditions.append("week = %(week)s")
            params['week'] = week

        if conditions:
            query += " AND " + " AND ".join(conditions)

        query += " ORDER BY storeID, year, month, week"

        df = execute_query(query, params=params)
        if df is None:
            return jsonify({"error": "Failed to fetch store profitability data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /store_profitability endpoint: {e}")
        return jsonify({"error": "Error fetching store profitability data"}), 500





@app.route('/product_preferences', methods=['GET'])
def product_preferences():
    """Endpoint to fetch product preferences data"""
    try:
        store_id = request.args.get('storeID')
        year = request.args.get('year')
        month = request.args.get('month')
        week = request.args.get('week')

        query = """
        SELECT 
            product_name,
            SUM(order_count) AS order_count
        FROM 
            product_preferences
        WHERE 1=1
        """

        conditions = []
        params = {}

        if store_id:
            conditions.append("storeID = %(storeID)s")
            params['storeID'] = store_id

        if year:
            conditions.append("year = %(year)s")
            params['year'] = year

        if month:
            conditions.append("month = %(month)s")
            params['month'] = month

        if week:
            conditions.append("week = %(week)s")
            params['week'] = week

        if conditions:
            query += " AND " + " AND ".join(conditions)

        query += " GROUP BY product_name ORDER BY order_count DESC LIMIT 8"

        df = execute_query(query, params=params)
        if df is None:
            return jsonify({"error": "Failed to fetch product preferences data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /product_preferences endpoint: {e}")
        return jsonify({"error": "Error fetching product preferences data"}), 500



"""customers"""



@app.route('/customers_with_orders', methods=['GET'])
def customers_with_orders():
    try:
        query = """
        SELECT
        COUNT(o.orderID) / 25 as order_count,
        c.latitude, c.longitude
        FROM orders o INNER JOIN customers c ON o.customerID = c.customerID 
        GROUP BY o.customerID
        """

        df = execute_query(query)

        if df is None:
            return jsonify({"error": "Failed to fetch customers with orders data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)

    except Exception as e:
        logging.error(f"Error in /customers_with_orders endpoint: {e}")
        return jsonify({"error": "Error fetching customers with orders data"}), 500


@app.route('/average_order_value', methods=['GET'])
def weekly_average_order_value():
    """ Returns the week, the average order value, and the average order count for the specified year """
    try:
        ne_lat = round(float(request.args.get('ne_lat')), 4)
        ne_lng = round(float(request.args.get('ne_lng')), 4)
        sw_lat = round(float(request.args.get('sw_lat')), 4)
        sw_lng = round(float(request.args.get('sw_lng')), 4)
        year = request.args.get('year')

        if year == "all":
            year_condition = ""
        else:
            year_condition = "AND YEAR(o.adjustedOrderDate) = %s"

        query = f"""
SELECT 
    week, 
    AVG(total) AS avg_order_value,
    AVG(order_count) AS avg_order_count_per_customer
FROM (
    SELECT 
        DATE_FORMAT(o.adjustedOrderDate, '%%Y-%%u') AS week, 
        o.total,
        COUNT(o.orderID) OVER (PARTITION BY o.customerID, DATE_FORMAT(o.adjustedOrderDate, '%%Y-%%u')) AS order_count
    FROM 
        extendedorders o
    INNER JOIN 
        stores s 
    ON 
        s.storeID = o.storeID
    WHERE
        s.latitude BETWEEN %s AND %s AND
        s.longitude BETWEEN %s AND %s
        {year_condition}
) subquery
GROUP BY week 
ORDER BY week;
        """

        if year == "all":
            params = (sw_lat, ne_lat, sw_lng, ne_lng)
        else:
            params = (sw_lat, ne_lat, sw_lng, ne_lng, int(year))

        df = execute_query(query, params)

        if df is None:
            return jsonify({"error": "Failed to fetch weekly average order value data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /average_order_value endpoint: {e}")
        return jsonify({"error": "Error fetching weekly average order value data"}), 500


@app.route('/top_customers_filtered', methods=['GET'])
def top_customers_filtered():
    """
    Parameters:
    ne_lat (float): Latitude of the North-East corner of the bounding box.
    ne_lng (float): Longitude of the North-East corner of the bounding box.
    sw_lat (float): Latitude of the South-West corner of the bounding box.
    sw_lng (float): Longitude of the South-West corner of the bounding box.
    year (int): The year to filter the orders.

    Response:
    data (array): An array of customer objects, each containing:
    customer_id (string): The ID of the customer.
    order_count (int): The total number of orders placed by the customer.
    first_order_date (string): The date of the customer's first order.
    """
    try:
        ne_lat = round(float(request.args.get('ne_lat')), 4)
        ne_lng = round(float(request.args.get('ne_lng')), 4)
        sw_lat = round(float(request.args.get('sw_lat')), 4)
        sw_lng = round(float(request.args.get('sw_lng')), 4)
        year = request.args.get('year')

        if year == "all":
            year_condition = ""
        else:
            year_condition = "AND YEAR(o.adjustedOrderDate) = %s"

        sql = f"""
SELECT 
    c.customerID AS customer_id,
    COUNT(o.orderID) AS order_count,
    MIN(o.adjustedOrderDate) AS first_order_date
FROM 
    customers c
INNER JOIN 
    extendedorders o 
ON 
    c.customerID = o.customerID
INNER JOIN 
    stores s 
ON 
    o.storeID = s.storeID
WHERE
    s.latitude BETWEEN %s AND %s AND
    s.longitude BETWEEN %s AND %s
    {year_condition}
GROUP BY 
    c.customerID
ORDER BY 
    order_count DESC
LIMIT 25;"""

        if year == "all":
            params = (sw_lat, ne_lat, sw_lng, ne_lng)
        else:
            params = (sw_lat, ne_lat, sw_lng, ne_lng, int(year))

        df = execute_query(sql, params)

        if df is None:
            return jsonify({"error": "Failed to fetch top customers data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)

    except Exception as e:
        logging.error(f"Error in /top_customers_filtered endpoint: {e}")
        return jsonify({"error": "Error fetching top customers data"}), 500


@app.route('/customer_loyalty', methods=['GET'])
def customer_frequency():
    """
    Parameters:
    ne_lat (float): Latitude of the North-East corner of the bounding box.
    ne_lng (float): Longitude of the North-East corner of the bounding box.
    sw_lat (float): Latitude of the South-West corner of the bounding box.
    sw_lng (float): Longitude of the South-West corner of the bounding box.
    year (int): The year to filter the orders.

    Response:
    data (array): An array of store objects, each containing:
    store_id (string): The ID of the store.
    more_than_15 (int): Number of customers visiting more than 15 times per month.
    more_than_10 (int): Number of customers visiting more than 10 times per month.
    more_than_5 (int): Number of customers visiting more than 5 times per month.
    less_than_5 (int): Number of customers visiting less than 5 times per month.
    """
    try:
        ne_lat = round(float(request.args.get('ne_lat')), 4)
        ne_lng = round(float(request.args.get('ne_lng')), 4)
        sw_lat = round(float(request.args.get('sw_lat')), 4)
        sw_lng = round(float(request.args.get('sw_lng')), 4)
        year = request.args.get('year')

        if year == "all":
            year_condition = ""
        else:
            year_condition = "AND YEAR(o.adjustedOrderDate) = %s"

        sql = f"""
SELECT 
    storeID,
    SUM(CASE WHEN monthly_visits > 15 THEN 1 ELSE 0 END) AS more_than_15,
    SUM(CASE WHEN monthly_visits > 10 AND monthly_visits <= 15 THEN 1 ELSE 0 END) AS more_than_10,
    SUM(CASE WHEN monthly_visits > 5 AND monthly_visits <= 10 THEN 1 ELSE 0 END) AS more_than_5,
    SUM(CASE WHEN monthly_visits <= 5 THEN 1 ELSE 0 END) AS less_than_5
FROM (
    SELECT 
        o.customerID,
        o.storeID,
        COUNT(o.orderID) / 12.0 AS monthly_visits
    FROM 
        extendedorders o
    INNER JOIN 
        stores s 
    ON 
        o.storeID = s.storeID
    WHERE
        s.latitude BETWEEN %s AND %s AND
        s.longitude BETWEEN %s AND %s
        {year_condition}
    GROUP BY 
        o.customerID, o.storeID
) customer_visits
GROUP BY storeID;
        """

        if year == "all":
            params = (sw_lat, ne_lat, sw_lng, ne_lng)
        else:
            params = (sw_lat, ne_lat, sw_lng, ne_lng, int(year))

        df = execute_query(sql, params)

        if df is None:
            return jsonify({"error": "Failed to fetch customer frequency data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)

    except Exception as e:
        logging.error(f"Error in /customer_loyalty endpoint: {e}")
        return jsonify({"error": "Error fetching customer frequency data"}), 500



"""chart für über stores"""

@app.route('/total_revenue', methods=['GET'])
def total_revenue():
    """Endpoint to fetch total revenue for all stores"""
    try:
        query = """
        SELECT 
            storeID,
            SUM(totalRevenue) as total_revenue
        FROM 
            monthly_store_revenue
        GROUP BY 
            storeID
        ORDER BY 
            total_revenue DESC
        """
        df = execute_query(query)
        if df is None or df.empty:
            return jsonify({"error": "Failed to fetch total revenue data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /total_revenue endpoint: {e}")
        return jsonify({"error": "Error fetching total revenue data"}), 500



"""homepage """


@app.route('/order_trends', methods=['GET'])
def order_trends():
    """Endpoint to fetch order trends"""
    try:
        query = """
        SELECT 
            DATE_FORMAT(orderDate, '%Y-%m') AS month, 
            COUNT(orderID) AS orderCount
        FROM 
            orders
        GROUP BY 
            month
        ORDER BY 
            month;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch order trend data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /order_trends endpoint: {e}")
        return jsonify({"error": "Error fetching order trend data"}), 500




@app.route('/customers_per_state', methods=['GET'])
def customers_per_state():
    """Endpoint to fetch customers per state data"""
    try:
        query = """
        SELECT 
            s.state, 
            COUNT(c.customerID) AS customerCount
        FROM 
            customers c
        JOIN stores s ON ABS(c.latitude - s.latitude) < 0.5 AND ABS(c.longitude - s.longitude) < 0.5
        GROUP BY s.state
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch customers per state data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /customers_per_state endpoint: {e}")
        return jsonify({"error": "Error fetching customers per state data"}), 500








# Endpoint for Total Quantity per Product
@app.route('/total_quantity_per_product', methods=['GET'])
def total_quantity_per_product():
    """Endpoint to fetch total quantity per product data"""
    try:
        query = """
        SELECT 
            p.Name AS productName, 
            COUNT(oi.orderItemID) AS totalQuantity
        FROM 
            orderItems oi
        JOIN products p ON oi.SKU = p.SKU
        GROUP BY 
            p.Name
        ORDER BY 
            totalQuantity DESC
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch total quantity per product data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /total_quantity_per_product endpoint: {e}")
        return jsonify({"error": "Error fetching total quantity per product data"}), 500

@app.route('/total_revenue_per_store', methods=['GET'])
def total_revenue_per_store():
    """Endpoint to fetch total revenue per store"""
    try:
        query = """
        SELECT s.storeID, SUM(o.total) AS totalRevenue
        FROM orders o
        JOIN stores s ON o.storeID = s.storeID
        GROUP BY s.storeID
        ORDER BY totalRevenue DESC
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch total revenue per store data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /total_revenue_per_store endpoint: {e}")
        return jsonify({"error": "Error fetching total revenue per store data"}), 500



@app.route('/stores_per_state', methods=['GET'])
def stores_per_state():
    """Endpoint to fetch store count per state"""
    try:
        query = """
        SELECT 
            state, 
            COUNT(storeID) AS storeCount
        FROM 
            stores
        GROUP BY 
            state
        ORDER BY 
            state;
        """
        df = execute_query(query)
        if df is None:
            return jsonify({"error": "Failed to fetch store count per state data"}), 500

        data = df.to_dict(orient='records')
        return jsonify(data=data)
    except Exception as e:
        logging.error(f"Error in /stores_per_state endpoint: {e}")
        return jsonify({"error": "Error fetching store count per state data"}), 500




if __name__ == '__main__':
    app.run(port=8080, debug=True)
