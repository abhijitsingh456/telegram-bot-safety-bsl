import telebot
from flask import Flask, request, abort

import os
from telebot import types
from telebot.util import quick_markup
from datetime import datetime, timedelta
import re


#imports for google sheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials

#imports for google drive
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Your bot token
BOT_TOKEN = ''

# Initialize Flask app
app = Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

secret = ""
bot.remove_webhook()
bot.set_webhook("https://missafetybsl.pythonanywhere.com/{}".format(secret))

@app.route('/{}'.format(secret), methods=["POST"])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ""
    else:
        abort(403)



# Dictionary to store user selections
user_choices = {}

# Dictionary to store the current menu level for each user
user_main_menu_level = {}
user_submenu_level = {}

# Define main menu levels
INSP = 0  #inspection
MEET = 1  #meeting
TRAIN = 2  #training

#Submenu levels for INSP
INSP_DATE_MENU = 0
INSP_CAT_MENU = 1
INSP_DEPTT_MENU = 2
INSP_LOC_MENU = 3
INSP_OBS_MENU = 4
INSP_DISCUSS_WITH = 5
INSP_COMP_MENU = 6
INSP_PIC_MENU = 7
INSP_SUBMIT_MENU = 8

#Submenu levels for MEET
MEET_DATE_MENU = 9
MEET_CAT_MENU = 10
MEET_DEPTT_MENU = 11
MEET_PART_MENU = 12  #no. of particiapnts
MEET_CHAIR_MENU = 13  #meet chaired by
MEET_PIC_MENU = 14
MEET_SUBMIT_MENU = 15

#Submenu levels for TRAIN
TRAIN_CAT_MENU = 16
TRAIN_DATE_MENU = 17
TRAIN_DEPTT_MENU = 18   #being skipped for now as current training categories don't belong to a single department
TRAIN_PART_MENU = 19
TRAIN_PIC_MENU = 20
TRAIN_SUBMIT_MENU = 21

UPLOADS_DIR = 'uploads'


############################ Google Sheets ##########################################

