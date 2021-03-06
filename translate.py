from fileinput import filename
import logging
from operator import contains
from pyexpat.errors import codes
import textwrap
from tkinter import E
import undetected_chromedriver.v2 as uc
import re, os, time, concurrent.futures
from pathlib import Path
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.remote_connection import logging
from selenium.webdriver.support.ui import WebDriverWait
import urllib3
import json

#Globals
THREADS = 5    #Number of threads to create
translationObjList = [None] * THREADS
bannedWordsList = []
choice = None
numOfFailures = 0
failureList = []

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
pattern3 = re.compile(r'\\+[A-Za-z0-9[\]]+|//')
#pattern3 = re.compile(r'[^\u3040-\u309F\u30A0-\u30FF\u3400-\u4DB5\u4E00-\u9FCB\uF900-\uFA6A\u2E80-\u2FD5\uFF5F-\uFF9F\u31F0-\u31FF\u3220-\u3243\u3280-\u337F\uFF40-\uFF5E\u2190-\u21FF\u0080-\u00FF\u2150-\u218F\u25A0-\u25FF\u2000-\u206F\u0020\w\\,.!?、]+|[\\\"\']+') #Match ANY Symbol or Variable

#Class to hold translation data
class translationObj:
    variableList = []
    text = ''
    lock = 0
    filterVarCalled = 0
    driver = None
    doOnce = 0
    count = 0

    def __init__(self):
        #Selenium
        options = uc.ChromeOptions()
        options.add_argument('log-level=2')
        options.add_argument('--no-first-run --no-service-autorun --password-store=basic')
        options.add_argument('--blink-settings=imagesEnabled=false')
        driver = uc.Chrome(options=options)
        driver.set_page_load_timeout(10)
        driver.implicitly_wait(10) 
        self.driver = driver  

    #Assign driver if not locked
    def getDriver(self):
        if (self.lock == 0):
            self.lock = 1
            return self.driver
        else:
            return None

    def release(self):
        self.variableList = []
        self.filterVarCalled = 0
        self.doOnce = 0
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
        print(translate("\r//メッセージバックを黒く\r", 0))
        quit()
        
    # Open File (Threads)
    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
        for filename in os.listdir("files"):
            if filename.endswith('json'):
                executor.submit(handle, filename)

    #Close Drivers
    for obj in translationObjList:
        obj.driver.close()

    # Final Thingies
    print("Failures: " + str(numOfFailures))
    with open('failureList.txt', 'w', encoding='utf-8') as outFile:
        for failure in failureList:
            outFile.write('{0}\n'.format(failure))
        outFile.close()

def handle(filename):
    with open('translate/' + filename, 'w', encoding='UTF-8') as outFile:
        with open('files/' + filename, 'r', encoding='UTF-8') as f:
            # Map Files
            if 'Map' in filename:
                translatedData = parseMap(json.load(f))
                json.dump(translatedData, outFile, ensure_ascii=False)
                print('Translated: {0}'.format(filename))

            # Common Event Files
            elif 'CommonEvents' in filename:
                translatedData = parseCommonEvents(json.load(f))
                json.dump(translatedData, outFile, ensure_ascii=False)
                print('Translated: {0}'.format(filename))

            # Troops Files
            elif 'Troops' in filename:
                translatedData = parseTroops(json.load(f))
                json.dump(translatedData, outFile, ensure_ascii=False)
                print('Translated: {0}'.format(filename))

            # Scenario Files
            elif 'Scenario' in filename:
                translatedData = parseScenario(json.load(f))
                json.dump(translatedData, outFile, ensure_ascii=False)
                print('Translated: {0}'.format(filename))

#Google Translate Function
def getAllElementsAsString(driver):
    elementList = driver.find_elements_by_xpath("//span[@class='Q4iAWc']")
    text = ''
    for element in elementList:
        text += (element.get_attribute("innerHTML"))

    return text

#Create drivers for translation based on THREADS
def createDrivers():
    for i in range(len(translationObjList)):
        translationObjList[i] = translationObj()

