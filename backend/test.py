import pymysql

# Establish a database connection
connection = pymysql.connect(
    host='localhost',
    user='root',
    password='Pizzaservice123!',
    database='pizzadata'
)

try:
    with connection.cursor() as cursor:
        # Select all columns for medium-sized pizzas from the products table
        cursor.execute("SELECT * FROM products WHERE Size='Medium'")
        medium_pizzas = cursor.fetchall()

    # Display the results
    if medium_pizzas:
        print("Medium-sized pizzas:")
        for pizza in medium_pizzas:
            print(pizza)
    else:
        print("No medium-sized pizzas found.")

finally:
    connection.close()
