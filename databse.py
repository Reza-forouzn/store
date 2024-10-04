import mysql.connector


cnx = mysql.connector.connect(user="store",password="store",host="127.0.0.1",database="store",collation="utf8mb4_unicode_ci", charset="utf8mb4",)
print ("connected to db")
cursor = cnx.cursor()
query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'store';"
# query = "SELECT * WHERE table_schema = 'store'"
# cursor= cnx.cursor()
# d = cursor.execute(query)
cursor.execute(query)
d = cursor.fetchall() 
# print (d)
# print (type (d))
# print (len(d))
lt = list()
if len(d) == 0 :
    print("store database has no table")
    
if len(d) != 0 :
    for row in d:
        # print(row[0])
        lt.append(row[0])
    
    print ("The store databse table name(s) are as follow: " ,"\n",' ,'.join(lt))

x = input("please insert the table name: ")


cnx.close()