##--------------TRANSLATE--------------##
def translate(text, engine):
    try:         
        # Assign object to thread
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
        if(engine == 0):
            tO.doOnce = 0
            while("Content message" in tO.text or tO.doOnce == 0):
                #Get Page and Translate
                logging.info('DEEPL: ' + tO.text + ' using driver ' + str(driver))
                url = 'https://www.deepl.com/translator#ja/en/' + tO.text
                driver.get(url)

                #Wait until translation is finished loading
                match = WebDriverWait(driver, 10).until(lambda driver: 
                    re.search(r'^(?!\s*$).+', driver.find_element_by_id('target-dummydiv').get_attribute("innerHTML"))
                )
                tO.text = match.group()
                tO.text = tO.text.strip()
                tO.doOnce = 1
        
        #GOOGLE
        else:
            #Get Page and Translate
            logging.info('GOOGLE: ' + tO.text + ' using driver ' + str(driver))
            url = 'https://translate.google.com/?sl=ja&tl=en&text=' + tO.text
            driver.get(url)

            #Wait until translation is finished loading
            match = WebDriverWait(driver, 10).until(lambda driver: getAllElementsAsString(driver))
            tO.text = match

        #Clean
        tO = filterVariables(tO)
        tO.count = 0
        tO.release()

        #Final QA
        tO.text = re.sub(r"\b%s\b" % 'wow', 'ah', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r"\b%s\b" % ', my God', '', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r"\b%s\b" % 'Oh my god', 'Ah', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r"\b%s\b" % 'Oh my god', 'Ah', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r"\b%s\b" % ', sir.', '', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r"\b%s\b" % ', sir', '', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r"\b%s\b" % 'moo', 'kuchu', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r"\b%s\b" % 'Gimme', 'guchu', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r"\b%s\b" % 'sperming', 'milking', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r"\b%s\b" % 'sperm', 'semen', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r"\b%s\b" % 'man parts', 'privates', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r"\b%s\b" % 'he is', 'they are', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r"\b%s\b" % 'she is', 'they are', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r"\b%s\b" % 'help me, man', 'help me... please...', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r"\b%s\b" % 'Ouch', 'coming', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r'\b%s\b' % "I'm kinda tickled", 'I find it funny', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r'\b%s\b' % "huh", 'eh', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r'\b%s\b' % "dark ones", 'thick cum', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r'\b%s\b' % "っ", '', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r'\b%s\b' % "launched a pimple", 'came', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r'\b%s\b' % "nub", 'rub', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r'\b%s\b' % "pizzle", 'cum', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r'\b%s\b' % "zako", 'weak', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r'\b%s\b' % "hips", 'ass', tO.text, flags=re.IGNORECASE)
        tO.text = re.sub(r"(\W\W)I don't know+([,\.])", r'\1eh\2', tO.text)

        #Formatting
        tO.text = re.sub(r'(.{12,})\1', r'\1', tO.text)  # Long repeating phrases
        tO.text = tO.text[0].upper() + tO.text[1:]
        tO.text = re.sub(' +', ' ', tO.text)
        tO.text = textwrap.fill(text=tO.text, width=53)
        tO.text = tO.text.strip('.')

        return tO.text

    except TimeoutException:
        tO.count += 1  # Increment Timeout
        print('{0} Timeout #: {1}'.format(tO.text, tO.count))

        #DESPAIR
        if tO.count > 5:
            tO.release()
            tO.count = 0
            print('Failed to translate: ' + tO.text)
            global numOfFailures
            global failureList
            numOfFailures += 1
            text = text.replace('\\', '\\\\') # Need to fix the backslashes again
            failureList.append(tO.text + '|' + text)
            return(text)

        #Try Google
        if tO.count > 2:
            tO.release()
            return translate(text, 1)  
        
        tO.release()
        return translate(text, 0) # Try Again

#Filter variables from string, then put back
def filterVariables(tO):

    # Clean Before Translation
    tO.text = tO.text.replace('&lt;', '<')
    tO.text = tO.text.replace('&gt;', '>')
    tO.text = tO.text.replace('゛', '" ')
    tO.text = tO.text.replace('（', '(')
    tO.text = tO.text.replace('）', ')')
    #tO.text = re.sub(r'(?<!\\)"', '', tO.text)
    tO.text = tO.text.replace('\u3000', ' ')
    #tO.text = re.sub(r'[…]+', '', tO.text)
    #tO.text = tO.text.replace('。', '. ')
    #tO.text = tO.text.replace('、', ', ')
    #tO.text = tO.text.replace('！', '!')

    # tO.text = re.sub(r'(.){1}\1+([\\,.!<>\s])', r'\1\2', tO.text) Removes Duplicate Trailing
    tO.text = re.sub(r'([…]){1}\1+', r'\1', tO.text)
    tO.text = re.sub(r'([!！]){1}\1+', r'\1', tO.text)
    tO.text = tO.text.replace('…！', '！')
    #tO.text = tO.text.replace('…', '..')
    tO.text = re.sub(r'(…+)([^。])', r'\1 \2', tO.text)
    tO.text = re.sub(r"(.+) ([>\]\)\'\"])", r'\1\2', tO.text)
    tO.text = re.sub(r"([<\[\(\'\"]) (.+)", r'\1\2', tO.text)
    tO.text = tO.text.replace('\r', r'\r')
    #tO.text = tO.text.replace('\\', '\\\\')
    #tO.text = tO.text.strip()

    #1. Replace variables and translate. 
    if(re.search(pattern3, tO.text) != None and tO.filterVarCalled == 0):
        tO.variableList = re.findall(pattern3, tO.text)
        tO.variableList = list(set(tO.variableList))    # Removed duplicates in list
        i = 0
        for var in tO.variableList:
            tO.text = tO.text.replace(var, '<id\'' + str(i) + '\'>')
            i += 1

        tO.filterVarCalled = 1
        return tO

    #2. Replace placeholders.
    elif(re.search(r'\<[Ii][Dd]\'[0-9]\'\>+', tO.text)):
        i = 0
        for var in tO.variableList:
            var = var.replace('\\', '\\\\')
            tO.text = re.sub("<id\'" + str(i) + "\'>", var, tO.text, flags=re.IGNORECASE)
            i += 1

        #tO.text = re.sub(r'(?<=[^\.])\.', '', tO.text)
        tO.filterVarCalled = 1

        return tO

    #Easy translation. Replace Nothing.
    tO.filterVarCalled = 1
    tO.text = tO.text.replace('\\', '\\\\')
    return tO