# Define the scope and credentials for Google Sheets API
scope = ['https://spreadsheets.google.com/feeds',
   'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)

# Authorize the client with credentials
client = gspread.authorize(creds)

# Open the Google Spreadsheet by its name
spreadsheet_name = 'Safety-Records'
inspection_sheet = client.open(spreadsheet_name).worksheet('Inspection')
meeting_sheet = client.open(spreadsheet_name).worksheet('Meeting')
training_sheet = client.open(spreadsheet_name).worksheet('Training')
###############################################################################################

##############################    Google Drive  ################################################
drive_service = build('drive', 'v3', credentials=creds)
###############################################################################################


main_menu = ["Inspection", "Meeting", "Training"]
inspection_categories = ["General","Audio-Visual System", "Central Cable Gallery", "Conveyor Gallery", "EOT Crane", "Illumination", "Locomotive", "Rail-Road Level Crossing","Safety Walk"]
inspection_departments = ["ACVS","BF","CED","CO&CC","CR(E)","CR(M)","CRM","CRM-3","DNW","EL&TC","EMD","ERS","ETL","FORGE SHOP",\
"GM(E)","GM(M)","GU","HM(E)","HM(M)","HRCF","HSM","I&A","ICF","IMF","M/C SHOP","OG&CBRS","PEB","PFRS","PROJECTS","R&R",\
"RCL","RED","RGBS","RMHP","RMP","SF & PS","SGP", "SMS-1","SMS-2&CCS","SP","MRD","STORES","STRL SHOP","TBS","TRAFFIC","WMD"]
next_observation_choices = ["Same Category, Deptt. & Location?","Same Category, Deptt. but Different Location?","Start Fresh"]  #choices user has after they have submitted an observations

meeting_categories=["DLSIC","SAC","SAW", "Contractor Safety Committee"]
meeting_departments=["BF","CED","CO&CC","CRM","CRM-3","DNW","ELECTRICAL MAINT.","EMD",\
                     "GU","HRCF","HSM","I&A","MECHANICAL MAINT.","MRD","RCL","RED","RGBS","RMHP",\
                      "RMP","SHOPS & FDY.","SMS-1","SMS-2&CCS","SP","TBS","TRAFFIC","WMD"]

training_categories=["One Day Safety Awareness Training for Non-Exec","Two Day Safety Awareness Training for Exec",\
                     "Half Day Electrical Safety Training"]
#"Two Day Safety Awareness Training for Exec" has been hardcoded in func handle_date_callback and function handle_date() for calculating end_date

compliance_status = ["Complied","Not Complied", "Good Point"]
@bot.message_handler(commands=['start'])
def start(message):
    global user_main_menu_level
    global user_submenu_level
    user_main_menu_level = {}
    user_submenu_level = {}
    chat_id = message.chat.id
    dict = {}
    for type in main_menu:
      dict[type] = {'callback_data':type}
    markup = quick_markup(dict, row_width=1)
    bot.send_message(chat_id, "Choose what you want to do:", reply_markup=markup)

#callback handler when no menu levels is assigned
#ensures this by checking if the user_main_menu_level is empty
@bot.callback_query_handler(func=lambda call: not(bool(user_main_menu_level)))
def main_callback_query(call):
    chat_id = call.message.chat.id
    if call.data == "Inspection":
      user_main_menu_level[chat_id] = INSP
      user_submenu_level[chat_id] = INSP_CAT_MENU
      ask_category(chat_id)
    elif call.data == "Meeting":
      user_main_menu_level[chat_id] = MEET
      user_submenu_level[chat_id] = MEET_CAT_MENU
      ask_category(chat_id)
    elif call.data == "Training":
      user_main_menu_level[chat_id] = TRAIN
      user_submenu_level[chat_id] = TRAIN_CAT_MENU
      ask_category(chat_id)


# Get today's date
today = datetime.today()
# Format the date as dd-mm-yyyy
today_date = today.strftime('%d-%m-%Y')
# Calculate yesterday's date
yesterday = today - timedelta(days=1)
yesterday_date = yesterday.strftime('%d-%m-%Y')

def ask_date(chat_id):
    markup = quick_markup({today_date:{"callback_data":today_date},
                          yesterday_date:{"callback_data":yesterday_date}}, row_width=2)
    bot.send_message(chat_id, "Choose a Date or type it in DD-MM-YYYY format:", reply_markup=markup)

#callbcak handler for date
@bot.callback_query_handler(func=lambda call: user_submenu_level.get(call.message.chat.id) == INSP_DATE_MENU or \
                            user_submenu_level.get(call.message.chat.id) == MEET_DATE_MENU or\
                            user_submenu_level.get(call.message.chat.id) == TRAIN_DATE_MENU)
def handle_date_callback(call):
  chat_id = call.message.chat.id
  if call.data == today_date or call.data == yesterday_date:
    if (user_submenu_level.get(call.message.chat.id) == INSP_DATE_MENU):
      user_submenu_level[chat_id] = INSP_DEPTT_MENU
      user_choices[chat_id]["date"]=call.data
      ask_department(chat_id)
    elif (user_submenu_level.get(call.message.chat.id) == MEET_DATE_MENU):
      user_submenu_level[chat_id] = MEET_DEPTT_MENU
      user_choices[chat_id]["date"]=call.data
      ask_department(chat_id)
    elif (user_submenu_level.get(call.message.chat.id) == TRAIN_DATE_MENU):
      user_submenu_level[chat_id] = TRAIN_PART_MENU
      user_choices[chat_id]["start_date"]=call.data
      if user_choices[chat_id]["training_category"]=="Two Day Safety Awareness Training for Exec":
         date = datetime.strptime(call.data, '%d-%m-%Y')
         user_choices[chat_id]["end_date"]=(date+timedelta(days=1)).strftime('%d-%m-%Y')
      else:
         user_choices[chat_id]["end_date"]=call.data
      ask_participants(chat_id)


#used to handle the case when someone types a date other than the options provided.
@bot.message_handler(func=lambda message: user_submenu_level.get(message.chat.id) == INSP_DATE_MENU or\
                            user_submenu_level.get(message.chat.id) == MEET_DATE_MENU or\
                            user_submenu_level.get(message.chat.id) == TRAIN_DATE_MENU)
def handle_date(message):
  chat_id = message.chat.id
  # Define the regular expression pattern for dd-mm-yyyy format
  pattern = r'^\d{2}-\d{2}-\d{4}$'
  # Check if the string matches the pattern
  if re.match(pattern, message.text):
    user_choices[chat_id]["date"]=message.text
    if (user_submenu_level.get(chat_id) == INSP_DATE_MENU):
      user_submenu_level[chat_id] = INSP_DEPTT_MENU
      ask_department(chat_id)
    elif (user_submenu_level.get(chat_id) == MEET_DATE_MENU):
      user_submenu_level[chat_id] = MEET_DEPTT_MENU
      ask_department(chat_id)
    elif (user_submenu_level.get(chat_id) == TRAIN_DATE_MENU):
      user_submenu_level[chat_id] = TRAIN_PART_MENU
      user_choices[chat_id]["start_date"]=message.text
      if user_choices[chat_id]["training_category"]=="Two Day Safety Awareness Training for Exec":
         date = datetime.strptime(message.text, '%d-%m-%Y')
         user_choices[chat_id]["end_date"]=(date+timedelta(days=1)).strftime('%d-%m-%Y')
      else:
         user_choices[chat_id]["end_date"]=message.text
      ask_participants(chat_id)
  else:
    bot.send_message(chat_id, "Please enter the date in DD-MM-YYYY format only")


def ask_category(chat_id):
    dict = {}
    if (user_submenu_level[chat_id] == INSP_CAT_MENU):
      for category in inspection_categories:
        dict[category] = {'callback_data': category}
      markup = quick_markup(dict, row_width=2)
      bot.send_message(chat_id, "Choose an Inspection Category:", reply_markup=markup)
    elif(user_submenu_level[chat_id] == MEET_CAT_MENU):
      for category in meeting_categories:
        dict[category] = {'callback_data': category}
      markup = quick_markup(dict, row_width=2)
      bot.send_message(chat_id, "Choose a Meeting Category:", reply_markup=markup)
    elif(user_submenu_level[chat_id] == TRAIN_CAT_MENU):
      for category in training_categories:
        dict[category] = {'callback_data': category}
      markup = quick_markup(dict, row_width=1)
      bot.send_message(chat_id, "Choose a Training Category:", reply_markup=markup)


def ask_department(chat_id):
    dict = {}
    if (user_submenu_level[chat_id] == INSP_DEPTT_MENU):
      for department in inspection_departments:
          dict[department] = {'callback_data': department}
      markup = quick_markup(dict, row_width=4)
    elif (user_submenu_level[chat_id] == MEET_DEPTT_MENU):
      for department in meeting_departments:
          dict[department] = {'callback_data': department}
      markup = quick_markup(dict, row_width=3)
    bot.send_message(chat_id, "Choose a Department:", reply_markup=markup)

#applicable only for meetings & trainings (not for inspesction)
def ask_participants(chat_id):
  bot.send_message(chat_id, "Please Enter Number of Participants (Enter NA if not applicable or not available):")

@bot.message_handler(func=lambda message: user_submenu_level.get(message.chat.id) == MEET_PART_MENU or\
                     user_submenu_level.get(message.chat.id) == TRAIN_PART_MENU)
def record_part(message):   #record no. of participants in meeting or training
    chat_id = message.chat.id
    if user_submenu_level[chat_id] == MEET_PART_MENU:
      user_submenu_level[chat_id] = MEET_CHAIR_MENU
      user_choices[chat_id]["participants"]=message.text
      ask_chaired_by(chat_id)
    elif user_submenu_level[chat_id] == TRAIN_PART_MENU:
      user_submenu_level[chat_id] = TRAIN_PIC_MENU
      user_choices[chat_id]["participants"]=message.text
      ask_for_photo(chat_id)

def ask_chaired_by(chat_id):
    bot.send_message(chat_id, "Please enter who chaired the meeting:")

@bot.message_handler(func=lambda message: user_submenu_level.get(message.chat.id) == MEET_CHAIR_MENU)
def record_chaired_by(message):   #record who chaired the meeting
    chat_id = message.chat.id
    if user_submenu_level[chat_id] == MEET_CHAIR_MENU:
      user_submenu_level[chat_id] = MEET_PIC_MENU
      user_choices[chat_id]["chaired_by"]=message.text
      ask_for_photo(chat_id)

def ask_location(chat_id):
    bot.send_message(chat_id, "Please Enter Location:")

@bot.message_handler(func=lambda message: user_submenu_level.get(message.chat.id) == INSP_LOC_MENU)
def record_loc(message):  #record location
    chat_id = message.chat.id
    if user_submenu_level[chat_id] == INSP_LOC_MENU:
      user_submenu_level[chat_id] = INSP_OBS_MENU
      user_choices[chat_id]["location"]=message.text
      ask_observation(chat_id)

def ask_observation(chat_id):
    bot.send_message(chat_id, "Please Enter Observation:")

@bot.message_handler(func=lambda message: user_submenu_level.get(message.chat.id) == INSP_OBS_MENU)
def record_obs(message):  #record observation
      chat_id = message.chat.id
      if user_submenu_level[chat_id] == INSP_OBS_MENU:
        user_submenu_level[chat_id] = INSP_DISCUSS_WITH
        user_choices[chat_id]["observation"]=message.text
        ask_discussed_with(chat_id)

def ask_discussed_with(chat_id):
    bot.send_message(chat_id, "Please Enter Discussed With (or in cases of Safety Walk who led the Safety Walk): ")

@bot.message_handler(func=lambda message: user_submenu_level.get(message.chat.id) == INSP_DISCUSS_WITH)
def record_discussed_with(message):  #record discussed with
      chat_id = message.chat.id
      if user_submenu_level[chat_id] == INSP_DISCUSS_WITH:
        user_submenu_level[chat_id] = INSP_COMP_MENU
        user_choices[chat_id]["discussed_with"]=message.text
        ask_compliance_status(chat_id)

def ask_compliance_status(chat_id):
    dict = {}
    for status in compliance_status:
      dict[status] = {'callback_data': status}
    markup = quick_markup(dict, row_width=3)
    bot.send_message(chat_id, "Please enter Compliance Status", reply_markup=markup)

def ask_for_photo(chat_id):
  markup = quick_markup({"SKIP":{"callback_data":"SKIP"}}, row_width=1)
  if "photo" not in user_choices[chat_id]: #if user has uploaded no photo, show a choice to SKIP uploading
    bot.send_message(chat_id, "Please upload a photo or choose SKIP:", reply_markup=markup) 
  else:  #if user has already uploaded a photo, show a choice to upload another photo
    bot.send_message(chat_id, "Please upload a photo:")

def show_submit_button(chat_id):
    markup = quick_markup({"Submit":{'callback_data': "submit"}}, row_width=1)
    bot.send_message(chat_id, "Choose Submit to Save", reply_markup=markup)

def print_choices(message):
    chat_id = message.chat.id
    if chat_id in user_choices:
        confirm_msg = "Your Choices are:"+"\n"\
          +user_choices[chat_id]["inspection_category"]+"\n"\
          +user_choices[chat_id]["department"]+"\n"\
          +user_choices[chat_id]["location"]+"\n"\
          +user_choices[chat_id]["observation"]+"\n"\
          +user_choices[chat_id]["discussed_with"]+"\n"\
          +user_choices[chat_id]["compliance_status"]
        bot.send_message(chat_id, confirm_msg)

def upload_photo_to_google_drive(file_id, image_path):
  file_metadata = {
    'name': f'{file_id}.jpg',
    'parents': ["1Pw3zmGy0M3p-fwAYarevmM0DnqSZbWIv"]  #ID of the folder where you want to upload the image
  }
  media = MediaFileUpload(image_path, mimetype='image/jpeg')
  uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='webViewLink').execute()
  photo_link = uploaded_file.get('webViewLink')
  return photo_link

