import logging
from pyexpat.errors import codes
import undetected_chromedriver.v2 as uc
import re, os, time, concurrent.futures
from pathlib import Path
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.remote_connection import logging
from selenium.webdriver.support.ui import WebDriverWait
import urllib3
import json

#Globals`
THREADS = 5    #Number of threads to create
translationObjList = [None] * THREADS
bannedWordsList = []
choice = None

#Token
TOKEN = ''
with open('token.json') as f:
    TOKEN = json.load(f)['token']
    f.close()

#Logging
logging.getLogger().setLevel('ERROR')

#HTTP
http = urllib3.PoolManager()

#Regex
pattern1 = re.compile(r'((?:[^\\\"]|\\.)*?)[\"\'<>【】]') #Match ANY in quotes
pattern2 = re.compile(r'([\u3040-\u309F\u30A0-\u30FF\u3400-\u4DB5\u4E00-\u9FCB\uF900-\uFA6A\u2E80-\u2FD5\uFF5F-\uFF9F\u31F0-\u31FF\u3220-\u3243\u3280-\u337F\uFF40-\uFF5E\u2600-\u26FF]+)') #Match ANY JA Text
pattern3 = re.compile(r'[\\]+[a-z]+\[[0-9]+\]|[\\]+[a-z]+')
#pattern3 = re.compile(r'[^\u3040-\u309F\u30A0-\u30FF\u3400-\u4DB5\u4E00-\u9FCB\uF900-\uFA6A\u2E80-\u2FD5\uFF5F-\uFF9F\u31F0-\u31FF\u3220-\u3243\u3280-\u337F\uFF40-\uFF5E\u2190-\u21FF\u0080-\u00FF\u2150-\u218F\u25A0-\u25FF\u2000-\u206F\u0020\w\\,.!?、]+|[\\\"\']+') #Match ANY Symbol or Variable

#Class to hold translation data
class translationObj:
    variableList = []
    text = ''
    lock = 0
    filterVarCalled = 0
    driver = None
    doOnce = 0

    def __init__(self):
        #Selenium
        options = uc.ChromeOptions()
        options.add_argument('log-level=2')
        options.add_argument('--no-first-run --no-service-autorun --password-store=basic')
        driver = uc.Chrome(options=options)
        driver.set_page_load_timeout(15)
        driver.implicitly_wait(15) 
        self.driver = driver  

    #Assign driver if not locked
    def getDriver(self):
        if (self.lock == 0):
            self.lock = 1
            return self.driver
        else:
            return None

    def release(self):
        self.lock = 0

##--------------MAIN--------------##
def main():
    global choice
    #Give Options to choose type of translation
    while not(choice == '1' or choice == '2'):
        choice = input('Choose Translation Type:\n[1] Translate Files\n[2] Single Translation\n')

    #Create Directory and Drivers
    Path("translate").mkdir(parents=True, exist_ok=True)
    createDrivers()

    #Single Translation
    if(choice == '2'):
        translate('おはようございます')
        quit()
        
    # Open File
    for filename in os.listdir("files"):
        with open('translate/' + filename, 'w', encoding='UTF-8') as outFile:
            with open('files/' + filename, 'r', encoding='UTF-8') as f:

                # Json Files
                if (filename.endswith('json') is True):
                    translatedData = findMatch(json.load(f))
                    json.dump(translatedData, outFile, ensure_ascii=False)
                    print('Translated: ' + filename)
                    
                else:
                    # Replace Each Line
                    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:

                        # The following submits all lines
                        fs = [executor.submit(findMatch, line) for line in f]

                        # as_completed return arbitrary future when it is done
                        # Use simple for-loop ensure the future are iterated sequentially
                        for future in fs:
                            outFile.write(future.result())

    #Close Drivers
    for obj in translationObjList:
        obj.driver.close()

#Create drivers for translation based on THREADS
def createDrivers():
    for i in range(len(translationObjList)):
        translationObjList[i] = translationObj()

