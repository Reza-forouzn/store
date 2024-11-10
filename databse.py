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
cd = 0
lt = list()
if len(d) == 0 :
    print("store database has no table")
    x = input("please insert the table name: ")
    cd = 1
    
if len(d) != 0 :
    for row in d:
        # print(row[0])
        lt.append(row[0])
    
    print ("The store databse table name(s) are as follow: " ,"\n",' ,'.join(lt))

x = input("please insert the table name: ")
x.replace(" ", "")
while x.isalpha() != True:
    x = input("please insert valid table name: ")
x.lower
# if x.isalpha() == True:
#     x = x.lower
# else: 
#     x = input("please insert the table name: ")

if cd == 1:
    ed = 1
else:
    ed = 0
    
while ed == 0:
    if x in lt:
        x = input("table name exists, please insert new table name: ")
        x.replace(" ", "")
        while x.isalpha() != True:
            x = input("please insert valid table name: ")
        x = x.lower

    else: 
        query = ("CREATE TABLE store.%s ()ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;" % (x))
        cursor.execute(query)
        cnx.commit()
        print ("new table inserted to database")
        ed = 1



cnx.close()