#used to check if the user wants to upload a photo or not
#and if he has already uploaded a photo does he want to upload
#another photo for the same observation or not
#SKIP means No photo at all, Yes means another photo for the same observation, No means no more photos for the same observation
@bot.callback_query_handler(func=lambda call: user_submenu_level.get(call.message.chat.id) == INSP_PIC_MENU or\
                            user_submenu_level.get(call.message.chat.id) == MEET_PIC_MENU or\
                            user_submenu_level.get(call.message.chat.id) == TRAIN_PIC_MENU)
def handle_photo_callback(call):
  chat_id = call.message.chat.id
  if call.data == 'Yes':
    ask_for_photo(chat_id)
  elif call.data == 'No' or call.data== 'SKIP':
    if (user_submenu_level.get(chat_id) == INSP_PIC_MENU):
      user_submenu_level[chat_id] = INSP_SUBMIT_MENU
    elif (user_submenu_level.get(chat_id) == MEET_PIC_MENU):
      user_submenu_level[chat_id] = MEET_SUBMIT_MENU
    elif (user_submenu_level.get(chat_id) == TRAIN_PIC_MENU):
      user_submenu_level[chat_id] = TRAIN_SUBMIT_MENU
    if call.data == 'SKIP':
      user_choices[chat_id]["photo"] = ""
    show_submit_button(chat_id)

