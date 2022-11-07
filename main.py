import uuid
import psycopg2
import requests
import time
import json
from datetime import datetime, timedelta
from pytz import timezone


# тестовая программа для проверки взаимодействия между АСА и Скорпион
# По сути представляет из себя набор тестов, соответствующий таблицам http://192.168.10.207:8090/pages/viewpage.action?pageId=143262262
# и http://192.168.10.207:8090/pages/viewpage.action?pageId=146964664
# нумероваться тесты будут в соответствии с номерами строк данных таблиц

# заявка
class zvk(object):
    def __init__(self, dcAipCode=None, equipment_cim_id=None, userState=None, workState=None, ZVKdevState=None, totalRepDBeg=None, totalRepDEnd=None, send_timestamp=None,
                 db_host=None, db_user=None, db_password=None, db_name=None, db_port=None, zvk_address=None, token=None):

        self.db_host = db_host
        self.db_user = db_user
        self.db_password = db_password
        self.db_name = db_name
        self.db_port = db_port

        self.zvk_address = zvk_address
        self.token = token

        # необходимо убедится что guid заявки уникальный
        guid = uuid.uuid4()
        check_request = db_request(host=self.db_host, user=self.db_user, password=self.db_password, database=self.db_name, port=self.db_port,
                                   request_str="SELECT guid FROM repairs.zvk WHERE guid='"+str(guid)+"';")
        while check_request.execute_request() != []:
            guid = uuid.uuid4()
            check_request = db_request(host=self.db_host, user=self.db_user, password=self.db_password, database=self.db_name, port=self.db_port,
                                       request_str="SELECT guid FROM repairs.zvk WHERE guid='" + str(guid) + "';")
        self.guid = str(guid)

        # cim_id диспетчерского центра
        self.dcAipCode = dcAipCode
        # mrid  оборудования
        # необходимо из cim_id получить mrid
        if equipment_cim_id != None:
            mrid_request = db_request(host=self.db_host, user=self.db_user, password=self.db_password, database=self.db_name, port=self.db_port,
                                       request_str="SELECT master_resource_identifier FROM equipment.equipment_base WHERE cim_id='"+str(equipment_cim_id)+"' LIMIT 1;")
            mrid = str(mrid_request.execute_request()[0][0])

            if mrid != "None":
                self.deviceGUID = mrid
            else:
                self.deviceGUID = 'null'
        else:
            self.deviceGUID = None

        self.userState = userState
        self.workState = workState
        self.ZVKdevState = ZVKdevState
        self.totalRepDBeg = totalRepDBeg
        self.totalRepDEnd = totalRepDEnd

        self.send_timestamp = send_timestamp

    #медод формирования новой заявки
    def send_zvk(self):
        headers = {'accept': 'application/json', 'Authorization': self.token, 'Content-Type': 'application/json'}

        zvk_json = [
            {
                "guid": self.guid,
                "id": 100,
                "dcAipCode": self.dcAipCode,
                "selfNum": 11111,
                "alienNum": 55555,
                "enterpriseName": "test enterpriseName",
                "categoryName": "неплановая",
                "userState": self.userState,
                "workState": self.workState,
                "deviceType": "test deviceType",
                "prevZVKId": 0,
                "nextZVKId": 0,
                "zvkDeviceState": self.ZVKdevState,
                "deviceGUID": self.deviceGUID,
                "repairType": "test repairType",
                "emergencyReadiness": "04:00",
                "grounding": "test grounding",
                "planDBeg": self.totalRepDBeg,
                "planDEnd": self.totalRepDEnd,
                "needRepDBeg": self.totalRepDBeg,
                "needRepDEnd": self.totalRepDEnd,
                "permRepDBeg": self.totalRepDBeg,
                "permRepDEnd": self.totalRepDEnd,
                "factRepDBeg": self.totalRepDBeg,
                "factRepDEnd": self.totalRepDEnd,
                "totalRepDBeg": self.totalRepDBeg,
                "totalRepDEnd": self.totalRepDEnd,
                "repairContent": "test repairContent",
                "origin": "test origin"
            }
        ]

        response = requests.post(url=str(self.zvk_address)+'zvk/merge', data=json.dumps(zvk_json).encode('utf-8'), headers=headers)

        if response.status_code == 200:
            self.send_timestamp = datetime.now()
            return response.content
        else:
            return 'Error: '+ str(response.content)

    # метод получения информации о заявке по guid
    def getZVK(self, guid):
        headers = {'accept': 'application/json', 'Authorization': self.token}
        response = requests.get(url=str(self.zvk_address)+'zvk/search', params={'guid': guid, 'top': 50, 'rowspPage': 50}, headers=headers)
        if response.status_code == 200:
            return response.content.decode('utf-8')
        else:
            return 'Error: '+ str(response.content)

    #метод изменения заявки по guid
    def edit_zvk(self, guid, param_name:str, value):
        headers = {'accept': 'application/json', 'Authorization': self.token, 'Content-Type': 'application/json'}
        zvk_json = json.loads(self.getZVK(guid))
        for z in zvk_json:
            z[param_name] = value
            response = requests.post(url=str(self.zvk_address)+'zvk/merge?mergeOn=guid', data=b'['+json.dumps(z).encode('utf-8')+b']', headers=headers)

            if response.status_code != 200:
                print('Error: '+ str(response.content))

    #метод закрытия заявки по guid
    def close_zvk(self, guid):
        timestamp_10 = str(datetime.now(timezone('Europe/Moscow')) - timedelta(days=5)).replace(' ', 'T')
        self.edit_zvk(guid, "workState", "wsClosed")
        self.edit_zvk(guid, "factRepDEnd", timestamp_10)

    #метод удаления заявки из БД
    def delete_zvk(self, guid):
        headers = {'accept': 'application/json', 'Authorization': self.token}
        zvk_json = json.loads(self.getZVK(guid))
        for z in zvk_json:
            response = requests.delete(url=str(self.zvk_address)+'zvk/'+str(z['internalId']), headers=headers)
            if response.status_code != 200:
                print('Error: '+ str(response.content))

