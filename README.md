# telegram-bot-safety-bsl
Telegram Bot for for Safety Deaprtment of Bokaro Steel Plant
What does this telegram bot is:-
1. To record observations related to safety inspection conducted by Safety Officers of Bokaro Steel Plant (Steel Authority of India Limited) on a daily basis using elaborate menus and submenus. An observation also includes iamge(s) related to the obesrvation.
2. The bot then passes this observation to a Google Spreadsheet - one row corresponds to one observation. The bot also uploads the image(s) onto the Google Drive and then adds the link to that image as one cell of the row corresponding to that observation.

Benefits:-
1. These observations are a very rich source of data for us at Safety Department.
2. Earlier, WhatsApp was used for communicating such information which was very unorganized, and it was not possible to keep track of the observations.
3. Now with this bot, we have given structure to the observations so that they are centrally stored on cloud and can be accessed, analyzed and inference be drawn from the data and that too anywhere at any time.
4. Also, a lot of these observations require compliance from the concerned agency. Having a central repository of these observations makes it extremely quick to keep track and remind the concerned agencies of pending pointws against their head. This wasn't possible earlier.

Setup:-
1. The bot currently runs on pythonanywhere.com server and it uses a Flask Webhook API to react to incoming messages from telegram.
2. To use Google Drive API, a json file names credentials.json is required.
3. Also add the bot token for Telegram Bot and a secret key for API endpoint.
