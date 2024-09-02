import mysql.connector
import datetime

cnx = mysql.connector.connect(user="test",password="test",host="127.0.0.1",database="test",collation="utf8mb4_unicode_ci", charset="utf8mb4",)

# cursor = cnx.cursor()
cursor = cnx.cursor(buffered=True)

query = "Show tables;"
cursor.execute(query) 
l1 = cursor.fetchall()

if len(l1) == 0:
    print ("database is empty for now")
else:
    s = ""
    for i in range (0,len(l1)):
        s += str(l1[i])
    print ("databses tables are as follow: \n%s" %s)

table = input ("please enter table name: ")
# domain = input ("please enter domain name: ")
# date = input('Enter a date in YYYY-MM-DD format: ')

query = "SELECT * FROM `{}`".format(table)
cursor.execute(query)
# cursor.execute("INSERT INTO `%s` VALUES (%%s, %%s)" % table, (domain, date))

rows = cursor.fetchall()

# Fetch and display column names
# cursor.execute(f"DESCRIBE `{table}`;")
# columns = cursor.fetchall()
# column_names = [col[0] for col in columns]


print (rows)
cnx.commit()
cnx.close()