def ask_choice_for_next_observation(chat_id):
    dict = {}
    for choice in next_observation_choices:
      dict[choice] = {'callback_data': choice}
    markup = quick_markup(dict, row_width=1)
    bot.send_message(chat_id, "Please choose what you want to do for the next observation", reply_markup=markup)

#callback handler for inspection categories
#ensures this by checking if the user_main_menu_level is INSP
@bot.callback_query_handler(func=lambda call: user_main_menu_level.get(call.message.chat.id) == INSP)
def insp_callback_query(call):
    chat_id = call.message.chat.id
    if call.data in inspection_categories:
        if user_submenu_level[chat_id] == INSP_CAT_MENU:
            user_submenu_level[chat_id] = INSP_DATE_MENU
            user_choices[chat_id]={"inspection_category":call.data}
            ask_date(chat_id)
    elif call.data in inspection_departments:
        if user_submenu_level[chat_id] == INSP_DEPTT_MENU:
            user_submenu_level[chat_id] = INSP_LOC_MENU
            user_choices[chat_id]["department"]=call.data
            ask_location(chat_id)
    elif call.data in compliance_status:
        if user_submenu_level[chat_id] == INSP_COMP_MENU:
            user_submenu_level[chat_id] = INSP_PIC_MENU
            user_choices[chat_id]["compliance_status"]=call.data
            print_choices(call.message)
            ask_for_photo(chat_id)
    elif call.data == 'submit':
        if user_submenu_level[chat_id] == INSP_SUBMIT_MENU:
          inspection_sheet.append_rows([[user_choices[chat_id]["date"],\
             user_choices[chat_id]["inspection_category"],\
             user_choices[chat_id]["department"],\
             user_choices[chat_id]["location"],\
             user_choices[chat_id]["observation"],\
             user_choices[chat_id]["compliance_status"],\
             user_choices[chat_id]["photo"],\
             user_choices[chat_id]["discussed_with"]]])
          bot.send_message(chat_id, "Data Saved Successfuly")
          ask_choice_for_next_observation(chat_id)
    elif call.data in next_observation_choices:
        if user_submenu_level[chat_id] == INSP_SUBMIT_MENU:
          if call.data==next_observation_choices[2]: #Start Fresh
              user_submenu_level[chat_id] = INSP_CAT_MENU
              user_choices[chat_id] = {}
              ask_category(chat_id)
          elif call.data==next_observation_choices[0] or call.data==next_observation_choices[1]:
              user_choices[chat_id].pop('observation')
              user_choices[chat_id].pop('compliance_status')
              user_choices[chat_id].pop('photo')
              user_choices[chat_id].pop('discussed_with')
              if call.data==next_observation_choices[1]: #New observation with same Category & Deptt. but different Location?
                  user_choices[chat_id].pop('location')
                  user_submenu_level[chat_id] = INSP_LOC_MENU
                  ask_location(chat_id)
              else:
                  user_submenu_level[chat_id] = INSP_OBS_MENU
                  ask_observation(chat_id)