# ТС
class signal(object):
    def __init__(self, dateTime, inService, cim_id, stateSourceId, send_timestamp=None,
                 db_host=None, db_user=None, db_password=None, db_name=None, db_port=None, signal_address=None, token=None):

        self.db_host = db_host
        self.db_user = db_user
        self.db_password = db_password
        self.db_name = db_name
        self.db_port = db_port

        self.signal_address = signal_address
        self.token = token


        self.dateTime = str(dateTime).replace(" ", "T")
        self.inService = inService
        self.cim_id = cim_id
        # необходимо из cim_id получить ScorpId
        scorpId_request = db_request(host=self.db_host, user=self.db_user, password=self.db_password, database=self.db_name, port=self.db_port,
                                  request_str="SELECT id FROM equipment.equipment_base WHERE cim_id='" + str(cim_id) + "' LIMIT 1;")
        scorpId = str(scorpId_request.execute_request()[0][0])
        self.scorpId = scorpId
        # необходимо из cim_id получить mrid
        mrid_request = db_request(host=self.db_host, user=self.db_user, password=self.db_password, database=self.db_name, port=self.db_port,
                                     request_str="SELECT master_resource_identifier FROM equipment.equipment_base WHERE cim_id='" + str(
                                         cim_id) + "' LIMIT 1;")
        mrid = str(mrid_request.execute_request()[0][0])
        self.mrid = mrid
        self.stateSourceId = stateSourceId
        self.send_timestamp = send_timestamp

    def send_signal(self):
        headers = {'accept': 'application/json', 'Authorization': self.token, 'Content-Type': 'application/json'}
        signal_json = [
            {
                "dateTime": self.dateTime,
                "inService": self.inService,
                "ScorpId": self.scorpId,
                "stateSourceId": self.stateSourceId
            }
        ]
        self.send_timestamp = str(datetime.now(timezone('Europe/Moscow'))).replace(" ", "T")
        time.sleep(10)
        response = requests.post(url=str(self.signal_address)+'states/update-states', data=json.dumps(signal_json).encode('utf-8'), headers=headers)
        if response.status_code == 200:
            return response.content
        else:
            return 'Error: '+ str(str(response.content).encode('utf-8').decode())

    # метод проверки полученного json
    def check_result(self, check_timestamp):
        query_check_json_in_db = db_request(host=self.db_host, user=self.db_user, password=self.db_password, database=self.db_name, port=self.db_port,
                                            request_str="SELECT data::json->>'equipment_id' AS equipment_cim_id, " +
                                                        "data::json->>'state' AS equipment_state, " +
                                                        "data::json->>'reason' AS reason, " +
                                                        "data::json->>'time_stamp' AS signal_timestamp, " +
                                                        "data::json->>'equipment_type' AS equipment_type, " +
                                                        "receipted_time " +
                                                        "FROM public.asm_service_scorpion_json " +
                                                        "WHERE receipted_time > '" + check_timestamp + "' " +
                                                        "ORDER BY receipted_time DESC ;")
        return query_check_json_in_db.execute_request()

class db_request(object):
    def __init__(self, host, user, password, database, port, request_str):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.request_str = request_str

    def execute_request(self):
        connection = psycopg2.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database,
            port=self.port
        )
        connection.autocommit = True
        try:
            with connection.cursor() as cursor:
                cursor.execute(self.request_str)
                return cursor.fetchall()
        except Exception as ex:
            print(ex)
            return None
        finally:
            if connection:
                connection.close()