##--------------TRANSLATE--------------##
def translate(text):
    try:         
        #Assign object to thread
        tO = None
        driver = None
        while(tO == None):
            for obj in translationObjList:
                if(obj.lock == 0):
                    tO = obj
                    tO.text = text
                    driver = tO.getDriver()
                    break   

        #Filter
        tO = filterVariables(tO)

        #DEEPL
        # if(len(text) > 6):
        tO.doOnce = 0
        while("Content message" in tO.text or tO.doOnce == 0):
            #Get Page and Translate
            logging.info('DEEPL: ' + tO.text + ' using driver ' + str(driver))
            url = 'https://www.deepl.com/translator#ja/en/' + tO.text
            driver.get(url)

            #Wait until translation is finished loading
            match = WebDriverWait(driver, 20).until(lambda driver: 
                re.search(r'^(?!\s*$).+', driver.find_element_by_id('target-dummydiv').get_attribute("innerHTML"))
            )
            tO.text = match.group()
            tO.doOnce = 1

        # #GoogleTL
        # else:
        #     tO.doOnce = 0
        #     while("Content message" in tO.text or tO.doOnce == 0):
        #         #Get Page and Translate
        #         logging.info('GOOGLE: ' + tO.text + ' using driver ' + str(driver))
                
        #         eBody = json.dumps([{'Text':tO.text}]).encode('utf-8')
        #         resp = http.request(
        #             "POST", 
        #             "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&from=ja&to=en",
        #             body=eBody,
        #             headers={
        #                 'Ocp-Apim-Subscription-Key':TOKEN,
        #                 'Ocp-Apim-Subscription-Region':'southcentralus',
        #                 'Content-Type':'application/json'
        #             }
        #         )
        #         data = json.loads(resp.data.decode('utf-8'))
        #         tO.text = data[0]['translations'][0]['text']
        #         tO.doOnce = 1

        #Clean
        tO = filterVariables(tO)
        tO.filterVarCalled = 0
        tO.release()

        #Final QA
        tO.text = tO.text.replace('[ ', '[')
        tO.text = tO.text.replace(' ]', ']')
        tO.text = tO.text.replace('( ', '(')
        tO.text = tO.text.replace(' )', ')')
        tO.text = tO.text.replace('< ', '<')
        tO.text = tO.text.replace(' >', '>')

        return tO.text

    except TimeoutException:
        logging.error('Failed to find translation for line: ' + tO.text)

        # - May get stuck if enabled
        # Path("tmp").mkdir(parents=True, exist_ok=True)
        # with open('/tmp/log.txt', 'a+'):
        #     f.write(tO.text)
        #     f.close()

        tO.release()
        return translate(tO.text)

#Filter variables from string, then put back
def filterVariables(tO):
    #Quick Strip
    tO.text = tO.text.strip()
    tO.text = tO.text.replace('。', '.')
    tO.text = re.sub(r'[…]+', '...', tO.text)
    tO.text = re.sub(r'(?<!\\)"', '', tO.text)
    tO.text = tO.text.replace('\u3000', ' ')
    tO.text = tO.text.replace('！', '')

    #1. Replace variables and translate. 
    if(re.search(pattern3, tO.text) != None and tO.filterVarCalled == 0):
        tO.variableList = re.findall(pattern3, tO.text)
        i = 0
        for var in tO.variableList:
            tO.text = tO.text.replace(var, '{' + str(i) + '}', 1)
            i += 1

        tO.text = tO.text.replace('{', '[')
        tO.text = tO.text.replace('}', ']')
        tO.filterVarCalled = 1
        return tO

    #2. Replace placeholders.
    elif(re.search(r'\[[0-9]\]+', tO.text)):
        i = 0
        for var in tO.variableList:
            tO.text = tO.text.replace('[' + str(i) + ']', var)
            i += 1

        tO.text = re.sub(r'(?<=[^\.])\.', '', tO.text)
        tO.filterVarCalled = 1

        return tO

    #Easy translation. Replace Nothing.
    tO.filterVarCalled = 1
    tO.text = tO.text.replace('\\', '\\\\')
    return tO