#callback handler for meeting categories
#ensures this by checking if the user_main_menu_level is MEET
@bot.callback_query_handler(func=lambda call: user_main_menu_level.get(call.message.chat.id) == MEET)
def meet_callback_query(call):
    chat_id = call.message.chat.id
    if call.data in meeting_categories:
        if user_submenu_level[chat_id] == MEET_CAT_MENU:
          user_submenu_level[chat_id] = MEET_DATE_MENU
          user_choices[chat_id]={"meeting_category":call.data}
          ask_date(chat_id)
    if call.data in meeting_departments:
        if user_submenu_level[chat_id] == MEET_DEPTT_MENU:
          user_submenu_level[chat_id] = MEET_PART_MENU
          user_choices[chat_id]["meeting_department"]=call.data
          ask_participants(chat_id)
    elif call.data == 'submit':
        if user_submenu_level[chat_id] == MEET_SUBMIT_MENU:
          user_submenu_level[chat_id] = MEET_CAT_MENU
          meeting_sheet.append_rows([[user_choices[chat_id]["date"],\
             user_choices[chat_id]["meeting_category"],\
             user_choices[chat_id]["meeting_department"],\
             user_choices[chat_id]["participants"],\
             user_choices[chat_id]["chaired_by"],\
             user_choices[chat_id]["photo"]]])
          bot.send_message(chat_id, "Data Saved Successfuly")
          user_choices[chat_id] = {}
          ask_category(chat_id)