if __name__ == '__main__':

    # url_create_zvk = 'http://192.168.10.15:1114/api/repairsservice/repairs/zvk/merge'
    # url_get_zvk = 'http://192.168.10.15:1114/api/repairsservice/repairs/zvk/search'
    # url_edit_zvk = 'http://192.168.10.15:1114/api/repairsservice/repairs/zvk/merge?mergeOn=guid'
    # url_signal = 'http://192.168.10.15:1113/api/stateservice/states/update-states'
    #my_token = 'Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJodHRwOi8vc2NoZW1hcy5kaXZpc2lvbnoucnUvYXBpL2lkZW50aXR5L2NsYWltcy9zeXNhZG1pbiI6IlRydWUiLCJodHRwOi8vc2NoZW1hcy54bWxzb2FwLm9yZy93cy8yMDA1LzA1L2lkZW50aXR5L2NsYWltcy9uYW1lIjoic3lzdGVtIiwibmJmIjoxNjY2NDQ3MjE4LCJleHAiOjE2NjY1MDcyNzgsImlzcyI6IkRpdmlzaW9ueiIsImF1ZCI6Imh0dHA6Ly9sb2NhbGhvc3Q6NTkzOTIifQ.Bs4EsVHqGaPb8OBBCfDucNOU6OVlcX2ePtwrZXGPVfJab1jHWMvs3d2_BAea1qf7VqpgvlhyFpMSBpMrCoVgNi1rNCTlH5PGn0oQ2C2dZlfiZPbW_lE8E9jdBvUEoqNQofH_hIfmjL-3cpJCcB0wMD6MlTJ-yo_Vqt-NQrEvZnCuUCk7kQz9YZeWJhob8_jSlX2FJcInUBybSh3ks_qt7u-cnlDFP8VduZMzjanhVfGyorrUcpzO4HqPL82ZCt-GFzUqdH-9K1xgxxos7qt3lTtGwOVlcvsMzOPw3S8lXVZ8dvRMoaIq_YlA2Cl4uVo1vBX-gheD9OV4p4nMPt21Jg'
    # #cim_id оборудования с нормальным состоянием true
    # cim_id_normal_true = '066d1608-a368-44de-9afa-33bd46a4e41b'
    # # cim_id оборудования с нормальным состоянием false
    # cim_id_normal_false = '4ab359c8-131c-4a71-ad6f-4b46335e7b28'
    # # cim_id выключателя
    # cim_id_breaker = '4ab359c8-131c-4a71-ad6f-4b46335e7b28'
    # # id диспетчерского центра для создания заявки на оборудование с нормальным состоянием true
    # dcAipCode_normal_true = '2fc94e33-9cf1-4e8a-ac66-2b99c7fac3b6'
    # # id диспетчерского центра для создания заявки на оборудование с нормальным состоянием false
    # dcAipCode_normal_false = '2fc94e33-9cf1-4e8a-ac66-2b99c7fac3b6'

    with open('settings.json') as f:
        settings_file = json.load(f)

    zvk_address = settings_file['repairsService_address']
    signal_address = settings_file['stateService_address']
    my_token = settings_file['token']
    cim_id_normal_true = settings_file['cim_id_normal_true']
    dcAipCode_normal_true = settings_file['dcAipCode_normal_true']
    cim_id_normal_false = settings_file['cim_id_normal_false']
    dcAipCode_normal_false = settings_file['dcAipCode_normal_false']
    cim_id_breaker = settings_file['cim_id_breaker']
    dcAipCode_breaker = settings_file['dcAipCode_breaker']
    stateSourceId = settings_file['stateSourceId']

    db_host = settings_file['db_host']
    db_user = settings_file['db_user']
    db_password = settings_file['db_password']
    db_name = settings_file['db_name']
    db_port = settings_file['db_port']

    #метка времени до которой нужно проверять наличие полученных json-ов
    check_timestamp = ''

    #Состояние оборудования совпадает с предыдущим состоянием
    #п.1
    # сформируем сигнал для приведения состояния оборудования к состоянию true
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    #подождем 30 сек
    time.sleep(10)
    #повторно сформируем сигнал для приведения состояния оборудования к состоянию true
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    #подождем 30 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id:
            i+=1
    if i == 0:
        print("Тест Состояние оборудования совпадает с предыдущим состоянием п.1: ОК")
    else:
        print("Тест Состояние оборудования совпадает с предыдущим состоянием п.1: Error")

    # п.2
    # сформируем сигнал для приведения состояния оборудования к состоянию false
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 30 сек
    time.sleep(10)
    # повторно сформируем сигнал для приведения состояния оборудования к состоянию false
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 30 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id:
            i += 1
    if i == 0:
        print("Тест Состояние оборудования совпадает с предыдущим состоянием п.2: ОК")
    else:
        print("Тест Состояние оборудования совпадает с предыдущим состоянием п.2: Error")

    # #-------------------------------------------------------------------------------------------------------
    #
    # # Нет заявки
    # # п.3.1
    # сформируем сигнал для приведения исходного состояния оборудования к состоянию true
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # подождем 10 сек
    time.sleep(10)

    # закроем для оборудования все открытые заявки и заявки с неопределённым состоянием на текущий момент для оборудования с нормальным состоянием true
    zvk_request = db_request(host=db_host, user=db_user, password=db_password, database=db_name, port=db_port,
                             request_str="SELECT guid FROM repairs.zvk WHERE device_guid = '" + signal_1.mrid + "' " +
                                         "--AND work_state in ('wsOpened', 'wsNone') " +
                                         "ORDER BY total_rep_d_end DESC")

    z = zvk(zvk_address=zvk_address, token=my_token, db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port)
    timestamp_10 = str(datetime.now(timezone('Europe/Moscow'))-timedelta(days=5)).replace(' ', 'T')
    for z_guid in zvk_request.execute_request():
        z.edit_zvk(z_guid[0], "workState", "wsClosed")
        z.edit_zvk(z_guid[0], "factRepDEnd", timestamp_10)

    # сформируем сигнал для аварийного отключения оборудования (состоянию false)
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'false' and j[2] == 'true':
            i += 1
    if i == 1:
        print("Тест Нет заявки п.3.1: ОК")
    else:
        print("Тест Нет заявки п.3.1: Error")

    # п.3.2
    # сформируем сигнал для приведения исходного состояния оборудования к состоянию true
    signal_2 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_false, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_2.send_signal()
    # подождем 10 сек
    time.sleep(10)
    # закроем для оборудования все открытые заявки и заявки с неопределённым состоянием на текущий момент для оборудования с нормальным состоянием false
    zvk_request = db_request(host=db_host, user=db_user, password=db_password, database=db_name, port=db_port,
                             request_str="SELECT guid FROM repairs.zvk WHERE device_guid = '" + signal_2.mrid + "' " +
                                         "--AND work_state in ('wsOpened', 'wsNone') " +
                                         "ORDER BY total_rep_d_end DESC")

    z = zvk(zvk_address=zvk_address, token=my_token, db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port)
    timestamp_10 = str(datetime.now(timezone('Europe/Moscow')) - timedelta(days=5)).replace(' ', 'T')
    for z_guid in zvk_request.execute_request():
        z.edit_zvk(z_guid[0], "workState", "wsClosed")
        z.edit_zvk(z_guid[0], "factRepDEnd", timestamp_10)

    # сформируем сигнал для оперативного отключения оборудования (состоянию false)
    signal_2 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_false, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_2.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_2.check_result(signal_2.send_timestamp):
        if j[0] == signal_2.cim_id and j[1] == 'false' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Нет заявки п.3.2: ОК")
    else:
        print("Тест Нет заявки п.3.2: Error")


    # п.4.1
    # сформируем сигнал для приведения исходного состояния оборудования к состоянию false
    timestamp_1 = str(datetime.now(timezone('Europe/Moscow')))
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)
    # сформируем сигнал для оперативного включения оборудования (состоянию true)
    timestamp_1 = str(datetime.now(timezone('Europe/Moscow')))
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Нет заявки п.4.1: ОК")
    else:
        print("Тест Нет заявки п.4.1: Error")

    # п.4.2
    # сформируем сигнал для приведения исходного состояния оборудования к состоянию false
    signal_2 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_false, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_2.send_signal()
    # подождем 10 сек
    time.sleep(10)
    # сформируем сигнал для оперативного включения оборудования (состоянию true)

    signal_2 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_false, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_2.send_signal()

    # подождем 30 сек
    time.sleep(10)

    i = 0
    for j in signal_2.check_result(signal_2.send_timestamp):
        if j[0] == signal_2.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Нет заявки п.4.2: ОК")
    else:
        print("Тест Нет заявки п.4.2: Error")


    #--------------------------------------------------------------------------------------------------------
    # Есть заявка в статусе Разрешенная, но не Открытая
    # п.5
    # приведем оборудование в исходное состояние true
    timestamp_1 = str(datetime.now(timezone('Europe/Moscow')))
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()


    # создавдим новую разрешенную, но не открытую заявку
    timestamp_start_zvk = str(datetime.now(timezone('Europe/Moscow')) - timedelta(days=1)).replace(' ', 'T')
    timestamp_end_zvk = str(datetime.now(timezone('Europe/Moscow')) + timedelta(days=1)).replace(' ', 'T')
    z1 = zvk(dcAipCode_normal_true, cim_id_normal_true, 'usAllowed', 'wsNone', 'dsOff ',
             timestamp_start_zvk, None, zvk_address=zvk_address, token=my_token,
             db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port)

    z1.send_zvk()
    # подождем 10 сек
    time.sleep(10)

    # сформируем сигнал оперативного отключения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'false' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная, но не Открытая п.5: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная, но не Открытая п.5: Error")

    # п.6
    # приведем оборудование в исходное состояние true
    timestamp_1 = str(datetime.now(timezone('Europe/Moscow')))
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим ранее созданную разрешенную, но не открытую заявку
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOn')

    # подождем 10 сек
    time.sleep(10)

    # сформируем сигнал аварийного отключения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'false' and j[2] == 'true':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная, но не Открытая п.6: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная, но не Открытая п.6: Error")


    # п.7
    # приведем оборудование в исходное состояние true
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим ранее созданную разрешенную, но не открытую заявку
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsNone')

    # подождем 10 сек
    time.sleep(10)

    # сформируем сигнал аварийного отключения оборудования
    timestamp_1 = str(datetime.now(timezone('Europe/Moscow')))
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'false' and j[2] == 'true':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная, но не Открытая п.7: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная, но не Открытая п.7: Error")


    # п.8
    # приведем оборудование в исходное состояние false
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим ранее созданную разрешенную, но не открытую заявку
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOff')
    # подождем 10 сек
    time.sleep(10)

    # сформируем сигнал оперативного включения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная, но не Открытая п.8: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная, но не Открытая п.8: Error")


    # п.9
    # приведем оборудование в исходное состояние false
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим ранее созданную разрешенную, но не открытую заявку
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOn')
    # подождем 10 сек
    time.sleep(10)

    # сформируем сигнал оперативного включения оборудования
    timestamp_1 = str(datetime.now(timezone('Europe/Moscow')))
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная, но не Открытая п.9: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная, но не Открытая п.9: Error")


    # п.10
    # приведем оборудование в исходное состояние false
    timestamp_1 = str(datetime.now(timezone('Europe/Moscow')))
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                        db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим ранее созданную разрешенную, но не открытую заявку
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsNone')
    # подождем 10 сек
    time.sleep(10)

    # сформируем сигнал оперативного включения оборудования
    timestamp_1 = str(datetime.now(timezone('Europe/Moscow')))
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная, но не Открытая п.10: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная, но не Открытая п.10: Error")

    #----------------------------------------------------------------------------------------------------------
    # Есть заявка в статусе Разрешенная и Открытая
    #п.11
    # приведем оборудование в исходное состояние true
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    #изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOff')
    z1.edit_zvk(z1.guid, 'workState', 'wsOpened')
    z1.edit_zvk(z1.guid, 'factRepDEnd', None)
    z1.edit_zvk(z1.guid, 'totalRepDEnd', None)
    # подождем 10 сек
    time.sleep(10)

    # сформируем сигнал оперативного отключения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'false' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная и Открытая п.11: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная и Открытая п.11: Error")

    #п.12
    # приведем оборудование в исходное состояние true
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOn')

    # сформируем сигнал аварийного отключения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'false' and j[2] == 'true':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная и Открытая п.12: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная и Открытая п.12: Error")


    #п.13
    # приведем оборудование в исходное состояние true
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk( z1.guid, 'zvkDeviceState', 'dsNone')

    # сформируем сигнал аварийного отключения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'false' and j[2] == 'true':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная и Открытая п.13: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная и Открытая п.13: Error")


    # п.14
    # приведем оборудование в исходное состояние false
    timestamp_1 = str(datetime.now(timezone('Europe/Moscow')))
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOff')

    # сформируем сигнал оперативного включения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная и Открытая п.14: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная и Открытая п.14: Error")

    # п.15
    # приведем оборудование в исходное состояние false
    timestamp_1 = str(datetime.now(timezone('Europe/Moscow')))
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOn')

    # сформируем сигнал оперативного включения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная и Открытая п.15: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная и Открытая п.15: Error")


    # п.16
    # приведем оборудование в исходное состояние false
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsNone')

    # сформируем сигнал оперативного включения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная и Открытая п.16: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная и Открытая п.16: Error")


    #------------------------------------------------------------------------------------------------------------
    # Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит уже после закрытия заявки)
    # п.17
    # приведем оборудование в исходное состояние true
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOff')
    z1.edit_zvk(z1.guid, 'workState', 'wsClosed')
    z1.edit_zvk(z1.guid, 'factRepDEnd', str(signal_1.send_timestamp).replace(" ", "T"))

    # сформируем сигнал аварийного отключения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'false' and j[2] == 'true':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит уже после закрытия заявки) п.17: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит уже после закрытия заявки) п.17: Error")