def findMatch(data):
    # Search Events
    for event in data['events']:
        if event:
            for page in event['pages']:
                if page:
                    for list in page['list']:
                        #Event Code: 401 Show Text
                        if (list['code'] == 401):
                            for i, parameter in enumerate(list['parameters']):
                                list['parameters'][i] = checkLine(parameter)

                        #Event Code: 102 Show Choice
                        if (list['code'] == 102):
                            for i, choice in enumerate(list['parameters'][0]):
                                print(choice)
                                list['parameters'][0][i] = checkLine(choice)

    return data

def checkLine(line):
    # Check if match in line
    if (re.search(pattern2, line) is not None):

        if (choice == '1'):
            #Bye Bye Dupes
            translatedLine = translate("".join(dict.fromkeys(line)))

            #Replace backslashes due to regex  
            translatedLine = translatedLine.replace('\\', '\\\\')
            line = re.sub(r"(?<!\w)" + re.escape(line) + r"(?!\w)", translatedLine, line, 1)

        else:
            logging.error('Choice Variable is an invalid value')
                    
        return line
    # Skip Line
    else:
        logging.info('Skipping: ' + line)
        return line

#Call Main and get time
start = time.time()
main()
end = time.time()

# Event codes 
#     case 401 : return 'Show Text';              break;
#     case 102 : return 'Show Choices';           break;
#     case 103 : return 'Input Number';           break;
#     case 104 : return 'Select Item';            break;
#     case 405 : return 'Show Scrolling Text';    break;
#     case 111 : return 'Conditional Branch';     break;
#     case 119 : return 'Common Event';           break;
#     case 121 : return 'Control Switches';       break;
#     case 122 : return 'Control Variables';      break;
#     case 125 : return 'Change Gold';            break;
#     case 126 : return 'Change Items';           break;
#     case 127 : return 'Change Weapons';         break;
#     case 128 : return 'Change Armors';          break;
#     case 129 : return 'Change Party Member';    break;
#     case 201 : return 'Transfer Player';        break;
#     case 202 : return 'Set Vehicle Location';   break;
#     case 203 : return 'Set Event Location';     break;
#     case 505 : return 'Set Movement Route';     break;
#     case 212 : return 'Show Animation';         break;
#     case 231 : return 'Show Picture';           break;
#     case 232 : return 'Move Picture';           break;
#     case 285 : return 'Get Location Info';      break;
#     case 301 : return 'Battle Processing';      break;
#     case 302 :
#     case 605 : return 'Shop Processing';        break;
#     case 303 : return 'Name Input Processing';  break;
#     case 311 : return 'Change HP';              break;
#     case 312 : return 'Change MP';              break;
#     case 326 : return 'Change TP';              break;
#     case 313 : return 'Change State';           break;
#     case 314 : return 'Recover All';            break;
#     case 315 : return 'Change EXP';             break;
#     case 316 : return 'Change Level';           break;
#     case 317 : return 'Change Parameter';       break;
#     case 318 : return 'Change Skill';           break;
#     case 319 : return 'Change Equipment';       break;
#     case 320 : return 'Change Name';            break;
#     case 321 : return 'Change Class';           break;
#     case 322 : return 'Change Actor Images';    break;
#     case 324 : return 'Change Nickname';        break;
#     case 325 : return 'Change Profile';         break;
#     case 331 : return 'Change Enemy HP';        break;
#     case 332 : return 'Change Enemy MP';        break;
#     case 342 : return 'Change Enemy TP';        break;
#     case 333 : return 'Change Enemy State';     break;
#     case 336 : return 'Enemy Transform';        break;
#     case 337 : return 'Show Battle Animation';  break;
#     case 339 : return 'Force Action';           break;
#     default : return code;