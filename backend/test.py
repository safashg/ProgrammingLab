from flask import Flask, jsonify
import mysql.connector

app = Flask(__name__)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Pizzaservice123!',
    'database': 'your_database_name',  # replace with your actual database name
    'port': 3306  # default port for MySQL, can be omitted
}


@app.route('/store/most_orders', methods=['GET'])
def store_with_most_orders():
    try:
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor(dictionary=True)

        query = """
        SELECT storeID, COUNT(orderID) AS order_count
        FROM orders
        GROUP BY storeID
        ORDER BY order_count DESC
        LIMIT 1
        """
        cursor.execute(query)
        result = cursor.fetchone()

        cursor.close()
        connection.close()

        if result:
            return jsonify({"storeID": result['storeID'], "order_count": result['order_count']})
        else:
            return jsonify({"message": "No orders found"}), 404
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500


if __name__ == '__main__':
    app.run(debug=True)