# п.18
    # приведем оборудование в исходное состояние true
    timestamp_1 = str(datetime.now(timezone('Europe/Moscow')))
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOn')

    # сформируем сигнал аварийного отключения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'false' and j[2] == 'true':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит уже после закрытия заявки) п.18: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит уже после закрытия заявки) п.18: Error")


# п.19
    # приведем оборудование в исходное состояние true
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsNone')

    # сформируем сигнал аварийного отключения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'false' and j[2] == 'true':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит уже после закрытия заявки) п.19: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит уже после закрытия заявки) п.19: Error")


# п.20
    # приведем оборудование в исходное состояние false
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOff')

    # сформируем сигнал оперативного включения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит уже после закрытия заявки) п.20: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит уже после закрытия заявки) п.20: Error")


# п.21
    # приведем оборудование в исходное состояние false
    timestamp_1 = str(datetime.now(timezone('Europe/Moscow')))
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOn')

    # сформируем сигнал оперативного включения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит уже после закрытия заявки) п.21: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит уже после закрытия заявки) п.21: Error")


# п.22
    # приведем оборудование в исходное состояние false
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsNone')

    # сформируем сигнал оперативного включения оборудования
    timestamp_1 = str(datetime.now(timezone('Europe/Moscow')))
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит уже после закрытия заявки) п.22: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит уже после закрытия заявки) п.22: Error")

