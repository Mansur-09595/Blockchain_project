from app import mysql, session
from blockchain import Block, Blockchain

#настраиваемые исключения для ошибок транзакций
class InvalidTransactionException(Exception): pass
class InsufficientFundsException(Exception): pass

class Table():
    def __init__(self, table_name, *args):
        self.table = table_name
        self.columns = "(%s)" %",".join(args)
        self.columnsList = args

        #если таблицы еще нет, создайте ее.
        if isnewtable(table_name):
            create_data = ""
            for column in self.columnsList:
                create_data += "%s varchar(100)," %column

            cur = mysql.connection.cursor() #создать таблицу
            cur.execute("CREATE TABLE %s(%s)" %(self.table, create_data[:len(create_data)-1]))
            cur.close()

    def getall(self):
        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM %s" %self.table)
        data = cur.fetchall(); return data

    def getone(self, search, value):
        data = {}; cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM %s WHERE %s = \"%s\"" %(self.table, search, value))
        if result > 0: data = cur.fetchone()
        cur.close(); return data

    def deleteone(self, search, value):
        cur = mysql.connection.cursor()
        cur.execute("DELETE from %s where %s = \"%s\"" %(self.table, search, value))
        mysql.connection.commit(); cur.close()

    #Удалить все значения из таблицы
    def deleteall(self):
        self.drop() #удалить таблицу и создать заново
        self.__init__(self.table, *self.columnsList)

    def drop(self):
        cur = mysql.connection.cursor()
        cur.execute("DROP TABLE %s" %self.table)
        cur.close()

    def insert(self, *args):
        data = ""
        for arg in args: #преобразовать данные в строковый формат mysql
            data += "\"%s\"," %(arg)

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO %s%s VALUES(%s)" %(self.table, self.columns, data[:len(data)-1]))
        mysql.connection.commit()
        cur.close()

def sql_raw(execution):
    cur = mysql.connection.cursor()
    cur.execute(execution)
    mysql.connection.commit()
    cur.close()

#Проверить, существует ли уже таблица
def isnewtable(tableName):
    cur = mysql.connection.cursor()

    try:
        results = cur.execute("SELECT * from  %s" %tableName)
        cur.close()
    except:
        return True
    else:
        return False

#Проверить, существует ли пользователь
def isnewuser(username):
    users = Table("users", "name", "email", "username", "password")
    data = users.getall()
    usernames = [user.get('username') for user in data]

    return False if username in usernames else True

#Oтправить деньги от одного пользователя к другому
def send_money(sender, recipient, amount):
    try: amount = float(amount)
    except ValueError:
        raise InvalidTransactionException("Invalid Transaction.")
    
    #Проверка, что у пользователя достаточно денег для отправки (исключение, если это БАНК)
    if amount > get_balance(sender) and sender != "BANK":
        raise InsufficientFundsException("Insufficient Funds.")

    #Проверка, что пользователь не отправляет деньги себе или сумма меньше или равна 0
    elif sender == recipient or amount <= 0.00:
        raise InvalidTransactionException("Invalid Transaction.")

    #Проверка, что получатель существует
    elif isnewuser(recipient):
        raise InvalidTransactionException("User Does Not Exist.")

    #обновить блокчейн и синхронизироваться с mysql
    blockchain = get_blockchain()
    number = len(blockchain.chain) + 1
    data = "%s-->%s-->%s" %(sender, recipient, amount)
    blockchain.mine(Block(number, data=data))
    sync_blockchain(blockchain)
    
#Получить баланс пользователя
def get_balance(username):
    balance = 0.00
    blockchain = get_blockchain()

    #цикл через блокчейн и обновление баланса
    for block in blockchain.chain:
        data = block.data.split("-->")
        if username == data[0]:
            balance -= float(data[2])
        elif username == data[1]:
            balance += float(data[2])
    return balance

#Получить блокчейн из mysql и преобразовать в объект Blockchain
def get_blockchain():
    blockchain = Blockchain()
    blockchain_sql = Table("blockchain", "number", "hash", "previous", "data", "nonce")
    for blocks in blockchain_sql.getall():
        blockchain.add(Block(int(blocks.get('number')), blocks.get('previous'), blocks.get('data'), blocks.get('nonce')))
    
    return blockchain

#Обновить блокчейн в таблице mysql
def sync_blockchain(blockchain):
    blockchain_sql = Table("blockchain", "number", "hash", "previous", "data", "nonce")
    blockchain_sql.deleteall()

    for block in blockchain.chain:
        blockchain_sql.insert(str(block.number), block.hash(), block.previous_hash, block.data, block.nonce)

# def test():
#     blockchain = Blockchain()
#     database = ["hello", "goodbye", "test", "DATA here"]

#     num = 0

#     for data in database:
#         num += 1
#         blockchain.mine(Block(number=num, data=data))

#     sync_blockchain(blockchain)