#callback handler for training categories
#ensures this by checking if the user_main_menu_level is TRAIN
@bot.callback_query_handler(func=lambda call: user_main_menu_level.get(call.message.chat.id) == TRAIN)
def train_callback_query(call):
    chat_id = call.message.chat.id
    if call.data in training_categories:
        if user_submenu_level[chat_id] == TRAIN_CAT_MENU:
          user_submenu_level[chat_id] = TRAIN_DATE_MENU
          user_choices[chat_id]={"training_category":call.data}
          ask_date(chat_id)
    elif call.data == 'submit':
        if user_submenu_level[chat_id] == TRAIN_SUBMIT_MENU:
          user_submenu_level[chat_id] = TRAIN_CAT_MENU
          training_sheet.append_rows([[user_choices[chat_id]["training_category"],\
             user_choices[chat_id]["start_date"],\
             user_choices[chat_id]["end_date"],\
             user_choices[chat_id]["participants"],\
             user_choices[chat_id]["photo"]]])
          bot.send_message(chat_id, "Data Saved Successfuly")
          user_choices[chat_id] = {}
          ask_category(chat_id)

@bot.callback_query_handler(func=lambda call: True)
def skip_callback_query(call):
  print ("jrtyjtjtjtjtjuttuktuktukrmryuk,rlry,kryu,rkury,kuy,kuh,ufk,k,i,uyfk,u,u,yu8,y,yfrt,")
  chat_id = call.message.chat.id
  if call.data=="SKIP":
    if (user_submenu_level.get(chat_id) == INSP_PIC_MENU):
      user_submenu_level[chat_id] = INSP_SUBMIT_MENU
    elif (user_submenu_level.get(chat_id) == MEET_PIC_MENU):
      user_submenu_level[chat_id] = MEET_SUBMIT_MENU
    elif (user_submenu_level.get(chat_id) == TRAIN_PIC_MENU):
      user_submenu_level[chat_id] = TRAIN_SUBMIT_MENU
    user_choices[chat_id]["photo"] = ""
    show_submit_button(chat_id)


@bot.message_handler(content_types=['photo'],func=lambda message: user_submenu_level.get(message.chat.id) == INSP_PIC_MENU or\
                            user_submenu_level.get(message.chat.id) == MEET_PIC_MENU or\
                              user_submenu_level.get(message.chat.id) == TRAIN_PIC_MENU)
def handle_photo(message):
  chat_id = message.chat.id
  file_id = message.photo[-1].file_id  # Get the file_id of the last photo sent
  # Download the photo
  file_info = bot.get_file(file_id)
  downloaded_file = bot.download_file(file_info.file_path)
  # Save the photo locally
  image_path = os.path.join(UPLOADS_DIR, f'{file_id}.jpg')
  with open(image_path, 'wb') as image_file:
      image_file.write(downloaded_file)
  # Upload the photo to Google Drive
  try:
    if "photo" in user_choices[chat_id]:
      user_choices[chat_id]["photo"] += ", "
      user_choices[chat_id]["photo"] += upload_photo_to_google_drive(file_id, image_path)
    else:
        user_choices[chat_id]["photo"] = upload_photo_to_google_drive(file_id, image_path)
    bot.send_message(chat_id, "Photo uploaded successfully!")
  except:
      bot.send_message(chat_id, "Error Uploading Photo")
      bot.send_message(chat_id, "Try Again")
  os.remove(image_path)
  #ask user if he wants to upload more photos
  markup = quick_markup({
      'Yes': {'callback_data': 'Yes'},
      'No': {'callback_data': 'No'}
  }, row_width=2)
  bot.send_message(chat_id, "Upload another photo for the same observation?", reply_markup=markup)