#-------------------------------------------------------------------------------------------------
# Есть заявка в статусе Разрешенная, но Снятая
# п.23
    # приведем оборудование в исходное состояние true
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOn')
    z1.edit_zvk(z1.guid, 'workState', 'wsNone')
    z1.edit_zvk(z1.guid, 'userState', 'usDenyed')
    z1.edit_zvk(z1.guid, 'factRepDEnd', str(datetime.now(timezone('Europe/Moscow')) + timedelta(days=1)).replace(" ", "T"))

    # сформируем сигнал аварийного отключения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'false' and j[2] == 'true':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная, но Снятая п.23: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная, но Снятая п.23: Error")

# п.24
    # приведем оборудование в исходное состояние false
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOff')

    # сформируем сигнал оперативного включения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная, но Снятая п.24: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная, но Снятая п.24: Error")

#--------------------------------------------------------------------------------------------------
# Есть аварийная заявка Открытая, но не Разрешенная
# п.25
    # приведем оборудование в исходное состояние true
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOff')
    z1.edit_zvk(z1.guid, 'userState', 'usNotViewed')
    z1.edit_zvk(z1.guid, 'workState', None)
    z1.edit_zvk(z1.guid, 'factRepDEnd', None)

    # сформируем сигнал аварийного отключения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'false' and j[2] == 'true':
            i += 1
    if i == 1:
        print("Тест Есть аварийная заявка Открытая, но не Разрешенная п.25: ОК")
    else:
        print("Тест Есть аварийная заявка Открытая, но не Разрешенная п.25: Error")

