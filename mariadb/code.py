import mysql.connector


cnx = mysql.connector.connect(user="test",password="test",host="127.0.0.1",database="test",collation="utf8mb4_unicode_ci", charset="utf8mb4",)
print ("connected to db")
cursor = cnx.cursor()
query = "select * from people"
d = cursor.execute(query)
print (d)
cnx.close()