def searchCodes(page, list):
    for i, list in enumerate(page['list']):

        #Event Code: 401 Show Text
        string = ''
        if page['list'][i]['code'] == 401:
            string += list['parameters'][0]
            while(page['list'][i + 1]['code'] == 401):
                # if not page['list'][i + 1]['parameters'][0] == '':
                #     string += ' '      #Adds space beween strings
                string += page['list'][i + 1]['parameters'][0]
                page['list'][i + 1]['parameters'][0] = ''
                i += 1
            list['parameters'][0] = checkLine(string)
            string = ''

        #Event Code: 102 Show Choice
        if (list['code'] == 102):
            for i, choice in enumerate(list['parameters'][0]):
                list['parameters'][0][i] = checkLine(choice)
        
        #Event Code: 108 Screen Text
        if (list['code'] == 108):
            for mapName in (list['parameters']):
                if('info:' in mapName):
                    mapName = mapName.replace('info:', '')
                    mapName = 'info:' + checkLine(mapName)
                    list['parameters'][0] = mapName.replace(' ', '\t')
                else:
                    mapName = checkLine(mapName)
                    list['parameters'][0] = mapName.replace(' ', '\t')

        # #Event Code: 356 DTEXT
        # if (list['code'] == 356):
        #     for DTEXT in (list['parameters']):
        #         if (re.search(pattern2, DTEXT) is not None and 'D_TEXT' in DTEXT):
        #             DTEXT = DTEXT.replace('D_TEXT ', '')
        #             DTEXT = 'D_TEXT ' + checkLine(DTEXT)
        #             list['parameters'][0] = DTEXT

def searchScenarioCodes(list):
    for i in range(len(list)):

        #Event Code: 401 Show Text
        string = ''
        if list[i]['code'] == 401:
            topListEntry = i
            string += list[i]['parameters'][0]
            while(list[i + 1]['code'] == 401):
                # if not page['list'][i + 1]['parameters'][0] == '':
                #     string += ' '      #Adds space beween strings
                string += list[i + 1]['parameters'][0]
                list[i + 1]['parameters'][0] = ''
                i += 1
            list[topListEntry]['parameters'][0] = checkLine(string)
            string = ''

        #Event Code: 102 Show Choice
        if (list[i]['code'] == 102):
            for j in range(len(list[i]['parameters'])):
                list[i]['parameters'][j] = checkLine(choice)
        
        # #Event Code: 108 Screen Text
        # if (list['code'] == 108):
        #     for mapName in (list['parameters']):
        #         if('info:' in mapName):
        #             mapName = mapName.replace('info:', '')
        #             mapName = 'info:' + checkLine(mapName)
        #             list['parameters'][0] = mapName.replace(' ', '\t')
        #         else:
        #             mapName = checkLine(mapName)
        #             list['parameters'][0] = mapName.replace(' ', '\t')

        # #Event Code: 356 DTEXT
        # if (list['code'] == 356):
        #     for DTEXT in (list['parameters']):
        #         if (re.search(pattern2, DTEXT) is not None and 'D_TEXT' in DTEXT):
        #             DTEXT = DTEXT.replace('D_TEXT ', '')
        #             DTEXT = 'D_TEXT ' + checkLine(DTEXT)
        #             list['parameters'][0] = DTEXT

def parseMap(data):
    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
        for event in data['events']:
            if event:
                executor.submit(handleParseMap, event)                     
    return data

def handleParseMap(event):
    for page in event['pages']:
        if page:
            string = ""
            searchCodes(page, list)
    return page

def parseCommonEvents(data):
    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
        for page in data:
            if page:
                executor.submit(handleParseCommonEvents, page)
        return data

def handleParseCommonEvents(page):
    searchCodes(page, list)
    return page

def parseTroops(data):
    # Search Events
    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
        for event in data:
            if event:
                executor.submit(handleParseTroops, event)
        return data

def handleParseTroops(event):
    for page in event['pages']:
        if page:
            searchCodes(page, list)
    return page

def parseScenario(data):
    with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:
        for list in data:
            if data[list]:
                executor.submit(handleParseScenario, data[list])
        return data

def handleParseScenario(list):
    searchScenarioCodes(list)
    return list

def checkLine(line):

    # Check if match in line
    if (re.search(pattern2, line) is not None):

        # # Let Google handle sfx
        if (choice == '1'):
            translatedLine = translate(line, 0)

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
print("Seconds: " + str(end - start))

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