# п.26
    # приведем оборудование в исходное состояние true
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'userState', 'usViewed')
    z1.edit_zvk(z1.guid, 'workState', 'wsOpened')


    # сформируем сигнал оперативного отключения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'false' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть аварийная заявка Открытая, но не Разрешенная п.26: ОК")
    else:
        print("Тест Есть аварийная заявка Открытая, но не Разрешенная п.26: Error")
        for j in signal_1.check_result(signal_1.send_timestamp):
            if j[0] == signal_1.cim_id:
                print(j)


# п.27
    # приведем оборудование в исходное состояние true
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'userState', 'usDelayed')
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOn')


    # сформируем сигнал аварийного отключения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'false' and j[2] == 'true':
            i += 1
    if i == 1:
        print("Тест Есть аварийная заявка Открытая, но не Разрешенная п.27: ОК")
    else:
        print("Тест Есть аварийная заявка Открытая, но не Разрешенная п.27: Error")
        for j in signal_1.check_result(signal_1.send_timestamp):
            if j[0] == signal_1.cim_id:
                print(j)

# п.28
    # приведем оборудование в исходное состояние false
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOff')

    # сформируем сигнал оперативного включения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть аварийная заявка Открытая, но не Разрешенная п.28: ОК")
    else:
        print("Тест Есть аварийная заявка Открытая, но не Разрешенная п.28: Error")
        for j in signal_1.check_result(signal_1.send_timestamp):
            if j[0] == signal_1.cim_id:
                print(j)

# п.29
    # приведем оборудование в исходное состояние false
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true,  stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsNone')

    # сформируем сигнал оперативного включения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть аварийная заявка Открытая, но не Разрешенная п.29: ОК")
    else:
        print("Тест Есть аварийная заявка Открытая, но не Разрешенная п.29: Error")
        for j in signal_1.check_result(signal_1.send_timestamp):
            if j[0] == signal_1.cim_id:
                print(j)

#-------------------------------------------------------------------------------------------------------
# Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит с меткой времени, лежащей внутри закрытой заявки)
# п.30
    # приведем оборудование в исходное состояние true
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOff')
    z1.edit_zvk(z1.guid, 'userState', 'usAllowed ')
    z1.edit_zvk(z1.guid, 'workState', 'wsClosed ')
    z1.edit_zvk(z1.guid, 'factRepDEnd', str(datetime.now(timezone('Europe/Moscow'))+timedelta(minutes=20)).replace(' ', 'T'))


    # сформируем сигнал оперативного отключения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'false' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит с меткой времени, лежащей внутри закрытой заявки) п.30: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит с меткой времени, лежащей внутри закрытой заявки) п.30: Error")
        for j in signal_1.check_result(signal_1.send_timestamp):
            if j[0] == signal_1.cim_id:
                print(j)

# п.31
    # приведем оборудование в исходное состояние true
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOn')

    # сформируем сигнал аварийного отключения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'false' and j[2] == 'true':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит с меткой времени, лежащей внутри закрытой заявки) п.31: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит с меткой времени, лежащей внутри закрытой заявки) п.31: Error")
        for j in signal_1.check_result(signal_1.send_timestamp):
            if j[0] == signal_1.cim_id:
                print(j)

# п.32
    # приведем оборудование в исходное состояние true
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsNone')


    # сформируем сигнал аварийного отключения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'false' and j[2] == 'true':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит с меткой времени, лежащей внутри закрытой заявки) п.32: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит с меткой времени, лежащей внутри закрытой заявки) п.32: Error")
        for j in signal_1.check_result(signal_1.send_timestamp):
            if j[0] == signal_1.cim_id:
                print(j)

# п.33
    # приведем оборудование в исходное состояние false
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true,stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOff')


    # сформируем сигнал оперативного включения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит с меткой времени, лежащей внутри закрытой заявки) п.33: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит с меткой времени, лежащей внутри закрытой заявки) п.33: Error")
        for j in signal_1.check_result(signal_1.send_timestamp):
            if j[0] == signal_1.cim_id:
                print(j)

# п.34
    # приведем оборудование в исходное состояние false
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsOn')

    # сформируем сигнал оперативного включения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит с меткой времени, лежащей внутри закрытой заявки) п.34: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит с меткой времени, лежащей внутри закрытой заявки) п.34: Error")
        for j in signal_1.check_result(signal_1.send_timestamp):
            if j[0] == signal_1.cim_id:
                print(j)

# п.35
    # приведем оборудование в исходное состояние false
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()

    # изменим открытую ранее заявку для предыдущего блока тестов
    z1.edit_zvk(z1.guid, 'zvkDeviceState', 'dsNone')

    # сформируем сигнал оперативного включения оборудования
    signal_1 = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_normal_true, stateSourceId,
                      db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_1.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_1.check_result(signal_1.send_timestamp):
        if j[0] == signal_1.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит с меткой времени, лежащей внутри закрытой заявки) п.35: ОК")
    else:
        print("Тест Есть заявка в статусе Разрешенная и уже Закрытая (ТС приходит с меткой времени, лежащей внутри закрытой заявки) п.35: Error")
        for j in signal_1.check_result(signal_1.send_timestamp):
            if j[0] == signal_1.cim_id:
                print(j)

#-------------------------------------------------------------------------------------------------------
    print('ВЫКЛЮЧАТЕЛИ')
# Состояние оборудования совпадает с предыдущим состоянием
# п.1.1
# приведем выключатель в исходное состояние true
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()

    # закроем все существующие заявки для выключателя
    zvk_request = db_request(host=db_host, user=db_user, password=db_password, database=db_name, port=db_port,
                             request_str="SELECT guid FROM repairs.zvk WHERE device_guid = '" + signal_breaker.mrid + "' " +
                                         "--AND work_state in ('wsOpened', 'wsNone') " +
                                         "ORDER BY total_rep_d_end DESC")

    z = zvk(zvk_address=zvk_address, token=my_token, db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port)
    timestamp_11 = str(datetime.now(timezone('Europe/Moscow')) - timedelta(days=5)).replace(' ', 'T')
    for z_guid in zvk_request.execute_request():
        z.edit_zvk(z_guid[0], "workState", "wsClosed")
        z.edit_zvk(z_guid[0], "factRepDEnd", timestamp_11)

    # сформируем сигнал включения выключателя
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()
    # подождем 10 сек
    time.sleep(10)


    i = 0
    for j in signal_breaker.check_result(signal_breaker.send_timestamp):
        if j[0] == signal_breaker.cim_id:
            i += 1
    if i == 0:
        print("Тест Состояние оборудования совпадает с предыдущим состоянием п.1.1: ОК")
    else:
        print("Тест Состояние оборудования совпадает с предыдущим состоянием п.1.1: Error")
        for j in signal_breaker.check_result(signal_breaker.send_timestamp):
            if j[0] == signal_breaker.cim_id:
                print(j)

# п.1.2
# приведем выключатель в исходное состояние false
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()

    # сформируем сигнал отключения выключателя
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_breaker.check_result(signal_breaker.send_timestamp):
        if j[0] == signal_breaker.cim_id:
            i += 1
    if i == 0:
        print("Тест Состояние оборудования совпадает с предыдущим состоянием п.1.2: ОК")
    else:
        print("Тест Состояние оборудования совпадает с предыдущим состоянием п.1.2: Error")
        for j in signal_breaker.check_result(signal_breaker.send_timestamp):
            if j[0] == signal_breaker.cim_id:
                print(j)


# Нет действующей заявки
# п.2.1
# приведем выключатель в исходное состояние true
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()

    # сформируем сигнал отключения выключателя
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_breaker.check_result(signal_breaker.send_timestamp):
        if j[0] == signal_breaker.cim_id and j[1] == 'false' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Нет действующей заявки п.2.1: ОК")
    else:
        print("Тест Нет действующей заявки п.2.1: Error")
        for j in signal_breaker.check_result(signal_breaker.send_timestamp):
            if j[0] == signal_breaker.cim_id:
                print(j)

# п.2.2
# приведем выключатель в исходное состояние false
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()

    # сформируем сигнал включения выключателя
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_breaker.check_result(signal_breaker.send_timestamp):
        if j[0] == signal_breaker.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Нет действующей заявки п.2.2: ОК")
    else:
        print("Тест Нет действующей заявки п.2.2: Error")
        for j in signal_breaker.check_result(signal_breaker.send_timestamp):
            if j[0] == signal_breaker.cim_id:
                print(j)

# п.2.3
# приведем выключатель в неопределенное исходное состояние
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), None, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()

    # сформируем сигнал отключения выключателя
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_breaker.check_result(signal_breaker.send_timestamp):
        if j[0] == signal_breaker.cim_id and j[1] == 'false' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Нет действующей заявки п.2.3: ОК")
    else:
        print("Тест Нет действующей заявки п.2.3: Error")
        for j in signal_breaker.check_result(signal_breaker.send_timestamp):
            if j[0] == signal_breaker.cim_id:
                print(j)

# п.2.4
# приведем выключатель в неопределенное исходное состояние
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), None, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()

    # сформируем сигнал включения выключателя
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_breaker.check_result(signal_breaker.send_timestamp):
        if j[0] == signal_breaker.cim_id and j[1] == 'true' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест Нет действующей заявки п.2.4: ОК")
    else:
        print("Тест Нет действующей заявки п.2.4: Error")
        for j in signal_breaker.check_result(signal_breaker.send_timestamp):
            if j[0] == signal_breaker.cim_id:
                print(j)

#---------------------------------------------------------------------------------------------
# Есть заявка в статусе Открытая (с отключением)
# 3.1.
    # приведем выключатель в исходное состояние true
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()

    #сформируем заявку для выключателя
    z_breaker = zvk(dcAipCode_normal_true, cim_id_breaker, 'usAllowed', 'wsOpened', 'dsOff ',
                    timestamp_start_zvk, timestamp_end_zvk,
                    db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, zvk_address=zvk_address, token=my_token)

    z_breaker.send_zvk()
    z_breaker.edit_zvk(z_breaker.guid, 'factRepDEnd', None)

    # сформируем сигнал отключения выключателя
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_breaker.check_result(signal_breaker.send_timestamp):
        if j[0] == signal_breaker.cim_id and j[1] == 'false' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест сть заявка в статусе Открытая (с отключением) п.3.1: ОК")
    else:
        print("Тест сть заявка в статусе Открытая (с отключением) п.3.1: Error")
        for j in signal_breaker.check_result(signal_breaker.send_timestamp):
            if j[0] == signal_breaker.cim_id:
                print(j)

# 3.2.
    # приведем выключатель в неопределенное исходное состояние
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), None, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()

    # сформируем сигнал отключения выключателя
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_breaker.check_result(signal_breaker.send_timestamp):
        if j[0] == signal_breaker.cim_id and j[1] == 'false' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест сть заявка в статусе Открытая (с отключением) п.3.2: ОК")
    else:
        print("Тест сть заявка в статусе Открытая (с отключением) п.3.2: Error")
        for j in signal_breaker.check_result(signal_breaker.send_timestamp):
            if j[0] == signal_breaker.cim_id:
                print(j)

# 3.3.
    # приведем выключатель в исходное состояние false
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), False, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()

    # сформируем сигнал включения выключателя
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_breaker.check_result(signal_breaker.send_timestamp):
        if j[0] == signal_breaker.cim_id:
            i += 1
    if i == 0:
        print("Тест сть заявка в статусе Открытая (с отключением) п.3.3: ОК")
    else:
        print("Тест сть заявка в статусе Открытая (с отключением) п.3.3: Error")
        for j in signal_breaker.check_result(signal_breaker.send_timestamp):
            if j[0] == signal_breaker.cim_id:
                print(j)

# 3.4.
    # приведем выключатель в неопределенное исходное состояние
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), None, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()

    # сформируем сигнал включения выключателя
    signal_breaker = signal(str(datetime.now(timezone('Europe/Moscow'))), True, cim_id_breaker, stateSourceId,
                            db_host=db_host, db_user=db_user, db_password=db_password, db_name=db_name, db_port=db_port, signal_address=signal_address, token=my_token)
    signal_breaker.send_signal()
    # подождем 10 сек
    time.sleep(10)

    i = 0
    for j in signal_breaker.check_result(signal_breaker.send_timestamp):
        if j[0] == signal_breaker.cim_id and j[1] == 'false' and j[2] == 'false':
            i += 1
    if i == 1:
        print("Тест сть заявка в статусе Открытая (с отключением) п.3.4: ОК")
    else:
        print("Тест сть заявка в статусе Открытая (с отключением) п.3.4: Error")
        for j in signal_breaker.check_result(signal_breaker.send_timestamp):
            if j[0] == signal_breaker.cim_id:
                print(j)

#---------------------------------------------------------------------------------------------------------
# Удалим все созданные для тестирования заявки (странно, но при попытке удаления сервер выдает код 500)
# z1.delete_zvk(z1.guid)
# z_breaker.delete_zvk(z_breaker.guid)

msg = str(input('Для завершения нажмите пробел'))